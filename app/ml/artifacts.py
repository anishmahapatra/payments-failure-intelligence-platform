from typing import Any

from app.api.schemas.payment import FailureClass
from app.ml.model_bundle import ModelPrediction, TrainedModelBundle, build_reason_hints


class HeuristicModel:
    model_version = "heuristic-v1"

    def predict(self, features: dict[str, Any]) -> ModelPrediction:
        risk_components = [
            min(features["retry_count"] * 0.12, 0.35),
            min(features["network_latency_ms"] / 4000, 0.35),
            min(features["prior_store_failure_rate"] * 0.8, 0.2),
            min(features["prior_terminal_failure_rate"] * 0.8, 0.25),
        ]
        risk_score = max(0.01, min(0.99, round(sum(risk_components), 4)))

        if features["network_latency_ms"] > 1800:
            failure_class: FailureClass = "network_timeout"
        elif features["gateway_code"] in {"DO_NOT_HONOR", "INSUFFICIENT_FUNDS", "GENERIC_DECLINE"}:
            failure_class = "gateway_decline"
        elif features["terminal_type"] in {"legacy_pos", "self_checkout"} and features["retry_count"] >= 2:
            failure_class = "terminal_issue"
        elif features["amount"] > 250 and features["channel"] in {"online", "mobile_wallet"}:
            failure_class = "fraud_or_risk_hold"
        else:
            failure_class = "unknown"

        reasons = build_reason_hints(
            features,
            ["retry_count", "network_latency_ms", "prior_terminal_failure_rate"],
        )
        return ModelPrediction(
            risk_score=risk_score,
            failure_class=failure_class,
            reasons=reasons,
            model_version=self.model_version,
        )


def load_model_bundle(path) -> TrainedModelBundle:
    return TrainedModelBundle.load(path)
