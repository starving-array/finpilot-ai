from . import constants as C


def get_volatility_flag(value, metric, business_type):
    rules = C.SEASONALITY_RULES.get(business_type, {}).get(metric)
    if rules is None:
        return {"flag": "unavailable", "message": f"No seasonality data for {metric} in {business_type}"}

    if rules["relevance"] != "primary":
        return {"flag": "not_applicable", "message": rules["reason"]}

    normal_hi = rules["normal_range"][1]
    expected_hi = rules["expected_high_range"][1] if rules["expected_high_range"] else normal_hi

    if value <= expected_hi:
        return {"flag": "normal", "message": f"{metric} volatility within expected range"}

    return {
        "flag": "elevated",
        "message": rules["reason"],
        "value": value,
        "expected_range": {"lo": normal_hi, "hi": expected_hi},
    }


def compute_seasonality_penalty(observed_cvs, business_type, current_month):
    if business_type not in C.SEASONALITY_RULES:
        return {"total_penalty": 0.0, "triggered_metrics": []}

    rules = C.SEASONALITY_RULES[business_type]
    triggered = []
    total_penalty = 0.0

    for metric, observed_cv in observed_cvs.items():
        if observed_cv is None:
            continue

        if metric not in rules:
            continue

        rule = rules[metric]
        if rule["relevance"] != "primary":
            continue

        hi = rule["expected_high_range"][1] if rule["expected_high_range"] else rule["normal_range"][1]

        if observed_cv <= hi:
            continue

        penalty = rule["risk_penalty"]
        peak_discount = current_month in rule["peak_months"]
        if peak_discount:
            penalty *= C.SEASONALITY_PEAK_MONTH_DISCOUNT

        triggered.append({
            "metric": metric,
            "observed_cv": round(observed_cv, 4),
            "expected_ceiling": hi,
            "base_penalty": rule["risk_penalty"],
            "penalty_applied": round(penalty, 4),
            "peak_month_discount": peak_discount,
            "reason": rule["reason"],
        })
        total_penalty += penalty

    total_penalty = min(total_penalty, C.SEASONALITY_TOTAL_PENALTY_CAP)
    return {
        "total_penalty": round(total_penalty, 4),
        "triggered_metrics": triggered,
    }
