import json
import hashlib
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
from sklearn.metrics import classification_report, f1_score, cohen_kappa_score, precision_score, recall_score, confusion_matrix
from sklearn.model_selection import StratifiedKFold, train_test_split

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.constants import (
    RANDOM_STATE, OPTUNA_N_TRIALS, ECE_MAX, PRECISION_LOW_RISK_TARGET, RECALL_HIGH_RISK_TARGET
)
from training.feature_engineering import (
    load_customers, build_feature_pipeline, FEATURE_NAMES, INVERSE_CATEGORY_MAP,
)

AUGMENTED_FEATURE_NAMES = FEATURE_NAMES + [f"{name}_missing" for name in FEATURE_NAMES]

LOW_RISK_CLASSES = {2, 3}
HIGH_RISK_CLASSES = {0, 1}

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent.parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

SEED = RANDOM_STATE
N_TRIALS = OPTUNA_N_TRIALS
N_FOLDS = 5


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
            "max_depth": 8,
            "learning_rate": 0.05,
            "num_leaves": 31,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_samples": 20,
            "reg_alpha": 0.1,
            "reg_lambda": 0.1,
        }

    def objective(trial):
        params = {
            "objective": "multiclass",
            "num_class": 4,
            "n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "max_depth": trial.suggest_int("max_depth", 3, 12),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 15, 127),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            "verbose": -1,
            "random_state": SEED,
        }

        X_tr, X_val, y_tr, y_val = train_test_split(
            X_train, y_train, test_size=0.2, random_state=SEED, stratify=y_train,
        )

        model = lgb.LGBMClassifier(**params)
        model.fit(
            X_tr, y_tr,
            eval_set=[(X_val, y_val)],
            eval_metric="multi_logloss",
            callbacks=[lgb.early_stopping(10), lgb.log_evaluation(0)],
            feature_name=AUGMENTED_FEATURE_NAMES,
        )
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


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, proba: np.ndarray | None = None) -> dict:
    metrics = {
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted")),
        "quadratic_weighted_kappa": float(cohen_kappa_score(y_true, y_pred, weights="quadratic")),
    }

    for cls in range(4):
        cls_name = INVERSE_CATEGORY_MAP[cls]
        recall = recall_score(y_true, y_pred, labels=[cls], average=None)[0]
        metrics[f"recall_{cls_name}"] = float(recall)

    if proba is not None:
        metrics["ece"] = float(expected_calibration_error(y_true, proba))
        biz_metrics = compute_business_metrics(y_true, proba)
        metrics.update(biz_metrics)

    cm = confusion_matrix(y_true, y_pred)
    metrics["confusion_matrix"] = cm.tolist()

    return metrics


def train_model(customers_path: str | Path) -> dict:
    logger.info(f"Loading customers from {customers_path}")
    customers = load_customers(customers_path)
    logger.info(f"Loaded {len(customers)} customers")

    X, y, labels, metadata = build_feature_pipeline(customers)
    logger.info(f"Feature matrix: {X.shape}")
    logger.info(f"Label distribution: {metadata['label_distribution']}")

    dates = np.array([c.get("profile_date", "2023-01") for c in customers])

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

    params = {
        "objective": "multiclass",
        "num_class": 4,
        "metric": "multi_logloss",
        "verbosity": -1,
        "random_state": SEED,
        "n_jobs": -1,
        **best_params,
    }

    model = lgb.LGBMClassifier(**params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        eval_metric="multi_logloss",
        callbacks=[lgb.early_stopping(10), lgb.log_evaluation(50)],
        feature_name=AUGMENTED_FEATURE_NAMES,
    )

    y_val_pred = model.predict(X_val)
    y_val_proba = model.predict_proba(X_val)
    y_test_pred = model.predict(X_test)
    y_test_proba = model.predict_proba(X_test)

    logger.info("\n=== Validation Classification Report ===")
    logger.info(f"\n{classification_report(y_val, y_val_pred, target_names=list(INVERSE_CATEGORY_MAP.values()))}")

    logger.info("\n=== Test (OOD) Classification Report ===")
    logger.info(f"\n{classification_report(y_test, y_test_pred, target_names=list(INVERSE_CATEGORY_MAP.values()))}")

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

    metrics = {
        "val_precision_low_risk": float(val_biz["precision_low_risk"]),
        "val_recall_high_risk": float(val_biz["recall_high_risk"]),
        "val_ece": float(val_biz["ece"]),
        "test_precision_low_risk": float(test_biz["precision_low_risk"]),
        "test_recall_high_risk": float(test_biz["recall_high_risk"]),
        "test_ece": float(test_biz["ece"]),
        "validation_gates_passed": bool(val_biz["validation_gates_passed"] and test_biz["validation_gates_passed"]),
    }

    model_version = f"1.0.{_count_existing_versions()}"
    artifact = {
        "model": model,
        "version": model_version,
        "metadata": {
            "training_date": datetime.now(timezone.utc).isoformat(),
            "dataset_hash": _compute_dataset_hash(customers),
            "metrics": metrics,
            "feature_schema": metadata["augmented_features"],
            "n_samples": metadata["n_samples"],
            "n_features": X.shape[1],
            "n_train": X_train.shape[0],
            "n_val": X_val.shape[0],
            "n_test": X_test.shape[0],
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

    latest_symlink = MODEL_DIR / "model_latest.joblib"
    if latest_symlink.exists():
        latest_symlink.unlink()
    joblib.dump(artifact, latest_symlink)
    logger.info(f"Model also saved as {latest_symlink}")

    summary = {
        "model_version": model_version,
        "path": str(model_path),
        "metrics": metrics,
        "n_train": X_train.shape[0],
        "n_val": X_val.shape[0],
        "n_test": X_test.shape[0],
        "feature_count": X.shape[1],
    }

    report_path = MODEL_DIR / "training_report.json"
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    logger.info(f"Training report saved to {report_path}")

    return summary


def _count_existing_versions() -> int:
    return len(list(MODEL_DIR.glob("model_*.joblib")))


def _compute_dataset_hash(customers: list[dict]) -> str:
    pans = sorted(c["customer"]["pan"] for c in customers)
    raw = ",".join(pans).encode()
    return hashlib.sha256(raw).hexdigest()


if __name__ == "__main__":
    customers_path = sys.argv[1] if len(sys.argv) > 1 else "../synthetic-data/output/customers.json"
    train_model(customers_path)
