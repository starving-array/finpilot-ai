#!/usr/bin/env python3
"""
Calibrate blank-slate thresholds to maximize separation between
traditional-rich and alternative-dependent groups per business type.

Usage: python calibrate_thresholds.py [--input output/profiles.csv]
"""

import argparse
import csv
import math
from pathlib import Path

import numpy as np

import config as C


def safe_float(val, default=0.0):
    if val is None or val == "" or val == "None":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def compute_financial_capacity(turnover: float, electricity_units: float, business_type: str) -> float:
    if turnover is not None and turnover >= C.GST_TURNOVER_THRESHOLD:
        return float(min(math.sqrt(turnover) / C.FINANCIAL_CAPACITY_SQRT_DIVISOR, 1.0))
    units = safe_float(electricity_units)
    percentile = C.ELEC_90TH_PERCENTILE.get(business_type, C.DEFAULT_ELEC_PERCENTILE)
    return float(min(units / percentile, 1.0))


def calibrate_thresholds(profiles: list[dict]) -> dict:
    best_gst_thresh, best_upi_thresh = C.GST_TURNOVER_THRESHOLD, C.BST_FALLBACK["upi"]
    max_separation = 0.0

    for gst_th in range(5000, 50001, 1000):
        for upi_th in range(2, 51, 2):
            traditional_rich = [
                p for p in profiles
                if (safe_float(p.get("gst_monthly_turnover_avg"), 0) >= gst_th
                    and safe_float(p.get("upi_monthly_txn_count"), -1) >= upi_th)
            ]
            alt_dependent = [
                p for p in profiles
                if ((safe_float(p.get("gst_monthly_turnover_avg")) is None or safe_float(p.get("gst_monthly_turnover_avg"), 0) < gst_th)
                    and (safe_float(p.get("upi_monthly_txn_count"), -1) < 0 or safe_float(p.get("upi_monthly_txn_count"), -1) < upi_th))
            ]

            if len(traditional_rich) < 10 or len(alt_dependent) < 10:
                continue

            bt = p.get("business_type", "services") if profiles else "services"
            traditional_cap = np.mean([
                compute_financial_capacity(
                    safe_float(p.get("gst_monthly_turnover_avg")),
                    p.get("electricity_monthly_units_avg"),
                    p.get("business_type", "services"),
                )
                for p in traditional_rich
            ])
            alt_cap = np.mean([
                compute_financial_capacity(
                    safe_float(p.get("gst_monthly_turnover_avg")),
                    p.get("electricity_monthly_units_avg"),
                    p.get("business_type", "services"),
                )
                for p in alt_dependent
            ])
            separation = abs(traditional_cap - alt_cap)

            if separation > max_separation:
                max_separation = separation
                best_gst_thresh, best_upi_thresh = gst_th, upi_th

    return {
        "gst_turnover_threshold": best_gst_thresh,
        "upi_txn_threshold": best_upi_thresh,
        "max_separation": round(max_separation, 4),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="output/profiles.csv")
    args = parser.parse_args()

    input_path = Path(args.input)
    with open(input_path) as f:
        reader = csv.DictReader(f)
        profiles = list(reader)

    print(f"Loaded {len(profiles)} profiles from {input_path}")
    print("Calibrating blank-slate thresholds...\n")

    result = calibrate_thresholds(profiles)

    print(f"Optimal GST turnover threshold: ₹{result['gst_turnover_threshold']:,}/month")
    print(f"Optimal UPI txn threshold:       {result['upi_txn_threshold']} txns/month")
    print(f"Max separation achieved:         {result['max_separation']:.4f}")


if __name__ == "__main__":
    main()
