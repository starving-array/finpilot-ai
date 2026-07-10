"""
Shadow Model Pipeline — offline script.

Trains a LightGBM model on extended features (~47), compares its AUC against
the approved sklearn GBM (6 features), and outputs a JSON summary:
  {"auc_gap": 0.03, "top_new_features": ["fuel_x_water_interaction: 0.08", ...]}

Usage:
    python shadow_model_pipeline.py [--csv ../synthetic-data/output/profiles_labeled.csv]

This is a production foundation tool (Phase 8). It does NOT replace the approved model.
It runs offline and alerts when the shadow model discovers patterns the approved model misses.
"""
import json
import logging
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from training.train_model import (
    load_labeled_csv,
    CATEGORY_MAP,
    INVERSE_CATEGORY_MAP,
    CATEGORY_ORDER,
    _safe,
    _safe_int,
    SEED,
    TEST_SIZE,
    compute_dataset_hash,
)
from training.feature_engineering_extended import (
    compute_shadow_features,
    APPROVED_FEATURE_NAMES,
)
from feature_engineering import FEATURE_NAMES

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def train_and_compare(csv_path: str | Path) -> dict:
    csv_path = Path(csv_path)
    rows = load_labeled_csv(csv_path)
    logger.info(f"Shadow pipeline loaded {len(rows)} profiles from {csv_path}")

    X_approved_list = []
    X_shadow_list = []
    y_list = []
    skipped = 0

    for row in rows:
        label = row.get("bucket", "")
        if label not in CATEGORY_MAP:
            skipped += 1
            continue

        approved_feats, _ = compute_all_features_from_row_shadow(row)
        X_approved_list.append([approved_feats[n] for n in FEATURE_NAMES])

        shadow_feats = compute_shadow_features(row)
        X_shadow_list.append([shadow_feats[n] for n in shadow_feats])

        y_list.append(CATEGORY_MAP[label])

    if skipped:
        logger.warning(f"Skipped {skipped} rows with unknown labels")

    X_approved = np.array(X_approved_list, dtype=np.float64)
    X_shadow = np.array(X_shadow_list, dtype=np.float64)
    y = np.array(y_list, dtype=np.int32)

    n_samples, n_approved = X_approved.shape
    n_shadow = X_shadow.shape[1]
    logger.info(f"Shadow feature matrix: {X_shadow.shape} ({n_shadow} features vs {n_approved} approved)")

    from sklearn.model_selection import train_test_split
    X_approved_train, X_approved_test, X_shadow_train, X_shadow_test, y_train, y_test = train_test_split(
        X_approved, X_shadow, y, test_size=TEST_SIZE, random_state=SEED, stratify=y,
    )
    logger.info(f"Train: {X_approved_train.shape[0]}, Test: {X_approved_test.shape[0]}")

    from sklearn.ensemble import GradientBoostingClassifier
    approved_model = GradientBoostingClassifier(
        n_estimators=200, learning_rate=0.05, max_depth=4,
        min_samples_leaf=5, random_state=SEED,
    )
    approved_model.fit(X_approved_train, y_train)

    try:
        import lightgbm as lgb
        shadow_model = lgb.LGBMClassifier(
            n_estimators=500, learning_rate=0.03, max_depth=6,
            min_child_samples=5, num_leaves=31, random_state=SEED,
            verbose=-1,
        )
        shadow_model.fit(X_shadow_train, y_train)
        shadow_auc = _compute_macro_auc(shadow_model, X_shadow_test, y_test)
    except ImportError:
        logger.warning("lightgbm not installed — using sklearn GBM as proxy shadow model")
        shadow_model = GradientBoostingClassifier(
            n_estimators=500, learning_rate=0.03, max_depth=6,
            min_samples_leaf=5, random_state=SEED,
        )
        shadow_model.fit(X_shadow_train, y_train)
        shadow_auc = _compute_macro_auc_approx(shadow_model, X_shadow_test, y_test)

    approved_auc = _compute_macro_auc_approx(approved_model, X_approved_test, y_test)
    auc_gap = shadow_auc - approved_auc

    approved_f1 = _compute_macro_f1(approved_model, X_approved_test, y_test)
    shadow_f1 = _compute_macro_f1(shadow_model, X_shadow_test, y_test)

    feature_importance = _get_top_new_features(
        shadow_model, APPROVED_FEATURE_NAMES,
        compute_shadow_features(rows[0]).keys(),
    )

    summary = {
        "approved_model": "sklearn GBM (6 approved features)",
        "shadow_model": "LightGBM ({} features)".format(n_shadow) if 'lightgbm' in sys.modules else "sklearn GBM ({} features)".format(n_shadow),
        "n_profiles": len(rows),
        "n_approved_features": n_approved,
        "n_shadow_features": n_shadow,
        "approved_test_macro_f1": round(float(approved_f1), 4),
        "shadow_test_macro_f1": round(float(shadow_f1), 4),
        "approved_test_macro_auc": round(float(approved_auc), 4),
        "shadow_test_macro_auc": round(float(shadow_auc), 4),
        "auc_gap": round(float(auc_gap), 4),
        "f1_gap": round(float(shadow_f1 - approved_f1), 4),
        "top_new_features": [
            f"{name}: {imp:.4f}" for name, imp in feature_importance[:10]
        ],
        "feature_importance_gap_gt_0_02": auc_gap > 0.02,
        "recommends_retraining": auc_gap > 0.02,
        "note": (
            "Shadow model outperforms approved model by >0.02 AUC — "
            "recommend reviewing top features for approval pipeline. "
            if auc_gap > 0.02
            else "No significant gap — approved model is competitive."
        ),
    }

    report_path = Path(__file__).parent.parent.parent / "models" / "shadow_report.json"
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    logger.info(f"Shadow report saved to {report_path}")

    return summary


def _compute_macro_auc(model, X_test, y_test):
    """Compute macro-averaged AUC for multi-class."""
    from sklearn.metrics import roc_auc_score
    y_proba = model.predict_proba(X_test)
    try:
        return roc_auc_score(y_test, y_proba, multi_class="ovr", average="macro")
    except Exception:
        return 0.0


def _compute_macro_auc_approx(model, X_test, y_test):
    """Fallback AUC computation for sklearn models."""
    from sklearn.metrics import roc_auc_score
    y_proba = model.predict_proba(X_test)
    try:
        return roc_auc_score(y_test, y_proba, multi_class="ovr", average="macro")
    except Exception:
        return 0.0


def _compute_macro_f1(model, X_test, y_test):
    from sklearn.metrics import f1_score
    y_pred = model.predict(X_test)
    return f1_score(y_test, y_pred, average="macro")


def _get_top_new_features(shadow_model, approved_feature_names, all_feature_names):
    """Return features not in the approved model, ranked by importance."""
    all_feats = list(all_feature_names)
    approved_set = set(approved_feature_names)
    new_indices = [i for i, name in enumerate(all_feats) if name not in approved_set]

    importances = None
    if hasattr(shadow_model, "feature_importances_"):
        importances = shadow_model.feature_importances_
    elif hasattr(shadow_model, "booster_"):
        importances = shadow_model.booster_.feature_importance(importance_type="gain")
    else:
        return [("unavailable", 0.0)]

    new_importances = [(all_feats[i], float(importances[i])) for i in new_indices]
    new_importances.sort(key=lambda x: x[1], reverse=True)
    return new_importances


def compute_all_features_from_row_shadow(row: dict) -> tuple:
    from feature_engineering import compute_all_features
    return compute_all_features(
        gst_registered=row.get("gst_registered", "false").lower() in ("true", "1", "yes"),
        gst_monthly_turnover_avg=_safe(row.get("gst_monthly_turnover_avg")),
        gst_filing_regularity=_safe(row.get("gst_filing_regularity")),
        upi_monthly_txn_count=_safe_int(row.get("upi_monthly_txn_count")),
        upi_monthly_txn_value=_safe(row.get("upi_monthly_txn_value")),
        electricity_monthly_units_avg=_safe(row.get("electricity_monthly_units_avg")),
        electricity_payment_delay_days_avg=_safe(row.get("electricity_payment_delay_days_avg")),
        epfo_contribution_regularity=_safe(row.get("epfo_contribution_regularity")),
        epfo_employee_count=_safe_int(row.get("epfo_employee_count")),
        epfo_contribution_amount=_safe(row.get("epfo_contribution_amount")),
        water_monthly_consumption_kl=_safe(row.get("water_monthly_consumption_kl")),
        water_payment_delay_days_avg=_safe(row.get("water_payment_delay_days_avg")),
        fuel_monthly_spend_avg=_safe(row.get("fuel_monthly_spend_avg")),
        fuel_spend_volatility=_safe(row.get("fuel_spend_volatility")),
        requested_loan_amount=_safe(row.get("requested_loan_amount")),
        years_in_operation=_safe(row.get("years_in_operation")),
        business_type=row.get("business_type", "retail"),
    )


def _count_existing_versions() -> int:
    model_dir = Path(__file__).parent.parent.parent / "models"
    return len(list(model_dir.glob("shadow_*.json")))


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "../synthetic-data/output/profiles_labeled.csv"
    result = train_and_compare(csv_path)
    print(json.dumps(result, indent=2))
