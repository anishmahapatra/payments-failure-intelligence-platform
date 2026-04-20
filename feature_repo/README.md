# Feast Feature Repository

This repository defines the local Feast feature contract used by the payment failure intelligence platform.

## Entity

- `payment_event`
  - join key: `payment_id`

## Features

- `retry_count`
- `network_latency_ms`
- `terminal_failure_rate_1h`
- `store_failure_rate_1h`
- `peak_hour_flag`
- `payment_amount_bucket`
- `channel`

## Local MVP mode

The project keeps Feast in local-compatible mode for v1:

- feature definitions live in this folder
- offline feature data is generated into `feature_repo/data/payment_features.parquet`
- the runtime API does not depend on a live Feast online store to start

## Training usage

The synthetic data generator writes a feature-aligned parquet file that mirrors the same operational fields used by model training.

## Inference usage

Inference currently uses a feature lookup abstraction that builds a feature vector from request payload fields and derived values such as `peak_hour_flag` and `payment_amount_bucket`.

This keeps the runtime path simple while preserving a defensible Feast contract for future online feature serving.

## MVP limitations

- no live Feast online retrieval on the scoring path
- no materialization workflow beyond local generated data
- feature definitions are intentionally narrow and tied to the current payment-risk use case

