import logging
import uuid
from datetime import datetime

import numpy as np
from fastapi import APIRouter, HTTPException

from . import constants as C
from .explain import compute_shap
from .feature_engineering import FEATURE_NAMES, compute_all_features
from .model_loader import model_manager
from .schemas import (
    CapacityFlag,
    EpfoPlausibilityFlag,
    ErrorResponse,
    FeatureFlags,
    PredictRequest,
    PredictResponse,
    ScoreResult,
    SeasonalityAdjustment,
    SeasonalityFlagValue,
    SeasonalityFlags,
    SeasonalityTriggeredMetric,
    ShapExplanation,
)
from .seasonality import compute_seasonality_penalty

logger = logging.getLogger(__name__)
router = APIRouter()

CATEGORY_ORDER = C.CATEGORY_ORDER

BUSINESS_TYPE_MAP = {
    "gst_monthly_turnover_avg": "gst_monthly_turnover_avg",
    "gst_filing_regularity": "gst_filing_regularity",
    "electricity_monthly_units_avg": "electricity_monthly_units_avg",
    "electricity_payment_delay_days_avg": "electricity_payment_delay_days_avg",
    "epfo_contribution_regularity": "epfo_contribution_regularity",
    "epfo_employee_count": "epfo_employee_count",
    "water_monthly_consumption_kl": "water_monthly_consumption_kl",
    "water_payment_delay_days_avg": "water_payment_delay_days_avg",
    "fuel_monthly_spend_avg": "fuel_monthly_spend_avg",
    "fuel_spend_volatility": "fuel_spend_volatility",
}


@router.post("/predict", response_model=PredictResponse)
async def predict_endpoint(request: PredictRequest):
    request_id = str(uuid.uuid4())[:8]

    logger.info(f"Predict request received: customer_id={request.customer_id}, business_type={request.business_type}, enable_seasonality={request.enable_seasonality}")

    if not model_manager.is_loaded():
        raise HTTPException(status_code=503, detail="Model not loaded")

    if request.business_type not in C.VALID_BUSINESS_TYPES:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                error_code="INVALID_PROFILE_DATA",
                message=f"Invalid business_type: {request.business_type}. Must be one of: {', '.join(sorted(C.VALID_BUSINESS_TYPES))}",
                request_id=request_id,
            ).model_dump(),
        )

    model = model_manager.get_model()
    explainer = model_manager.get_explainer()

    try:
        features, flags = compute_all_features(
            gst_registered=request.gst_registered,
            gst_monthly_turnover_avg=request.gst_monthly_turnover_avg,
            gst_filing_regularity=request.gst_filing_regularity,
            upi_monthly_txn_count=request.upi_monthly_txn_count,
            upi_monthly_txn_value=request.upi_monthly_txn_value,
            electricity_monthly_units_avg=request.electricity_monthly_units_avg,
            electricity_payment_delay_days_avg=request.electricity_payment_delay_days_avg,
            epfo_contribution_regularity=request.epfo_contribution_regularity,
            epfo_employee_count=request.epfo_employee_count,
            epfo_contribution_amount=request.epfo_contribution_amount,
            water_monthly_consumption_kl=request.water_monthly_consumption_kl,
            water_payment_delay_days_avg=request.water_payment_delay_days_avg,
            fuel_monthly_spend_avg=request.fuel_monthly_spend_avg,
            fuel_spend_volatility=request.fuel_spend_volatility,
            requested_loan_amount=request.requested_loan_amount,
            years_in_operation=request.years_in_operation,
            business_type=request.business_type,
        )

        feature_vector = np.array([[features[n] for n in FEATURE_NAMES]], dtype=np.float64)

        proba = model.predict_proba(feature_vector)[0]
        pred_idx = int(model.predict(feature_vector)[0])
        bucket = CATEGORY_ORDER[pred_idx]
        probability = round(float(proba[pred_idx]), 4)

        composite_score = round(float(
            C.COMPOSITE_WEIGHTS["payment_regularity"] * features["payment_regularity"]
            + C.COMPOSITE_WEIGHTS["financial_capacity_proxy"] * features["financial_capacity_proxy"]
            + C.COMPOSITE_WEIGHTS["business_longevity"] * features["business_longevity"]
            + C.COMPOSITE_WEIGHTS["data_coverage"] * features["data_coverage"]
            + C.COMPOSITE_WEIGHTS["evidence_confidence"] * features["evidence_confidence"]
        ), 4)
        composite_score = max(composite_score, 0.0)

        seasonality_adjustment = None
        if request.enable_seasonality:
            reference_month = request.reference_month if request.reference_month is not None else datetime.now().month
            observed_cvs = _build_observed_cvs(request, flags)
            penalty_result = compute_seasonality_penalty(
                observed_cvs, request.business_type, reference_month,
            )
            if penalty_result["total_penalty"] > 0:
                adjusted_score = round(max(composite_score - penalty_result["total_penalty"], 0.0), 4)
                seasonality_adjustment = SeasonalityAdjustment(
                    enabled=True,
                    total_penalty_before_cap=round(
                        sum(m["penalty_applied"] for m in penalty_result["triggered_metrics"]), 4
                    ),
                    cap_applied=penalty_result["total_penalty"] < sum(
                        m["penalty_applied"] for m in penalty_result["triggered_metrics"]
                    ),
                    seasonality_adjusted_score=adjusted_score,
                    triggered_metrics=[
                        SeasonalityTriggeredMetric(**m) for m in penalty_result["triggered_metrics"]
                    ],
                )
            else:
                seasonality_adjustment = SeasonalityAdjustment(enabled=True)

        shap_result = compute_shap(explainer, model, feature_vector, flags["is_blank_slate"], request.business_type)

        shap_explanation = None
        if shap_result:
            shap_explanation = ShapExplanation(
                shap_values=shap_result["shap_values"],
                base_value=shap_result["base_value"],
                feature_ranking=shap_result["feature_ranking"],
                human_readable_summary=shap_result["human_readable_summary"],
                traditional_signal_contribution=shap_result.get("traditional_signal_contribution", 0.0),
                alternative_signal_contribution=shap_result.get("alternative_signal_contribution", 0.0),
            )

        seasonality_flags = SeasonalityFlags()
        fuel_flag = flags.get("seasonality_flags", {}).get("fuel")
        if fuel_flag is not None:
            seasonality_flags.fuel = SeasonalityFlagValue(**fuel_flag)

        result = ScoreResult(
            customer_id=request.customer_id,
            bucket=bucket,
            probability=probability,
            composite_score=composite_score,
            features=features,
            flags=FeatureFlags(
                is_blank_slate=flags["is_blank_slate"],
                financial_capacity_corroboration=flags.get("financial_capacity_corroboration"),
                financial_capacity_source=flags.get("financial_capacity_source"),
                epfo_plausibility=EpfoPlausibilityFlag(**flags["epfo_plausibility"]),
                capacity_flag=CapacityFlag(**flags["capacity_flag"]),
                seasonality_flags=seasonality_flags,
            ),
            shap_explanation=shap_explanation,
            model_version=model_manager.model_version,
            traditional_signal_contribution=shap_result.get("traditional_signal_contribution", 0.0) if shap_result else 0.0,
            alternative_signal_contribution=shap_result.get("alternative_signal_contribution", 0.0) if shap_result else 0.0,
            seasonality_adjustment=seasonality_adjustment,
        )

        return PredictResponse(
            status="success",
            result=result,
            request_id=request_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction failed for {request.customer_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="PREDICTION_FAILED",
                message=str(e),
                request_id=request_id,
            ).model_dump(),
        )


def _estimate_cv_from_norm(value, p90):
    if p90 is None or p90 <= 0 or value is None:
        return None
    norm = p90 * 0.4  # median estimate for right-skewed distributions
    if norm <= 0:
        return None
    return abs(value - norm) / norm


def _build_observed_cvs(request, flags):
    cvs = {}

    if request.fuel_spend_volatility is not None:
        cvs["fuel_monthly_spend_avg"] = float(request.fuel_spend_volatility)

    bt = request.business_type
    if request.electricity_monthly_units_avg is not None:
        p90 = C.ELEC_90TH_PERCENTILE.get(bt, C.DEFAULT_ELEC_PERCENTILE)
        cv = _estimate_cv_from_norm(request.electricity_monthly_units_avg, p90)
        if cv is not None:
            cvs["electricity_monthly_units_avg"] = round(cv, 4)

    if request.gst_monthly_turnover_avg is not None:
        p90 = C.TURNOVER_90TH_PERCENTILE.get(bt, C.DEFAULT_TURNOVER_PERCENTILE)
        cv = _estimate_cv_from_norm(request.gst_monthly_turnover_avg, p90)
        if cv is not None:
            cvs["gst_monthly_turnover_avg"] = round(cv, 4)

    if request.water_monthly_consumption_kl is not None:
        cv = _estimate_cv_from_norm(request.water_monthly_consumption_kl, request.electricity_monthly_units_avg / 3 if request.electricity_monthly_units_avg else None)
        if cv is not None:
            cvs["water_monthly_consumption_kl"] = round(cv, 4)

    if request.epfo_employee_count is not None and request.gst_monthly_turnover_avg is not None:
        implied_cv = abs(request.epfo_employee_count - 5.0) / 5.0 if request.epfo_employee_count > 0 else 0.0
        cvs["epfo_employee_count"] = round(min(implied_cv, 2.0), 4)

    return cvs


@router.get("/health")
async def health():
    from fastapi.responses import JSONResponse
    model = model_manager.get_model()
    explainer = model_manager.get_explainer()
    if model is None:
        return JSONResponse(
            status_code=503,
            content={
                "status": "DEGRADED",
                "model_version": "0.0.0",
                "model_loaded": False,
                "shap_loaded": False,
            },
        )
    return {
        "status": "UP",
        "model_version": model_manager.model_version,
        "model_loaded": True,
        "shap_loaded": explainer is not None,
        "model_type": model_manager.get_model_type(),
    }


@router.get("/models/{version}/metadata", response_model=dict)
async def model_metadata(version: str):
    from .schemas import ModelMetadata
    metadata = model_manager.get_metadata()
    if not metadata and version != model_manager.model_version:
        raise HTTPException(status_code=404, detail=f"Model version {version} not found")
    return ModelMetadata(
        model_version=model_manager.model_version,
        training_date=metadata.get("training_date", ""),
        dataset_hash=metadata.get("dataset_hash", ""),
        metrics=metadata.get("metrics", {}),
        feature_schema=metadata.get("feature_schema", []),
        artifact_path=metadata.get("artifact_path", ""),
        deployed_at=metadata.get("deployed_at", ""),
        deployed_by=metadata.get("deployed_by", "system"),
        status="active" if model_manager.is_loaded() else "unavailable",
    ).model_dump()
