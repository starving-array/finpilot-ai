import math


VALID_BUSINESS_TYPES = {
    "manufacturing", "logistics", "retail", "services", "trading",
    "food_and_beverage", "agriculture", "construction",
}

# ─── Domain A: Financial Capacity ─────────────────────────────────────────

ELEC_90TH_PERCENTILE = {
    "manufacturing": 7800.0,
    "logistics": 1100.0,
    "retail": 1600.0,
    "services": 850.0,
    "trading": 1000.0,
    "food_and_beverage": 2400.0,
    "agriculture": 1900.0,
    "construction": 650.0,
}
DEFAULT_ELEC_PERCENTILE = 1000.0

TURNOVER_90TH_PERCENTILE = {
    "manufacturing": 7500000.0,
    "logistics": 4500000.0,
    "retail": 1800000.0,
    "services": 1500000.0,
    "trading": 12000000.0,
    "food_and_beverage": 2000000.0,
    "agriculture": 4000000.0,
    "construction": 10000000.0,
}
DEFAULT_TURNOVER_PERCENTILE = 2000000.0

# ─── Domain B: Payment Regularity / Evidence Confidence ───────────────────

DELAY_DENOMINATOR_DAYS = 30.0
SMOOTHING_FACTOR = 2.0
MIN_SIGNAL_FLOOR = 0.01
EVIDENCE_CONFIDENCE_FALLBACK = 0.5
EVIDENCE_CONFIDENCE_HIGH_SINGLE = 0.6
EVIDENCE_CONFIDENCE_LOW_SINGLE = 0.4
EVIDENCE_CONFIDENCE_NO_SIGNALS = 0.3
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
    "food_and_beverage": {"gst": 18000, "upi": 18},
    "agriculture":       {"gst": 9000,  "upi": 4},
    "construction":      {"gst": 25000, "upi": 6},
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
    "manufacturing":    {"gst": 1.0, "epfo": 1.0, "electricity": 1.4, "water": 1.2, "fuel": 0.4},
    "logistics":       {"gst": 1.0, "epfo": 0.8, "electricity": 0.6, "water": 0.4, "fuel": 1.6},
    "retail":          {"gst": 1.2, "epfo": 1.1, "electricity": 0.9, "water": 0.6, "fuel": 0.4},
    "services":        {"gst": 1.0, "epfo": 1.4, "electricity": 0.5, "water": 0.3, "fuel": 0.4},
    "trading":         {"gst": 1.3, "epfo": 1.0, "electricity": 0.6, "water": 0.3, "fuel": 0.9},
    "food_and_beverage": {"gst": 1.0, "epfo": 0.8, "electricity": 1.2, "water": 1.0, "fuel": 0.6},
    "agriculture":      {"gst": 0.6, "epfo": 0.4, "electricity": 1.0, "water": 0.8, "fuel": 0.7},
    "construction":     {"gst": 1.2, "epfo": 0.6, "electricity": 0.3, "water": 0.3, "fuel": 1.4},
}
UNIFORM_WEIGHTS = {"gst": 1.0, "epfo": 1.0, "electricity": 1.0, "water": 1.0, "fuel": 1.0}
SIGNAL_KEYS_ORDER = ["gst", "epfo", "electricity", "water", "fuel"]

# ─── Domain H: Label Buckets ──────────────────────────────────────────────

BUCKET_THRESHOLDS = [
    ("disciplined", 0.80),
    ("yes-to-go", 0.65),
    ("non-disciplined", 0.45),
    ("no-to-go", 0.00),
]

RISK_MAP = {
    "disciplined": 0.90,
    "yes-to-go": 0.70,
    "non-disciplined": 0.40,
    "no-to-go": 0.10,
}

# ─── Domain I: Seasonality Volatility Ranges ──────────────────────────────

SEASONALITY_RULES = {
    "manufacturing": {
        "electricity_monthly_units_avg": {
            "normal_range": [0.05, 0.15], "expected_high_range": [0.15, 0.35],
            "peak_seasons": ["summer", "festive"], "peak_months": [4, 5, 6, 9, 10],
            "relevance": "primary", "risk_penalty": 0.05,
            "reason": "Summer cooling load and pre-festive production ramp-up raise units drawn.",
        },
        "fuel_monthly_spend_avg": {
            "normal_range": [0.08, 0.20], "expected_high_range": [0.20, 0.40],
            "peak_seasons": ["summer", "festive"], "peak_months": [4, 5, 6, 10, 11],
            "relevance": "primary", "risk_penalty": 0.05,
            "reason": "Diesel genset usage rises during summer power cuts and festive overtime.",
        },
        "water_monthly_consumption_kl": {
            "normal_range": [0.05, 0.15], "expected_high_range": [0.15, 0.30],
            "peak_seasons": ["summer"], "peak_months": [4, 5, 6],
            "relevance": "primary", "risk_penalty": 0.03,
            "reason": "Process/cooling water demand increases with summer temperatures.",
        },
        "epfo_employee_count": {
            "normal_range": [0.00, 0.08], "expected_high_range": [0.08, 0.20],
            "peak_seasons": ["festive", "harvest"], "peak_months": [9, 10, 11],
            "relevance": "primary", "risk_penalty": 0.04,
            "reason": "Contract labour added ahead of festive and harvest orders.",
        },
        "gst_monthly_turnover_avg": {
            "normal_range": [0.10, 0.25], "expected_high_range": [0.25, 0.45],
            "peak_seasons": ["festive", "harvest"], "peak_months": [9, 10, 11, 3, 4],
            "relevance": "primary", "risk_penalty": 0.06,
            "reason": "Order books swell before Diwali/wedding season and post-harvest cycles.",
        },
        "gst_filing_regularity": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Filing regularity is a compliance-discipline metric, not seasonal.",
        },
        "epfo_contribution_regularity": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Statutory contribution discipline is behavioural rather than seasonal.",
        },
    },
    "logistics": {
        "electricity_monthly_units_avg": {
            "normal_range": [0.05, 0.12], "expected_high_range": [0.12, 0.25],
            "peak_seasons": ["summer"], "peak_months": [4, 5, 6],
            "relevance": "primary", "risk_penalty": 0.03,
            "reason": "Warehouse cooling load rises in summer.",
        },
        "fuel_monthly_spend_avg": {
            "normal_range": [0.10, 0.25], "expected_high_range": [0.25, 0.50],
            "peak_seasons": ["harvest", "festive", "monsoon"], "peak_months": [3, 4, 10, 11, 7, 8],
            "relevance": "primary", "risk_penalty": 0.04,
            "reason": "Harvest agri-movement and festive e-commerce volume spikes fuel spend.",
        },
        "water_monthly_consumption_kl": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Water is not an operationally meaningful input for logistics.",
        },
        "epfo_employee_count": {
            "normal_range": [0.00, 0.10], "expected_high_range": [0.10, 0.25],
            "peak_seasons": ["festive"], "peak_months": [9, 10, 11],
            "relevance": "primary", "risk_penalty": 0.04,
            "reason": "Driver and warehouse headcount scales for festive dispatch surge.",
        },
        "gst_monthly_turnover_avg": {
            "normal_range": [0.10, 0.25], "expected_high_range": [0.25, 0.45],
            "peak_seasons": ["festive", "harvest"], "peak_months": [9, 10, 11, 3, 4],
            "relevance": "primary", "risk_penalty": 0.05,
            "reason": "Freight billing tracks festive and harvest dispatch cycles.",
        },
        "gst_filing_regularity": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Filing discipline is not seasonal.",
        },
        "epfo_contribution_regularity": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Contribution regularity is independent of freight seasonality.",
        },
    },
    "retail": {
        "electricity_monthly_units_avg": {
            "normal_range": [0.05, 0.15], "expected_high_range": [0.15, 0.30],
            "peak_seasons": ["summer", "festive"], "peak_months": [4, 5, 6, 10, 11],
            "relevance": "primary", "risk_penalty": 0.03,
            "reason": "AC/refrigeration load peaks in summer; festive extended hours add load.",
        },
        "fuel_monthly_spend_avg": {
            "normal_range": [0.10, 0.20], "expected_high_range": [0.20, 0.35],
            "peak_seasons": ["festive", "wedding"], "peak_months": [10, 11, 12, 1],
            "relevance": "primary", "risk_penalty": 0.03,
            "reason": "Last-mile delivery and stock-replenishment trips increase during peaks.",
        },
        "water_monthly_consumption_kl": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Water use in retail is minimal and carries no seasonal risk signal.",
        },
        "epfo_employee_count": {
            "normal_range": [0.00, 0.10], "expected_high_range": [0.10, 0.25],
            "peak_seasons": ["festive", "wedding"], "peak_months": [10, 11, 12, 1],
            "relevance": "primary", "risk_penalty": 0.04,
            "reason": "Temporary sales staff hired for Diwali and wedding-season footfall.",
        },
        "gst_monthly_turnover_avg": {
            "normal_range": [0.15, 0.30], "expected_high_range": [0.30, 0.55],
            "peak_seasons": ["festive", "wedding"], "peak_months": [9, 10, 11, 12, 1, 2],
            "relevance": "primary", "risk_penalty": 0.06,
            "reason": "Retail turnover concentrated around Diwali and wedding season.",
        },
        "gst_filing_regularity": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Filing regularity for retail is compliance-discipline, not seasonal.",
        },
        "epfo_contribution_regularity": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Contribution discipline is not driven by retail sales seasonality.",
        },
    },
    "services": {
        "electricity_monthly_units_avg": {
            "normal_range": [0.03, 0.10], "expected_high_range": [0.10, 0.20],
            "peak_seasons": ["summer"], "peak_months": [4, 5, 6],
            "relevance": "primary", "risk_penalty": 0.02,
            "reason": "Office AC load rises modestly in summer; less volatile than production sectors.",
        },
        "fuel_monthly_spend_avg": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Office-based service MSMEs have negligible fuel dependency.",
        },
        "water_monthly_consumption_kl": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Water consumption for office-based services is minimal.",
        },
        "epfo_employee_count": {
            "normal_range": [0.00, 0.06], "expected_high_range": [0.06, 0.15],
            "peak_seasons": [], "peak_months": [],
            "relevance": "primary", "risk_penalty": 0.03,
            "reason": "Service-sector headcount is typically stable; any sharp swing is the signal.",
        },
        "gst_monthly_turnover_avg": {
            "normal_range": [0.08, 0.18], "expected_high_range": [0.18, 0.30],
            "peak_seasons": ["festive"], "peak_months": [1, 2, 3],
            "relevance": "primary", "risk_penalty": 0.03,
            "reason": "Some uptick around fiscal year-end as clients close budgets.",
        },
        "gst_filing_regularity": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "No structural seasonal driver of filing regularity for services.",
        },
        "epfo_contribution_regularity": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Contribution discipline is not seasonally driven for services.",
        },
    },
    "trading": {
        "electricity_monthly_units_avg": {
            "normal_range": [0.05, 0.12], "expected_high_range": [0.12, 0.25],
            "peak_seasons": ["summer"], "peak_months": [4, 5, 6],
            "relevance": "primary", "risk_penalty": 0.03,
            "reason": "Warehouse/godown cooling and lighting rises in summer.",
        },
        "fuel_monthly_spend_avg": {
            "normal_range": [0.10, 0.22], "expected_high_range": [0.22, 0.45],
            "peak_seasons": ["festive", "harvest"], "peak_months": [9, 10, 11, 3, 4],
            "relevance": "primary", "risk_penalty": 0.04,
            "reason": "Inbound/outbound transport of traded goods spikes around peak cycles.",
        },
        "water_monthly_consumption_kl": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Water is not a material operational input for trading businesses.",
        },
        "epfo_employee_count": {
            "normal_range": [0.00, 0.10], "expected_high_range": [0.10, 0.22],
            "peak_seasons": ["festive"], "peak_months": [9, 10, 11],
            "relevance": "primary", "risk_penalty": 0.03,
            "reason": "Loading/unloading staff scaled for festive stocking cycles.",
        },
        "gst_monthly_turnover_avg": {
            "normal_range": [0.15, 0.30], "expected_high_range": [0.30, 0.55],
            "peak_seasons": ["festive", "harvest"], "peak_months": [9, 10, 11, 3, 4],
            "relevance": "primary", "risk_penalty": 0.06,
            "reason": "Trading turnover is lumpy, concentrated around festive and harvest cycles.",
        },
        "gst_filing_regularity": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Filing discipline is independent of trading-volume seasonality.",
        },
        "epfo_contribution_regularity": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Contribution discipline is not seasonally driven for trading.",
        },
    },
    "food_and_beverage": {
        "electricity_monthly_units_avg": {
            "normal_range": [0.08, 0.20], "expected_high_range": [0.20, 0.40],
            "peak_seasons": ["summer", "festive", "wedding"], "peak_months": [4, 5, 6, 10, 11, 12],
            "relevance": "primary", "risk_penalty": 0.05,
            "reason": "Refrigeration and AC loads peak in summer; catering/banquet events add load.",
        },
        "fuel_monthly_spend_avg": {
            "normal_range": [0.10, 0.22], "expected_high_range": [0.22, 0.40],
            "peak_seasons": ["festive", "wedding"], "peak_months": [10, 11, 12, 1, 2],
            "relevance": "primary", "risk_penalty": 0.04,
            "reason": "Catering delivery and LPG costs rise sharply during wedding and festive season.",
        },
        "water_monthly_consumption_kl": {
            "normal_range": [0.08, 0.18], "expected_high_range": [0.18, 0.35],
            "peak_seasons": ["summer", "wedding"], "peak_months": [4, 5, 6, 11, 12, 1],
            "relevance": "primary", "risk_penalty": 0.03,
            "reason": "Kitchen/catering water use rises with summer demand and wedding volumes.",
        },
        "epfo_employee_count": {
            "normal_range": [0.00, 0.12], "expected_high_range": [0.12, 0.28],
            "peak_seasons": ["wedding", "festive"], "peak_months": [11, 12, 1, 2, 10],
            "relevance": "primary", "risk_penalty": 0.04,
            "reason": "Catering and hospitality staff hired on contract for wedding and festive seasons.",
        },
        "gst_monthly_turnover_avg": {
            "normal_range": [0.15, 0.30], "expected_high_range": [0.30, 0.55],
            "peak_seasons": ["wedding", "festive"], "peak_months": [11, 12, 1, 2, 10],
            "relevance": "primary", "risk_penalty": 0.06,
            "reason": "Restaurant/caterer turnover is dominated by wedding and festive banquet calendar.",
        },
        "gst_filing_regularity": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Filing regularity for F&B is a compliance-discipline metric.",
        },
        "epfo_contribution_regularity": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Contribution discipline is not treated as a seasonal signal for F&B.",
        },
    },
    "agriculture": {
        "electricity_monthly_units_avg": {
            "normal_range": [0.10, 0.25], "expected_high_range": [0.25, 0.50],
            "peak_seasons": ["summer", "harvest"], "peak_months": [3, 4, 5, 10, 11],
            "relevance": "primary", "risk_penalty": 0.04,
            "reason": "Irrigation pump load peaks pre-monsoon; processing units draw heavily during harvest.",
        },
        "fuel_monthly_spend_avg": {
            "normal_range": [0.15, 0.30], "expected_high_range": [0.30, 0.60],
            "peak_seasons": ["harvest", "monsoon"], "peak_months": [3, 4, 10, 11, 7, 8],
            "relevance": "primary", "risk_penalty": 0.04,
            "reason": "Sowing and harvest windows drive expected fuel spikes for machinery and transport.",
        },
        "water_monthly_consumption_kl": {
            "normal_range": [0.15, 0.30], "expected_high_range": [0.30, 0.60],
            "peak_seasons": ["summer", "monsoon"], "peak_months": [3, 4, 5, 6, 7],
            "relevance": "primary", "risk_penalty": 0.03,
            "reason": "Irrigation water demand tied to crop cycle and monsoon timing.",
        },
        "epfo_employee_count": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Agricultural labour is predominantly informal and rarely EPFO-registered.",
        },
        "gst_monthly_turnover_avg": {
            "normal_range": [0.25, 0.45], "expected_high_range": [0.45, 0.70],
            "peak_seasons": ["harvest"], "peak_months": [3, 4, 10, 11],
            "relevance": "primary", "risk_penalty": 0.05,
            "reason": "Turnover is lumpy, concentrated in one or two harvest windows per year.",
        },
        "gst_filing_regularity": {
            "normal_range": [0.05, 0.15], "expected_high_range": [0.15, 0.30],
            "peak_seasons": ["harvest", "monsoon"], "peak_months": [3, 4, 10, 11, 7, 8],
            "relevance": "primary", "risk_penalty": 0.02,
            "reason": "Harvest work pressure and rural connectivity issues genuinely cause filing delays.",
        },
        "epfo_contribution_regularity": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Low EPFO registration share makes contribution regularity an unreliable signal.",
        },
    },
    "construction": {
        "electricity_monthly_units_avg": {
            "normal_range": [0.10, 0.22], "expected_high_range": [0.22, 0.40],
            "peak_seasons": ["summer", "winter"], "peak_months": [3, 4, 5, 11, 12, 1, 2],
            "relevance": "primary", "risk_penalty": 0.03,
            "reason": "Grid electricity use tied to active dry-season construction months.",
        },
        "fuel_monthly_spend_avg": {
            "normal_range": [0.15, 0.30], "expected_high_range": [0.30, 0.55],
            "peak_seasons": ["summer", "winter"], "peak_months": [11, 12, 1, 2, 3, 4],
            "relevance": "primary", "risk_penalty": 0.04,
            "reason": "Heavy machinery and genset use concentrated in dry-season construction window.",
        },
        "water_monthly_consumption_kl": {
            "normal_range": [0.10, 0.22], "expected_high_range": [0.22, 0.40],
            "peak_seasons": ["summer"], "peak_months": [3, 4, 5],
            "relevance": "primary", "risk_penalty": 0.03,
            "reason": "Concrete curing and dust suppression drive higher water use in dry season.",
        },
        "epfo_employee_count": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Construction labour is migrant/contract-based with limited direct EPFO registration.",
        },
        "gst_monthly_turnover_avg": {
            "normal_range": [0.20, 0.40], "expected_high_range": [0.40, 0.65],
            "peak_seasons": ["summer", "winter"], "peak_months": [11, 12, 1, 2, 3, 4],
            "relevance": "primary", "risk_penalty": 0.05,
            "reason": "Billing tracks the dry-season construction window; monsoon dip is structural.",
        },
        "gst_filing_regularity": {
            "normal_range": [0.05, 0.15], "expected_high_range": [0.15, 0.30],
            "peak_seasons": ["monsoon"], "peak_months": [7, 8, 9],
            "relevance": "primary", "risk_penalty": 0.02,
            "reason": "Monsoon site shutdowns and project-based contracting disrupt filing cadence.",
        },
        "epfo_contribution_regularity": {
            "normal_range": [0.00, 0.10], "expected_high_range": None,
            "peak_seasons": [], "peak_months": [],
            "relevance": "none", "risk_penalty": 0.0,
            "reason": "Given the informal labour structure, EPFO regularity is not a reliable signal.",
        },
    },
}

SEASONALITY_TOTAL_PENALTY_CAP = 0.10
SEASONALITY_PEAK_MONTH_DISCOUNT = 0.5

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

PRECISION_LOW_RISK_TARGET = 0.65
RECALL_HIGH_RISK_TARGET = 0.65
ECE_MAX = 0.30
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
