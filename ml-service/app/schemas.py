from pydantic import BaseModel, Field
from typing import Optional


class EpfoPlausibilityFlag(BaseModel):
    flag: str
    message: str
    implied_wage: Optional[float] = None
    employee_count: Optional[int] = None
    contribution_type: Optional[str] = None


class CapacityFlag(BaseModel):
    flag: str
    message: str
    loan_to_revenue_ratio: Optional[float] = None
    source: Optional[str] = None


class SeasonalityFlagValue(BaseModel):
    flag: str
    message: str
    value: Optional[float] = None
    expected_range: Optional[dict] = None


class SeasonalityFlags(BaseModel):
    fuel: Optional[SeasonalityFlagValue] = None
    electricity: Optional[SeasonalityFlagValue] = None
    gst: Optional[SeasonalityFlagValue] = None
    water: Optional[SeasonalityFlagValue] = None
    epfo: Optional[SeasonalityFlagValue] = None


class FeatureFlags(BaseModel):
    is_blank_slate: bool
    financial_capacity_corroboration: Optional[str] = None
    financial_capacity_source: Optional[str] = None
    epfo_plausibility: EpfoPlausibilityFlag
    capacity_flag: CapacityFlag
    seasonality_flags: SeasonalityFlags


class SeasonalityTriggeredMetric(BaseModel):
    metric: str
    observed_cv: float
    expected_ceiling: float
    base_penalty: float
    penalty_applied: float
    peak_month_discount: bool
    reason: str


class SeasonalityAdjustment(BaseModel):
    enabled: bool
    total_penalty_before_cap: float = 0.0
    cap_applied: bool = False
    seasonality_adjusted_score: Optional[float] = None
    triggered_metrics: list[SeasonalityTriggeredMetric] = []


class PredictRequest(BaseModel):
    customer_id: str = Field(..., description="Customer ID (e.g. CUST00001)")
    gst_registered: Optional[bool] = None
    gst_monthly_turnover_avg: Optional[float] = None
    gst_filing_regularity: Optional[float] = None
    upi_monthly_txn_count: Optional[int] = None
    upi_monthly_txn_value: Optional[float] = None
    electricity_monthly_units_avg: Optional[float] = None
    electricity_payment_delay_days_avg: Optional[float] = None
    epfo_contribution_regularity: Optional[float] = None
    epfo_employee_count: Optional[int] = None
    epfo_contribution_amount: Optional[float] = None
    water_monthly_consumption_kl: Optional[float] = None
    water_payment_delay_days_avg: Optional[float] = None
    fuel_monthly_spend_avg: Optional[float] = None
    fuel_spend_volatility: Optional[float] = None
    requested_loan_amount: Optional[float] = None
    years_in_operation: Optional[float] = None
    business_type: str = Field(default="retail", description="manufacturing|logistics|retail|services|trading|food_and_beverage|agriculture|construction")
    enable_seasonality: bool = Field(default=False, description="Apply seasonality adjustment")
    reference_month: Optional[int] = Field(default=None, description="Month (1-12) for seasonality calculation, defaults to current")


class FeatureRank(BaseModel):
    feature_name: str
    value: float
    shap_value: float
    rank: int
    direction: str
    business_description: str
    source: str = Field(default="standard", description="alternative|mixed|standard")


class ShapExplanation(BaseModel):
    shap_values: dict[str, float]
    base_value: float
    feature_ranking: list[FeatureRank]
    human_readable_summary: str
    traditional_signal_contribution: float = 0.0
    alternative_signal_contribution: float = 0.0


class ScoreResult(BaseModel):
    customer_id: str
    bucket: str
    probability: float
    composite_score: float
    features: dict[str, float]
    flags: FeatureFlags
    shap_explanation: Optional[ShapExplanation] = None
    model_version: str
    traditional_signal_contribution: float = 0.0
    alternative_signal_contribution: float = 0.0
    seasonality_adjustment: Optional[SeasonalityAdjustment] = None


class PredictResponse(BaseModel):
    status: str = "success"
    result: ScoreResult
    request_id: str


class ErrorResponse(BaseModel):
    status: str = "error"
    error_code: str
    message: str
    details: Optional[dict] = None
    request_id: Optional[str] = None


class ModelMetadata(BaseModel):
    model_version: str
    training_date: str
    dataset_hash: str
    metrics: dict
    feature_schema: list[str]
    artifact_path: str
    deployed_at: str
    deployed_by: str
    status: str
