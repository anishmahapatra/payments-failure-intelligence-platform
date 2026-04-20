from app.db.models import JobStatus
from app.services.job_service import VALID_TRANSITIONS, can_transition


def test_valid_job_state_transition_exists() -> None:
    assert can_transition(JobStatus.queued, JobStatus.processing) is True
    assert JobStatus.processing in VALID_TRANSITIONS[JobStatus.queued]


def test_completed_job_cannot_transition() -> None:
    assert VALID_TRANSITIONS[JobStatus.completed] == set()
    assert can_transition(JobStatus.completed, JobStatus.failed) is False
