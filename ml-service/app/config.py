from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_host: str = "localhost"
    redis_port: int = 6379
    model_path: str = "/app/models/model_latest.joblib"
    model_checksum: str = ""
    max_features: int = 50
    shap_timeout_seconds: int = 10
    inference_timeout_seconds: int = 5
    epfo_min_monthly_wage: float = 7500.0
    epfo_max_monthly_wage: float = 200000.0
    epfo_employer_contribution_rate: float = 0.12
    epfo_employee_contribution_rate: float = 0.12
    loan_to_revenue_cap: float = 0.60
    loan_to_elec_proxy_multiplier: float = 3.0
    longevity_scale_years: float = 15.0
    elec_default_percentile: float = 1000.0
    turnover_capacity_threshold: float = 15000.0
    blank_slate_gst_turnover: float = 20000.0
    blank_slate_upi_count: int = 10
    blank_slate_upi_value: float = 10000.0
    blank_slate_gst_min: float = 5000.0
    blank_slate_gst_max: float = 50000.0
    blank_slate_upi_min: int = 2
    blank_slate_upi_max: int = 50

    class Config:
        env_prefix = ""
        env_file = ".env"


settings = Settings()
