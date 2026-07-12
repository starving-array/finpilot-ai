import hashlib
import logging
import os
from pathlib import Path

import joblib
import numpy as np
import shap

from .config import settings

logger = logging.getLogger(__name__)

CATEGORY_ORDER = ["no-to-go", "non-disciplined", "yes-to-go", "disciplined"]


class ModelManager:
    def __init__(self):
        self._model = None
        self._regressor = None
        self._explainer = None
        self._metadata = {}
        self.model_version = "0.0.0"
        self._model_type = "unknown"

    def load(self, path: str | None = None):
        model_path = path or settings.model_path
        if not os.path.exists(model_path):
            logger.warning(f"Model not found at {model_path}. Running in degraded mode.")
            self._model = None
            self._explainer = None
            self.model_version = "0.0.0"
            return

        artifact = joblib.load(model_path)
        if isinstance(artifact, dict):
            self._model = artifact.get("model")
            self._regressor = artifact.get("regressor")
            self.model_version = artifact.get("version", "0.0.0")
            self._model_type = artifact.get("model_type", "unknown")
            self._metadata = artifact.get("metadata", {})
        else:
            self._model = artifact
            self._regressor = None
            self.model_version = "1.0.0"
            self._model_type = "legacy"
            self._metadata = {}

        if self._model is None:
            logger.warning("Model artifact contains no model object. Running in degraded mode.")
            self.model_version = "0.0.0"
            return

        if settings.model_checksum:
            with open(model_path, "rb") as f:
                actual_checksum = hashlib.sha256(f.read()).hexdigest()
            if actual_checksum != settings.model_checksum:
                raise ValueError(f"Model checksum mismatch: expected {settings.model_checksum}, got {actual_checksum}")
            logger.info(f"Model checksum verified: {actual_checksum[:16]}...")

        self._load_explainer()
        logger.info(f"Model v{self.model_version} loaded from {model_path}")

    def _load_explainer(self):
        try:
            self._explainer = shap.TreeExplainer(self._model)
            logger.info("SHAP TreeExplainer loaded")
        except Exception as e:
            logger.warning(f"SHAP explainer loading failed: {e}. Explanations will be unavailable.")
            self._explainer = None

    def is_loaded(self) -> bool:
        return self._model is not None

    def get_model(self):
        return self._model

    def get_explainer(self):
        return self._explainer

    def get_regressor(self):
        return self._regressor

    def get_model_type(self):
        return self._model_type

    def get_metadata(self):
        return self._metadata

    def get_category_order(self) -> list[str]:
        if hasattr(self._model, "classes_"):
            return list(self._model.classes_)
        return CATEGORY_ORDER


model_manager = ModelManager()


def load_model():
    model_manager.load()
