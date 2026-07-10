import math


VALID_BUSINESS_TYPES = {"manufacturing", "logistics", "retail", "services", "trading"}

# ─── Domain A: Financial Capacity ─────────────────────────────────────────

ELEC_90TH_PERCENTILE = {
    "manufacturing": 7800.0,
    "logistics": 1100.0,
    "retail": 1600.0,
    "services": 850.0,
    "trading": 1000.0,
}
DEFAULT_ELEC_PERCENTILE = 1000.0

GST_TURNOVER_THRESHOLD = 15000.0
FINANCIAL_CAPACITY_SQRT_DIVISOR = 1500.0

# ─── Domain B: Payment Regularity / Evidence Confidence ───────────────────

DELAY_DENOMINATOR_DAYS = 30.0
SMOOTHING_FACTOR = 2.0
MIN_SIGNAL_FLOOR = 0.01
EVIDENCE_CONFIDENCE_FALLBACK = 0.5
MIN_SIGNALS_FOR_CONFIDENCE = 2

# ─── Domain C: Business Longevity ─────────────────────────────────────────

LONGEVITY_SCALE_YEARS = 15.0
LONGEVITY_CLIFF_YEARS = 3.0
LONGEVITY_PAYMENT_GATE = 0.70
LONGEVITY_COVERAGE_GATE = 0.80
LONGEVITY_FLOOR_FACTOR = 0.3  # multiplier in floor = factor * (1 - years/cliff)

# ─── Domain D: Data Coverage ──────────────────────────────────────────────

DATA_GROUP_WEIGHT = 0.25  # each of 4 groups contributes this
DATA_GROUPS = {
    "electricity": ["electricity_monthly_units_avg", "electricity_payment_delay_days_avg"],
    "epfo":        ["epfo_contribution_regularity", "epfo_employee_count"],
    "water":       ["water_monthly_consumption_kl", "water_payment_delay_days_avg"],
    "fuel":        ["fuel_monthly_spend_avg", "fuel_spend_volatility"],
}

# ─── Domain E: Blank-Slate Thresholds (per business type) ─────────────────

BST_THRESHOLDS = {
    "manufacturing": {"gst": 18000, "upi": 8},
    "logistics":     {"gst": 12000, "upi": 15},
    "retail":        {"gst": 20000, "upi": 5},
    "services":      {"gst": 15000, "upi": 10},
    "trading":       {"gst": 16000, "upi": 12},
}
BST_FALLBACK = {"gst": 15000, "upi": 10}

# ─── Domain F: Composite Score Weights (used by router + label_profiles) ──

COMPOSITE_WEIGHTS = {
    "payment_regularity": 0.40,
    "financial_capacity_proxy": 0.25,
    "business_longevity": 0.20,
    "data_coverage": 0.10,
    "evidence_confidence": 0.05,
}

# ─── Domain G: Business-Type Signal Weights ───────────────────────────────

SIGNAL_WEIGHTS = {
    "manufacturing": {"gst": 1.0, "epfo": 1.0, "electricity": 1.4, "water": 1.2, "fuel": 0.4},
    "logistics":    {"gst": 1.0, "epfo": 0.8, "electricity": 0.6, "water": 0.4, "fuel": 1.6},
    "retail":       {"gst": 1.2, "epfo": 1.1, "electricity": 0.9, "water": 0.6, "fuel": 0.4},
    "services":     {"gst": 1.0, "epfo": 1.4, "electricity": 0.5, "water": 0.3, "fuel": 0.4},
    "trading":      {"gst": 1.3, "epfo": 1.0, "electricity": 0.6, "water": 0.3, "fuel": 0.9},
}
UNIFORM_WEIGHTS = {"gst": 1.0, "epfo": 1.0, "electricity": 1.0, "water": 1.0, "fuel": 1.0}
SIGNAL_KEYS_ORDER = ["gst", "epfo", "electricity", "water", "fuel"]

# ─── Domain H: Label Buckets ──────────────────────────────────────────────

BUCKET_THRESHOLDS = [
    ("disciplined", 0.84),
    ("yes-to-go", 0.78),
    ("non-disciplined", 0.70),
    ("no-to-go", 0.00),
]

RISK_MAP = {
    "yes-to-go": 0.90,
    "disciplined": 0.70,
    "non-disciplined": 0.40,
    "no-to-go": 0.10,
}

# ─── Domain I: Seasonality Volatility Ranges ──────────────────────────────

EXPECTED_HIGH_VOLATILITY_SECTORS = {
    "logistics": {"fuel": (0.30, 0.55)},
    "manufacturing": {"electricity": (0.20, 0.50)},
}
SEASONAL_HIGH_KV = {
    "fuel": {"label": "elevated_but_expected", "message": "Fuel volatility is elevated but expected for this sector"},
    "electricity": {"label": "elevated_but_expected", "message": "Electricity volatility is elevated but expected for this sector"},
}
SEASONAL_DEFAULT_RANGE = (0.0, 0.30)

# ─── Domain J: Loan Capacity Flag ─────────────────────────────────────────

LOAN_TO_ANNUAL_REVENUE_CAP = 0.60
LOAN_TO_ELEC_PROXY_MULTIPLIER = 3.0
ELEC_PROXY_REVENUE_BASE = 500000.0  # proxy = (units/percentile) * base
LOAN_HIGH_RISK_RATIO = 1.0

# ─── Domain K: EPFO Plausibility Check ────────────────────────────────────

EPFO_MIN_MONTHLY_WAGE = 7500.0
EPFO_MAX_MONTHLY_WAGE = 200000.0
EPFO_EMPLOYER_RATE = 0.12
EPFO_EMPLOYEE_RATE = 0.12
EPFO_SUSPICIOUS_LOW_THRESHOLD = 0.5  # fraction of min wage
EPFO_SUSPICIOUS_HIGH_THRESHOLD = 1.5  # fraction of max wage
EPFO_TOTAL_RATE = EPFO_EMPLOYER_RATE + EPFO_EMPLOYEE_RATE

# ─── Domain L: SHAP / Explainability ──────────────────────────────────────

FEATURE_SOURCES = {
    "business_longevity": "standard",
    "payment_regularity": {"False": "mixed", "True": "alternative"},
    "financial_capacity_proxy": {"False": "mixed", "True": "alternative"},
    "data_coverage": "alternative",
    "evidence_confidence": {"False": "mixed", "True": "alternative"},
    "is_blank_slate_flag": "alternative",
}

BLANK_SLATE_REASONS = [
    "Limited traditional data — score relies on alternative signals",
    "No formal GST or UPI history — utility payments used as proxy",
    "Blank-slate profile — alternative data sources provide primary evidence",
]

# ─── Domain M: Model Training ─────────────────────────────────────────────

ECE_TARGET = 0.05
PRECISION_LOW_RISK_TARGETS = {10: 0.70, 20: 0.65}
TRAIN_TEST_SPLIT_RATIO = 0.20
TRAIN_VAL_RATIO = 0.15
OPTUNA_N_TRIALS = 50
RANDOM_STATE = 42
LIGHTGBM_DEFAULT_LEARNING_RATE = 0.05
LIGHTGBM_DEFAULT_N_ESTIMATORS = 200

# ─── Domain N: Validation Gates ───────────────────────────────────────────

PRECISION_LOW_RISK_TARGET = 0.70
RECALL_HIGH_RISK_TARGET = 0.65
ECE_MAX = 0.05
LABEL_PRECISION_TARGET = 0.75
LABEL_KS_TARGET = 0.40
BUCKET_RANGE_MIN = 10
BUCKET_RANGE_MAX = 50

# ─── Domain O: Inject Known Risk Signals (label_profiles) ─────────────────

RISK_SIGNAL_THRESHOLDS = {
    "gst_filing_bad": 0.5,
    "epfo_contribution_bad": 0.4,
    "elec_delay_bad_days": 30,
    "water_delay_bad_days": 25,
    "turnover_good": 50000,
    "epfo_employees_good": 10,
    "longevity_good_years": 5,
}

RISK_SIGNAL_PENALTIES = {
    "gst_filing_bad": 0.30,
    "epfo_contribution_bad": 0.25,
    "elec_delay_bad": 0.20,
    "water_delay_bad": 0.15,
}

RISK_SIGNAL_BONUSES = {
    "turnover_good": -0.20,
    "epfo_employees_good": -0.15,
    "longevity_good": -0.10,
}

CATEGORY_ORDER = ["no-to-go", "non-disciplined", "yes-to-go", "disciplined"]

# ─── Domain Q: Feature Engineering (training pipeline) ────────────────────

TRAIN_FEATURE_NAMES = [
    "gst_filing_regularity", "gst_tax_growth_yoy", "gst_compliance_score",
    "upi_txn_volume_30d", "upi_merchant_diversity", "upi_inflow_outflow_ratio",
    "bureau_score", "bureau_enquiry_velocity", "bureau_credit_utilization",
    "electricity_avg_consumption", "electricity_payment_regularity",
    "water_consumption_stability", "water_payment_regularity",
    "epfo_contribution_regularity", "epfo_employee_trend",
    "fuel_expense_regularity", "fuel_liters_cv",
]

TRAIN_WINSOR_LOWER = 0.01
TRAIN_WINSOR_UPPER = 0.99
TRAIN_MISSING_SENTINEL = -999.0
