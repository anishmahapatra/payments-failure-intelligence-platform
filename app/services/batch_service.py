from sqlalchemy.orm import Session

from app.api.schemas.job import (
    BatchJobCreateRequest,
    BatchJobCreateResponse,
    BatchJobStatusResponse,
)
from app.api.schemas.payment import BatchJobSummary
from app.core.constants import JOB_STATUS_COMPLETED
from app.core.exceptions import BatchProcessingError
from app.services.job_service import JobService
from app.services.payment_scoring import PaymentScoringService
from app.services.storage_service import StorageService


class BatchService:
    def __init__(self, db: Session):
        self.db = db
        self.job_service = JobService(db)
        self.storage_service = StorageService(db)
        self.scoring_service = PaymentScoringService()

    def submit_batch(self, payload: BatchJobCreateRequest) -> BatchJobCreateResponse:
        job = self.job_service.create_job(payload)
        self.storage_service.store_batch_request(job, payload.model_dump())
        return BatchJobCreateResponse(
            job_id=job.job_id,
            status=job.status,
            submitted_at=job.created_at,
        )

    def get_status(self, job_id: str) -> BatchJobStatusResponse:
        job = self.job_service.get_job_by_job_id(job_id)
        return BatchJobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            submitted_at=job.created_at,
            updated_at=job.updated_at,
            completed_at=job.completed_at,
            result=BatchJobSummary.model_validate(job.result_payload) if job.result_payload else None,
            error_message=job.error_message,
        )

    def process_next_job(self) -> bool:
        job_id = self.job_service.get_next_job_id()
        if job_id is None:
            return False

        job = self.job_service.get_job_by_job_id(job_id)
        if job.status == JOB_STATUS_COMPLETED:
            return True

        self.job_service.mark_processing(job)
        try:
            payload = BatchJobCreateRequest.model_validate(job.request_payload)
            _, summary = self.scoring_service.score_batch(db=self.db, requests=payload.payments)
            self.storage_service.store_batch_result(job, summary.model_dump())
            self.job_service.mark_completed(job)
            return True
        except Exception as exc:
            if job.attempt_count >= self.job_service.settings.worker_max_attempts:
                self.job_service.mark_failed(job, str(exc))
            else:
                self.job_service.mark_for_retry(job, str(exc))
            raise BatchProcessingError(str(exc)) from exc
