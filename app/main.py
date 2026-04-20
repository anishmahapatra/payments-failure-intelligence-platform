from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.payments import router as payments_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, get_logger
from app.core.metrics import ERROR_COUNTER, REQUEST_COUNTER, REQUEST_LATENCY
from app.db.session import initialize_database

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    logger.info("application_started", extra={"event": "application_started"})
    yield
    logger.info("application_stopped", extra={"event": "application_stopped"})


app = FastAPI(
    title="Payment Failure Intelligence Platform",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(payments_router)
app.include_router(jobs_router)
app.include_router(health_router)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method
    start = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        ERROR_COUNTER.labels(path=path, method=method, error_type="unhandled").inc()
        raise
    finally:
        duration = perf_counter() - start
        REQUEST_COUNTER.labels(path=path, method=method, status_code=str(status_code)).inc()
        REQUEST_LATENCY.labels(path=path, method=method).observe(duration)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    ERROR_COUNTER.labels(path="validation", method="request", error_type="validation").inc()
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed",
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    ERROR_COUNTER.labels(path="application", method="request", error_type=exc.code).inc()
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": [exc.message],
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", extra={"event": "unhandled_exception"})
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "Unexpected error while processing request",
                "details": [str(exc)],
            }
        },
    )
