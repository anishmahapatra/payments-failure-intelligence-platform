from collections import Counter
from statistics import mean

from sqlalchemy.orm import Session

from app.api.schemas.payment import BatchJobSummary, PaymentScoreRequest, PaymentScoreResponse
from app.core.logging import get_logger
from app.db.models import ScoringRequestLog
from app.services.feature_lookup import FeatureLookupService
from app.services.model_registry import ModelRegistryService
from app.services.recommendations import map_recommended_action

logger = get_logger(__name__)


class PaymentScoringService:
    def __init__(self):
        self.feature_lookup = FeatureLookupService()
        self.model_registry = ModelRegistryService()

    def score_single(self, db: Session, request: PaymentScoreRequest) -> PaymentScoreResponse:
        features = self.feature_lookup.build_feature_vector(request)
        prediction = self.model_registry.get_active_model().predict(features)
        response = PaymentScoreResponse(
            payment_id=request.payment_id,
            risk_score=prediction.risk_score,
            predicted_failure_class=prediction.failure_class,
            recommended_action=map_recommended_action(
                prediction.risk_score,
                prediction.failure_class,
            ),
            model_version=prediction.model_version,
            reasons=prediction.reasons,
        )
        db.add(
            ScoringRequestLog(
                payment_id=request.payment_id,
                model_version=response.model_version,
                request_payload=request.model_dump(),
                response_payload=response.model_dump(),
            )
        )
        db.commit()
        logger.info(
            "payment_scored",
            extra={"event": "payment_scored", "payment_id": request.payment_id},
        )
        return response

    def score_batch(
        self,
        db: Session,
        requests: list[PaymentScoreRequest],
    ) -> tuple[list[PaymentScoreResponse], BatchJobSummary]:
        responses = [self.score_single(db=db, request=request) for request in requests]
        failure_classes = Counter(response.predicted_failure_class for response in responses)
        recommended_actions = Counter(response.recommended_action for response in responses)
        summary = BatchJobSummary(
            total_events=len(responses),
            high_risk_events=sum(response.risk_score >= 0.7 for response in responses),
            average_risk_score=round(mean(response.risk_score for response in responses), 4),
            failure_class_distribution=dict(failure_classes),
            recommended_action_distribution=dict(recommended_actions),
        )
        return responses, summary
