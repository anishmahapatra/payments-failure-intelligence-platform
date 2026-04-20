from app.core.constants import JOB_STATUS_COMPLETED, JOB_STATUS_PROCESSING, JOB_STATUS_QUEUED
from app.services.job_service import VALID_TRANSITIONS, can_transition


def test_valid_job_state_transition_exists() -> None:
    assert can_transition(JOB_STATUS_QUEUED, JOB_STATUS_PROCESSING) is True
    assert JOB_STATUS_PROCESSING in VALID_TRANSITIONS[JOB_STATUS_QUEUED]


def test_completed_job_cannot_transition() -> None:
    assert VALID_TRANSITIONS[JOB_STATUS_COMPLETED] == set()
    assert can_transition(JOB_STATUS_COMPLETED, JOB_STATUS_QUEUED) is False
