import pytest
from app.epfo_checks import check_epfo_plausibility


class TestCheckEpfoPlausibility:
    def test_no_data_returns_unavailable(self):
        result = check_epfo_plausibility(None, None)
        assert result["flag"] == "unavailable"

    def test_zero_count_returns_unavailable(self):
        result = check_epfo_plausibility(0, 10000)
        assert result["flag"] == "unavailable"

    def test_zero_amount_returns_unavailable(self):
        result = check_epfo_plausibility(10, 0)
        assert result["flag"] == "unavailable"

    def test_plausible_data_returns_plausible(self):
        result = check_epfo_plausibility(10, 30000)
        assert result["flag"] == "plausible"
        assert result["implied_wage"] >= 7500
        assert result["implied_wage"] <= 200000

    def test_low_implied_wage_returns_suspicious(self):
        result = check_epfo_plausibility(10, 1000)
        assert result["flag"] == "suspicious_low_critical"

    def test_very_low_implied_wage_returns_critical(self):
        result = check_epfo_plausibility(10, 500)
        assert "critical" in result["flag"]

    def test_high_implied_wage_returns_suspicious(self):
        result = check_epfo_plausibility(2, 200000)
        assert "suspicious_high" in result["flag"]
        assert result["implied_wage"] > 200000

    def test_moderately_low_wage_returns_warning(self):
        result = check_epfo_plausibility(10, 15000)
        assert "warning" in result["flag"] or "plausible" in result["flag"]

    def test_employee_count_matches(self):
        result = check_epfo_plausibility(25, 75000)
        assert result["employee_count"] == 25
