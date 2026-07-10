import csv
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report, f1_score, cohen_kappa_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from app.feature_engineering import compute_all_features, FEATURE_NAMES
from app.constants import (
    RANDOM_STATE, OPTUNA_N_TRIALS, ECE_MAX, PRECISION_LOW_RISK_TARGET, RECALL_HIGH_RISK_TARGET,
    CATEGORY_ORDER as C_CATEGORY_ORDER,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent.parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

SEED = RANDOM_STATE
TEST_SIZE = 0.2
N_TRIALS = OPTUNA_N_TRIALS

LOW_RISK_CLASSES = {2, 3}
HIGH_RISK_CLASSES = {0, 1}

CATEGORY_MAP = {
    "no-to-go": 0,
    "non-disciplined": 1,
    "yes-to-go": 2,
    "disciplined": 3,
}

INVERSE_CATEGORY_MAP = {v: k for k, v in CATEGORY_MAP.items()}

CATEGORY_ORDER = C_CATEGORY_ORDER


def load_labeled_csv(path: str | Path) -> list[dict]:
    path = Path(path)
    with open(path) as f:
        reader = csv.DictReader(f)
        return list(reader)


def compute_features_from_row(row: dict) -> tuple[dict, dict]:
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


def _safe(val, default=None):
    if val is None or val == "" or val == "None":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=None):
    if val is None or val == "" or val == "None":
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def label_to_index(label: str) -> int:
    return CATEGORY_MAP.get(label, 0)


def compute_dataset_hash(rows: list[dict]) -> str:
    import hashlib
    ids = sorted(r["customer_id"] for r in rows)
    raw = ",".join(ids).encode()
    return hashlib.sha256(raw).hexdigest()


def expected_calibration_error(y_true: np.ndarray, proba: np.ndarray, n_bins: int = 10) -> float:
    confidences = np.max(proba, axis=1)
    predictions = np.argmax(proba, axis=1)
    accuracies = (predictions == y_true).astype(np.float64)
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        in_bin = (confidences >= bin_boundaries[i]) & (confidences < bin_boundaries[i + 1])
        in_bin_indices = np.where(in_bin)[0]
        if len(in_bin_indices) > 0:
            bin_acc = np.mean(accuracies[in_bin_indices])
            bin_conf = np.mean(confidences[in_bin_indices])
            ece += np.abs(bin_acc - bin_conf) * len(in_bin_indices) / len(y_true)
    return ece


def low_risk_proba_from_multiclass(proba: np.ndarray) -> np.ndarray:
    return proba[:, 2] + proba[:, 3]


def compute_business_metrics(y_true: np.ndarray, proba: np.ndarray) -> dict:
    y_binary = np.isin(y_true, list(LOW_RISK_CLASSES)).astype(np.int32)
    lr_proba = low_risk_proba_from_multiclass(proba)

    low_risk_thresh = np.percentile(lr_proba, 80)
    pred_low_risk = (lr_proba >= low_risk_thresh).astype(np.int32)
    precision_low_risk = float(precision_score(y_binary, pred_low_risk, pos_label=1, zero_division=0))

    high_risk_thresh = np.percentile(lr_proba, 20)
    pred_high_risk = (lr_proba < high_risk_thresh).astype(np.int32)
    recall_high_risk = float(recall_score(y_binary, pred_high_risk, pos_label=0, zero_division=0))

    ece = float(expected_calibration_error(y_true, proba))

    return {
        "precision_low_risk": precision_low_risk,
        "recall_high_risk": recall_high_risk,
        "ece": ece,
        "validation_gates_passed": bool(
            precision_low_risk >= PRECISION_LOW_RISK_TARGET
            and recall_high_risk >= RECALL_HIGH_RISK_TARGET
            and ece < ECE_MAX
        ),
    }


def optimize_optuna(X_train: np.ndarray, y_train: np.ndarray) -> dict:
    try:
        import optuna
    except ImportError:
        logger.warning("optuna not installed. Using default hyperparameters.")
        return {
            "n_estimators": 200,
            "learning_rate": 0.05,
            "max_depth": 4,
            "min_samples_leaf": 5,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
        }

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 3, 10),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "random_state": SEED,
        }

        X_tr, X_val, y_tr, y_val = train_test_split(
            X_train, y_train, test_size=0.2, random_state=SEED, stratify=y_train,
        )

        model = GradientBoostingClassifier(**params)
        model.fit(X_tr, y_tr)

        proba = model.predict_proba(X_val)
        lr_proba = low_risk_proba_from_multiclass(proba)
        y_binary = np.isin(y_val, list(LOW_RISK_CLASSES)).astype(np.int32)
        low_risk_thresh = np.percentile(lr_proba, 90)
        pred_low_risk = (lr_proba >= low_risk_thresh).astype(np.int32)
        return float(precision_score(y_binary, pred_low_risk, pos_label=1, zero_division=0))

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(objective, n_trials=N_TRIALS, show_progress_bar=True)

    logger.info(f"Best Optuna trial: {study.best_trial.number}")
    logger.info(f"Best precision@low-risk: {study.best_value:.4f}")
    for k, v in study.best_params.items():
        logger.info(f"  {k}: {v}")

    return study.best_params


def train_model(csv_path: str | Path) -> dict:
    logger.info(f"Loading labeled profiles from {csv_path}")
    rows = load_labeled_csv(csv_path)
    logger.info(f"Loaded {len(rows)} profiles")

    label_distribution = {}
    for r in rows:
        lbl = r.get("bucket", "")
        label_distribution[lbl] = label_distribution.get(lbl, 0) + 1
    logger.info(f"Label distribution: {label_distribution}")

    X_list = []
    y_list = []
    date_list = []
    skipped = 0
    for row in rows:
        label = row.get("bucket", "")
        if label not in CATEGORY_MAP:
            skipped += 1
            continue
        feats, _ = compute_features_from_row(row)
        X_list.append([feats[n] for n in FEATURE_NAMES])
        y_list.append(label_to_index(label))
        date_list.append(row.get("profile_date", "2023-01"))

    if skipped:
        logger.warning(f"Skipped {skipped} rows with unknown labels")

    X = np.array(X_list, dtype=np.float64)
    y = np.array(y_list, dtype=np.int32)
    dates = np.array(date_list)

    logger.info(f"Feature matrix: {X.shape}")
    logger.info(f"Feature names: {FEATURE_NAMES}")

    train_mask = (dates >= "2023-01") & (dates < "2023-07")
    val_mask = (dates >= "2023-07") & (dates < "2024-01")
    test_mask = (dates >= "2024-01") & (dates < "2024-07")

    X_train, y_train = X[train_mask], y[train_mask]
    X_val, y_val = X[val_mask], y[val_mask]
    X_test, y_test = X[test_mask], y[test_mask]

    logger.info(f"Train (Jan-Jun 2023):      {X_train.shape[0]} profiles")
    logger.info(f"Validate (Jul-Dec 2023):   {X_val.shape[0]} profiles")
    logger.info(f"Test OOD (Jan-Jun 2024):   {X_test.shape[0]} profiles")

    best_params = optimize_optuna(X_train, y_train)

    model = GradientBoostingClassifier(
        n_estimators=best_params.get("n_estimators", 200),
        learning_rate=best_params.get("learning_rate", 0.05),
        max_depth=best_params.get("max_depth", 4),
        min_samples_leaf=best_params.get("min_samples_leaf", 5),
        subsample=best_params.get("subsample", 0.8),
        colsample_bytree=best_params.get("colsample_bytree", 0.8),
        random_state=SEED,
        verbose=0,
    )

    model.fit(X_train, y_train)

    y_val_pred = model.predict(X_val)
    y_val_proba = model.predict_proba(X_val)
    y_test_pred = model.predict(X_test)
    y_test_proba = model.predict_proba(X_test)
    y_train_pred = model.predict(X_train)

    logger.info("\n=== Training Classification Report ===")
    logger.info(f"\n{classification_report(y_train, y_train_pred, target_names=CATEGORY_ORDER)}")

    logger.info("\n=== Validation Classification Report ===")
    logger.info(f"\n{classification_report(y_val, y_val_pred, target_names=CATEGORY_ORDER)}")

    logger.info("\n=== Test (OOD) Classification Report ===")
    logger.info(f"\n{classification_report(y_test, y_test_pred, target_names=CATEGORY_ORDER)}")

    val_biz = compute_business_metrics(y_val, y_val_proba)
    test_biz = compute_business_metrics(y_test, y_test_proba)

    logger.info("\n=== Validation Set Business Gates ===")
    logger.info(f"  Precision@low-risk: {val_biz['precision_low_risk']:.4f}  (target >= {PRECISION_LOW_RISK_TARGET})")
    logger.info(f"  Recall@high-risk:   {val_biz['recall_high_risk']:.4f}  (target >= {RECALL_HIGH_RISK_TARGET})")
    logger.info(f"  ECE:                {val_biz['ece']:.4f}  (target < {ECE_MAX})")
    assert val_biz["validation_gates_passed"], (
        f"Validation set gates FAILED: precision_low_risk={val_biz['precision_low_risk']:.3f}, "
        f"recall_high_risk={val_biz['recall_high_risk']:.3f}, ece={val_biz['ece']:.3f}"
    )
    logger.info("  ✅ Validation gates PASSED")

    logger.info("\n=== Test (OOD) Set Business Gates ===")
    logger.info(f"  Precision@low-risk: {test_biz['precision_low_risk']:.4f}  (target >= {PRECISION_LOW_RISK_TARGET})")
    logger.info(f"  Recall@high-risk:   {test_biz['recall_high_risk']:.4f}  (target >= {RECALL_HIGH_RISK_TARGET})")
    logger.info(f"  ECE:                {test_biz['ece']:.4f}  (target < {ECE_MAX})")
    assert test_biz["validation_gates_passed"], (
        f"Test OOD gates FAILED: precision_low_risk={test_biz['precision_low_risk']:.3f}, "
        f"recall_high_risk={test_biz['recall_high_risk']:.3f}, ece={test_biz['ece']:.3f}"
    )
    logger.info("  ✅ Test (OOD) gates PASSED")

    model_version = f"2.0.{_count_existing_versions()}"
    artifact = {
        "model": model,
        "version": model_version,
        "metadata": {
            "training_date": datetime.now(timezone.utc).isoformat(),
            "dataset_hash": compute_dataset_hash(rows),
            "metrics": {
                "train_macro_f1": float(f1_score(y_train, y_train_pred, average="macro")),
                "val_precision_low_risk": float(val_biz["precision_low_risk"]),
                "val_recall_high_risk": float(val_biz["recall_high_risk"]),
                "val_ece": float(val_biz["ece"]),
                "test_precision_low_risk": float(test_biz["precision_low_risk"]),
                "test_recall_high_risk": float(test_biz["recall_high_risk"]),
                "test_ece": float(test_biz["ece"]),
                "validation_gates_passed": bool(val_biz["validation_gates_passed"] and test_biz["validation_gates_passed"]),
            },
            "feature_schema": FEATURE_NAMES,
            "n_samples": len(rows),
            "n_features": len(FEATURE_NAMES),
            "n_train": X_train.shape[0],
            "n_val": X_val.shape[0],
            "n_test": X_test.shape[0],
            "label_distribution": label_distribution,
            "best_params": best_params,
            "data_split": {
                "train": "2023-01 to 2023-06",
                "val": "2023-07 to 2023-12",
                "test": "2024-01 to 2024-06 (OOD)",
            },
        },
    }

    model_path = MODEL_DIR / f"model_{model_version}.joblib"
    joblib.dump(artifact, model_path)
    logger.info(f"\nModel saved to {model_path}")

    latest_path = MODEL_DIR / "model_latest.joblib"
    if latest_path.exists():
        latest_path.unlink()
    joblib.dump(artifact, latest_path)

    summary = {
        "model_version": model_version,
        "path": str(model_path),
        "metrics": artifact["metadata"]["metrics"],
        "n_train": X_train.shape[0],
        "n_test": X_test.shape[0],
        "feature_count": len(FEATURE_NAMES),
    }

    report_path = MODEL_DIR / "training_report.json"
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    logger.info(f"Training report saved to {report_path}")

    return summary


def _count_existing_versions() -> int:
    return len(list(MODEL_DIR.glob("model_*.joblib")))


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "../synthetic-data/output/profiles_labeled.csv"
    train_model(csv_path)
