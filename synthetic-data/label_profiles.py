#!/usr/bin/env python3
"""
Read profiles.csv → compute composite score → assign bucket → validate distribution.
Formula from new_architecture.md Section 5.6.

Usage: python label_profiles.py [--input output/profiles.csv] [--output output/profiles_labeled.csv]
"""

import argparse
import csv
import math
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import ks_2samp
from sklearn.metrics import precision_score

import config as C

BUCKET_THRESHOLDS = C.BUCKET_THRESHOLDS


def safe_float(val, default=0.0):
    if val is None or val == "" or val == "None":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val, default=None):
    if val is None or val == "" or val == "None":
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def pick_signal_keys(p: dict) -> list:
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


def compute_payment_regularity(p: dict, business_type: str) -> float:
    signals = []
    signal_keys = []

    gst_reg = safe_float(p.get("gst_filing_regularity"), -1)
    if gst_reg >= 0:
        signals.append(gst_reg)
        signal_keys.append("gst")

    epfo_reg = safe_float(p.get("epfo_contribution_regularity"), -1)
    if epfo_reg >= 0:
        signals.append(epfo_reg)
        signal_keys.append("epfo")

    elec_delay = safe_float(p.get("electricity_payment_delay_days_avg"), -1)
    if elec_delay >= 0:
        norm_delay = elec_delay / C.DELAY_DENOMINATOR_DAYS
        signals.append(max(C.MIN_SIGNAL_FLOOR, 1.0 / (1.0 + C.SMOOTHING_FACTOR * norm_delay)))
        signal_keys.append("electricity")

    water_delay = safe_float(p.get("water_payment_delay_days_avg"), -1)
    if water_delay >= 0:
        norm_delay = water_delay / C.DELAY_DENOMINATOR_DAYS
        signals.append(max(C.MIN_SIGNAL_FLOOR, 1.0 / (1.0 + C.SMOOTHING_FACTOR * norm_delay)))
        signal_keys.append("water")

    if not signals:
        return 0.0

    weights = C.SIGNAL_WEIGHTS.get(business_type, {})
    weighted = [s * weights.get(k, 1.0) for s, k in zip(signals, signal_keys)]
    total_weight = sum(weights.get(k, 1.0) for k in signal_keys)
    normalized = [ws / total_weight * len(signals) for ws in weighted]

    return float(np.mean(normalized))


def compute_financial_capacity(p: dict, business_type: str) -> float:
    turnover = safe_float(p.get("gst_monthly_turnover_avg"))
    if turnover is not None and turnover >= C.GST_TURNOVER_THRESHOLD:
        return min(math.sqrt(turnover) / C.FINANCIAL_CAPACITY_SQRT_DIVISOR, 1.0)
    units = safe_float(p.get("electricity_monthly_units_avg"))
    percentile = C.ELEC_90TH_PERCENTILE.get(business_type, C.DEFAULT_ELEC_PERCENTILE)
    return min(units / percentile, 1.0)


def compute_data_coverage(p: dict) -> float:
    present = 0.0
    for cols in C.DATA_GROUPS.values():
        if any(safe_float(p.get(c), -1) >= 0 for c in cols):
            present += C.DATA_GROUP_WEIGHT
    return present


def compute_evidence_confidence(p: dict) -> float:
    signals = []
    gst_reg = safe_float(p.get("gst_filing_regularity"), -1)
    if gst_reg >= 0:
        signals.append(gst_reg)
    epfo_reg = safe_float(p.get("epfo_contribution_regularity"), -1)
    if epfo_reg >= 0:
        signals.append(epfo_reg)
    elec_delay = safe_float(p.get("electricity_payment_delay_days_avg"), -1)
    if elec_delay >= 0:
        norm_delay = elec_delay / C.DELAY_DENOMINATOR_DAYS
        signals.append(max(C.MIN_SIGNAL_FLOOR, 1.0 / (1.0 + C.SMOOTHING_FACTOR * norm_delay)))
    water_delay = safe_float(p.get("water_payment_delay_days_avg"), -1)
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


def compute_business_longevity(p: dict, payment_regularity: float, data_coverage: float) -> float:
    years = safe_float(p.get("years_in_operation"))
    raw = min(years / C.LONGEVITY_SCALE_YEARS, 1.0)
    if years < C.LONGEVITY_CLIFF_YEARS and payment_regularity >= C.LONGEVITY_PAYMENT_GATE and data_coverage >= C.LONGEVITY_COVERAGE_GATE:
        floor = C.LONGEVITY_FLOOR_FACTOR * (1.0 - years / C.LONGEVITY_CLIFF_YEARS)
        raw = max(raw, floor)
    return raw


def compute_composite_score(p: dict, business_type: str) -> float:
    coverage = compute_data_coverage(p)
    payment_reg = compute_payment_regularity(p, business_type)
    financial_cap = compute_financial_capacity(p, business_type)
    longevity = compute_business_longevity(p, payment_reg, coverage)
    evidence_conf = compute_evidence_confidence(p)

    score = (
        C.COMPOSITE_WEIGHTS["payment_regularity"] * payment_reg
        + C.COMPOSITE_WEIGHTS["financial_capacity_proxy"] * financial_cap
        + C.COMPOSITE_WEIGHTS["business_longevity"] * longevity
        + C.COMPOSITE_WEIGHTS["data_coverage"] * coverage
        + C.COMPOSITE_WEIGHTS["evidence_confidence"] * evidence_conf
    )
    return round(float(score), 4)


def assign_bucket(composite_score: float) -> str:
    for bucket, threshold in BUCKET_THRESHOLDS:
        if composite_score >= threshold:
            return bucket
    return "no-to-go"


def validate_distribution(profiles: list) -> bool:
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


def clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def map_bucket_to_risk(bucket: str) -> float:
    return C.RISK_MAP[bucket]


def validate_labels(profiles: list[dict], actual_outcomes: list[float]) -> dict:
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


def compute_label_probabilities(p: dict) -> dict:
    def _map_to_01(value: float) -> float:
        return clip(value, 0.0, 1.0)

    repayment_score = _map_to_01(p.get("loan_repayment_history", 0.5) if p.get("loan_repayment_history") else 0.5)
    vendor_score = _map_to_01(p.get("vendor_payment_discipline", 0.5) if p.get("vendor_payment_discipline") else 0.5)
    continuity_score = _map_to_01(p.get("business_continuity", 0.5) if p.get("business_continuity") else 0.5)

    weights = {
        "repayment": 0.5 * 0.6,
        "vendor": 0.3 * 0.5,
        "continuity": 0.2 * 0.4,
    }
    total_weight = sum(weights.values())

    disciplined_prob = (
        weights["repayment"] * repayment_score
        + weights["vendor"] * vendor_score
        + weights["continuity"] * continuity_score
    ) / total_weight

    return {
        "yes_to_go_prob": max(0, disciplined_prob - 0.2),
        "disciplined_prob": disciplined_prob,
        "non_disciplined_prob": max(0, 0.5 - disciplined_prob),
        "no_to_go_prob": max(0, 0.3 - disciplined_prob),
    }


def inject_known_risk_signals(profile: dict) -> float:
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
