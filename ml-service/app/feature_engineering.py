import math

import numpy as np

try:
    from .business_weights import get_weights, apply_signal_weights
    from .seasonality import get_volatility_flag
    from .epfo_checks import check_epfo_plausibility
    from .capacity_flag import compute_capacity_flag
    from . import constants as C
except ImportError:
    from business_weights import get_weights, apply_signal_weights
    from seasonality import get_volatility_flag
    from epfo_checks import check_epfo_plausibility
    from capacity_flag import compute_capacity_flag
    import constants as C

FEATURE_NAMES = [
    "payment_regularity",
    "financial_capacity_proxy",
    "business_longevity",
    "data_coverage",
    "evidence_confidence",
    "is_blank_slate_flag",
]


def safe_float(val, default=0.0):
    if val is None or val == "" or val == "None":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def compute_payment_regularity(
    gst_filing_regularity=None,
    epfo_contribution_regularity=None,
    electricity_payment_delay_days_avg=None,
    water_payment_delay_days_avg=None,
    business_type="retail",
):
    signals = {}
    signal_keys = []

    gst = safe_float(gst_filing_regularity, -1)
    if gst >= 0:
        signals["gst"] = gst
        signal_keys.append("gst")

    epfo = safe_float(epfo_contribution_regularity, -1)
    if epfo >= 0:
        signals["epfo"] = epfo
        signal_keys.append("epfo")

    elec_delay = safe_float(electricity_payment_delay_days_avg, -1)
    if elec_delay >= 0:
        norm_delay = elec_delay / C.DELAY_DENOMINATOR_DAYS
        signals["electricity"] = max(C.MIN_SIGNAL_FLOOR, 1.0 / (1.0 + C.SMOOTHING_FACTOR * norm_delay))
        signal_keys.append("electricity")

    water_delay = safe_float(water_payment_delay_days_avg, -1)
    if water_delay >= 0:
        norm_delay = water_delay / C.DELAY_DENOMINATOR_DAYS
        signals["water"] = max(C.MIN_SIGNAL_FLOOR, 1.0 / (1.0 + C.SMOOTHING_FACTOR * norm_delay))
        signal_keys.append("water")

    if not signals:
        return 0.0

    weighted = apply_signal_weights(signals, business_type)
    values = list(weighted.values())
    return float(np.mean(values)) * len(values)


def compute_financial_capacity_proxy(
    gst_monthly_turnover_avg=None,
    electricity_monthly_units_avg=None,
    business_type="retail",
):
    turnover = safe_float(gst_monthly_turnover_avg)
    if turnover is not None and turnover >= C.GST_TURNOVER_THRESHOLD:
        return float(min(math.sqrt(turnover) / C.FINANCIAL_CAPACITY_SQRT_DIVISOR, 1.0))
    units = safe_float(electricity_monthly_units_avg)
    percentile = C.ELEC_90TH_PERCENTILE.get(business_type, C.DEFAULT_ELEC_PERCENTILE)
    return min(units / percentile, 1.0)


def compute_business_longevity(years_in_operation=None, payment_regularity=0.0, data_coverage=0.0):
    years = safe_float(years_in_operation)
    raw = min(years / C.LONGEVITY_SCALE_YEARS, 1.0)
    if years < C.LONGEVITY_CLIFF_YEARS and payment_regularity >= C.LONGEVITY_PAYMENT_GATE and data_coverage >= C.LONGEVITY_COVERAGE_GATE:
        floor = C.LONGEVITY_FLOOR_FACTOR * (1.0 - years / C.LONGEVITY_CLIFF_YEARS)
        raw = max(raw, floor)
    return raw


def compute_data_coverage(
    electricity_monthly_units_avg=None,
    electricity_payment_delay_days_avg=None,
    epfo_contribution_regularity=None,
    epfo_employee_count=None,
    water_monthly_consumption_kl=None,
    water_payment_delay_days_avg=None,
    fuel_monthly_spend_avg=None,
    fuel_spend_volatility=None,
):
    fields = {
        "electricity": [electricity_monthly_units_avg, electricity_payment_delay_days_avg],
        "epfo": [epfo_contribution_regularity, epfo_employee_count],
        "water": [water_monthly_consumption_kl, water_payment_delay_days_avg],
        "fuel": [fuel_monthly_spend_avg, fuel_spend_volatility],
    }
    present = 0.0
    for cols in fields.values():
        if any(safe_float(c, -1) >= 0 for c in cols):
            present += C.DATA_GROUP_WEIGHT
    return min(present, 1.0)


def compute_evidence_confidence(
    gst_filing_regularity=None,
    epfo_contribution_regularity=None,
    electricity_payment_delay_days_avg=None,
    water_payment_delay_days_avg=None,
):
    signals = []
    gst = safe_float(gst_filing_regularity, -1)
    if gst >= 0:
        signals.append(gst)
    epfo = safe_float(epfo_contribution_regularity, -1)
    if epfo >= 0:
        signals.append(epfo)
    elec_delay = safe_float(electricity_payment_delay_days_avg, -1)
    if elec_delay >= 0:
        norm_delay = elec_delay / C.DELAY_DENOMINATOR_DAYS
        signals.append(max(C.MIN_SIGNAL_FLOOR, 1.0 / (1.0 + C.SMOOTHING_FACTOR * norm_delay)))
    water_delay = safe_float(water_payment_delay_days_avg, -1)
    if water_delay >= 0:
        norm_delay = water_delay / C.DELAY_DENOMINATOR_DAYS
        signals.append(max(C.MIN_SIGNAL_FLOOR, 1.0 / (1.0 + C.SMOOTHING_FACTOR * norm_delay)))

    if len(signals) < C.MIN_SIGNALS_FOR_CONFIDENCE:
        return C.EVIDENCE_CONFIDENCE_FALLBACK

    arr = np.array(signals)
    mean = arr.mean()
    std = arr.std()
    cv = std / mean if mean > 0 else 1.0
    return float(min(1.0 - cv, 1.0))


def is_blank_slate(
    gst_registered=None,
    gst_monthly_turnover_avg=None,
    upi_monthly_txn_count=None,
    upi_monthly_txn_value=None,
    business_type="retail",
):
    thresholds = C.BST_THRESHOLDS.get(business_type, C.BST_FALLBACK)
    gst_thin = (
        safe_float(gst_monthly_turnover_avg) is None
        or safe_float(gst_monthly_turnover_avg, 0) < thresholds["gst"]
    )
    upi_thin = (
        safe_float(upi_monthly_txn_count, -1) < 0
        or safe_float(upi_monthly_txn_count, -1) < thresholds["upi"]
    )
    return gst_thin and upi_thin


def compute_all_features(
    gst_registered=None,
    gst_monthly_turnover_avg=None,
    gst_filing_regularity=None,
    upi_monthly_txn_count=None,
    upi_monthly_txn_value=None,
    electricity_monthly_units_avg=None,
    electricity_payment_delay_days_avg=None,
    epfo_contribution_regularity=None,
    epfo_employee_count=None,
    epfo_contribution_amount=None,
    water_monthly_consumption_kl=None,
    water_payment_delay_days_avg=None,
    fuel_monthly_spend_avg=None,
    fuel_spend_volatility=None,
    requested_loan_amount=None,
    years_in_operation=None,
    business_type="retail",
):
    payment_reg = compute_payment_regularity(
        gst_filing_regularity=gst_filing_regularity,
        epfo_contribution_regularity=epfo_contribution_regularity,
        electricity_payment_delay_days_avg=electricity_payment_delay_days_avg,
        water_payment_delay_days_avg=water_payment_delay_days_avg,
        business_type=business_type,
    )
    financial_cap = compute_financial_capacity_proxy(
        gst_monthly_turnover_avg=gst_monthly_turnover_avg,
        electricity_monthly_units_avg=electricity_monthly_units_avg,
        business_type=business_type,
    )
    data_cov = compute_data_coverage(
        electricity_monthly_units_avg=electricity_monthly_units_avg,
        electricity_payment_delay_days_avg=electricity_payment_delay_days_avg,
        epfo_contribution_regularity=epfo_contribution_regularity,
        epfo_employee_count=epfo_employee_count,
        water_monthly_consumption_kl=water_monthly_consumption_kl,
        water_payment_delay_days_avg=water_payment_delay_days_avg,
        fuel_monthly_spend_avg=fuel_monthly_spend_avg,
        fuel_spend_volatility=fuel_spend_volatility,
    )
    longevity = compute_business_longevity(
        years_in_operation=years_in_operation,
        payment_regularity=payment_reg,
        data_coverage=data_cov,
    )
    evidence_conf = compute_evidence_confidence(
        gst_filing_regularity=gst_filing_regularity,
        epfo_contribution_regularity=epfo_contribution_regularity,
        electricity_payment_delay_days_avg=electricity_payment_delay_days_avg,
        water_payment_delay_days_avg=water_payment_delay_days_avg,
    )
    blank_slate = is_blank_slate(
        gst_registered=gst_registered,
        gst_monthly_turnover_avg=gst_monthly_turnover_avg,
        upi_monthly_txn_count=upi_monthly_txn_count,
        upi_monthly_txn_value=upi_monthly_txn_value,
        business_type=business_type,
    )

    features = {
        "payment_regularity": round(payment_reg, 4),
        "financial_capacity_proxy": round(financial_cap, 4),
        "business_longevity": round(longevity, 4),
        "data_coverage": round(data_cov, 4),
        "evidence_confidence": round(evidence_conf, 4),
        "is_blank_slate_flag": 1.0 if blank_slate else 0.0,
    }

    flags = {
        "is_blank_slate": blank_slate,
        "epfo_plausibility": check_epfo_plausibility(epfo_employee_count, epfo_contribution_amount),
        "capacity_flag": compute_capacity_flag(
            requested_loan_amount=requested_loan_amount,
            gst_monthly_turnover_avg=gst_monthly_turnover_avg,
            electricity_monthly_units_avg=electricity_monthly_units_avg,
            business_type=business_type,
        ),
        "seasonality_flags": {
            "fuel": get_volatility_flag(safe_float(fuel_spend_volatility), "fuel", business_type),
            "electricity": get_volatility_flag(
                safe_float(electricity_payment_delay_days_avg) / C.DELAY_DENOMINATOR_DAYS if safe_float(electricity_payment_delay_days_avg, -1) >= 0 else 0.0,
                "electricity",
                business_type,
            ),
        },
    }

    return features, flags
