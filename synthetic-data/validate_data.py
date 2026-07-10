#!/usr/bin/env python3
"""
Data validation script for synthetic data.
Verifies data integrity, completeness, and referential consistency.
"""

import json
from pathlib import Path
from collections import Counter


def validate_customers(customers: list[dict]) -> list[str]:
    errors = []
    pans = set()

    for i, c in enumerate(customers):
        profile = c["customer"]

        # PAN validation
        pan = profile["pan"]
        if pan in pans:
            errors.append(f"Customer {i}: Duplicate PAN {pan}")
        pans.add(pan)

        if not pan or len(pan) != 10:
            errors.append(f"Customer {i}: Invalid PAN length {pan}")

        # Required fields
        if not profile.get("name"):
            errors.append(f"Customer {i}: Missing name")
        if not profile.get("kyc_status"):
            errors.append(f"Customer {i}: Missing KYC status")

        # UUID format
        try:
            import uuid
            uuid.UUID(profile["customer_id"])
        except (ValueError, KeyError):
            errors.append(f"Customer {i}: Invalid customer_id")

        # Completeness check
        comp = c.get("completeness", {})
        if comp.get("blank_slate_mode"):
            if comp.get("traditional", 1) > 0.3:
                errors.append(f"Customer {i}: Blank-slate flag but traditional completeness {comp.get('traditional')} > 0.3")

        # Features should have proper values
        features = c.get("features", {})
        if not features:
            errors.append(f"Customer {i}: Empty features")

        # Label validation
        label = c.get("labels", {}).get("consensus_label")
        if label and label not in ["YES_TO_GO", "DISCIPLINED", "NON_DISCIPLINED", "NO_TO_GO"]:
            errors.append(f"Customer {i}: Invalid label {label}")

    return errors


def validate_completeness_distribution(customers: list[dict]) -> list[str]:
    warnings = []
    comps = [c["completeness"]["overall"] for c in customers]
    blank_count = sum(1 for c in customers if c["completeness"]["blank_slate_mode"])

    avg_comp = sum(comps) / len(comps) if comps else 0
    if avg_comp < 0.3 or avg_comp > 0.9:
        warnings.append(f"Average completeness {avg_comp:.2f} outside expected range [0.3, 0.9]")

    if blank_count < 20:
        warnings.append(f"Only {blank_count} blank-slate scenarios (expected >= 20)")

    return warnings


def validate_label_distribution(customers: list[dict]) -> list[str]:
    warnings = []
    labels = Counter()

    for c in customers:
        lbl = c["labels"]["consensus_label"]
        if lbl:
            labels[lbl] += 1

    if not labels:
        warnings.append("No consensus labels generated")
    else:
        total = sum(labels.values())
        for cat in ["YES_TO_GO", "DISCIPLINED", "NON_DISCIPLINED", "NO_TO_GO"]:
            pct = labels.get(cat, 0) / total * 100
            if pct < 5:
                warnings.append(f"Category {cat} only {pct:.1f}% of labeled data (may cause class imbalance)")

    return warnings


def validate_feature_coverage(customers: list[dict]) -> list[str]:
    warnings = []
    feature_keys = set()

    for c in customers:
        feature_keys.update(c.get("features", {}).keys())

    expected = {
        "gst_filing_regularity", "gst_tax_growth_yoy", "gst_compliance_score",
        "upi_txn_volume_30d", "upi_merchant_diversity", "upi_inflow_outflow_ratio",
        "bureau_score", "bureau_enquiry_velocity", "bureau_credit_utilization",
        "electricity_avg_consumption", "electricity_payment_regularity",
        "water_consumption_stability", "water_payment_regularity",
        "epfo_contribution_regularity", "epfo_employee_trend",
        "fuel_expense_regularity", "fuel_liters_cv",
    }

    missing = expected - feature_keys
    if missing:
        warnings.append(f"Missing expected features: {missing}")

    extra = feature_keys - expected
    if extra:
        warnings.append(f"Unexpected features: {extra}")

    return warnings


def main():
    customers_file = Path(__file__).parent / "output" / "customers.json"
    if not customers_file.exists():
        print(f"Error: {customers_file} not found. Run generate_all.py first.")
        return

    with open(customers_file) as f:
        customers = json.load(f)

    print(f"Validating {len(customers)} customer records...\n")

    all_errors = []
    all_errors.extend(validate_customers(customers))
    all_errors.extend(validate_completeness_distribution(customers))
    all_errors.extend(validate_label_distribution(customers))
    all_errors.extend(validate_feature_coverage(customers))

    if not all_errors:
        print("  All validations passed!")
    else:
        print(f"  Found {len(all_errors)} issue(s):")
        for err in all_errors:
            print(f"    - {err}")

    # Summary stats
    comps = [c["completeness"]["overall"] for c in customers]
    print(f"\n  Average completeness: {sum(comps)/len(comps):.2f}")
    print(f"  Min completeness: {min(comps):.2f}")
    print(f"  Max completeness: {max(comps):.2f}")

    blank_count = sum(1 for c in customers if c["completeness"]["blank_slate_mode"])
    print(f"  Blank-slate scenarios: {blank_count}")

    labeled = sum(1 for c in customers if c["labels"]["consensus_label"])
    print(f"  Labeled customers: {labeled}")
    print(f"  Unlabeled customers: {len(customers) - labeled}")

    from collections import Counter
    labels = Counter()
    for c in customers:
        lbl = c["labels"]["consensus_label"]
        if lbl:
            labels[lbl] += 1
    if labels:
        print(f"  Label distribution: {dict(labels)}")


if __name__ == "__main__":
    main()
