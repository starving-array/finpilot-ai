import logging
import uuid

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
    SeasonalityFlagValue,
    SeasonalityFlags,
    ShapExplanation,
)

logger = logging.getLogger(__name__)
router = APIRouter()

CATEGORY_ORDER = C.CATEGORY_ORDER


@router.post("/predict", response_model=PredictResponse)
async def predict_endpoint(request: PredictRequest):
    request_id = str(uuid.uuid4())[:8]

    logger.info(f"Predict request received: customer_id={request.customer_id}, business_type={request.business_type}, gst_registered={request.gst_registered}")

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

        result = ScoreResult(
            customer_id=request.customer_id,
            bucket=bucket,
            probability=probability,
            composite_score=composite_score,
            features=features,
            flags=FeatureFlags(
                is_blank_slate=flags["is_blank_slate"],
                epfo_plausibility=EpfoPlausibilityFlag(**flags["epfo_plausibility"]),
                capacity_flag=CapacityFlag(**flags["capacity_flag"]),
                seasonality_flags=SeasonalityFlags(
                    fuel=SeasonalityFlagValue(**flags["seasonality_flags"]["fuel"]),
                    electricity=SeasonalityFlagValue(**flags["seasonality_flags"]["electricity"]),
                ),
            ),
            shap_explanation=shap_explanation,
            model_version=model_manager.model_version,
            traditional_signal_contribution=shap_result.get("traditional_signal_contribution", 0.0) if shap_result else 0.0,
            alternative_signal_contribution=shap_result.get("alternative_signal_contribution", 0.0) if shap_result else 0.0,
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
