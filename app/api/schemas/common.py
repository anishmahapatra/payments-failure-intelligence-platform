from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: list[str] | list[dict] | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorResponse


class HealthDependencyStatus(BaseModel):
    postgres: str
    redis: str


class HealthResponse(BaseModel):
    status: str
    dependencies: HealthDependencyStatus

