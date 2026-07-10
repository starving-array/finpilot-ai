import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from app.explain import compute_shap


class MockExplainer:
    def __init__(self, n_features=6):
        self.expected_value = [0.5, 0.3, 0.1, 0.1]

    def shap_values(self, X):
        return np.random.randn(1, 6, 4)


class TestComputeShap:
    def test_none_explainer_returns_none(self):
        result = compute_shap(None, None, np.zeros((1, 6)), False)
        assert result is None

    def test_returns_dict_with_expected_keys(self):
        explainer = MockExplainer()
        model = MagicMock()
        model.predict.return_value = np.array([0])
        feature_vector = np.random.randn(1, 6).astype(np.float64)

        result = compute_shap(explainer, model, feature_vector, False, "retail")

        assert result is not None
        assert "shap_values" in result
        assert "base_value" in result
        assert "feature_ranking" in result
        assert "human_readable_summary" in result
        assert "traditional_signal_contribution" in result
        assert "alternative_signal_contribution" in result

    def test_blank_slate_changes_source(self):
        explainer = MockExplainer()
        model = MagicMock()
        model.predict.return_value = np.array([0])
        feature_vector = np.random.randn(1, 6).astype(np.float64)

        result = compute_shap(explainer, model, feature_vector, True, "retail")

        assert result is not None
        for rank in result["feature_ranking"]:
            assert "source" in rank

    def test_exception_returns_none(self):
        explainer = MagicMock()
        explainer.shap_values.side_effect = RuntimeError("SHAP failed")
        model = MagicMock()
        feature_vector = np.zeros((1, 6))

        result = compute_shap(explainer, model, feature_vector, False)

        assert result is None
