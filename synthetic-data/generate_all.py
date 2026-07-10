#!/usr/bin/env python3
"""
FHSS Synthetic Data Generator
Generates 150+ customer profiles with varied data completeness,
traditional/alternative signals, blank-slate scenarios, and proxy labels.
"""

import json
import random
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generators.profile_generator import generate_customer_profile, generate_pan
from generators.traditional_signals import generate_gst_data, generate_upi_data, generate_bureau_data
from generators.alternative_signals import (
    generate_electricity_data,
    generate_water_data,
    generate_epfo_data,
    generate_fuel_data,
)
from generators.label_generator import generate_label_proxies, compute_consensus_label

random.seed(42)

DATE_START = datetime(2023, 1, 1)
DATE_END = datetime(2024, 6, 30)
DATE_SPAN_DAYS = (DATE_END - DATE_START).days

TOTAL_CUSTOMERS = 150
BLANK_SLATE_COUNT = 30  # 20% blank-slate scenarios

TRADITIONAL_FEATURES = [
    "gst_filing_regularity", "gst_tax_growth_yoy", "gst_compliance_score",
    "upi_txn_volume_30d", "upi_merchant_diversity", "upi_inflow_outflow_ratio",
    "bureau_score", "bureau_enquiry_velocity", "bureau_credit_utilization",
]

ALTERNATIVE_FEATURES = [
    "electricity_avg_consumption", "electricity_payment_regularity",
    "water_consumption_stability", "water_payment_regularity",
    "epfo_contribution_regularity", "epfo_employee_trend",
    "fuel_expense_regularity", "fuel_liters_cv",
]


def compute_completeness(data: dict, keys: list) -> float:
    if not keys:
        return 0.0
    present = sum(1 for k in keys if data.get(k) is not None and data.get(k, -1) >= 0)
    return present / len(keys)


def extract_features(traditional: dict, alternative: dict) -> dict:
    features = {}

    gst = traditional.get("gst", {})
    features["gst_filing_regularity"] = gst.get("filing_regularity", -1)
    features["gst_tax_growth_yoy"] = gst.get("tax_growth_yoy", -1)
    features["gst_compliance_score"] = gst.get("compliance_score", -1)

    upi = traditional.get("upi", {})
    features["upi_txn_volume_30d"] = upi.get("txn_volume_30d", -1)
    features["upi_merchant_diversity"] = upi.get("merchant_diversity", -1)
    features["upi_inflow_outflow_ratio"] = upi.get("inflow_outflow_ratio", -1)

    bureau = traditional.get("bureau", {})
    features["bureau_score"] = bureau.get("bureau_score", -1)
    features["bureau_enquiry_velocity"] = bureau.get("enquiry_count_90d", -1)
    features["bureau_credit_utilization"] = bureau.get("credit_utilization", -1)

    electricity = alternative.get("electricity", {})
    features["electricity_avg_consumption"] = electricity.get("avg_monthly_consumption", -1)
    features["electricity_payment_regularity"] = electricity.get("payment_regularity", -1)

    water = alternative.get("water", {})
    features["water_consumption_stability"] = water.get("consumption_stability", -1)
    features["water_payment_regularity"] = water.get("payment_regularity", -1)

    epfo = alternative.get("epfo", {})
    features["epfo_contribution_regularity"] = epfo.get("contribution_regularity", -1)
    features["epfo_employee_trend"] = epfo.get("employee_count_trend_6m", -999)

    fuel = alternative.get("fuel", {})
    features["fuel_expense_regularity"] = fuel.get("expense_regularity", -1)
    features["fuel_liters_cv"] = fuel.get("liters_per_month_cv", -1)

    return features


def random_profile_date() -> str:
    offset = random.randint(0, DATE_SPAN_DAYS)
    dt = DATE_START + timedelta(days=offset)
    return dt.strftime("%Y-%m")


def generate_customer(index: int, is_blank_slate: bool) -> dict:
    profile = generate_customer_profile(blank_slate=is_blank_slate, seed=index + 100)

    if is_blank_slate:
        traditional_completeness = round(random.uniform(0.0, 0.15), 2)
        alternative_completeness = round(random.uniform(0.5, 1.0), 2)
    else:
        traditional_completeness = round(random.uniform(0.5, 1.0), 2)
        alternative_completeness = round(random.uniform(0.3, 1.0), 2)

    traditional = {
        "gst": generate_gst_data(profile["vintage_months"], traditional_completeness),
        "upi": generate_upi_data(traditional_completeness),
        "bureau": generate_bureau_data() if not is_blank_slate else {},
    }

    alternative = {
        "electricity": generate_electricity_data(alternative_completeness),
        "water": generate_water_data(alternative_completeness),
        "epfo": generate_epfo_data(profile["vintage_months"], alternative_completeness),
        "fuel": generate_fuel_data(alternative_completeness),
    }

    features = extract_features(traditional, alternative)
    feat_completeness = compute_completeness(features, TRADITIONAL_FEATURES + ALTERNATIVE_FEATURES)
    trad_feat_completeness = compute_completeness(features, TRADITIONAL_FEATURES)

    proxies = generate_label_proxies(profile, traditional)
    label, label_confidence, label_scores = compute_consensus_label(proxies)

    profile_date = random_profile_date()

    return {
        "customer": profile,
        "traditional_data": traditional,
        "alternative_data": alternative,
        "features": features,
        "completeness": {
            "traditional": trad_feat_completeness,
            "overall": feat_completeness,
            "blank_slate_mode": is_blank_slate,
        },
        "labels": {
            "proxies": proxies,
            "consensus_label": label,
            "label_confidence": label_confidence,
            "label_scores": label_scores,
        },
        "profile_date": profile_date,
    }


def main():
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    all_customers = []

    blank_slate_indices = set(random.sample(range(TOTAL_CUSTOMERS), BLANK_SLATE_COUNT))

    for i in range(TOTAL_CUSTOMERS):
        is_blank_slate = i in blank_slate_indices
        customer = generate_customer(i, is_blank_slate)
        all_customers.append(customer)

    with open(output_dir / "customers.json", "w") as f:
        json.dump(all_customers, f, indent=2, default=str)

    print(f"Generated {len(all_customers)} customers")
    blank_count = sum(1 for c in all_customers if c["completeness"]["blank_slate_mode"])
    labeled_count = sum(1 for c in all_customers if c["labels"]["consensus_label"] is not None)
    print(f"  Blank-slate scenarios: {blank_count}")
    print(f"  Customers with consensus label: {labeled_count}")
    print(f"  Unlabeled: {len(all_customers) - labeled_count}")

    cat_dist = {}
    for c in all_customers:
        lbl = c["labels"]["consensus_label"]
        if lbl:
            cat_dist[lbl] = cat_dist.get(lbl, 0) + 1
    print(f"  Category distribution: {cat_dist}")
    print("Output written to output/customers.json")

    with open(output_dir / "customers.ndjson", "w") as f:
        for c in all_customers:
            f.write(json.dumps(c, default=str) + "\n")
    print("NDJSON written to output/customers.ndjson")


if __name__ == "__main__":
    main()
