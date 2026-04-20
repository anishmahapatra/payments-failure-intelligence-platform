from app.services.recommendations import map_recommended_action


def test_network_timeout_maps_to_retry_once() -> None:
    assert map_recommended_action(0.62, "network_timeout") == "retry_once"


def test_high_risk_maps_to_manual_review() -> None:
    assert map_recommended_action(0.92, "unknown") == "manual_review"

