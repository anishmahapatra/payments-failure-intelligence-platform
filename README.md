# payments-failure-intelligence-platform

Production-style payment failure intelligence MVP for restaurant and retail payment operations. The repository includes a FastAPI scoring API, a Redis-backed batch worker, PostgreSQL job tracking, local MLflow training flow, Feast feature definitions, and Docker Compose for local-first execution.

## Project overview

The platform supports two operational paths:

- real-time sync scoring for a single payment attempt
- asynchronous batch scoring with job submission and polling

Given payment and operational metadata, the system returns:

- `risk_score`
- `predicted_failure_class`
- `recommended_action`
- `model_version`

## Current architecture

```text
Client
  -> FastAPI API
      -> FeatureLookupService
      -> ModelRegistryService
      -> PaymentScoringService
      -> PostgreSQL scoring_request_logs

Client
  -> POST /payments/submit-batch
      -> BatchService
      -> PostgreSQL payment_batch_jobs
      -> Redis queue

Worker
  -> Redis queue
  -> BatchService
  -> PaymentScoringService
  -> PostgreSQL payment_batch_jobs result/status updates

Training
  -> synthetic data generator
  -> XGBoost training pipeline
  -> MLflow run logging
  -> local model bundle artifact
```

See [docs/architecture.md](/Users/anishmahapatra/Work/AI_Projects/payments-failure-intelligence-platform/docs/architecture.md).

## Repo structure

```text
app/
  api/
    routes/
    schemas/
  core/
  db/
  ml/
  services/
  workers/
config/
docs/
feature_repo/
infra/aws/
scripts/
tests/
training/
```

## Local run instructions

### Python setup

```bash
make install
source .venv/bin/activate
```

Alternative:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
```

### Environment

Use `.env.example` as the default local contract. Copy it to `.env` only if you need overrides.

### Initialize local assets

```bash
make init-db
make seed-data
make train
```

### Start the local stack

```bash
make up
```

Exposed services:

- API: [http://localhost:8000](http://localhost:8000)
- MLflow: [http://localhost:5000](http://localhost:5000)
- Prometheus: [http://localhost:9090](http://localhost:9090)
- Grafana: [http://localhost:3000](http://localhost:3000)

### Stop the local stack

```bash
make down
```

## Training flow

Generate local synthetic payment data:

```bash
make seed-data
```

Train the baseline models:

```bash
make train
```

Artifacts produced:

- `training/data/payment_events.csv`
- `feature_repo/data/payment_features.parquet`
- `training/artifacts/model_bundle.joblib`
- `training/artifacts/metrics.joblib`

If the model artifact does not exist yet, inference falls back to a deterministic heuristic model so the local MVP still starts.

## Sync scoring flow

Endpoint:

- `POST /payments/score-sync`

Example:

```bash
curl -X POST http://localhost:8000/payments/score-sync \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "pay_10001",
    "store_id": "store_014",
    "terminal_id": "term_0088",
    "channel": "card_present",
    "amount": 48.25,
    "tip_amount": 7.50,
    "retry_count": 1,
    "gateway_code": "APPROVED",
    "network_latency_ms": 240,
    "terminal_type": "smart_pos",
    "hour_of_day": 12,
    "day_of_week": 5,
    "prior_store_failure_rate": 0.07,
    "prior_terminal_failure_rate": 0.11
  }'
```

Response shape:

```json
{
  "payment_id": "pay_10001",
  "risk_score": 0.2841,
  "predicted_failure_class": "unknown",
  "recommended_action": "no_action",
  "model_version": "heuristic-v1",
  "reasons": [
    "Top model features: retry_count, network_latency_ms, prior_terminal_failure_rate"
  ]
}
```

## Async batch flow

Submit a batch job:

```bash
curl -X POST http://localhost:8000/payments/submit-batch \
  -H "Content-Type: application/json" \
  -d '{
    "idempotency_key": "batch-20260420-001",
    "payments": [
      {
        "payment_id": "pay_20001",
        "store_id": "store_021",
        "terminal_id": "term_0101",
        "channel": "online",
        "amount": 182.10,
        "tip_amount": 0,
        "retry_count": 2,
        "gateway_code": "GENERIC_DECLINE",
        "network_latency_ms": 1900,
        "terminal_type": "smart_pos",
        "hour_of_day": 19,
        "day_of_week": 4,
        "prior_store_failure_rate": 0.10,
        "prior_terminal_failure_rate": 0.15
      }
    ]
  }'
```

Poll the job:

```bash
curl http://localhost:8000/jobs/<job_id>
```

Response shape:

```json
{
  "job_id": "8bd4fbc0-8f10-41fc-98af-93b1f58b1661",
  "status": "completed",
  "submitted_at": "2026-04-20T09:15:00Z",
  "updated_at": "2026-04-20T09:15:04Z",
  "completed_at": "2026-04-20T09:15:04Z",
  "result": {
    "total_events": 1,
    "high_risk_events": 1,
    "average_risk_score": 0.88,
    "failure_class_distribution": {
      "network_timeout": 1
    },
    "recommended_action_distribution": {
      "manual_review": 1
    }
  },
  "error_message": null
}
```

Job statuses used by the platform:

- `queued`
- `processing`
- `completed`
- `failed`

## Observability

- `GET /health`
- `GET /metrics`
- structured JSON logging for API and worker
- Prometheus metrics for request count, request latency, error count, queue depth, batch job state counts, and worker batch outcomes
- starter Grafana dashboard in [config/grafana/dashboards/payment-platform-overview.json](/Users/anishmahapatra/Work/AI_Projects/payments-failure-intelligence-platform/config/grafana/dashboards/payment-platform-overview.json)

## AWS deployment target

Starter materials live in [infra/aws](/Users/anishmahapatra/Work/AI_Projects/payments-failure-intelligence-platform/infra/aws):

- API -> AWS App Runner
- worker -> ECS Fargate
- PostgreSQL -> RDS PostgreSQL
- Redis -> ElastiCache
- artifacts/results -> S3

This repo does not include Terraform or Kubernetes in v1.

## Known limitations

- Feast is documented and feature-aligned, but the online scoring path still builds features directly from the request payload for local simplicity
- batch results currently store summarized output, not full per-event persisted results
- MLflow registration is best-effort and local-first
- database schema management uses `create_all` rather than a migration tool in this MVP

## Next steps

- add schema migrations
- add richer batch result persistence/export
- add SHAP or similar explanation support behind the current reasoning abstraction
- add CI checks and container smoke tests
- add cloud deployment automation once the runtime contract is stable
