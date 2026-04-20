from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.job import BatchJobCreateRequest, BatchJobCreateResponse
from app.api.schemas.payment import PaymentScoreRequest, PaymentScoreResponse
from app.db.session import get_db_session
from app.services.batch_service import BatchService
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


@router.post("/payments/submit-batch", response_model=BatchJobCreateResponse, status_code=202)
def submit_batch(
    payload: BatchJobCreateRequest,
    db: Session = Depends(get_db_session),
) -> BatchJobCreateResponse:
    return BatchService(db).submit_batch(payload)


@router.get("/payments/config/model-version", include_in_schema=False)
def current_model_version() -> dict[str, str]:
    from app.services.model_registry import ModelRegistryService

    return {"model_version": ModelRegistryService().get_model_version()}
