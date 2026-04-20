from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.payment import (
    BatchJobResponse,
    BatchPaymentRequest,
    JobStatusResponse,
    PaymentScoreRequest,
    PaymentScoreResponse,
)
from app.core.config import get_settings
from app.core.metrics import BATCH_JOB_COUNTER
from app.db.models import BatchJob
from app.db.session import get_db_session
from app.services.job_service import JobService
from app.services.payment_scoring import PaymentScoringService

router = APIRouter(tags=["payments"])


def get_scoring_service() -> PaymentScoringService:
    return PaymentScoringService()


@router.post("/payments/score-sync", response_model=PaymentScoreResponse)
def score_payment(
    payload: PaymentScoreRequest,
    db: Session = Depends(get_db_session),
    scoring_service: PaymentScoringService = Depends(get_scoring_service),
) -> PaymentScoreResponse:
    return scoring_service.score_single(db=db, request=payload)


@router.post("/payments/submit-batch", response_model=BatchJobResponse, status_code=202)
def submit_batch(
    payload: BatchPaymentRequest,
    db: Session = Depends(get_db_session),
) -> BatchJobResponse:
    job_service = JobService(db)
    batch_job = job_service.create_job(payload)
    BATCH_JOB_COUNTER.labels(status="queued").inc()
    return BatchJobResponse(job_id=batch_job.id, status=batch_job.status.value, submitted_at=batch_job.created_at)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str, db: Session = Depends(get_db_session)) -> JobStatusResponse:
    job = db.get(BatchJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        submitted_at=job.created_at,
        updated_at=job.updated_at,
        attempts=job.attempts,
        summary=job.summary,
        error_message=job.error_message,
    )


@router.get("/payments/config/model-version", include_in_schema=False)
def current_model_version() -> dict[str, str]:
    settings = get_settings()
    return {"model_version": settings.model_version}
