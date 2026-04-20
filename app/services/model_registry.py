from pathlib import Path
from typing import Any, Protocol

from app.core.config import get_settings
from app.core.exceptions import ModelNotReadyError
from app.ml.artifacts import HeuristicModel, load_model_bundle
from app.ml.model_bundle import TrainedModelBundle


class PredictiveModel(Protocol):
    model_version: str

    def predict(self, features: dict[str, Any]) -> object:
        ...


class ModelRegistryService:
    def __init__(self, artifact_path: Path | None = None):
        settings = get_settings()
        self.artifact_path = artifact_path or settings.model_artifact
        self._active_model: PredictiveModel | None = None

    def get_active_model(self) -> PredictiveModel:
        if self._active_model is not None:
            return self._active_model

        if self.artifact_path.exists():
            self._active_model = load_model_bundle(self.artifact_path)
        else:
            self._active_model = HeuristicModel()
        return self._active_model

    def get_model_version(self) -> str:
        model = self.get_active_model()
        version = getattr(model, "model_version", None)
        if not version:
            raise ModelNotReadyError("Active model does not expose model_version metadata")
        return version

    def refresh(self) -> PredictiveModel:
        self._active_model = None
        return self.get_active_model()
