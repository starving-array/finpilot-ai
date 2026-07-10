"""
Extended feature engineering for the shadow model.

This module generates ~47 features from the same 16 raw input signals.
Features fall into 4 categories:
  1. Approved features (6) — same as the production model, for baseline comparison
  2. Missingness indicators (16) — one per raw field
  3. Interaction features (~15) — pairwise signal interactions
  4. Derived features (~10) — ratios, squared terms, business-type encodings

The shadow model uses ALL features. The approved model uses only category 1.
"""
import math

import numpy as np

try:
    from .feature_engineering import (
        compute_payment_regularity,
        compute_financial_capacity_proxy,
        compute_business_longevity,
        compute_data_coverage,
        compute_evidence_confidence,
        safe_float,
        FEATURE_NAMES as APPROVED_FEATURE_NAMES,
    )
except ImportError:
    from feature_engineering import (
        compute_payment_regularity,
        compute_financial_capacity_proxy,
        compute_business_longevity,
        compute_data_coverage,
        compute_evidence_confidence,
        safe_float,
        FEATURE_NAMES as APPROVED_FEATURE_NAMES,
    )

BUSINESS_TYPES = ["manufacturing", "logistics", "retail", "services", "trading"]
RAW_FIELDS = [
    "gst_registered", "gst_monthly_turnover_avg", "gst_filing_regularity",
    "upi_monthly_txn_count", "upi_monthly_txn_value",
    "electricity_monthly_units_avg", "electricity_payment_delay_days_avg",
    "epfo_contribution_regularity", "epfo_employee_count", "epfo_contribution_amount",
    "water_monthly_consumption_kl", "water_payment_delay_days_avg",
    "fuel_monthly_spend_avg", "fuel_spend_volatility",
    "requested_loan_amount", "years_in_operation",
]

SHADOW_FEATURE_NAMES = []


def compute_missingness(row: dict) -> dict:
    """One binary flag per raw field: 1 if present, 0 if null/missing."""
    flags = {}
    for field in RAW_FIELDS:
        val = row.get(field)
        flags[f"has_{field}"] = 1.0 if (val is not None and val != "" and val != "None") else 0.0
    return flags


def compute_interactions(row: dict) -> dict:
    """Pairwise interactions between key payment signals."""
    interactions = {}

    elec_delay = safe_float(row.get("electricity_payment_delay_days_avg", -1))
    water_delay = safe_float(row.get("water_payment_delay_days_avg", -1))
    epfo_reg = safe_float(row.get("epfo_contribution_regularity", -1))
    gst_reg = safe_float(row.get("gst_filing_regularity", -1))

    gst_turnover = safe_float(row.get("gst_monthly_turnover_avg", 0))
    loan = safe_float(row.get("requested_loan_amount", 0))
    years = safe_float(row.get("years_in_operation", 0))
    upi_count = safe_float(row.get("upi_monthly_txn_count", -1))
    upi_value = safe_float(row.get("upi_monthly_txn_value", 0))

    if elec_delay >= 0 and water_delay >= 0:
        interactions["elec_x_water_delay"] = elec_delay * water_delay
    else:
        interactions["elec_x_water_delay"] = -99.0

    if epfo_reg >= 0 and gst_reg >= 0:
        interactions["gst_x_epfo_regularity"] = gst_reg * epfo_reg
    else:
        interactions["gst_x_epfo_regularity"] = -99.0

    if elec_delay >= 0 and epfo_reg >= 0:
        interactions["elec_x_epfo"] = (1.0 - min(elec_delay / 45, 1.0)) * epfo_reg
    else:
        interactions["elec_x_epfo"] = -99.0

    if gst_turnover > 0 and years > 0:
        interactions["turnover_x_longevity"] = math.log10(gst_turnover) * years
    else:
        interactions["turnover_x_longevity"] = -99.0

    if loan > 0 and gst_turnover > 0:
        interactions["loan_x_turnover_ratio"] = loan / gst_turnover if gst_turnover > 0 else -99.0
    elif loan > 0:
        interactions["loan_x_turnover_ratio"] = 99.0
    else:
        interactions["loan_x_turnover_ratio"] = -99.0

    if upi_count >= 0 and upi_value > 0:
        avg_txn_value = upi_value / max(upi_count, 1)
        interactions["upi_avg_txn_value"] = avg_txn_value
    else:
        interactions["upi_avg_txn_value"] = -99.0

    fuel_vol = safe_float(row.get("fuel_spend_volatility", -1))
    fuel_spend = safe_float(row.get("fuel_monthly_spend_avg", 0))
    if fuel_vol >= 0 and fuel_spend > 0:
        interactions["fuel_vol_x_spend"] = fuel_vol * fuel_spend
    else:
        interactions["fuel_vol_x_spend"] = -99.0

    interactions["gst_squared"] = gst_turnover ** 2 if gst_turnover > 0 else -99.0

    return interactions


def compute_derived_features(row: dict) -> dict:
    """Business-type encoding, ratio features, variance across payment signals."""
    derived = {}
    business_type = row.get("business_type", "retail")

    for bt in BUSINESS_TYPES:
        derived[f"is_{bt}"] = 1.0 if business_type == bt else 0.0

    loan = safe_float(row.get("requested_loan_amount", 0))
    years = safe_float(row.get("years_in_operation", 0))
    gst_turnover = safe_float(row.get("gst_monthly_turnover_avg", 0))

    derived["loan_per_year_operating"] = loan / max(years, 0.5) if loan > 0 else 0.0

    if gst_turnover > 0 and years > 0:
        derived["turnover_per_year"] = gst_turnover / max(years, 0.5)
    else:
        derived["turnover_per_year"] = 0.0

    elec_units = safe_float(row.get("electricity_monthly_units_avg", 0))
    epfo_count = safe_float(row.get("epfo_employee_count", -1))
    if elec_units > 0 and epfo_count > 0:
        derived["elec_per_employee"] = elec_units / epfo_count
    else:
        derived["elec_per_employee"] = 0.0

    epfo_amt = safe_float(row.get("epfo_contribution_amount", 0))
    if epfo_count > 0 and epfo_amt > 0:
        derived["implied_wage_per_emp"] = (epfo_amt / 0.24) / epfo_count
    else:
        derived["implied_wage_per_emp"] = 0.0

    fuel_spend = safe_float(row.get("fuel_monthly_spend_avg", 0))
    fuel_vol = safe_float(row.get("fuel_spend_volatility", -1))
    if fuel_spend > 0 and fuel_vol >= 0:
        derived["fuel_risk_score"] = fuel_spend * fuel_vol
    else:
        derived["fuel_risk_score"] = 0.0

    return derived


def compute_shadow_features(row: dict) -> dict:
    """Compute all ~47 shadow model features for one profile row."""
    features = {}

    approved_feats, _ = compute_all_features_shadow(row)
    for k, v in approved_feats.items():
        features[k] = v

    missingness = compute_missingness(row)
    features.update(missingness)

    interactions = compute_interactions(row)
    features.update(interactions)

    derived = compute_derived_features(row)
    features.update(derived)

    return features


def compute_all_features_shadow(row: dict) -> tuple:
    """Replicates compute_all_features from feature_engineering.py for a single dict row."""
    from feature_engineering import compute_all_features
    return compute_all_features(
        gst_registered=row.get("gst_registered", "false").lower() in ("true", "1", "yes"),
        gst_monthly_turnover_avg=safe_float(row.get("gst_monthly_turnover_avg")),
        gst_filing_regularity=safe_float(row.get("gst_filing_regularity")),
        upi_monthly_txn_count=safe_float(row.get("upi_monthly_txn_count")),
        upi_monthly_txn_value=safe_float(row.get("upi_monthly_txn_value")),
        electricity_monthly_units_avg=safe_float(row.get("electricity_monthly_units_avg")),
        electricity_payment_delay_days_avg=safe_float(row.get("electricity_payment_delay_days_avg")),
        epfo_contribution_regularity=safe_float(row.get("epfo_contribution_regularity")),
        epfo_employee_count=safe_float(row.get("epfo_employee_count")),
        epfo_contribution_amount=safe_float(row.get("epfo_contribution_amount")),
        water_monthly_consumption_kl=safe_float(row.get("water_monthly_consumption_kl")),
        water_payment_delay_days_avg=safe_float(row.get("water_payment_delay_days_avg")),
        fuel_monthly_spend_avg=safe_float(row.get("fuel_monthly_spend_avg")),
        fuel_spend_volatility=safe_float(row.get("fuel_spend_volatility")),
        requested_loan_amount=safe_float(row.get("requested_loan_amount")),
        years_in_operation=safe_float(row.get("years_in_operation")),
        business_type=row.get("business_type", "retail"),
    )


def get_shadow_feature_names() -> list[str]:
    if not SHADOW_FEATURE_NAMES:
        sample = {k: 0.0 for k in APPROVED_FEATURE_NAMES}
        sample.update({f"has_{f}": 0.0 for f in RAW_FIELDS})
        sample.update({
            "elec_x_water_delay": 0.0,
            "gst_x_epfo_regularity": 0.0,
            "elec_x_epfo": 0.0,
            "turnover_x_longevity": 0.0,
            "loan_x_turnover_ratio": 0.0,
            "upi_avg_txn_value": 0.0,
            "fuel_vol_x_spend": 0.0,
            "gst_squared": 0.0,
        })
        for bt in BUSINESS_TYPES:
            sample[f"is_{bt}"] = 0.0
        sample.update({
            "loan_per_year_operating": 0.0,
            "turnover_per_year": 0.0,
            "elec_per_employee": 0.0,
            "implied_wage_per_emp": 0.0,
            "fuel_risk_score": 0.0,
        })
        SHADOW_FEATURE_NAMES.extend(sample.keys())
    return SHADOW_FEATURE_NAMES
