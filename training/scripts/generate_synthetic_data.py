from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
TRAINING_DATA_PATH = BASE_DIR / "training" / "data" / "payment_events.csv"
FEATURE_REPO_DATA_PATH = BASE_DIR / "feature_repo" / "data" / "payment_features.parquet"

FAILURE_CLASSES = [
    "network_timeout",
    "gateway_decline",
    "terminal_issue",
    "fraud_or_risk_hold",
    "unknown",
]


def generate_synthetic_payments(num_rows: int = 5000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    channels = np.array(["card_present", "online", "kiosk", "mobile_wallet"])
    gateway_codes = np.array(["APPROVED", "DO_NOT_HONOR", "INSUFFICIENT_FUNDS", "GENERIC_DECLINE"])
    terminal_types = np.array(["smart_pos", "legacy_pos", "kiosk_pos", "self_checkout"])

    frame = pd.DataFrame(
        {
            "payment_id": [f"pay_{i:07d}" for i in range(num_rows)],
            "store_id": rng.choice([f"store_{i:03d}" for i in range(1, 61)], size=num_rows),
            "terminal_id": rng.choice([f"term_{i:04d}" for i in range(1, 401)], size=num_rows),
            "channel": rng.choice(channels, size=num_rows, p=[0.45, 0.25, 0.15, 0.15]),
            "amount": rng.gamma(shape=2.5, scale=24, size=num_rows).round(2),
            "tip_amount": rng.gamma(shape=1.3, scale=4, size=num_rows).round(2),
            "retry_count": rng.integers(0, 4, size=num_rows),
            "gateway_code": rng.choice(gateway_codes, size=num_rows, p=[0.74, 0.08, 0.12, 0.06]),
            "network_latency_ms": rng.integers(20, 2500, size=num_rows),
            "terminal_type": rng.choice(terminal_types, size=num_rows, p=[0.45, 0.2, 0.2, 0.15]),
            "hour_of_day": rng.integers(0, 24, size=num_rows),
            "day_of_week": rng.integers(0, 7, size=num_rows),
            "prior_store_failure_rate": rng.uniform(0.01, 0.22, size=num_rows).round(4),
            "prior_terminal_failure_rate": rng.uniform(0.01, 0.35, size=num_rows).round(4),
        }
    )
    base_time = datetime.now(timezone.utc)
    frame["event_timestamp"] = [
        base_time - timedelta(minutes=int(value))
        for value in rng.integers(0, 60 * 24, size=num_rows)
    ]
    frame["created_timestamp"] = frame["event_timestamp"]
    frame["tip_amount"] = frame[["tip_amount", "amount"]].min(axis=1)
    frame["peak_hour_flag"] = frame["hour_of_day"].isin([11, 12, 13, 18, 19, 20]).astype(int)
    frame["terminal_failure_rate_1h"] = frame["prior_terminal_failure_rate"]
    frame["store_failure_rate_1h"] = frame["prior_store_failure_rate"]
    frame["payment_amount_bucket"] = pd.cut(
        frame["amount"],
        bins=[0, 20, 75, 200, np.inf],
        labels=["small", "medium", "large", "enterprise"],
        include_lowest=True,
    ).astype(str)

    risk_signal = (
        frame["retry_count"] * 0.4
        + (frame["network_latency_ms"] / 900)
        + frame["prior_store_failure_rate"] * 2.0
        + frame["prior_terminal_failure_rate"] * 2.2
        + (frame["gateway_code"] != "APPROVED").astype(int) * 0.8
        + (frame["channel"].isin(["online", "mobile_wallet"])).astype(int) * 0.3
        + (frame["terminal_type"].isin(["legacy_pos", "self_checkout"])).astype(int) * 0.25
    )
    failure_probability = 1 / (1 + np.exp(-(risk_signal - 1.9)))
    frame["label_failure"] = rng.binomial(1, np.clip(failure_probability, 0.02, 0.95))

    def choose_failure_class(row: pd.Series) -> str:
        if row["label_failure"] == 0:
            return "unknown"
        if row["network_latency_ms"] > 1500:
            return "network_timeout"
        if row["gateway_code"] != "APPROVED":
            return "gateway_decline"
        if row["terminal_type"] in {"legacy_pos", "self_checkout"} and row["retry_count"] >= 2:
            return "terminal_issue"
        if row["amount"] > 250 and row["channel"] in {"online", "mobile_wallet"}:
            return "fraud_or_risk_hold"
        return rng.choice(FAILURE_CLASSES)

    frame["label_failure_class"] = frame.apply(choose_failure_class, axis=1)
    return frame


def main() -> None:
    dataset = generate_synthetic_payments()
    TRAINING_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    FEATURE_REPO_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(TRAINING_DATA_PATH, index=False)
    dataset.to_parquet(FEATURE_REPO_DATA_PATH, index=False)
    print(f"Wrote training data to {TRAINING_DATA_PATH}")
    print(f"Wrote feature repo data to {FEATURE_REPO_DATA_PATH}")


if __name__ == "__main__":
    main()
