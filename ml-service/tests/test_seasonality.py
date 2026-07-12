import pytest
from app.seasonality import get_volatility_flag


class TestGetVolatilityFlag:
    def test_low_value_returns_normal(self):
        result = get_volatility_flag(0.1, "fuel_monthly_spend_avg", "retail")
        assert result["flag"] == "normal"

    def test_high_value_returns_elevated(self):
        result = get_volatility_flag(0.8, "fuel_monthly_spend_avg", "retail")
        assert result["flag"] == "elevated"

    def test_logistics_fuel_volatility_within_expected_range(self):
        result = get_volatility_flag(0.4, "fuel_monthly_spend_avg", "logistics")
        assert result["flag"] == "normal"

    def test_manufacturing_electricity_within_expected_range(self):
        result = get_volatility_flag(0.3, "electricity_monthly_units_avg", "manufacturing")
        assert result["flag"] == "normal"

    def test_logistics_fuel_above_expected_range(self):
        result = get_volatility_flag(0.6, "fuel_monthly_spend_avg", "logistics")
        assert result["flag"] == "elevated"

    def test_high_value_includes_expected_range(self):
        result = get_volatility_flag(0.8, "fuel_monthly_spend_avg", "retail")
        assert "expected_range" in result
        assert "lo" in result["expected_range"]
        assert "hi" in result["expected_range"]

    def test_high_value_includes_actual_value(self):
        result = get_volatility_flag(0.8, "fuel_monthly_spend_avg", "retail")
        assert result["value"] == 0.8
