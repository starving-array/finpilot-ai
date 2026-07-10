import logging

import numpy as np

from .feature_engineering import FEATURE_NAMES
from . import constants as C

logger = logging.getLogger(__name__)


def compute_shap(explainer, model, feature_vector: np.ndarray, blank_slate: bool, business_type: str = "retail") -> dict | None:
    if explainer is None:
        return None

    try:
        pred_idx = int(model.predict(feature_vector)[0])
        shap_values = explainer.shap_values(feature_vector)

        if isinstance(shap_values, list):
            svc = shap_values[pred_idx]
        elif shap_values.ndim == 3:
            svc = shap_values[0, :, pred_idx]
        else:
            svc = shap_values

        ev = explainer.expected_value
        base_value = float(ev[pred_idx]) if isinstance(ev, (list, np.ndarray)) else float(ev)

        ranked = []
        for i, name in enumerate(FEATURE_NAMES):
            sv = float(svc[i]) if i < len(svc) else 0.0
            direction = "positive" if sv >= 0 else "negative"

            source_map = C.FEATURE_SOURCES.get(name, {"False": "standard", "True": "standard"})
            if isinstance(source_map, dict):
                source = source_map["True"] if blank_slate else source_map["False"]
            else:
                source = source_map

            if name == "payment_regularity":
                if direction == "positive":
                    business_desc = f"Consistent {business_type} sector payment behavior across bills and taxes"
                else:
                    business_desc = f"Irregular {business_type} sector payment behavior suggests cash flow stress"
            elif name == "financial_capacity_proxy":
                if direction == "positive":
                    business_desc = f"Strong financial capacity relative to {business_type} sector peers"
                else:
                    business_desc = f"Limited financial capacity for loan servicing in {business_type} sector"
            elif name == "business_longevity":
                business_desc = (
                    "Established business history supports creditworthiness"
                    if direction == "positive"
                    else "Limited operational track record"
                )
            elif name == "data_coverage":
                business_desc = (
                    "Broad data coverage improves assessment reliability"
                    if direction == "positive"
                    else "Limited data sources constrain assessment"
                )
            elif name == "evidence_confidence":
                business_desc = (
                    "Consistent evidence across multiple sources"
                    if direction == "positive"
                    else "Conflicting signals across data sources"
                )
            elif name == "is_blank_slate_flag":
                business_desc = (
                    "Blank-slate profile — alternative data used"
                    if blank_slate
                    else "Standard data profile"
                )
            else:
                business_desc = f"{name} contributes {direction}ly"

            ranked.append({
                "feature_name": name,
                "value": float(feature_vector[0, i]) if i < feature_vector.shape[1] else 0.0,
                "shap_value": sv,
                "rank": 0,
                "direction": direction,
                "business_description": business_desc,
                "source": source,
            })

        ranked.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        for i, r in enumerate(ranked):
            r["rank"] = i + 1

        if blank_slate:
            alternative_note = C.BLANK_SLATE_REASONS[0]
        else:
            alt_count = sum(1 for r in ranked if r["source"] == "alternative")
            total = len(ranked)
            if alt_count / total >= 0.5:
                alternative_note = "Assessment heavily relies on alternative data"
            else:
                alternative_note = "Assessment based on mixed traditional and alternative data"

        top_3 = "; ".join(r["business_description"] for r in ranked[:3])
        human_readable_summary = f"{alternative_note}. {top_3}."

        traditional_contrib = 0.0
        alt_contrib = 0.0
        for r in ranked:
            if r["source"] == "standard":
                traditional_contrib += r["shap_value"]
            elif r["source"] == "alternative":
                alt_contrib += r["shap_value"]
            elif r["source"] == "mixed":
                traditional_contrib += r["shap_value"] * 0.5
                alt_contrib += r["shap_value"] * 0.5

        return {
            "shap_values": {r["feature_name"]: r["shap_value"] for r in ranked},
            "base_value": base_value,
            "feature_ranking": ranked,
            "human_readable_summary": human_readable_summary,
            "traditional_signal_contribution": traditional_contrib,
            "alternative_signal_contribution": alt_contrib,
        }

    except Exception as e:
        logger.error(f"SHAP computation failed: {e}")
        return None
