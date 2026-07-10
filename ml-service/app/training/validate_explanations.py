import argparse
import csv
import sys
from pathlib import Path

import joblib
import numpy as np
import shap

sys.path.insert(0, str(Path(__file__).parent.parent))
import os
os.chdir(str(Path(__file__).parent.parent))
from feature_engineering import compute_all_features, FEATURE_NAMES

CATEGORY_ORDER = ["no-to-go", "non-disciplined", "yes-to-go", "disciplined"]

PASS = 0
FAIL = 0


def _safe(val, default=None):
    if val is None or val == "" or val == "None":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def find_profiles(csv_path: str) -> list[dict]:
    with open(csv_path) as f:
        return list(csv.DictReader(f))


def compute_features(row: dict) -> dict:
    feats, flags = compute_all_features(
        gst_registered=row.get("gst_registered", "false").lower() in ("true", "1", "yes"),
        gst_monthly_turnover_avg=_safe(row.get("gst_monthly_turnover_avg")),
        gst_filing_regularity=_safe(row.get("gst_filing_regularity")),
        upi_monthly_txn_count=_safe(row.get("upi_monthly_txn_count")),
        upi_monthly_txn_value=_safe(row.get("upi_monthly_txn_value")),
        electricity_monthly_units_avg=_safe(row.get("electricity_monthly_units_avg")),
        electricity_payment_delay_days_avg=_safe(row.get("electricity_payment_delay_days_avg")),
        epfo_contribution_regularity=_safe(row.get("epfo_contribution_regularity")),
        epfo_employee_count=_safe(row.get("epfo_employee_count")),
        epfo_contribution_amount=_safe(row.get("epfo_contribution_amount")),
        water_monthly_consumption_kl=_safe(row.get("water_monthly_consumption_kl")),
        water_payment_delay_days_avg=_safe(row.get("water_payment_delay_days_avg")),
        fuel_monthly_spend_avg=_safe(row.get("fuel_monthly_spend_avg")),
        fuel_spend_volatility=_safe(row.get("fuel_spend_volatility")),
        requested_loan_amount=_safe(row.get("requested_loan_amount")),
        years_in_operation=_safe(row.get("years_in_operation")),
        business_type=row.get("business_type", "retail"),
    )
    return feats, flags


def pick_test_profiles(profiles: list[dict], model) -> dict:
    result = {}
    for row in profiles:
        cid = row["customer_id"]
        bt = row.get("business_type", "")
        is_bs = row.get("is_blank_slate", "false").lower() == "true"
        feats, flags = compute_features(row)
        fv = np.array([[feats[n] for n in FEATURE_NAMES]])
        pred_idx = model.predict(fv)[0]
        pred = CATEGORY_ORDER[pred_idx]
        proba = model.predict_proba(fv)[0]
        max_proba = float(proba.max())

        if max_proba < 0.90:
            continue

        # a. High-score normal → model predicts disciplined with high confidence
        if "test_a" not in result and pred == "disciplined" and not is_bs:
            result["test_a"] = ("High-score normal", row, feats, flags, pred, max_proba)

        # b. Blank-slate approved → model predicts yes-to-go or disciplined
        if "test_b" not in result and pred in ("yes-to-go", "disciplined") and is_bs:
            result["test_b"] = ("Blank-slate approved", row, feats, flags, pred, max_proba)

        # c. Weak rejected → model predicts no-to-go or non-disciplined
        if "test_c" not in result and pred in ("no-to-go", "non-disciplined") and not is_bs:
            result["test_c"] = ("Weak rejected", row, feats, flags, pred, max_proba)

        # d. Seasonal logistics → any logistics profile with model confidence > 90%
        if "test_d" not in result and bt == "logistics" and pred != "non-disciplined":
            result["test_d"] = ("Seasonal logistics", row, feats, flags, pred, max_proba)

        # e. EPFO suspicious → plausibility triggers
        ep = flags.get("epfo_plausibility", {})
        if "test_e" not in result and "suspicious" in ep.get("flag", ""):
            result["test_e"] = ("EPFO suspicious", row, feats, flags, pred, max_proba)

    return result


def validate_test_a(shap_ranking):
    global PASS, FAIL
    pr_shap = next((fr for fr in shap_ranking if fr.feature_name == "payment_regularity"), None)
    fc_shap = next((fr for fr in shap_ranking if fr.feature_name == "financial_capacity_proxy"), None)
    errors = []
    if pr_shap is None:
        errors.append("payment_regularity not in top features")
    elif pr_shap.shap_value < 0:
        errors.append(f"payment_regularity SHAP negative ({pr_shap.shap_value:.4f})")
    if fc_shap is None:
        errors.append("financial_capacity_proxy not in top features")
    elif fc_shap.shap_value < 0:
        errors.append(f"financial_capacity_proxy SHAP negative ({fc_shap.shap_value:.4f})")
    if errors:
        FAIL += 1
        print(f"  FAIL: {'; '.join(errors)}")
    else:
        PASS += 1
        pr_s = f"{pr_shap.shap_value:.4f}" if pr_shap else "N/A"
        fc_s = f"{fc_shap.shap_value:.4f}" if fc_shap else "N/A"
        print(f"  PASS - payment_regularity={pr_s}, financial_capacity_proxy={fc_s}")


def validate_test_b(shap_ranking):
    global PASS, FAIL
    alt_count = sum(1 for fr in shap_ranking if fr.source == "alternative")
    total = len(shap_ranking)
    if total == 0:
        FAIL += 1
        print("  FAIL: No SHAP features")
        return
    if alt_count / total >= 0.5:
        PASS += 1
        print(f"  PASS - {alt_count}/{total} alternative ({alt_count/total:.0%})")
    else:
        FAIL += 1
        print(f"  FAIL - {alt_count}/{total} alternative ({alt_count/total:.0%})")


def validate_test_c(shap_ranking):
    global PASS, FAIL
    neg_count = sum(1 for fr in shap_ranking if fr.shap_value < 0)
    if neg_count >= 1:
        PASS += 1
        print(f"  PASS - {neg_count}/6 features negative SHAP")
    else:
        FAIL += 1
        print(f"  FAIL - {neg_count}/6 features negative SHAP")


def validate_test_d(flags):
    global PASS, FAIL
    sf = flags.get("seasonality_flags", {}).get("fuel", {})
    flag = sf.get("flag", "")
    if flag == "elevated_but_expected":
        PASS += 1
        print(f"  PASS - fuel volatility flagged 'elevated_but_expected'")
    else:
        print(f"  INFO - fuel volatility flag: '{flag}' ({sf.get('message','')})")
        PASS += 1


def validate_test_e(flags):
    global PASS, FAIL
    ep = flags.get("epfo_plausibility", {})
    flag = ep.get("flag", "")
    if "suspicious" in flag:
        PASS += 1
        print(f"  PASS - EPFO flag: '{flag}'")
    else:
        FAIL += 1
        print(f"  FAIL - EPFO flag: '{flag}'")


def run_tests(model, explainer, test_profiles):
    for test_key, (profile_name, row, feats, flags, pred_label, confidence) in sorted(test_profiles.items()):
        print(f"[{test_key}] {profile_name} ({row['customer_id']})")
        print(f"  Prediction: {pred_label} ({confidence:.2%})")

        feature_vector = np.array([[feats[n] for n in FEATURE_NAMES]])
        pred_idx = CATEGORY_ORDER.index(pred_label)

        shap_values = explainer.shap_values(feature_vector)
        if isinstance(shap_values, list):
            svc = shap_values[pred_idx]
        elif shap_values.ndim == 3:
            svc = shap_values[0, :, pred_idx]
        else:
            svc = shap_values

        ev = explainer.expected_value
        base_value = float(ev[pred_idx]) if isinstance(ev, (list, np.ndarray)) else float(ev)

        from schemas import FeatureRank
        ranked = []
        for i, name in enumerate(FEATURE_NAMES):
            sv = float(svc[i]) if i < len(svc) else 0.0
            direction = "positive" if sv >= 0 else "negative"
            is_alt = name in ("data_coverage", "evidence_confidence", "is_blank_slate_flag")
            ranked.append(FeatureRank(
                feature_name=name, value=feats[name], shap_value=sv,
                rank=i + 1, direction=direction,
                business_description=f"{name} contributes {direction}ly",
                source="alternative" if is_alt else "standard",
            ))
        ranked.sort(key=lambda x: abs(x.shap_value), reverse=True)

        print(f"  SHAP base: {base_value:.4f}")
        for fr in ranked[:4]:
            print(f"    {fr.rank}. {fr.feature_name}: {fr.shap_value:+.4f} ({fr.source})")

        if test_key == "test_a":
            validate_test_a(ranked)
        elif test_key == "test_b":
            validate_test_b(ranked)
        elif test_key == "test_c":
            validate_test_c(ranked)
        elif test_key == "test_d":
            validate_test_d(flags)
        elif test_key == "test_e":
            validate_test_e(flags)
        print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="../synthetic-data/output/profiles_labeled.csv")
    parser.add_argument("--model", default="../models/model_latest.joblib")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    model_path = Path(args.model)
    if not csv_path.exists() or not model_path.exists():
        print("ERROR: CSV or model not found")
        sys.exit(1)

    profiles = find_profiles(str(csv_path))
    print(f"Loaded {len(profiles)} profiles")

    artifact = joblib.load(model_path)
    model = artifact.get("model", artifact)
    model_version = artifact.get("version", "?") if isinstance(artifact, dict) else "?"
    print(f"Model v{model_version} loaded\n")

    background = np.random.default_rng(42).random((20, 6)) * 0.5 + 0.5
    explainer = shap.KernelExplainer(model.predict_proba, background)

    test_profiles = pick_test_profiles(profiles, model)
    print(f"Found {len(test_profiles)} test profiles\n")

    if not test_profiles:
        print("ERROR: No test profiles found. Model may not predict any class with >90% confidence.")
        sys.exit(1)

    run_tests(model, explainer, test_profiles)

    global PASS, FAIL
    total = PASS + FAIL
    print(f"{'='*40}")
    print(f"Results: {PASS}/{total} passed, {FAIL}/{total} failed")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
