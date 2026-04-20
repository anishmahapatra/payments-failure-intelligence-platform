from datetime import datetime, timezone

from redis import Redis
from sqlalchemy.orm import Session

from app.api.schemas.payment import BatchPaymentRequest
from app.core.config import get_settings
from app.core.metrics import BATCH_JOB_COUNTER, QUEUE_DEPTH_GAUGE
from app.db.models import BatchJob, JobStatus

VALID_TRANSITIONS = {
    JobStatus.queued: {JobStatus.processing, JobStatus.failed},
    JobStatus.processing: {JobStatus.completed, JobStatus.failed},
    JobStatus.completed: set(),
    JobStatus.failed: {JobStatus.processing},
}


def can_transition(current_status: JobStatus, new_status: JobStatus) -> bool:
    return new_status in VALID_TRANSITIONS[current_status]


def get_redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)


class JobService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.redis = get_redis_client()

    def create_job(self, payload: BatchPaymentRequest) -> BatchJob:
        existing = (
            self.db.query(BatchJob)
            .filter(BatchJob.idempotency_key == payload.idempotency_key)
            .one_or_none()
        )
        if existing is not None:
            return existing

        job = BatchJob(
            idempotency_key=payload.idempotency_key,
            payload=payload.model_dump(),
            status=JobStatus.queued,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        self.redis.rpush(self.settings.redis_queue_name, job.id)
        QUEUE_DEPTH_GAUGE.set(self.redis.llen(self.settings.redis_queue_name))
        return job

    def get_next_job_id(self) -> str | None:
        item = self.redis.blpop(self.settings.redis_queue_name, timeout=self.settings.worker_poll_interval_seconds)
        QUEUE_DEPTH_GAUGE.set(self.redis.llen(self.settings.redis_queue_name))
        if item is None:
            return None
        _, job_id = item
        return job_id

    def transition_job_status(self, job: BatchJob, new_status: JobStatus) -> BatchJob:
        if not can_transition(job.status, new_status):
            raise ValueError(f"Invalid status transition from {job.status.value} to {new_status.value}")
        job.status = new_status
        job.updated_at = datetime.now(timezone.utc)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        BATCH_JOB_COUNTER.labels(status=new_status.value).inc()
        return job

    def mark_processing(self, job: BatchJob) -> BatchJob:
        job.attempts += 1
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return self.transition_job_status(job, JobStatus.processing)

    def mark_completed(self, job: BatchJob, summary: dict) -> BatchJob:
        job.summary = summary
        job.error_message = None
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return self.transition_job_status(job, JobStatus.completed)

    def mark_failed(self, job: BatchJob, error_message: str) -> BatchJob:
        job.error_message = error_message
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return self.transition_job_status(job, JobStatus.failed)

    def mark_for_retry(self, job: BatchJob, error_message: str) -> BatchJob:
        job.status = JobStatus.queued
        job.error_message = error_message
        job.updated_at = datetime.now(timezone.utc)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        self.redis.rpush(self.settings.redis_queue_name, job.id)
        QUEUE_DEPTH_GAUGE.set(self.redis.llen(self.settings.redis_queue_name))
        return job
