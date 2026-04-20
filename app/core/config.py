from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import DEFAULT_REDIS_QUEUE_NAME


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://payment_user:payment_pass@localhost:5432/payment_intelligence"
    redis_url: str = "redis://localhost:6379/0"
    redis_queue_name: str = DEFAULT_REDIS_QUEUE_NAME
    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_model_name: str = "payment-failure-intelligence"
    model_artifact_path: str = "training/artifacts/model_bundle.joblib"
    model_version: str = "heuristic-v1"
    prometheus_enabled: bool = True
    feast_repo_path: str = "feature_repo"
    use_feast_online_lookup: bool = False
    worker_poll_interval_seconds: int = 2
    worker_max_attempts: int = 3

    @property
    def model_artifact(self) -> Path:
        return Path(self.model_artifact_path)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
