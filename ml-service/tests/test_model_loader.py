import pytest
import os
import tempfile
import joblib
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from app.model_loader import ModelManager, model_manager


class TestModelManager:
    @pytest.fixture(autouse=True)
    def reset_manager(self):
        model_manager._model = None
        model_manager._explainer = None
        model_manager._metadata = {}
        model_manager.model_version = "0.0.0"

    def test_initial_state_is_degraded(self):
        assert model_manager.is_loaded() is False
        assert model_manager.get_model() is None
        assert model_manager.get_explainer() is None
        assert model_manager.model_version == "0.0.0"

    def test_load_nonexistent_path_returns_degraded(self):
        model_manager.load("/nonexistent/path.joblib")
        assert model_manager.is_loaded() is False
        assert model_manager.model_version == "0.0.0"

    def test_load_valid_model(self):
        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            path = f.name
            model = RandomForestClassifier(n_estimators=10, random_state=42)
            model.fit(np.random.rand(50, 6), np.random.randint(0, 4, 50))
            joblib.dump({"model": model, "version": "2.0.0", "metadata": {"metrics": {}}}, path)

        try:
            mm = ModelManager()
            mm.load(path)
            assert mm.is_loaded() is True
            assert mm.get_model() is not None
            assert mm.model_version == "2.0.0"
        finally:
            os.unlink(path)

    def test_load_plain_model_assigns_default_version(self):
        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            path = f.name
            model = RandomForestClassifier(n_estimators=10, random_state=42)
            model.fit(np.random.rand(50, 6), np.random.randint(0, 4, 50))
            joblib.dump(model, path)

        try:
            mm = ModelManager()
            mm.load(path)
            assert mm.is_loaded() is True
            assert mm.model_version == "1.0.0"
        finally:
            os.unlink(path)

    def test_get_metadata_returns_empty_if_not_present(self):
        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            path = f.name
            joblib.dump({"model": None, "version": "1.0.0"}, path)

        try:
            mm = ModelManager()
            mm.load(path)
            assert mm.get_metadata() == {}
        finally:
            os.unlink(path)

    def test_get_category_order_from_model(self):
        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            path = f.name
            model = RandomForestClassifier(n_estimators=10, random_state=42)
            y = np.random.randint(0, 4, 50)
            model.fit(np.random.rand(50, 6), y)
            joblib.dump({"model": model, "version": "1.0.0"}, path)

        try:
            mm = ModelManager()
            mm.load(path)
            order = mm.get_category_order()
            assert len(order) == 4
        finally:
            os.unlink(path)
