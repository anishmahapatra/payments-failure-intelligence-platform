from datetime import timedelta

from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float32, Int64, String

payment_events = Entity(name="payment_event", join_keys=["payment_id"])

payment_source = FileSource(
    path="data/payment_features.parquet",
    event_timestamp_column="event_timestamp",
    created_timestamp_column="created_timestamp",
)

payment_operational_features = FeatureView(
    name="payment_operational_features",
    entities=[payment_events],
    ttl=timedelta(days=2),
    schema=[
        Field(name="retry_count", dtype=Int64),
        Field(name="network_latency_ms", dtype=Int64),
        Field(name="terminal_failure_rate_1h", dtype=Float32),
        Field(name="store_failure_rate_1h", dtype=Float32),
        Field(name="peak_hour_flag", dtype=Int64),
        Field(name="payment_amount_bucket", dtype=String),
        Field(name="channel", dtype=String),
    ],
    source=payment_source,
)

