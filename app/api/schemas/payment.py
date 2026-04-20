from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

FailureClass = Literal[
    "network_timeout",
    "gateway_decline",
    "terminal_issue",
    "fraud_or_risk_hold",
    "unknown",
]

RecommendedAction = Literal[
    "retry_once",
    "failover_terminal",
    "escalate_gateway",
    "manual_review",
    "no_action",
]

Channel = Literal["card_present", "online", "kiosk", "mobile_wallet"]


class PaymentScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_id: str = Field(min_length=4, max_length=64)
    store_id: str = Field(min_length=2, max_length=32)
    terminal_id: str = Field(min_length=2, max_length=32)
    channel: Channel
    amount: float = Field(gt=0)
    tip_amount: float = Field(ge=0, default=0)
    retry_count: int = Field(ge=0, le=10)
    gateway_code: str = Field(min_length=2, max_length=32)
    network_latency_ms: int = Field(ge=0, le=10000)
    terminal_type: str = Field(min_length=2, max_length=32)
    hour_of_day: int = Field(ge=0, le=23)
    day_of_week: int = Field(ge=0, le=6)
    prior_store_failure_rate: float = Field(ge=0, le=1)
    prior_terminal_failure_rate: float = Field(ge=0, le=1)

    @field_validator("tip_amount")
    @classmethod
    def tip_not_greater_than_amount(cls, value: float, info) -> float:
        amount = info.data.get("amount")
        if amount is not None and value > amount:
            raise ValueError("tip_amount must not exceed amount")
        return value


class PaymentScoreResponse(BaseModel):
    payment_id: str
    risk_score: float
    predicted_failure_class: FailureClass
    recommended_action: RecommendedAction
    model_version: str
    reasons: list[str]


class BatchJobSummary(BaseModel):
    total_events: int
    high_risk_events: int
    average_risk_score: float
    failure_class_distribution: dict[str, int]
    recommended_action_distribution: dict[str, int]
