from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from app.api.schemas.payment import FailureClass


@dataclass
class ModelPrediction:
    risk_score: float
    failure_class: FailureClass
    reasons: list[str]
    model_version: str


@dataclass
class TrainedModelBundle:
    risk_model: Any
    failure_model: Any
    label_encoder: Any
    feature_columns: list[str]
    model_version: str
    top_feature_names: list[str]

    def predict(self, features: dict[str, Any]) -> ModelPrediction:
        frame = pd.DataFrame([features], columns=self.feature_columns)
        risk_probability = float(self.risk_model.predict_proba(frame)[0][1])
        failure_idx = int(self.failure_model.predict(frame)[0])
        failure_class = self.label_encoder.inverse_transform([failure_idx])[0]
        reasons = build_reason_hints(features, self.top_feature_names)
        return ModelPrediction(
            risk_score=round(risk_probability, 4),
            failure_class=failure_class,
            reasons=reasons,
            model_version=self.model_version,
        )

    def save(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, output_path)

    @classmethod
    def load(cls, path: Path) -> TrainedModelBundle:
        return joblib.load(path)


def build_reason_hints(features: dict[str, Any], top_feature_names: list[str]) -> list[str]:
    hints: list[str] = []
    if features.get("network_latency_ms", 0) > 1500:
        hints.append("High network latency observed")
    if features.get("retry_count", 0) >= 2:
        hints.append("Multiple retry attempts in session")
    if features.get("prior_terminal_failure_rate", 0) > 0.2:
        hints.append("Elevated terminal failure rate")
    if features.get("prior_store_failure_rate", 0) > 0.15:
        hints.append("Store failure rate is above normal baseline")
    if not hints:
        hints = [f"Top model features: {', '.join(top_feature_names[:3])}"]
    return hints
