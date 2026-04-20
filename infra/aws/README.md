# AWS Deployment Strategy

This repository is intentionally local-first in v1. AWS scaffolding is included to show the deployment path without introducing Kubernetes or Terraform before the platform shape is stable.

## Target topology

- API: container image in ECR, deployed with App Runner
- Worker: container image in ECR, deployed on ECS Fargate
- Database: Amazon RDS PostgreSQL
- Queue/cache: Amazon ElastiCache for Redis
- Artifacts/results: Amazon S3
- Metrics: Prometheus/Grafana replaced by managed alternatives later, or retained on ECS

## Deployment sequence

1. Build and push `api` and `worker` images to ECR.
2. Provision RDS PostgreSQL and ElastiCache Redis.
3. Create an S3 bucket for ML artifacts, batch summaries, and model bundles.
4. Deploy the API container to App Runner with the same environment contract used in `.env.example`.
5. Deploy the worker container to ECS Fargate with autoscaling based on queue depth or CPU.
6. Point MLflow artifact storage at S3 and keep the tracking backend in PostgreSQL.
7. Move secrets into AWS Secrets Manager or SSM Parameter Store.

## Notes

- Feast can continue as a local-compatible repo in v1 and later move to an offline/online store pair.
- No infrastructure-as-code is committed yet beyond starter manifests. Final automation should be added only after the runtime contract settles.
- CloudWatch metrics/logs are the most practical first operational step before introducing a larger observability stack.

