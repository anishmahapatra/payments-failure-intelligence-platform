from app.api.schemas.payment import FailureClass, RecommendedAction


def map_recommended_action(risk_score: float, failure_class: FailureClass) -> RecommendedAction:
    if risk_score >= 0.85 or failure_class == "fraud_or_risk_hold":
        return "manual_review"
    if failure_class == "network_timeout":
        return "retry_once"
    if failure_class == "gateway_decline":
        return "escalate_gateway"
    if failure_class == "terminal_issue":
        return "failover_terminal"
    return "no_action"

