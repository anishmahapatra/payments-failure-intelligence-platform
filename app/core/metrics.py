from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUEST_COUNTER = Counter(
    "payment_api_requests_total",
    "Count of API requests",
    ["path", "method", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "payment_api_request_latency_seconds",
    "API request latency",
    ["path", "method"],
)
ERROR_COUNTER = Counter(
    "payment_api_errors_total",
    "Count of API errors",
    ["path", "method", "error_type"],
)
BATCH_JOB_COUNTER = Counter(
    "payment_batch_jobs_total",
    "Count of batch jobs by state",
    ["status"],
)
WORKER_BATCH_COUNTER = Counter(
    "payment_worker_batch_jobs_total",
    "Count of worker batch processing outcomes",
    ["outcome"],
)
QUEUE_DEPTH_GAUGE = Gauge("payment_batch_queue_depth", "Current Redis queue depth")


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
