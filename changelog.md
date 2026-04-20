# Changelog

This file tracks major implementation changes, why they were made, and how they were validated.

## 2026-04-20

### 1) Initial platform scaffold and runnable MVP

#### What changed
- Created production-style repository structure across:
  - `app/api/routes`, `app/api/schemas`, `app/core`, `app/services`, `app/db`, `app/workers`, `app/ml`
  - `training`, `feature_repo`, `infra/aws`, `config/prometheus`, `config/grafana`, `tests`
- Added local runtime and developer files:
  - `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`
  - `.env.example`, `.gitignore`, `Makefile`
  - `Dockerfile.api`, `Dockerfile.worker`, `docker-compose.yml`
- Implemented core API/worker/database/model/training paths:
  - Sync scoring endpoint
  - Async batch submission + polling
  - Worker queue consumption and job status updates
  - Synthetic data generation and model training with MLflow logging
  - Prometheus metrics and Grafana provisioning

#### Why
- Deliver a local-first, enterprise-style MVP instead of a notebook/demo layout.
- Ensure full vertical slice: data -> training -> model artifact -> inference -> async processing -> observability.

---

### 2) API/domain refactor for cleaner architecture

#### What changed
- Added shared cross-cutting modules:
  - `app/core/constants.py`
  - `app/core/exceptions.py`
- Added explicit shared/job schemas:
  - `app/api/schemas/common.py`
  - `app/api/schemas/job.py`
- Split routes:
  - Replaced `app/api/routes/system.py` with:
    - `app/api/routes/health.py`
    - `app/api/routes/jobs.py`
  - Kept scoring and batch submit in `app/api/routes/payments.py`
- Added service abstractions:
  - `app/services/model_registry.py`
  - `app/services/storage_service.py`
  - `app/services/batch_service.py`
- Centralized model loading through `ModelRegistryService`.
- Switched scoring response field to `predicted_failure_class` for consistency.

#### Why
- Keep routes thin and business logic in services.
- Avoid scattered model-loading logic and string constants.
- Make error handling explicit and API responses cleaner.

---

### 3) Batch job persistence model hardening

#### What changed
- Refined batch DB model to `PaymentBatchJob` in `app/db/models.py` with:
  - `id`, `job_id`, `status`, `request_payload`, `result_payload`,
  - `error_message`, `attempt_count`, `created_at`, `updated_at`, `completed_at`
- Updated job orchestration to use status transitions and retry behavior.
- Added `StorageService` DB-backed persistence hooks for request/result payloads.

#### Why
- Align stored job metadata with async workflow requirements.
- Preserve clear batch lifecycle and pollable status contract.

---

### 4) Local ops/bootstrap improvements

#### What changed
- Added bootstrap scripts:
  - `scripts/init_db.py`
  - `scripts/seed_local_data.py`
  - `scripts/wait_for_postgres.sh`
- Added/updated Make targets:
  - `make install`, `make init-db`, `make seed-data`, `make train`, `make up`, `make down`, `make test`, `make lint`
- Hardened compose startup sequencing with health checks for Postgres/Redis.

#### Why
- Reduce local setup friction.
- Ensure API/worker startup waits for dependencies.
- Keep dev workflow repeatable and scriptable.

---

### 5) Documentation improvements

#### What changed
- Updated `README.md` to match real implementation:
  - architecture, setup, training flow, sync/async flows, observability, AWS targets, limitations
- Added `feature_repo/README.md` with Feast usage and MVP limitations.
- Refined `infra/aws/README.md`, `infra/aws/apprunner-api.yaml`, `infra/aws/ecs-worker-task.json` to match runtime contract.
- Updated `docs/architecture.md` to reflect route/service boundaries.

#### Why
- Keep documentation truthful to code.
- Make platform design reviewable by engineering stakeholders.

---

### 6) Test coverage additions and quality checks

#### What changed
- Existing tests covered:
  - schema validation
  - recommendation mapping
  - job state transition contract
  - synthetic generator sanity
- Added idempotency behavior test:
  - `tests/test_job_service_idempotency.py`
- Ran and passed:
  - `make lint`
  - `make test` (`9 passed`)

#### Why
- Validate critical business rules and prevent regressions in async path semantics.

---

### 7) Live runtime fixes discovered during end-to-end smoke testing

#### What changed
- Fixed `python-json-logger` import path:
  - `app/core/logging.py` now imports `JsonFormatter` from `pythonjsonlogger.jsonlogger`.
- Removed startup DB-init race:
  - API and worker no longer both execute `scripts/init_db.py` on container startup.
  - Worker no longer calls `initialize_database()` on boot.
- Marked `scripts/wait_for_postgres.sh` executable.
- Improved idempotency behavior:
  - `JobService.create_job` returns `(job, created)` and does not enqueue duplicates.
  - `BatchService.submit_batch` only stores request payload on first create.

#### Why
- Resolve container crashes and startup instability found under real Docker execution.
- Enforce correct idempotency semantics under repeated client submissions.

---

### 8) Smoke test outcomes

#### Verified working
- `GET /health`
- `POST /payments/score-sync`
- `POST /payments/submit-batch`
- `GET /jobs/{job_id}` with `queued -> completed`
- `GET /metrics` includes API and batch counters
- Worker processes queued jobs and writes completed summary payload

#### Note
- In Codex execution, host `localhost` port access is sandbox-limited.
- Endpoint validation was run from inside the running `api` container and also validated from the host VS Code terminal.

