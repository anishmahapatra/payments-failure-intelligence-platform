from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.job import BatchJobStatusResponse
from app.db.session import get_db_session
from app.services.batch_service import BatchService

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=BatchJobStatusResponse)
def get_job(job_id: str, db: Session = Depends(get_db_session)) -> BatchJobStatusResponse:
    return BatchService(db).get_status(job_id)

