# AWS Deployment Strategy

This repository is intentionally local-first in v1. The AWS materials here are starter documents and manifests for promoting the current Docker-based MVP without introducing Kubernetes or Terraform.

## Target topology

- API: container image in ECR, deployed with App Runner
- Worker: container image in ECR, deployed on ECS Fargate
- Database: Amazon RDS PostgreSQL
- Queue/cache: Amazon ElastiCache for Redis
- Artifacts/results: Amazon S3
- MLflow: keep the tracking server external or migrate tracking metadata to PostgreSQL with S3-backed artifacts
- Metrics/logs: start with CloudWatch logs and metrics; keep Prometheus/Grafana local for development only

## Deployment sequence

1. Build and push `api` and `worker` images to separate ECR repositories.
2. Provision RDS PostgreSQL and ElastiCache Redis.
3. Create an S3 bucket for trained model bundles and batch-result exports if the platform later externalizes them.
4. Deploy the API container to App Runner using the same environment variables used locally.
5. Deploy the worker container to ECS Fargate with the same database and Redis contract.
6. Move secrets into AWS Secrets Manager or SSM Parameter Store.
7. Decide whether MLflow remains a separate internal service or whether model bundles are promoted directly through S3 and deployment configuration.

## Notes

- Feast remains local-compatible in this MVP and is not yet wired to an AWS online feature store.
- No infrastructure-as-code is committed yet beyond starter manifests.
- The current runtime contract is PostgreSQL + Redis + model bundle artifact path; cloud automation should preserve that contract rather than change it.
