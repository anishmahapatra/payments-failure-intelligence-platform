# Architecture

The platform splits responsibilities across a synchronous API path, a Redis-backed asynchronous worker path, persistent job/request metadata in PostgreSQL, and a training stack that produces a reusable model bundle.

## Runtime

- `api`: FastAPI service for sync scoring, batch submission, health, and metrics
- `worker`: Redis queue consumer for asynchronous batch analysis
- `postgres`: job state and request log storage
- `redis`: queue transport
- `mlflow`: experiment tracking and model registration
- `prometheus` and `grafana`: local observability stack

## ML path

- `training/scripts/generate_synthetic_data.py` produces realistic payment event data
- `training/scripts/train_model.py` trains XGBoost models for risk and failure-class prediction
- `training/artifacts/model_bundle.joblib` is the runtime-loaded artifact
- `feature_repo/` contains Feast entity and feature view definitions for the same operational feature set

