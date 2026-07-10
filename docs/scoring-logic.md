# Scoring Logic

**FinPilot AI — Team DistributedMind**

---

## Table of Contents

1. [Overview](#1-overview)
2. [Raw Input Fields](#2-raw-input-fields)
3. [Blank-Slate Detection](#3-blank-slate-detection)
4. [Feature Engineering](#4-feature-engineering)
5. [Business-Type-Aware Weights](#5-business-type-aware-weights)
6. [Seasonality Handling](#6-seasonality-handling)
7. [Composite Score Formula](#7-composite-score-formula)
8. [Bucket Thresholds](#8-bucket-thresholds)
9. [Labeling Heuristic (Training Ground Truth)](#9-labeling-heuristic-training-ground-truth)
10. [Model Training Pipeline](#10-model-training-pipeline)
11. [SHAP Explainability](#11-shap-explainability)
12. [Diagnostic Flags](#12-diagnostic-flags)
13. [Edge Cases](#13-edge-cases)

---

## 1. Overview

The scoring system evaluates MSME creditworthiness using a blend of traditional data (GST, UPI) and alternative data (electricity, EPFO, water, fuel). All domain logic is centralized in `ml-service/app/constants.py`.

### Outputs

- **Composite Score**: Deterministic 0-1 score from a weighted formula of 5 features
- **Bucket**: Categorical rating (disciplined / yes-to-go / non-disciplined / no-to-go) from GBM
- **GBM Probability**: Model confidence in its prediction
- **SHAP Explanations**: Per-feature attribution for every prediction (6 features ranked)
- **Diagnostic Flags**: EPFO plausibility, loan-to-capacity, seasonality indicators

### Constants Location

All tunable parameters live in `ml-service/app/constants.py` under 15 domain groups (A-O). The ML service's `config.py` (`Settings` class) is decorative -- constants.py is the single source of truth.

---

## 2. Raw Input Fields

Every customer profile in `customer_profile` table contains these fields (sent to FastAPI `/predict`):

| Field | Type | Domain | Notes |
|-------|------|--------|-------|
| `customer_id` | str | Identity | Lookup key |
| `business_type` | str | Identity | manufacturing / logistics / retail / services / trading |
| `years_in_operation` | float | Identity | Decimal years |
| `gst_registered` | bool | Standard | |
| `gst_monthly_turnover_avg` | float | Standard | Null if unregistered |
| `gst_filing_regularity` | float | Standard | 0.0-1.0 |
| `upi_monthly_txn_count` | int | Standard | Null if no UPI history |
| `upi_monthly_txn_value` | float | Standard | |
| `electricity_monthly_units_avg` | float | Alternative | kWh |
| `electricity_payment_delay_days_avg` | float | Alternative | Days late |
| `epfo_contribution_regularity` | float | Alternative | 0.0-1.0 |
| `epfo_employee_count` | int | Alternative | |
| `epfo_contribution_amount` | float | Alternative | Monthly contribution (Rs) |
| `water_monthly_consumption_kl` | float | Alternative | |
| `water_payment_delay_days_avg` | float | Alternative | Days late |
| `fuel_monthly_spend_avg` | float | Alternative | |
| `fuel_spend_volatility` | float | Alternative | CV across 12 months |
| `requested_loan_amount` | float | Loan | |
| `is_blank_slate` | bool | Flag | Pre-computed (not sent; recomputed in ML) |

---

## 3. Blank-Slate Detection

**File**: `ml-service/app/feature_engineering.py:154-170`

A customer is "blank-slate" when both GST and UPI are below business-type-specific thresholds:

```python
BST_THRESHOLDS = {
    "manufacturing": {"gst": 18000, "upi": 8},
    "logistics":     {"gst": 12000, "upi": 15},
    "retail":        {"gst": 20000, "upi": 5},
    "services":      {"gst": 15000, "upi": 10},
    "trading":       {"gst": 16000, "upi": 12},
}
BST_FALLBACK = {"gst": 15000, "upi": 10}

def is_blank_slate(gst_registered, gst_monthly_turnover_avg,
                    upi_monthly_txn_count, upi_monthly_txn_value,
                    business_type="retail"):
    thresholds = BST_THRESHOLDS.get(business_type, BST_FALLBACK)
    gst_thin = (
        gst_monthly_turnover_avg is None
        or gst_monthly_turnover_avg < thresholds["gst"]
    )
    upi_thin = (
        upi_monthly_txn_count is None
        or upi_monthly_txn_count < thresholds["upi"]
    )
    return gst_thin and upi_thin  # BOTH must be thin
```

**Key constraints from `constants.py`**:
- `GST_TURNOVER_THRESHOLD = 15000.0` (minimum for financial capacity path)
- Blank-slate detection uses per-type thresholds (gst: 12000-20000, upi: 5-15)

---

## 4. Feature Engineering

All 6 features computed in `compute_all_features()` at both training and inference time (no drift).

### Feature 1: payment_regularity (Weight: 40%)

**File**: `feature_engineering.py:37-74`

```python
DELAY_DENOMINATOR_DAYS = 30.0       # Same for electricity and water
SMOOTHING_FACTOR = 2.0
MIN_SIGNAL_FLOOR = 0.01

def compute_payment_regularity(gst_filing_regularity=None,
                                epfo_contribution_regularity=None,
                                electricity_payment_delay_days_avg=None,
                                water_payment_delay_days_avg=None,
                                business_type="retail"):
    signals = {}  # dict[key] = value

    if gst_filing_regularity >= 0:
        signals["gst"] = gst_filing_regularity

    if epfo_contribution_regularity >= 0:
        signals["epfo"] = epfo_contribution_regularity

    if electricity_payment_delay_days_avg >= 0:
        norm_delay = electricity_payment_delay_days_avg / 30.0
        # Smooth function: delay=0 -> 1.0, delay=30 -> ~0.33, delay=60 -> ~0.17
        signals["electricity"] = max(0.01, 1.0 / (1.0 + 2.0 * norm_delay))

    if water_payment_delay_days_avg >= 0:
        norm_delay = water_payment_delay_days_avg / 30.0
        signals["water"] = max(0.01, 1.0 / (1.0 + 2.0 * norm_delay))

    if not signals:
        return 0.0

    weighted = apply_signal_weights(signals, business_type)
    values = list(weighted.values())
    return float(mean(values)) * len(values)  # Scaled by signal count
```

**Smooth delay function**: `1.0 / (1.0 + 2.0 * (delay/30))` -- monotonically decreasing, no discontinuity.

**Return scaling**: `mean * len(values)` -- ranges from 0 to ~4 (with 4 signals), providing dynamic range the GBM can learn from. With fewer signals, naturally reduces magnitude.

### Feature 2: financial_capacity_proxy (Weight: 25%)

**File**: `feature_engineering.py:77-87`

```python
ELEC_90TH_PERCENTILE = {
    "manufacturing": 7800.0, "logistics": 1100.0,
    "retail": 1600.0, "services": 850.0, "trading": 1000.0,
}
DEFAULT_ELEC_PERCENTILE = 1000.0
FINANCIAL_CAPACITY_SQRT_DIVISOR = 1500.0
GST_TURNOVER_THRESHOLD = 15000.0

def compute_financial_capacity_proxy(gst_monthly_turnover_avg=None,
                                      electricity_monthly_units_avg=None,
                                      business_type="retail"):
    if gst_monthly_turnover_avg is not None and gst_monthly_turnover_avg >= 15000.0:
        # sqrt(15000)/1500=0.08, sqrt(2.25M)/1500=1.0
        return min(sqrt(turnover) / 1500.0, 1.0)
    # Electricity proxy
    units = electricity_monthly_units_avg or 0
    percentile = ELEC_90TH_PERCENTILE.get(business_type, 1000.0)
    return min(units / percentile, 1.0)
```

**Square root scaling**: `sqrt(turnover)/1500` gives better differentiation in the low-to-mid range than log10, while still compressing the high end. A business with Rs 50K/month scores ~0.15, while Rs 2M/month scores ~0.94.

### Feature 3: business_longevity (Weight: 20%)

**File**: `feature_engineering.py:90-96`

```python
LONGEVITY_SCALE_YEARS = 15.0
LONGEVITY_CLIFF_YEARS = 3.0
LONGEVITY_PAYMENT_GATE = 0.70    # payment_reg >= 0.70 to qualify
LONGEVITY_COVERAGE_GATE = 0.80   # data_coverage >= 0.80 to qualify
LONGEVITY_FLOOR_FACTOR = 0.3     # max floor value at year 0

def compute_business_longevity(years_in_operation=None,
                                payment_regularity=0.0, data_coverage=0.0):
    years = years_in_operation or 0
    raw = min(years / 15.0, 1.0)

    # Smooth floor for young businesses with strong data:
    # floor = 0.3 * (1.0 - years/3.0) -> 0.30 at year 0, 0.00 at year 3
    if years < 3.0 and payment_regularity >= 0.70 and data_coverage >= 0.80:
        floor = 0.3 * (1.0 - years / 3.0)
        raw = max(raw, floor)

    return raw
```

**Smooth transition**: Unlike the old hard floor at 0.50, the current implementation uses a linearly decaying floor from 0.30 to 0.00 over 3 years. This avoids discontinuities at the 3-year boundary.

### Feature 4: data_coverage (Weight: 10%)

**File**: `feature_engineering.py:99-119`

```python
DATA_GROUP_WEIGHT = 0.25  # 4 groups x 0.25 = 1.0

def compute_data_coverage(electricity_*, epfo_*, water_*, fuel_*):
    fields = {
        "electricity": [electricity_monthly_units_avg, electricity_payment_delay_days_avg],
        "epfo": [epfo_contribution_regularity, epfo_employee_count],
        "water": [water_monthly_consumption_kl, water_payment_delay_days_avg],
        "fuel": [fuel_monthly_spend_avg, fuel_spend_volatility],
    }
    present = 0.0
    for cols in fields.values():
        if any(val >= 0 for val in cols):  # Any field present in group
            present += 0.25
    return min(present, 1.0)  # Returns 0, 0.25, 0.50, 0.75, or 1.0
```

### Feature 5: evidence_confidence (Weight: 5%)

**File**: `feature_engineering.py:122-151`

```python
MIN_SIGNALS_FOR_CONFIDENCE = 2
EVIDENCE_CONFIDENCE_FALLBACK = 0.5

def compute_evidence_confidence(gst_filing_regularity=None,
                                 epfo_contribution_regularity=None,
                                 electricity_payment_delay_days_avg=None,
                                 water_payment_delay_days_avg=None):
    signals = []
    if gst_filing_regularity >= 0: signals.append(gst_filing_regularity)
    if epfo_contribution_regularity >= 0: signals.append(epfo_contribution_regularity)
    if electricity_payment_delay_days_avg >= 0:
        norm = electricity_payment_delay_days_avg / 30.0
        signals.append(max(0.01, 1.0 / (1.0 + 2.0 * norm)))
    if water_payment_delay_days_avg >= 0:
        norm = water_payment_delay_days_avg / 30.0
        signals.append(max(0.01, 1.0 / (1.0 + 2.0 * norm)))

    if len(signals) < 2:
        return 0.5  # Neutral

    arr = np.array(signals)
    cv = arr.std() / arr.mean() if arr.mean() > 0 else 1.0
    return min(1.0 - cv, 1.0)
```

### Feature 6: is_blank_slate_flag (Binary flag for GBM)

```python
is_blank_slate_flag = 1.0 if blank_slate else 0.0
```

**NOT used in composite score** -- only as 6th input to the GBM model.

---

## 5. Business-Type-Aware Weights

**File**: `ml-service/app/business_weights.py`, constants in `constants.py:69-77`

Signal weights are applied within `payment_regularity` to reflect sector-specific relevance:

```python
SIGNAL_WEIGHTS = {
    "manufacturing": {"gst": 1.0, "epfo": 1.0, "electricity": 1.4, "water": 1.2, "fuel": 0.4},
    "logistics":    {"gst": 1.0, "epfo": 0.8, "electricity": 0.6, "water": 0.4, "fuel": 1.6},
    "retail":       {"gst": 1.2, "epfo": 1.1, "electricity": 0.9, "water": 0.6, "fuel": 0.4},
    "services":     {"gst": 1.0, "epfo": 1.4, "electricity": 0.5, "water": 0.3, "fuel": 0.4},
    "trading":      {"gst": 1.3, "epfo": 1.0, "electricity": 0.6, "water": 0.3, "fuel": 0.9},
}
UNIFORM_WEIGHTS = {"gst": 1.0, "epfo": 1.0, "electricity": 1.0, "water": 1.0, "fuel": 1.0}
```

**Implementation** (`business_weights.py:8-20`):

```python
def apply_signal_weights(signals: dict, business_type: str) -> dict:
    weights = SIGNAL_WEIGHTS.get(business_type, UNIFORM_WEIGHTS)
    total_weight = sum(weights.get(k, 1.0) for k in signals)
    result = {}
    for k, v in signals.items():
        w = weights.get(k, 1.0)
        result[k] = (v * w) / total_weight
    return result
```

Signals are passed as a dict (`{"gst": 0.8, "epfo": 0.9, "electricity": 0.7}`). Each signal value is multiplied by its sector weight and normalized by the total weight sum.

---

## 6. Seasonality Handling

**File**: `ml-service/app/seasonality.py`, constants in `constants.py:97-105`

Returns a dict (not just a string) with structured metadata:

```python
EXPECTED_HIGH_VOLATILITY_SECTORS = {
    "logistics": {"fuel": (0.30, 0.55)},
    "manufacturing": {"electricity": (0.20, 0.50)},
}
SEASONAL_DEFAULT_RANGE = (0.0, 0.30)

def get_volatility_flag(value: float, metric: str, business_type: str) -> dict:
    sector_rules = EXPECTED_HIGH_VOLATILITY_SECTORS.get(business_type, {})
    expected_range = sector_rules.get(metric)
    if expected_range is None:
        lo, hi = SEASONAL_DEFAULT_RANGE
    else:
        lo, hi = expected_range

    if value <= hi:
        return {"flag": "normal", "message": f"{metric} volatility within expected range"}

    return {
        "flag": "elevated_but_expected",
        "message": f"{metric} volatility ({value:.2f}) above typical range ({lo:.2f}-{hi:.2f})",
        "value": value,
        "expected_range": {"lo": lo, "hi": hi},
    }
```

**Note**: Seasonality flag is informational only -- does not affect composite score.

---

## 7. Composite Score Formula

**File**: `ml-service/app/router.py:80-86`

Deterministic formula using 5 features (NOT including `is_blank_slate_flag`):

```python
COMPOSITE_WEIGHTS = {
    "payment_regularity": 0.40,
    "financial_capacity_proxy": 0.25,
    "business_longevity": 0.20,
    "data_coverage": 0.10,
    "evidence_confidence": 0.05,
}

composite_score = (
    0.40 * payment_regularity
    + 0.25 * financial_capacity_proxy
    + 0.20 * business_longevity
    + 0.10 * data_coverage
    + 0.05 * evidence_confidence
)
```

This is computed server-side in the ML service and returned alongside the GBM bucket. The composite score is the numeric anchor visible to the underwriter; the GBM provides the learned classification.

---

## 8. Bucket Thresholds

### Production (used by GBM model for classification)

Bucket comes from `model.predict()` output, mapped via `CATEGORY_ORDER`:

```python
CATEGORY_ORDER = ["no-to-go", "non-disciplined", "yes-to-go", "disciplined"]
# model.classes_ = [0, 1, 2, 3] (integers from training)
# bucket = CATEGORY_ORDER[pred_idx]
```

### Labeling (used for training ground truth)

```python
BUCKET_THRESHOLDS = [
    ("disciplined", 0.84),
    ("yes-to-go", 0.78),
    ("non-disciplined", 0.70),
    ("no-to-go", 0.00),
]
```

| Bucket | Label Threshold | Risk Map |
|--------|-----------------|----------|
| `disciplined` | >= 0.84 | 0.70 |
| `yes-to-go` | >= 0.78 | 0.90 |
| `non-disciplined` | >= 0.70 | 0.40 |
| `no-to-go` | < 0.70 | 0.10 |

**Note**: The `yes-to-go` risk mapping (0.90) assigns the highest safety score to this bucket -- it represents the most creditworthy approvals, while `disciplined` (0.70) may include businesses with lower data coverage. This is the risk map used for label validation metrics, not for display.

---

## 9. Labeling Heuristic (Training Ground Truth)

**File**: `synthetic-data/label_profiles.py`

**IMPORTANT**: This prototype uses a **synthetic dataset with no real ground truth**. Customer profiles are labeled using the same composite score formula used at inference time.

```python
def compute_composite_score(p, business_type):
    coverage      = compute_data_coverage(p)
    payment_reg   = compute_payment_regularity(p, business_type)
    financial_cap = compute_financial_capacity(p, business_type)
    longevity     = compute_business_longevity(p, payment_reg, coverage)
    evidence_conf = compute_evidence_confidence(p)
    score = (
        0.40 * payment_reg + 0.25 * financial_cap
        + 0.20 * longevity + 0.10 * coverage + 0.05 * evidence_conf
    )
    return round(score, 4)

def assign_bucket(composite_score):
    for bucket, threshold in BUCKET_THRESHOLDS:  # [(disc, 0.84), (ytg, 0.78), ...]
        if composite_score >= threshold:
            return bucket
    return "no-to-go"
```

### Label Validation Protocol

The labeling script includes offline validation via injected risk signals:

```python
def inject_known_risk_signals(profile) -> float:
    risk = 0.0
    # Penalties (add risk):
    if gst_filing_regularity < 0.5:    risk += 0.30
    if epfo_regularity < 0.4:          risk += 0.25
    if electricity_delay > 30:         risk += 0.20
    if water_delay > 25:               risk += 0.15
    # Bonuses (reduce risk):
    if turnover > 50000:               risk -= 0.20
    if employees > 10:                 risk -= 0.15
    if years_in_operation > 5:         risk -= 0.10
    return clip(risk, 0.0, 1.0)
```

Validation targets: `precision@20% > 0.75` and `KS statistic > 0.40`.

---

## 10. Model Training Pipeline

**File**: `ml-service/app/training/train_model.py` (364 lines)

### Model Architecture

- **Algorithm**: `sklearn.ensemble.GradientBoostingClassifier`
- **Input features**: 6 (`FEATURE_NAMES`)
- **Output**: 4 classes mapped as `no-to-go=0`, `non-disciplined=1`, `yes-to-go=2`, `disciplined=3`
- **Label mapping**: `CATEGORY_MAP` dictionary, `INVERSE_CATEGORY_MAP` for inference

### Data Split (Temporal)

| Set | Period | Profiles | Purpose |
|-----|--------|----------|---------|
| Train | Jan-Jun 2023 | ~175 | Model fitting |
| Validate | Jul-Dec 2023 | ~87 | Optuna + hyperparameter tuning |
| Test (OOD) | Jan-Jun 2024 | ~88 | Out-of-distribution validation |

Dates come from `profile_date` column in synthetic data.

### Hyperparameter Optimization

When `optuna` is installed: 50 trials maximizing precision@low-risk (top 10% safest). Search space:
```
n_estimators: [100, 500], learning_rate: [0.01, 0.2] log
max_depth: [3, 8], min_samples_leaf: [3, 10]
subsample: [0.6, 1.0], colsample_bytree: [0.6, 1.0]
```

When `optuna` is not available: uses fixed defaults `{n_estimators=200, learning_rate=0.05, max_depth=4, min_samples_leaf=5, subsample=0.8, colsample_bytree=0.8}`.

### Validation Gates (MUST PASS)

| Metric | Target | Description |
|--------|--------|-------------|
| Precision@low-risk | >= 0.70 | Top 20% safest profiles are truly low-risk |
| Recall@high-risk | >= 0.65 | Bottom 20% risky profiles are identified |
| ECE (Expected Calibration Error) | < 0.05 | Confidence scores match actual correctness |

Both validation and test (OOD) sets must pass all gates.

### Output Artifact

```python
artifact = {
    "model": GradientBoostingClassifier,
    "version": "2.0.N",      # Auto-incremented
    "metadata": {
        "training_date": "ISO timestamp",
        "dataset_hash": "sha256 of sorted customer IDs",
        "metrics": {"precision_low_risk": 0.85, "recall_high_risk": 0.72, ...},
        "feature_schema": FEATURE_NAMES,
        "n_samples": 350,
        "label_distribution": {"disciplined": 120, ...},
        "best_params": {...},
        "data_split": {"train": "2023-01 to 2023-06", ...},
    }
}
```

Saved to `ml-service/models/model_<version>.joblib` and symlinked as `model_latest.joblib`.

---

## 11. SHAP Explainability

**File**: `ml-service/app/explain.py` (126 lines)

### Implementation

Uses `shap.KernelExplainer` with 20 random background samples (model-agnostic):

```python
background = np.random.default_rng(42).random((20, 6)) * 0.5 + 0.5
explainer = shap.KernelExplainer(model.predict_proba, background)
```

### Per-Prediction Flow

```python
pred_idx = int(model.predict(feature_vector)[0])
shap_values = explainer.shap_values(feature_vector)

# Multi-class handling:
if isinstance(shap_values, list):
    svc = shap_values[pred_idx]          # List per class
elif shap_values.ndim == 3:
    svc = shap_values[0, :, pred_idx]    # 3D array

base_value = float(ev[pred_idx])  # Expected value for predicted class
```

### Feature Ranking

ALL 6 features are ranked (not top-7), sorted by absolute SHAP value:

```python
ranked.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
for i, r in enumerate(ranked):
    r["rank"] = i + 1
```

### Source Tagging

```python
FEATURE_SOURCES = {
    "business_longevity": "standard",
    "payment_regularity": {"False": "mixed", "True": "alternative"},
    "financial_capacity_proxy": {"False": "mixed", "True": "alternative"},
    "data_coverage": "alternative",
    "evidence_confidence": {"False": "mixed", "True": "alternative"},
    "is_blank_slate_flag": "alternative",
}

# Per feature:
source_map = FEATURE_SOURCES.get(name, {"False": "standard", "True": "standard"})
if isinstance(source_map, dict):
    source = source_map["True"] if blank_slate else source_map["False"]
else:
    source = source_map
```

### Signal Contribution Split

Traditional vs alternative contributions estimated from source tags:

```python
for r in ranked:
    if r["source"] == "standard":
        traditional_contrib += r["shap_value"]
    elif r["source"] == "alternative":
        alt_contrib += r["shap_value"]
    elif r["source"] == "mixed":
        traditional_contrib += r["shap_value"] * 0.5
        alt_contrib += r["shap_value"] * 0.5
```

### Return Shape

```python
{
    "shap_values": {"payment_regularity": 0.34, ...},
    "base_value": 1.2,
    "feature_ranking": [
        {"feature_name": "payment_regularity", "value": 2.8, "shap_value": 0.34,
         "rank": 1, "direction": "positive",
         "business_description": "Consistent manufacturing sector payment behavior...",
         "source": "alternative"},
    ],
    "human_readable_summary": "Assessment heavily relies on alternative data...",
    "traditional_signal_contribution": 0.12,
    "alternative_signal_contribution": 0.88,
}
```

---

## 12. Diagnostic Flags

### 12.1 EPFO Plausibility

**File**: `ml-service/app/epfo_checks.py`

```python
TOTAL_EPFO_RATE = 0.24  # 12% employer + 12% employee

def check_epfo_plausibility(epfo_employee_count, epfo_contribution_amount):
    if not epfo_employee_count or not epfo_contribution_amount:
        return {"flag": "unavailable", "message": "..."}

    implied_wage = epfo_contribution_amount / (epfo_employee_count * 0.24)

    if implied_wage < 7500:
        severity = "critical" if implied_wage < 3750 else "warning"
        return {"flag": f"suspicious_low_{severity}", "implied_wage": ..., "message": "..."}

    if implied_wage > 200000:
        ratio = implied_wage / 200000
        severity = "critical" if ratio > 1.5 else "warning"
        return {"flag": f"suspicious_high_{severity}", "implied_wage": ..., "message": "..."}

    return {"flag": "plausible", "implied_wage": ..., "message": "..."}
```

**Return fields**: `flag`, `message`, `implied_wage` (float), `employee_count` (int)

### 12.2 Loan-to-Capacity Flag

**File**: `ml-service/app/capacity_flag.py`

```python
LOAN_TO_ANNUAL_REVENUE_CAP = 0.60  # threshold for caution
LOAN_HIGH_RISK_RATIO = 1.0        # threshold for high_risk
ELEC_PROXY_REVENUE_BASE = 500000.0

def compute_capacity_flag(loan, gst_turnover, electricity_units, business_type):
    if GST turnover available:
        annual_revenue = gst_turnover * 12
        source = "gst"
    elif electricity data available:
        percentile = ELEC_90TH_PERCENTILE.get(business_type, 1000.0)
        proxy_revenue = (electricity_units / percentile) * 500000.0
        source = "electricity_proxy"
    else:
        return {"flag": "insufficient_data", "message": "..."}

    ratio = loan / annual_revenue

    if ratio > LOAN_TO_ANNUAL_REVENUE_CAP:
        severity = "high_risk" if ratio > LOAN_HIGH_RISK_RATIO else "caution"
        return {"flag": severity, "loan_to_revenue_ratio": ratio, "source": source, "message": "..."}

    return {"flag": "normal", "loan_to_revenue_ratio": ratio, "source": source, "message": "..."}
```

**Flag values**: `normal` | `caution` | `high_risk` | `insufficient_data`

**Thresholds**: `caution > 0.60x`, `high_risk > 1.0x` annual revenue

### 12.3 Seasonality Flags

**File**: `ml-service/app/seasonality.py`

Returns structured dict per metric:

| Metric | Sector | Expected Range | Flag |
|--------|--------|----------------|------|
| `fuel` | logistics | 0.30 - 0.55 | `normal` or `elevated_but_expected` |
| `electricity` | manufacturing | 0.20 - 0.50 | `normal` or `elevated_but_expected` |
| any | others | 0.00 - 0.30 | defaults |

---

## 13. Edge Cases

| Edge Case | How it's handled | File |
|-----------|-----------------|------|
| Single weak alt-data signal | `payment_regularity` averages across all available signals; one weak signal dilutes rather than vetoes | `feature_engineering.py` |
| Customer with 3 documents vs 2 | `data_coverage` measures presence only -- never penalizes weak signals | `feature_engineering.py:99-119` |
| Seasonal business (high fuel CV) | Sector-specific thresholds; logistics fuel CV up to 0.55 is "expected" | `seasonality.py`, `constants.py:97-105` |
| Young business with strong alt-data | Smooth floor: `0.3 * (1.0 - years/3.0)` from year 0 to year 3 | `feature_engineering.py:90-96` |
| Blank-slate customer | Same model, different SHAP narrative; alt-data source tags | `feature_engineering.py:154-170`, `explain.py` |
| EPFO gaming (minimum contributions) | EPFO plausibility check on implied wage | `epfo_checks.py` |
| Large loan vs small business | Separate capacity flag, not part of credit score | `capacity_flag.py` |
| Conflicting signals across sources | `evidence_confidence` penalizes high CV; SHAP surfaces it | `feature_engineering.py:122-151` |
| No payment signals at all | Returns 0.0 for payment_regularity | `feature_engineering.py:69-70` |
| Null electricity/water delay | Signal skipped in averaging; no imputation needed | `feature_engineering.py:57-68` |
| Null GST turnover for non-blank-slate | GST is null; falls through to electricity proxy path | `feature_engineering.py:82-87` |
| No loan amount | Capacity flag returns `unavailable` | `capacity_flag.py:10-11` |
