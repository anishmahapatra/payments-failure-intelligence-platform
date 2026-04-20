from fastapi import APIRouter, Depends
from fastapi.responses import Response
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.schemas.common import HealthDependencyStatus, HealthResponse
from app.core.metrics import metrics_response
from app.db.session import get_db_session
from app.services.job_service import get_redis_client

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db_session)) -> HealthResponse:
    db.execute(text("SELECT 1"))
    redis_client: Redis = get_redis_client()
    redis_client.ping()
    return HealthResponse(
        status="ok",
        dependencies=HealthDependencyStatus(postgres="ok", redis="ok"),
    )


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return metrics_response()

