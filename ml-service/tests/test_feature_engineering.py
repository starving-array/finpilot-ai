import pytest
from app.feature_engineering import (
    compute_payment_regularity,
    compute_financial_capacity_proxy,
    compute_business_longevity,
    compute_data_coverage,
    compute_evidence_confidence,
    is_blank_slate,
    compute_all_features,
    safe_float,
    FEATURE_NAMES,
)


class TestSafeFloat:
    def test_none_returns_default(self):
        assert safe_float(None) == 0.0

    def test_empty_string_returns_default(self):
        assert safe_float("") == 0.0

    def test_string_none_returns_default(self):
        assert safe_float("None") == 0.0

    def test_valid_float_string(self):
        assert safe_float("3.14") == 3.14

    def test_valid_number(self):
        assert safe_float(42) == 42.0

    def test_custom_default(self):
        assert safe_float(None, -1) == -1.0


class TestComputePaymentRegularity:
    def test_all_signals_present(self):
        result = compute_payment_regularity(
            gst_filing_regularity=0.95,
            epfo_contribution_regularity=0.85,
            electricity_payment_delay_days_avg=5,
            water_payment_delay_days_avg=3,
            business_type="retail",
        )
        assert result > 0

    def test_no_signals_returns_zero(self):
        result = compute_payment_regularity(
            gst_filing_regularity=None,
            epfo_contribution_regularity=None,
            electricity_payment_delay_days_avg=None,
            water_payment_delay_days_avg=None,
        )
        assert result == 0.0

    def test_only_gst_signal(self):
        result = compute_payment_regularity(
            gst_filing_regularity=0.95,
            business_type="retail",
        )
        assert result > 0

    def test_negative_delays_are_ignored(self):
        result = compute_payment_regularity(
            electricity_payment_delay_days_avg=-1,
            business_type="retail",
        )
        assert result == 0.0

    def test_delay_regularity_scales_correctly(self):
        short_delay = compute_payment_regularity(
            electricity_payment_delay_days_avg=1,
            business_type="retail",
        )
        long_delay = compute_payment_regularity(
            electricity_payment_delay_days_avg=60,
            business_type="retail",
        )
        assert short_delay > long_delay


class TestComputeFinancialCapacityProxy:
    def test_high_turnover_returns_above_half(self):
        result = compute_financial_capacity_proxy(
            gst_monthly_turnover_avg=2000000,
            business_type="retail",
        )
        assert result > 0.5

    def test_low_turnover_uses_electricity(self):
        result = compute_financial_capacity_proxy(
            gst_monthly_turnover_avg=5000,
            electricity_monthly_units_avg=800,
            business_type="retail",
        )
        assert 0 <= result <= 1

    def test_no_data_returns_zero(self):
        result = compute_financial_capacity_proxy(business_type="retail")
        assert result == 0.0

    def test_manufacturing_electricity_threshold(self):
        result = compute_financial_capacity_proxy(
            gst_monthly_turnover_avg=5000,
            electricity_monthly_units_avg=7800,
            business_type="manufacturing",
        )
        assert result > 0.9


class TestComputeBusinessLongevity:
    def test_long_history_returns_near_one(self):
        result = compute_business_longevity(
            years_in_operation=15,
            payment_regularity=0.9,
            data_coverage=0.9,
        )
        assert result > 0.9

    def test_short_history_with_good_signals_gets_floor_boost(self):
        result = compute_business_longevity(
            years_in_operation=1,
            payment_regularity=0.8,
            data_coverage=0.85,
        )
        assert result > 1.0 / 15.0

    def test_no_years_returns_zero(self):
        result = compute_business_longevity(years_in_operation=None)
        assert result == 0.0


class TestComputeDataCoverage:
    def test_all_groups_present(self):
        result = compute_data_coverage(
            electricity_monthly_units_avg=1000,
            electricity_payment_delay_days_avg=5,
            epfo_contribution_regularity=0.8,
            epfo_employee_count=10,
            water_monthly_consumption_kl=100,
            water_payment_delay_days_avg=3,
            fuel_monthly_spend_avg=50000,
            fuel_spend_volatility=0.3,
        )
        assert result > 0.9

    def test_no_data_returns_zero(self):
        result = compute_data_coverage()
        assert result == 0.0

    def test_partial_coverage(self):
        result = compute_data_coverage(
            electricity_monthly_units_avg=1000,
            electricity_payment_delay_days_avg=5,
        )
        assert result == 0.25


class TestComputeEvidenceConfidence:
    def test_strong_agreement_returns_high(self):
        result = compute_evidence_confidence(
            gst_filing_regularity=0.9,
            epfo_contribution_regularity=0.85,
            electricity_payment_delay_days_avg=2,
            water_payment_delay_days_avg=3,
        )
        assert result > 0.7

    def test_few_signals_returns_fallback(self):
        result = compute_evidence_confidence(
            gst_filing_regularity=0.9,
        )
        assert result == 0.5

    def test_no_signals_returns_fallback(self):
        result = compute_evidence_confidence()
        assert result == 0.5


class TestIsBlankSlate:
    def test_no_data_is_blank(self):
        result = is_blank_slate(business_type="retail")
        assert result is True

    def test_high_gst_turnover_not_blank(self):
        result = is_blank_slate(
            gst_monthly_turnover_avg=50000,
            business_type="retail",
        )
        assert result is False

    def test_high_upi_count_not_blank(self):
        result = is_blank_slate(
            upi_monthly_txn_count=50,
            upi_monthly_txn_value=100000,
            business_type="retail",
        )
        assert result is False

    def test_low_gst_and_low_upi_is_blank(self):
        result = is_blank_slate(
            gst_monthly_turnover_avg=5000,
            upi_monthly_txn_count=2,
            business_type="retail",
        )
        assert result is True

    def test_manufacturing_threshold_different(self):
        manufacturing_blank = is_blank_slate(
            gst_monthly_turnover_avg=15000,
            upi_monthly_txn_count=6,
            business_type="manufacturing",
        )
        retail_blank = is_blank_slate(
            gst_monthly_turnover_avg=15000,
            upi_monthly_txn_count=6,
            business_type="retail",
        )
        assert manufacturing_blank is not retail_blank


class TestComputeAllFeatures:
    def test_returns_six_features(self):
        features, flags = compute_all_features(
            gst_registered=True,
            gst_monthly_turnover_avg=500000,
            gst_filing_regularity=0.95,
            upi_monthly_txn_count=100,
            upi_monthly_txn_value=250000,
            electricity_monthly_units_avg=2000,
            electricity_payment_delay_days_avg=5,
            epfo_contribution_regularity=0.85,
            epfo_employee_count=20,
            epfo_contribution_amount=45000,
            water_monthly_consumption_kl=150,
            water_payment_delay_days_avg=3,
            fuel_monthly_spend_avg=80000,
            fuel_spend_volatility=0.25,
            requested_loan_amount=500000,
            years_in_operation=8,
            business_type="retail",
        )
        assert len(features) == 6
        for name in FEATURE_NAMES:
            assert name in features

    def test_flags_contain_expected_keys(self):
        _, flags = compute_all_features(business_type="retail")
        assert "is_blank_slate" in flags
        assert "epfo_plausibility" in flags
        assert "capacity_flag" in flags
        assert "seasonality_flags" in flags

    def test_blank_slate_scenario(self):
        features, flags = compute_all_features(business_type="retail")
        assert flags["is_blank_slate"] is True
        assert features["is_blank_slate_flag"] == 1.0

    def test_full_data_scenario(self):
        features, flags = compute_all_features(
            gst_registered=True,
            gst_monthly_turnover_avg=500000,
            gst_filing_regularity=0.95,
            upi_monthly_txn_count=100,
            upi_monthly_txn_value=250000,
            electricity_monthly_units_avg=2000,
            electricity_payment_delay_days_avg=2,
            epfo_contribution_regularity=0.9,
            epfo_employee_count=25,
            epfo_contribution_amount=50000,
            water_monthly_consumption_kl=150,
            water_payment_delay_days_avg=3,
            fuel_monthly_spend_avg=80000,
            fuel_spend_volatility=0.2,
            requested_loan_amount=500000,
            years_in_operation=10,
            business_type="retail",
        )
        assert flags["is_blank_slate"] is False
        assert features["payment_regularity"] > 0
        assert features["financial_capacity_proxy"] > 0
