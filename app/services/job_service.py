from datetime import datetime, timezone

from redis import Redis
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.constants import (
    DEFAULT_REDIS_QUEUE_NAME,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_PROCESSING,
    JOB_STATUS_QUEUED,
)
from app.core.exceptions import JobNotFoundError
from app.core.metrics import BATCH_JOB_COUNTER, QUEUE_DEPTH_GAUGE
from app.db.models import PaymentBatchJob

VALID_TRANSITIONS = {
    JOB_STATUS_QUEUED: {JOB_STATUS_PROCESSING, JOB_STATUS_FAILED},
    JOB_STATUS_PROCESSING: {JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, JOB_STATUS_QUEUED},
    JOB_STATUS_COMPLETED: set(),
    JOB_STATUS_FAILED: {JOB_STATUS_PROCESSING, JOB_STATUS_QUEUED},
}


def can_transition(current_status: str, new_status: str) -> bool:
    return new_status in VALID_TRANSITIONS[current_status]


def get_redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)


class JobService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.redis = get_redis_client()
        if not self.settings.redis_queue_name:
            self.settings.redis_queue_name = DEFAULT_REDIS_QUEUE_NAME

    def create_job(self, payload) -> PaymentBatchJob:
        existing = (
            self.db.query(PaymentBatchJob)
            .filter(PaymentBatchJob.idempotency_key == payload.idempotency_key)
            .one_or_none()
        )
        if existing is not None:
            return existing

        job = PaymentBatchJob(
            idempotency_key=payload.idempotency_key,
            request_payload=payload.model_dump(),
            status=JOB_STATUS_QUEUED,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        self.redis.rpush(self.settings.redis_queue_name, job.job_id)
        QUEUE_DEPTH_GAUGE.set(self.redis.llen(self.settings.redis_queue_name))
        BATCH_JOB_COUNTER.labels(status=JOB_STATUS_QUEUED).inc()
        return job

    def get_next_job_id(self) -> str | None:
        item = self.redis.blpop(self.settings.redis_queue_name, timeout=self.settings.worker_poll_interval_seconds)
        QUEUE_DEPTH_GAUGE.set(self.redis.llen(self.settings.redis_queue_name))
        if item is None:
            return None
        _, job_id = item
        return job_id

    def get_job_by_job_id(self, job_id: str) -> PaymentBatchJob:
        job = (
            self.db.query(PaymentBatchJob)
            .filter(PaymentBatchJob.job_id == job_id)
            .one_or_none()
        )
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")
        return job

    def transition_job_status(self, job: PaymentBatchJob, new_status: str) -> PaymentBatchJob:
        if not can_transition(job.status, new_status):
            raise ValueError(f"Invalid status transition from {job.status} to {new_status}")
        job.status = new_status
        job.updated_at = datetime.now(timezone.utc)
        if new_status == JOB_STATUS_COMPLETED:
            job.completed_at = datetime.now(timezone.utc)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        BATCH_JOB_COUNTER.labels(status=new_status).inc()
        return job

    def mark_processing(self, job: PaymentBatchJob) -> PaymentBatchJob:
        job.attempt_count += 1
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return self.transition_job_status(job, JOB_STATUS_PROCESSING)

    def mark_completed(self, job: PaymentBatchJob) -> PaymentBatchJob:
        job.error_message = None
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return self.transition_job_status(job, JOB_STATUS_COMPLETED)

    def mark_failed(self, job: PaymentBatchJob, error_message: str) -> PaymentBatchJob:
        job.error_message = error_message
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return self.transition_job_status(job, JOB_STATUS_FAILED)

    def mark_for_retry(self, job: PaymentBatchJob, error_message: str) -> PaymentBatchJob:
        job.status = JOB_STATUS_QUEUED
        job.error_message = error_message
        job.updated_at = datetime.now(timezone.utc)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        self.redis.rpush(self.settings.redis_queue_name, job.job_id)
        QUEUE_DEPTH_GAUGE.set(self.redis.llen(self.settings.redis_queue_name))
        BATCH_JOB_COUNTER.labels(status=JOB_STATUS_QUEUED).inc()
        return job
