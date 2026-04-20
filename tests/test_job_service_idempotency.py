from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.schemas.job import BatchJobCreateRequest
from app.db.base import Base
from app.services.job_service import JobService


class FakeRedis:
    def __init__(self) -> None:
        self.items: list[str] = []

    def rpush(self, _: str, value: str) -> None:
        self.items.append(value)

    def blpop(self, _: str, timeout: int = 0):  # noqa: ARG002
        if not self.items:
            return None
        return ("q", self.items.pop(0))

    def llen(self, _: str) -> int:
        return len(self.items)


def build_payload(idempotency_key: str) -> BatchJobCreateRequest:
    return BatchJobCreateRequest(
        idempotency_key=idempotency_key,
        payments=[
            {
                "payment_id": "pay_t_1",
                "store_id": "store_01",
                "terminal_id": "term_01",
                "channel": "card_present",
                "amount": 20.0,
                "tip_amount": 2.0,
                "retry_count": 1,
                "gateway_code": "APPROVED",
                "network_latency_ms": 100,
                "terminal_type": "smart_pos",
                "hour_of_day": 10,
                "day_of_week": 2,
                "prior_store_failure_rate": 0.05,
                "prior_terminal_failure_rate": 0.07,
            }
        ],
    )


def test_create_job_is_idempotent(monkeypatch) -> None:
    fake_redis = FakeRedis()
    monkeypatch.setattr("app.services.job_service.get_redis_client", lambda: fake_redis)

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, class_=Session)

    with SessionLocal() as db:
        service = JobService(db)
        payload = build_payload("idem-key-1234")

        first_job, first_created = service.create_job(payload)
        second_job, second_created = service.create_job(payload)

        assert first_created is True
        assert second_created is False
        assert first_job.job_id == second_job.job_id
        assert len(fake_redis.items) == 1
