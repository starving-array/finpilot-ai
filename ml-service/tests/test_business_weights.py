import pytest
from app.business_weights import get_weights, apply_signal_weights


class TestGetWeights:
    def test_returns_retail_weights(self):
        weights = get_weights("retail")
        assert "gst" in weights
        assert "epfo" in weights
        assert "electricity" in weights
        assert "water" in weights
        assert "fuel" in weights
        assert weights["gst"] == 1.2

    def test_returns_manufacturing_weights(self):
        weights = get_weights("manufacturing")
        assert weights["electricity"] == 1.4
        assert weights["fuel"] == 0.4

    def test_returns_logistics_weights(self):
        weights = get_weights("logistics")
        assert weights["fuel"] == 1.6

    def test_unknown_type_returns_uniform(self):
        weights = get_weights("unknown")
        for k in ["gst", "epfo", "electricity", "water", "fuel"]:
            assert weights[k] == 1.0


class TestApplySignalWeights:
    def test_single_signal_weighted_correctly(self):
        result = apply_signal_weights(
            {"gst": 0.9},
            "retail",
        )
        assert result["gst"] == pytest.approx(0.9, rel=1e-9)

    def test_multiple_signals_sum_to_total_weight(self):
        result = apply_signal_weights(
            {"gst": 0.9, "epfo": 0.8},
            "retail",
        )
        gst_exp = 0.9 * 1.2 / (1.2 + 1.1)
        epfo_exp = 0.8 * 1.1 / (1.2 + 1.1)
        assert result["gst"] == pytest.approx(gst_exp, rel=1e-4)
        assert result["epfo"] == pytest.approx(epfo_exp, rel=1e-4)

    def test_unknown_business_type_uses_uniform(self):
        result = apply_signal_weights(
            {"gst": 1.0, "epfo": 1.0},
            "unknown",
        )
        total = sum(result.values())
        assert abs(total - 1.0) < 0.01

    def test_none_values_are_skipped(self):
        result = apply_signal_weights(
            {"gst": 0.9, "epfo": None},
            "retail",
        )
        assert "epfo" not in result
        assert "gst" in result
