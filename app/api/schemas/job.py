from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.payment import BatchJobSummary, PaymentScoreRequest


class BatchJobCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=8, max_length=128)
    payments: list[PaymentScoreRequest] = Field(min_length=1, max_length=500)


class BatchJobCreateResponse(BaseModel):
    job_id: str
    status: str
    submitted_at: datetime


class BatchJobStatusResponse(BaseModel):
    job_id: str
    status: str
    submitted_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    result: BatchJobSummary | None = None
    error_message: str | None = None

