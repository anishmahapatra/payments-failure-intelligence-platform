import pytest
from pydantic import ValidationError

from app.api.schemas.payment import PaymentScoreRequest


def test_payment_score_request_accepts_valid_payload() -> None:
    payload = PaymentScoreRequest(
        payment_id="pay_1001",
        store_id="store_01",
        terminal_id="term_01",
        channel="card_present",
        amount=42.5,
        tip_amount=5.0,
        retry_count=1,
        gateway_code="APPROVED",
        network_latency_ms=120,
        terminal_type="smart_pos",
        hour_of_day=12,
        day_of_week=3,
        prior_store_failure_rate=0.05,
        prior_terminal_failure_rate=0.08,
    )
    assert payload.payment_id == "pay_1001"


def test_payment_score_request_rejects_tip_above_amount() -> None:
    with pytest.raises(ValidationError):
        PaymentScoreRequest(
            payment_id="pay_1001",
            store_id="store_01",
            terminal_id="term_01",
            channel="card_present",
            amount=10.0,
            tip_amount=11.0,
            retry_count=0,
            gateway_code="APPROVED",
            network_latency_ms=120,
            terminal_type="smart_pos",
            hour_of_day=12,
            day_of_week=3,
            prior_store_failure_rate=0.05,
            prior_terminal_failure_rate=0.08,
        )

