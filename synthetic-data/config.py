"""
Single source of truth: re-exports from ml-service/app/constants.py.
All domain constants are defined there, not duplicated here.
"""
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent
_ml_service_path = str(_repo_root / "ml-service")
if _ml_service_path not in sys.path:
    sys.path.insert(0, _ml_service_path)

from app.constants import (
    ELEC_90TH_PERCENTILE,
    DEFAULT_ELEC_PERCENTILE,
    TURNOVER_90TH_PERCENTILE,
    DEFAULT_TURNOVER_PERCENTILE,
    DELAY_DENOMINATOR_DAYS,
    SMOOTHING_FACTOR,
    MIN_SIGNAL_FLOOR,
    EVIDENCE_CONFIDENCE_FALLBACK,
    MIN_SIGNALS_FOR_CONFIDENCE,
    LONGEVITY_SCALE_YEARS,
    LONGEVITY_CLIFF_YEARS,
    LONGEVITY_PAYMENT_GATE,
    LONGEVITY_COVERAGE_GATE,
    LONGEVITY_FLOOR_FACTOR,
    DATA_GROUP_WEIGHT,
    DATA_GROUPS,
    BST_THRESHOLDS,
    BST_FALLBACK,
    COMPOSITE_WEIGHTS,
    SIGNAL_WEIGHTS,
    UNIFORM_WEIGHTS,
    BUCKET_THRESHOLDS,
    RISK_MAP,
    RISK_SIGNAL_THRESHOLDS,
    RISK_SIGNAL_PENALTIES,
    RISK_SIGNAL_BONUSES,
    CATEGORY_ORDER,
    LABEL_PRECISION_TARGET,
    LABEL_KS_TARGET,
    BUCKET_RANGE_MIN,
    BUCKET_RANGE_MAX,
    VALID_BUSINESS_TYPES,
)
