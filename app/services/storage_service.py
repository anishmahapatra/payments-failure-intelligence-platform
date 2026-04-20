from sqlalchemy.orm import Session

from app.db.models import PaymentBatchJob


class StorageService:
    """DB-backed storage abstraction for local MVP batch payloads/results."""

    def __init__(self, db: Session):
        self.db = db

    def store_batch_request(self, job: PaymentBatchJob, payload: dict) -> PaymentBatchJob:
        job.request_payload = payload
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def store_batch_result(self, job: PaymentBatchJob, result: dict) -> PaymentBatchJob:
        job.result_payload = result
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def load_batch_result(self, job: PaymentBatchJob) -> dict | None:
        return job.result_payload

