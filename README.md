# payments-failure-intelligence-platform

Production-style machine learning platform for payment failure intelligence in restaurant and retail payment operations.

## Why this exists

Payment operations teams need more than a notebook and a single model artifact. They need a service boundary for real-time inference, a queue-backed batch path for operational analysis, experiment tracking, reproducible training, observable runtime behavior, and a deployment path that can move from local Docker Compose to AWS without rewriting the project shape.

This repository provides that v1 foundation.

## Primary capabilities

- Real-time payment failure scoring and failure-class prediction
- Recommended action output for operators and support workflows
- Asynchronous batch analysis with job polling
- PostgreSQL-backed job/request tracking
- Redis-backed worker queue
- MLflow experiment tracking and model registration hooks
- Feast feature repository for operational payment features
- Prometheus metrics and Grafana dashboard provisioning
- AWS-ready deployment scaffolding without introducing Kubernetes in v1

## Architecture

```text
Client -> FastAPI API -> scoring service -> model registry -> model bundle / heuristic fallback
                    -> PostgreSQL request log
                    -> Redis queue for batch jobs

Redis queue -> Worker -> scoring service -> PostgreSQL job status + summary

Training scripts -> synthetic data -> XGBoost models -> MLflow + model bundle artifact
Feature repo -> Feast entity + feature views for operational payment signals
```

See [docs/architecture.md](/Users/anishmahapatra/Work/AI_Projects/payments-failure-intelligence-platform/docs/architecture.md) for the runtime layout.

## Repository structure

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
training/
  scripts/
feature_repo/
infra/
  aws/
config/
  prometheus/
  grafana/
docs/
tests/
```

## Core services

### API service

- `POST /payments/score-sync`
- `POST /payments/submit-batch`
- `GET /payments/jobs/{job_id}`
- `GET /health`
- `GET /metrics`

### Worker service

- Polls Redis for queued batch job ids
- Loads the persisted job payload from PostgreSQL
- Scores each payment event
- Writes aggregate job summary and status transitions back to PostgreSQL

### Database

- `batch_jobs`: queue-backed async job tracking
- `scoring_request_logs`: request/response audit trail for sync scoring

### Feature store

- Local-compatible Feast repository under [`feature_repo`](/Users/anishmahapatra/Work/AI_Projects/payments-failure-intelligence-platform/feature_repo)
- Operational payment features include retry count, network latency, store/terminal failure rates, peak hour flag, amount bucket, and channel
- v1 runtime does not require Feast online serving to start; the API uses a feature lookup abstraction backed by request payload data and keeps the Feast repo aligned for future online/offline evolution

## Local setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose

### Environment

Copy `.env.example` to `.env` if you want local overrides. The compose stack works with `.env.example` as committed defaults.

### Install dependencies locally

```bash
make install
source .venv/bin/activate
```

Equivalent manual setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

If you prefer `requirements.txt` installs:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
```

### Start the stack

```bash
make up
```

Services:

- API: [http://localhost:8000](http://localhost:8000)
- MLflow: [http://localhost:5000](http://localhost:5000)
- Prometheus: [http://localhost:9090](http://localhost:9090)
- Grafana: [http://localhost:3000](http://localhost:3000) with `admin/admin`

### Stop the stack

```bash
make down
```

## Training flow

Generate realistic synthetic training data:

```bash
make seed-data
```

Train and persist the baseline models:

```bash
make train
```

Training outputs:

- `training/data/payment_events.csv`
- `feature_repo/data/payment_features.parquet`
- `training/artifacts/model_bundle.joblib`
- `training/artifacts/metrics.joblib`
- MLflow run metadata and attempted registry registration

The runtime will use the trained model bundle when present. If no bundle exists yet, it falls back to a deterministic heuristic scorer so the system still runs locally.

## Inference flow

### Sync scoring

Request:

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

Response:

```json
{
  "payment_id": "pay_10001",
  "risk_score": 0.2841,
  "likely_failure_class": "unknown",
  "recommended_action": "no_action",
  "model_version": "heuristic-v1",
  "reasons": [
    "Top model features: retry_count, network_latency_ms, prior_terminal_failure_rate"
  ]
}
```

### Batch scoring

Submit:

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

Poll:

```bash
curl http://localhost:8000/jobs/<job_id>
```

Job response shape:

```json
{
  "job_id": "8bd4fbc0-8f10-41fc-98af-93b1f58b1661",
  "status": "completed",
  "submitted_at": "2026-04-20T09:15:00Z",
  "updated_at": "2026-04-20T09:15:04Z",
  "attempts": 1,
  "summary": {
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

## Observability

- Structured JSON logs for API and worker
- Prometheus metrics:
  - request count
  - request latency
  - error count
  - batch job count
  - queue depth
- Starter Grafana dashboard under [`config/grafana/dashboards/payment-platform-overview.json`](/Users/anishmahapatra/Work/AI_Projects/payments-failure-intelligence-platform/config/grafana/dashboards/payment-platform-overview.json)

## AWS deployment target

Starter deployment materials live in [`infra/aws`](/Users/anishmahapatra/Work/AI_Projects/payments-failure-intelligence-platform/infra/aws):

- App Runner starter manifest for the API
- ECS Fargate task definition starter for the worker
- deployment strategy document covering ECR, RDS, ElastiCache, and S3

This is deliberately scaffolding only. v1 avoids Terraform and Kubernetes so the application contract can settle first.

## Testing

Run:

```bash
make test
```

Current tests cover:

- request schema validation
- recommendation mapping logic
- job state transition contract
- synthetic data generator sanity

## Assumptions

- v1 accepts operational features in the request payload for online scoring instead of requiring live feature retrieval from Feast
- the local stack should remain runnable before a trained model exists, so a deterministic fallback scorer is included
- MLflow registration is attempted but non-fatal if the local registry backend is not fully configured
- batch job summaries are persisted in PostgreSQL; raw per-event batch outputs are not stored separately in v1
- AWS support in this repo is documentation and starter manifests, not full automation

## Roadmap

- Replace fallback online feature lookup with a Feast-backed online store path
- Add richer per-payment batch result persistence
- Add SHAP explanations behind the existing reason-generation abstraction
- Add CI pipelines and migration tooling
- Add cloud deployment automation after the runtime contract stabilizes
