from app.api.schemas.payment import FailureClass, RecommendedAction
from app.core.constants import (
    RECOMMENDATION_ESCALATE_GATEWAY,
    RECOMMENDATION_FAILOVER_TERMINAL,
    RECOMMENDATION_MANUAL_REVIEW,
    RECOMMENDATION_NO_ACTION,
    RECOMMENDATION_RETRY_ONCE,
)


def map_recommended_action(risk_score: float, failure_class: FailureClass) -> RecommendedAction:
    if risk_score >= 0.85 or failure_class == "fraud_or_risk_hold":
        return RECOMMENDATION_MANUAL_REVIEW
    if failure_class == "network_timeout":
        return RECOMMENDATION_RETRY_ONCE
    if failure_class == "gateway_decline":
        return RECOMMENDATION_ESCALATE_GATEWAY
    if failure_class == "terminal_issue":
        return RECOMMENDATION_FAILOVER_TERMINAL
    return RECOMMENDATION_NO_ACTION
