import logging
import time

import numpy as np
import shap

from .config import settings
from .model_loader import model_manager
from .schemas import PredictRequest, PredictResponse, ShapExplanation, FeatureRank

logger = logging.getLogger(__name__)

CATEGORIES = ["YES_TO_GO", "DISCIPLINED", "NON_DISCIPLINED", "NO_TO_GO"]

EXPLANATION_TEMPLATES = {
    "gst_filing_regularity": {
        "positive": "Consistent GST filing indicates strong compliance discipline",
        "negative": "Irregular GST filing suggests compliance gaps",
    },
    "gst_tax_growth_yoy": {
        "positive": "Year-on-year GST growth confirms business is expanding",
        "negative": "Declining GST revenue suggests business contraction",
    },
    "gst_compliance_score": {
        "positive": "High GST compliance reflects organized financial management",
        "negative": "Low GST compliance raises concerns about governance practices",
    },
    "upi_txn_volume_30d": {
        "positive": "Strong UPI transaction volume demonstrates active business operations",
        "negative": "Low UPI transaction volume limits available credit evidence",
    },
    "upi_merchant_diversity": {
        "positive": "Diverse merchant network indicates a broad customer base",
        "negative": "Concentrated merchant transactions create dependency risk",
    },
    "upi_inflow_outflow_ratio": {
        "positive": "Healthy inflow-to-outflow ratio shows strong liquidity position",
        "negative": "Negative cash flow balance suggests working capital stress",
    },
    "bureau_score": {
        "positive": "Strong credit history demonstrates repayment discipline",
        "negative": "Weak credit bureau profile indicates higher default risk",
    },
    "bureau_enquiry_velocity": {
        "positive": "Few recent credit enquiries reflect measured borrowing behavior",
        "negative": "Multiple recent credit enquiries signal urgent credit seeking",
    },
    "bureau_credit_utilization": {
        "positive": "Low credit utilization indicates responsible borrowing habits",
        "negative": "High credit utilization warns of over-leverage risk",
    },
    "electricity_avg_consumption": {
        "positive": "Steady electricity usage confirms continuous business operations",
        "negative": "Erratic power consumption suggests operational instability",
    },
    "electricity_payment_regularity": {
        "positive": "Timely electricity payments demonstrate financial discipline",
        "negative": "Irregular electricity payments indicate cash flow constraints",
    },
    "water_consumption_stability": {
        "positive": "Stable water usage confirms consistent business activity",
        "negative": "Uneven water consumption implies operational inconsistency",
    },
    "water_payment_regularity": {
        "positive": "On-time water bill payments show responsible financial behavior",
        "negative": "Delayed water payments signal potential cash flow stress",
    },
    "epfo_contribution_regularity": {
        "positive": "Regular EPFO payments reflect a stable formal workforce",
        "negative": "Inconsistent EPFO contributions suggest employment instability",
    },
    "epfo_employee_trend": {
        "positive": "Growing employee count signals business expansion and stability",
        "negative": "Shrinking workforce indicates possible business contraction",
    },
    "fuel_expense_regularity": {
        "positive": "Consistent fuel spending points to stable logistics operations",
        "negative": "Erratic fuel expenses suggest operational disruptions",
    },
    "fuel_liters_cv": {
        "positive": "Predictable fuel consumption confirms efficient fleet management",
        "negative": "Highly variable fuel usage implies logistics inefficiency",
    },
}


def predict(request: PredictRequest) -> PredictResponse:
    model = model_manager.get_model()
    if model is None:
        return PredictResponse(
            category="NO_TO_GO",
            probabilities={c: 0.25 for c in CATEGORIES},
            feature_values=request.features,
            model_version="0.0.0",
            confidence=0.0,
        )

    start = time.time()

    feature_vector = _build_feature_vector(request.features, model)
    probabilities = model.predict_proba(feature_vector)[0]
    prediction_idx = int(np.argmax(probabilities))
    category = CATEGORIES[prediction_idx]

    shap_explanation = None
    if request.explain:
        try:
            shap_explanation = _compute_shap(feature_vector, model, request.features)
        except Exception as e:
            logger.error(f"SHAP computation failed: {e}")

    confidence = _compute_confidence(probabilities, request.features)

    elapsed = time.time() - start
    logger.info(f"Prediction completed in {elapsed*1000:.1f}ms", extra={
        "category": category,
        "confidence": confidence,
        "model_version": model_manager.model_version,
    })

    return PredictResponse(
        category=category,
        probabilities={CATEGORIES[i]: float(probabilities[i]) for i in range(len(CATEGORIES))},
        feature_values=request.features,
        shap_explanation=shap_explanation,
        model_version=model_manager.model_version,
        confidence=confidence,
    )


def _build_feature_vector(features: dict, model) -> np.ndarray:
    if hasattr(model, "feature_name_"):
        expected = model.feature_name_
        vec = np.zeros((1, len(expected)))
        for i, name in enumerate(expected):
            vec[0, i] = features.get(name, 0.0)
        return vec
    return np.array([list(features.values())]).reshape(1, -1)


def _compute_shap(feature_vector: np.ndarray, model, raw_features: dict) -> ShapExplanation | None:
    try:
        prediction_idx = int(model.predict(feature_vector)[0])
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(feature_vector)
    except Exception as e:
        logger.error(f"SHAP computation failed: {e}")
        return None

    if isinstance(shap_values, list):
        shap_values = shap_values[prediction_idx]
    elif shap_values.ndim == 3:
        shap_values = shap_values[0, :, prediction_idx]

    shap_values_flat = shap_values[0] if shap_values.ndim > 1 else shap_values
    if isinstance(explainer.expected_value, (list, np.ndarray)):
        base_value = float(explainer.expected_value[prediction_idx])
    else:
        base_value = float(explainer.expected_value)

    feature_names = list(raw_features.keys())
    if len(shap_values_flat) != len(feature_names):
        feature_names = feature_names[:len(shap_values_flat)]

    shap_dict = {}
    for i, name in enumerate(feature_names):
        if i < len(shap_values_flat):
            shap_dict[name] = float(shap_values_flat[i])

    ranked = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)
    feature_ranking = []
    for rank, (name, sv) in enumerate(ranked[:10], 1):
        direction = "positive" if sv >= 0 else "negative"
        template = EXPLANATION_TEMPLATES.get(name, {})
        business_desc = template.get(direction, f"Feature {name} contributes {'positively' if direction == 'positive' else 'negatively'}")
        feature_ranking.append(FeatureRank(
            feature_name=name,
            value=raw_features.get(name, 0.0),
            shap_value=sv,
            rank=rank,
            direction=direction,
            business_description=business_desc,
        ))

    summary_parts = []
    for fr in feature_ranking[:3]:
        summary_parts.append(fr.business_description)
    human_readable_summary = "; ".join(summary_parts)

    return ShapExplanation(
        shap_values=shap_dict,
        base_value=base_value,
        feature_ranking=feature_ranking,
        human_readable_summary=human_readable_summary,
    )


def _compute_confidence(probabilities: np.ndarray, features: dict) -> float:
    n_classes = len(probabilities)
    entropy = -np.sum(probabilities * np.log(np.clip(probabilities, 1e-10, 1)))
    normalized_entropy = entropy / np.log(n_classes) if n_classes > 1 else 0.0

    present = sum(1 for v in features.values() if v is not None)
    total = len(features) if features else 1
    completeness = present / max(total, 1)

    confidence = 0.5 * (1 - normalized_entropy) + 0.3 * completeness + 0.2 * 1.0
    return round(float(np.clip(confidence * 100, 0, 100)), 2)
