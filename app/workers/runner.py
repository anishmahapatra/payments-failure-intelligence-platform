import time

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.metrics import WORKER_BATCH_COUNTER
from app.db.session import SessionLocal
from app.services.batch_service import BatchService

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


def process_once() -> bool:
    db = SessionLocal()
    try:
        processed = BatchService(db).process_next_job()
        if processed:
            WORKER_BATCH_COUNTER.labels(outcome="processed").inc()
        return processed
    except Exception as exc:
        WORKER_BATCH_COUNTER.labels(outcome="failed").inc()
        logger.exception("batch_job_failed", extra={"event": "batch_job_failed", "error": str(exc)})
        return True
    finally:
        db.close()


def main() -> None:
    logger.info("worker_started", extra={"event": "worker_started"})
    while True:
        processed = process_once()
        if not processed:
            time.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    main()
