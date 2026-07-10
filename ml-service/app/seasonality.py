from . import constants as C


def get_volatility_flag(
    value: float,
    metric: str,
    business_type: str,
) -> dict:
    sector_rules = C.EXPECTED_HIGH_VOLATILITY_SECTORS.get(business_type, {})
    expected_range = sector_rules.get(metric)
    if expected_range is None:
        lo, hi = C.SEASONAL_DEFAULT_RANGE
    else:
        lo, hi = expected_range

    if value <= hi:
        return {"flag": "normal", "message": f"{metric} volatility within expected range"}

    kv = C.SEASONAL_HIGH_KV.get(metric, {})
    return {
        "flag": kv.get("label", "elevated"),
        "message": kv.get("message", f"{metric} volatility ({value:.2f}) above typical range ({lo:.2f}-{hi:.2f})"),
        "value": value,
        "expected_range": {"lo": lo, "hi": hi},
    }
