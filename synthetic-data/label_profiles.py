#!/usr/bin/env python3
"""
Read profiles.csv → compute features via feature_engineering → composite score → assign bucket → validate.
"""
import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import ks_2samp
from sklearn.metrics import precision_score

import config as C

FEATURE_ENGINEERING_PATH = str(Path(__file__).resolve().parent.parent / "ml-service")
if FEATURE_ENGINEERING_PATH not in sys.path:
    sys.path.insert(0, FEATURE_ENGINEERING_PATH)

from app.feature_engineering import (
    safe_float,
    safe_float_or_none,
    compute_all_features,
    FEATURE_NAMES,
)

BUCKET_THRESHOLDS = C.BUCKET_THRESHOLDS


def assign_bucket(composite_score):
    for bucket, threshold in BUCKET_THRESHOLDS:
        if composite_score >= threshold:
            return bucket
    return "no-to-go"


def pick_signal_keys(p):
    keys = []
    if safe_float(p.get("gst_filing_regularity"), -1) >= 0:
        keys.append("gst")
    if safe_float(p.get("epfo_contribution_regularity"), -1) >= 0:
        keys.append("epfo")
    if safe_float(p.get("electricity_payment_delay_days_avg"), -1) >= 0:
        keys.append("electricity")
    if safe_float(p.get("water_payment_delay_days_avg"), -1) >= 0:
        keys.append("water")
    return keys


def compute_composite_score(p, business_type):
    feats, _ = compute_all_features(
        gst_registered=p.get("gst_registered", "false").lower() in ("true", "1", "yes"),
        gst_monthly_turnover_avg=safe_float_or_none(p.get("gst_monthly_turnover_avg")),
        gst_filing_regularity=safe_float_or_none(p.get("gst_filing_regularity")),
        upi_monthly_txn_count=safe_float_or_none(p.get("upi_monthly_txn_count")),
        upi_monthly_txn_value=safe_float_or_none(p.get("upi_monthly_txn_value")),
        electricity_monthly_units_avg=safe_float_or_none(p.get("electricity_monthly_units_avg")),
        electricity_payment_delay_days_avg=safe_float_or_none(p.get("electricity_payment_delay_days_avg")),
        epfo_contribution_regularity=safe_float_or_none(p.get("epfo_contribution_regularity")),
        epfo_employee_count=safe_float_or_none(p.get("epfo_employee_count")),
        epfo_contribution_amount=safe_float_or_none(p.get("epfo_contribution_amount")),
        water_monthly_consumption_kl=safe_float_or_none(p.get("water_monthly_consumption_kl")),
        water_payment_delay_days_avg=safe_float_or_none(p.get("water_payment_delay_days_avg")),
        fuel_monthly_spend_avg=safe_float_or_none(p.get("fuel_monthly_spend_avg")),
        fuel_spend_volatility=safe_float_or_none(p.get("fuel_spend_volatility")),
        requested_loan_amount=safe_float_or_none(p.get("requested_loan_amount")),
        years_in_operation=safe_float_or_none(p.get("years_in_operation")),
        business_type=business_type,
    )
    score = (
        C.COMPOSITE_WEIGHTS["payment_regularity"] * feats["payment_regularity"]
        + C.COMPOSITE_WEIGHTS["financial_capacity_proxy"] * feats["financial_capacity_proxy"]
        + C.COMPOSITE_WEIGHTS["business_longevity"] * feats["business_longevity"]
        + C.COMPOSITE_WEIGHTS["data_coverage"] * feats["data_coverage"]
        + C.COMPOSITE_WEIGHTS["evidence_confidence"] * feats["evidence_confidence"]
    )
    return round(float(score), 4)


def validate_distribution(profiles):
    buckets = Counter(p["bucket"] for p in profiles)
    total = len(profiles)
    all_ok = True
    print("  Bucket distribution:")
    for bucket, threshold in BUCKET_THRESHOLDS:
        count = buckets.get(bucket, 0)
        pct = count / total * 100
        status = "OK" if C.BUCKET_RANGE_MIN <= pct <= C.BUCKET_RANGE_MAX else "WARN"
        if status == "WARN":
            all_ok = False
        print(f"    {bucket:20s}: {count:3d} ({pct:5.1f}%) {status}")
    if not all_ok:
        print(f"  WARNING: Some buckets outside {C.BUCKET_RANGE_MIN}-{C.BUCKET_RANGE_MAX}% range. Adjust thresholds and re-run.")
    return all_ok


def clip(value, lo, hi):
    return max(lo, min(hi, value))


def map_bucket_to_risk(bucket):
    return C.RISK_MAP[bucket]


def validate_labels(profiles, actual_outcomes):
    predicted_buckets = [assign_bucket(compute_composite_score(p, p.get("business_type", "retail"))) for p in profiles]
    risk_scores = [map_bucket_to_risk(b) for b in predicted_buckets]

    low_risk_threshold = np.percentile(risk_scores, 80)
    precision_at_20 = precision_score(
        actual_outcomes,
        [1 if s >= low_risk_threshold else 0 for s in risk_scores],
        pos_label=1,
    )

    good_scores = [risk_scores[i] for i, o in enumerate(actual_outcomes) if o == 1]
    bad_scores = [risk_scores[i] for i, o in enumerate(actual_outcomes) if o == 0]
    ks_statistic = ks_2samp(good_scores, bad_scores).statistic

    return {
        "precision_at_20": float(precision_at_20),
        "ks_statistic": float(ks_statistic),
        "is_valid": bool(precision_at_20 > C.LABEL_PRECISION_TARGET and ks_statistic > C.LABEL_KS_TARGET),
    }


def inject_known_risk_signals(profile):
    risk = 0.0
    t = C.RISK_SIGNAL_THRESHOLDS

    if safe_float(profile.get("gst_filing_regularity", 1), 1) < t["gst_filing_bad"]:
        risk += C.RISK_SIGNAL_PENALTIES["gst_filing_bad"]
    if safe_float(profile.get("epfo_contribution_regularity", 1), 1) < t["epfo_contribution_bad"]:
        risk += C.RISK_SIGNAL_PENALTIES["epfo_contribution_bad"]
    if safe_float(profile.get("electricity_payment_delay_days_avg", 0)) > t["elec_delay_bad_days"]:
        risk += C.RISK_SIGNAL_PENALTIES["elec_delay_bad"]
    if safe_float(profile.get("water_payment_delay_days_avg", 0)) > t["water_delay_bad_days"]:
        risk += C.RISK_SIGNAL_PENALTIES["water_delay_bad"]

    if safe_float(profile.get("gst_monthly_turnover_avg", 0)) > t["turnover_good"]:
        risk += C.RISK_SIGNAL_BONUSES["turnover_good"]
    if safe_int(profile.get("epfo_employee_count", 0), 0) > t["epfo_employees_good"]:
        risk += C.RISK_SIGNAL_BONUSES["epfo_employees_good"]
    if safe_float(profile.get("years_in_operation", 0)) > t["longevity_good_years"]:
        risk += C.RISK_SIGNAL_BONUSES["longevity_good"]

    return clip(risk, 0.0, 1.0)


def safe_int(val, default=None):
    if val is None or val == "" or val == "None":
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="output/profiles.csv")
    parser.add_argument("--output", default="output/profiles_labeled.csv")
    parser.add_argument("--validate", action="store_true", help="Run label validation with injected risk signals")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    with open(input_path) as f:
        reader = csv.DictReader(f)
        profiles = list(reader)

    print(f"Loaded {len(profiles)} profiles from {input_path}")

    for p in profiles:
        bt = p.get("business_type", "retail")
        score = compute_composite_score(p, bt)
        p["composite_score"] = score
        p["bucket"] = assign_bucket(score)

    if args.validate:
        print("\n=== Label Validation ===")
        true_risks = [inject_known_risk_signals(p) for p in profiles]
        pred_buckets = [p["bucket"] for p in profiles]
        pred_risks = [map_bucket_to_risk(b) for b in pred_buckets]

        low_risk_thresh = np.percentile(pred_risks, 80)
        safe_count = sum(1 for r in true_risks if r < 0.2)
        if safe_count > 0:
            precision_at_20 = sum(
                1 for i, r in enumerate(true_risks)
                if r < 0.2 and pred_risks[i] >= low_risk_thresh
            ) / safe_count
        else:
            precision_at_20 = 0.0

        good_risks = [pred_risks[i] for i, r in enumerate(true_risks) if r < 0.2]
        bad_risks = [pred_risks[i] for i, r in enumerate(true_risks) if r >= 0.2]
        ks_stat = ks_2samp(good_risks, bad_risks).statistic if good_risks and bad_risks else 0.0

        print(f"  Precision@20% (lowest risk): {precision_at_20:.4f}  (target > {C.LABEL_PRECISION_TARGET})")
        print(f"  KS statistic:                {ks_stat:.4f}  (target > {C.LABEL_KS_TARGET})")
        if precision_at_20 > C.LABEL_PRECISION_TARGET and ks_stat > C.LABEL_KS_TARGET:
            print("  ✅ Label validation PASSED")
        else:
            print("  ❌ Label validation FAILED")

    fieldnames = list(profiles[0].keys())

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(profiles)

    print(f"Labeled {len(profiles)} profiles -> {output_path}")
    print(f"\nBucket distribution (thresholds):")
    for bucket, threshold in BUCKET_THRESHOLDS:
        count = sum(1 for p in profiles if p["bucket"] == bucket)
        avg_score = np.mean([float(p["composite_score"]) for p in profiles if p["bucket"] == bucket]) if count > 0 else 0
        print(f"  {bucket:20s}: {count:3d} profiles, avg score: {avg_score:.4f}")

    print()
    ok = validate_distribution(profiles)
    exit(0 if ok else 1)


if __name__ == "__main__":
    main()
