import json
import numpy as np
from pathlib import Path
from typing import Optional


FEATURE_NAMES = [
    "gst_filing_regularity", "gst_tax_growth_yoy", "gst_compliance_score",
    "upi_txn_volume_30d", "upi_merchant_diversity", "upi_inflow_outflow_ratio",
    "bureau_score", "bureau_enquiry_velocity", "bureau_credit_utilization",
    "electricity_avg_consumption", "electricity_payment_regularity",
    "water_consumption_stability", "water_payment_regularity",
    "epfo_contribution_regularity", "epfo_employee_trend",
    "fuel_expense_regularity", "fuel_liters_cv",
]

CATEGORY_MAP = {
    "YES_TO_GO": 0,
    "DISCIPLINED": 1,
    "NON_DISCIPLINED": 2,
    "NO_TO_GO": 3,
}

INVERSE_CATEGORY_MAP = {v: k for k, v in CATEGORY_MAP.items()}

WINSOR_LOWER = 0.01
WINSOR_UPPER = 0.99
MISSING_SENTINEL = -999.0


def load_customers(path: str | Path) -> list[dict]:
    path = Path(path)
    with open(path) as f:
        return json.load(f)


def filter_labeled(customers: list[dict]) -> tuple[list[dict], list[str]]:
    labeled = []
    labels = []
    for c in customers:
        label = c.get("labels", {}).get("consensus_label")
        if label and label in CATEGORY_MAP:
            labeled.append(c)
            labels.append(label)
    return labeled, labels


def extract_feature_matrix(customers: list[dict]) -> np.ndarray:
    n = len(customers)
    m = len(FEATURE_NAMES)
    X = np.full((n, m), MISSING_SENTINEL, dtype=np.float64)

    for i, c in enumerate(customers):
        features = c.get("features", {})
        for j, name in enumerate(FEATURE_NAMES):
            val = features.get(name, MISSING_SENTINEL)
            if val is not None and val != MISSING_SENTINEL:
                X[i, j] = float(val)

    return X


def encode_labels(labels: list[str]) -> np.ndarray:
    return np.array([CATEGORY_MAP[l] for l in labels], dtype=np.int32)


def impute_missing(X: np.ndarray) -> np.ndarray:
    X_out = X.copy()
    for j in range(X.shape[1]):
        col = X[:, j]
        valid = col[col != MISSING_SENTINEL]
        if len(valid) > 0:
            median_val = np.median(valid)
            X_out[:, j] = np.where(col == MISSING_SENTINEL, median_val, col)
        else:
            X_out[:, j] = 0.0
    return X_out


def winsorize(X: np.ndarray) -> np.ndarray:
    X_out = X.copy()
    for j in range(X.shape[1]):
        col = X[:, j]
        lower = np.percentile(col, WINSOR_LOWER * 100)
        upper = np.percentile(col, WINSOR_UPPER * 100)
        X_out[:, j] = np.clip(col, lower, upper)
    return X_out


def add_missingness_indicators(X: np.ndarray) -> np.ndarray:
    missing_mask = (X == MISSING_SENTINEL).astype(np.float64)
    return np.hstack([X, missing_mask])


def build_feature_pipeline(customers: list[dict]) -> tuple[np.ndarray, np.ndarray, list[str], dict]:
    labeled_customers, label_strings = filter_labeled(customers)

    if not labeled_customers:
        raise ValueError("No labeled customers found")

    X_raw = extract_feature_matrix(labeled_customers)
    y = encode_labels(label_strings)

    X_imputed = impute_missing(X_raw)
    X_winsor = winsorize(X_imputed)
    X_augmented = add_missingness_indicators(X_winsor)

    metadata = {
        "n_samples": len(labeled_customers),
        "n_features": X_augmented.shape[1],
        "base_features": FEATURE_NAMES,
        "augmented_features": FEATURE_NAMES + [f"{name}_missing" for name in FEATURE_NAMES],
        "category_mapping": CATEGORY_MAP,
        "label_distribution": {
            label: label_strings.count(label) for label in sorted(set(label_strings))
        },
    }

    return X_augmented, y, label_strings, metadata
