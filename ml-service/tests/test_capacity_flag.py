import pytest
from app.capacity_flag import compute_capacity_flag


class TestComputeCapacityFlag:
    def test_no_loan_returns_unavailable(self):
        result = compute_capacity_flag(
            requested_loan_amount=None,
            gst_monthly_turnover_avg=None,
            electricity_monthly_units_avg=None,
            business_type="retail",
        )
        assert result["flag"] == "unavailable"

    def test_zero_loan_returns_unavailable(self):
        result = compute_capacity_flag(
            requested_loan_amount=0,
            gst_monthly_turnover_avg=50000,
            electricity_monthly_units_avg=None,
            business_type="retail",
        )
        assert result["flag"] == "unavailable"

    def test_low_loan_to_revenue_returns_normal(self):
        result = compute_capacity_flag(
            requested_loan_amount=100000,
            gst_monthly_turnover_avg=50000,
            electricity_monthly_units_avg=None,
            business_type="retail",
        )
        assert result["flag"] == "normal"
        assert result["source"] == "gst"

    def test_high_loan_to_revenue_returns_caution(self):
        result = compute_capacity_flag(
            requested_loan_amount=400000,
            gst_monthly_turnover_avg=50000,
            electricity_monthly_units_avg=None,
            business_type="retail",
        )
        assert result["flag"] == "caution"

    def test_very_high_loan_to_revenue_returns_high_risk(self):
        result = compute_capacity_flag(
            requested_loan_amount=1000000,
            gst_monthly_turnover_avg=50000,
            electricity_monthly_units_avg=None,
            business_type="retail",
        )
        assert result["flag"] == "high_risk"

    def test_falls_back_to_electricity_when_no_gst(self):
        result = compute_capacity_flag(
            requested_loan_amount=100000,
            gst_monthly_turnover_avg=None,
            electricity_monthly_units_avg=1000,
            business_type="retail",
        )
        assert result["source"] == "electricity_proxy"
        assert result["flag"] in ("normal", "caution")

    def test_no_gst_no_electricity_returns_insufficient_data(self):
        result = compute_capacity_flag(
            requested_loan_amount=100000,
            gst_monthly_turnover_avg=None,
            electricity_monthly_units_avg=None,
            business_type="retail",
        )
        assert result["flag"] == "insufficient_data"

    def test_retail_vs_manufacturing_electricity_threshold(self):
        retail = compute_capacity_flag(
            requested_loan_amount=200000,
            gst_monthly_turnover_avg=None,
            electricity_monthly_units_avg=800,
            business_type="retail",
        )
        manufacturing = compute_capacity_flag(
            requested_loan_amount=200000,
            gst_monthly_turnover_avg=None,
            electricity_monthly_units_avg=800,
            business_type="manufacturing",
        )
        assert retail["loan_to_revenue_ratio"] != manufacturing["loan_to_revenue_ratio"]
