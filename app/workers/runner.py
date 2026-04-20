import time

from pydantic import ValidationError

from app.api.schemas.payment import BatchPaymentRequest
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.models import BatchJob, JobStatus
from app.db.session import SessionLocal, initialize_database
from app.services.job_service import JobService
from app.services.payment_scoring import PaymentScoringService

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


def process_once() -> bool:
    db = SessionLocal()
    try:
        job_service = JobService(db)
        scoring_service = PaymentScoringService()
        job_id = job_service.get_next_job_id()
        if job_id is None:
            return False

        job = db.get(BatchJob, job_id)
        if job is None or job.status == JobStatus.completed:
            return True

        job_service.mark_processing(job)
        payload = BatchPaymentRequest.model_validate(job.payload)
        _, summary = scoring_service.score_batch(db=db, requests=payload.payments)
        job_service.mark_completed(job, summary.model_dump())
        logger.info("batch_job_completed", extra={"event": "batch_job_completed", "job_id": job.id})
        return True
    except ValidationError as exc:
        if job is not None:
            job_service.mark_failed(job, f"Payload validation failed: {exc}")
        logger.exception("batch_job_validation_failed", extra={"event": "batch_job_validation_failed"})
        return True
    except Exception as exc:
        if "job" in locals() and job is not None:
            if job.attempts >= settings.worker_max_attempts:
                job_service.mark_failed(job, str(exc))
            else:
                job_service.mark_for_retry(job, str(exc))
        logger.exception("batch_job_failed", extra={"event": "batch_job_failed"})
        return True
    finally:
        db.close()


def main() -> None:
    initialize_database()
    logger.info("worker_started", extra={"event": "worker_started"})
    while True:
        processed = process_once()
        if not processed:
            time.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    main()
