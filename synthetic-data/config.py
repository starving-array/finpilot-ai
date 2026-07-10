"""
Centralized constants for the synthetic-data pipeline.
Kept in sync with ml-service/app/constants.py for cross-pipeline consistency.
"""

# ─── Domain A: Financial Capacity ─────────────────────────────────────────

ELEC_90TH_PERCENTILE = {
    "manufacturing": 7800,
    "logistics": 1100,
    "retail": 1600,
    "services": 850,
    "trading": 1000,
}
DEFAULT_ELEC_PERCENTILE = 1000

GST_TURNOVER_THRESHOLD = 15000
FINANCIAL_CAPACITY_SQRT_DIVISOR = 1500.0

# ─── Domain B: Payment Regularity / Evidence Confidence ───────────────────

DELAY_DENOMINATOR_DAYS = 30
SMOOTHING_FACTOR = 2.0
MIN_SIGNAL_FLOOR = 0.01
EVIDENCE_CONFIDENCE_FALLBACK = 0.5
MIN_SIGNALS_FOR_CONFIDENCE = 2

# ─── Domain C: Business Longevity ─────────────────────────────────────────

LONGEVITY_SCALE_YEARS = 15
LONGEVITY_CLIFF_YEARS = 3
LONGEVITY_PAYMENT_GATE = 0.70
LONGEVITY_COVERAGE_GATE = 0.80
LONGEVITY_FLOOR_FACTOR = 0.3

# ─── Domain D: Data Coverage ──────────────────────────────────────────────

DATA_GROUP_WEIGHT = 0.25
DATA_GROUPS = {
    "electricity": ["electricity_monthly_units_avg", "electricity_payment_delay_days_avg"],
    "epfo":        ["epfo_contribution_regularity", "epfo_employee_count"],
    "water":       ["water_monthly_consumption_kl", "water_payment_delay_days_avg"],
    "fuel":        ["fuel_monthly_spend_avg", "fuel_spend_volatility"],
}

# ─── Domain E: Blank-Slate Thresholds ─────────────────────────────────────

BST_THRESHOLDS = {
    "manufacturing": {"gst": 18000, "upi": 8},
    "logistics":     {"gst": 12000, "upi": 15},
    "retail":        {"gst": 20000, "upi": 5},
    "services":      {"gst": 15000, "upi": 10},
    "trading":       {"gst": 16000, "upi": 12},
}
BST_FALLBACK = {"gst": 15000, "upi": 10}

# ─── Domain F: Composite Score Weights ────────────────────────────────────

COMPOSITE_WEIGHTS = {
    "payment_regularity": 0.40,
    "financial_capacity_proxy": 0.25,
    "business_longevity": 0.20,
    "data_coverage": 0.10,
    "evidence_confidence": 0.05,
}
SIGNAL_WEIGHTS = {
    "manufacturing": {"gst": 1.0, "epfo": 1.0, "electricity": 1.4, "water": 1.2, "fuel": 0.4},
    "logistics":    {"gst": 1.0, "epfo": 0.8, "electricity": 0.6, "water": 0.4, "fuel": 1.6},
    "retail":       {"gst": 1.2, "epfo": 1.1, "electricity": 0.9, "water": 0.6, "fuel": 0.4},
    "services":     {"gst": 1.0, "epfo": 1.4, "electricity": 0.5, "water": 0.3, "fuel": 0.4},
    "trading":      {"gst": 1.3, "epfo": 1.0, "electricity": 0.6, "water": 0.3, "fuel": 0.9},
}

# ─── Domain G: Label Buckets ──────────────────────────────────────────────

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

# ─── Domain H: Known Risk Signal Injection ────────────────────────────────

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

# ─── Domain I: Validation Gates ───────────────────────────────────────────

LABEL_PRECISION_TARGET = 0.75
LABEL_KS_TARGET = 0.40
BUCKET_RANGE_MIN = 10
BUCKET_RANGE_MAX = 50
