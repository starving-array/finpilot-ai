from pydantic import BaseModel, Field
from typing import Optional


class EpfoPlausibilityFlag(BaseModel):
    flag: str
    message: str
    implied_wage: Optional[float] = None
    employee_count: Optional[int] = None


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
    fuel: SeasonalityFlagValue
    electricity: SeasonalityFlagValue


class FeatureFlags(BaseModel):
    is_blank_slate: bool
    epfo_plausibility: EpfoPlausibilityFlag
    capacity_flag: CapacityFlag
    seasonality_flags: SeasonalityFlags


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
    business_type: str = Field(default="retail", description="manufacturing|logistics|retail|services|trading")


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
