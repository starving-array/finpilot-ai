import pytest
from app.config import settings


class TestSettings:
    def test_default_redis_host(self):
        assert settings.redis_host == "localhost"

    def test_default_redis_port(self):
        assert settings.redis_port == 6379

    def test_default_model_path(self):
        assert settings.model_path == "/app/models/model_latest.joblib"

    def test_epfo_defaults(self):
        assert settings.epfo_min_monthly_wage == 7500.0
        assert settings.epfo_max_monthly_wage == 200000.0
        assert settings.epfo_employer_contribution_rate == 0.12
        assert settings.epfo_employee_contribution_rate == 0.12

    def test_loan_defaults(self):
        assert settings.loan_to_revenue_cap == 0.60
        assert settings.loan_to_elec_proxy_multiplier == 3.0

    def test_longevity_default(self):
        assert settings.longevity_scale_years == 15.0

    def test_blank_slate_defaults(self):
        assert settings.blank_slate_gst_turnover == 20000.0
        assert settings.blank_slate_upi_count == 10
        assert settings.blank_slate_gst_min == 5000.0
