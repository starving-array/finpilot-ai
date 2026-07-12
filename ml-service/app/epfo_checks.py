import math
try:
    from . import constants as C
except ImportError:
    import constants as C


def _detect_contribution_rate(amount, employee_count):
    """
    Auto-detect whether epfo_contribution_amount is employer-only (12%) or total (24%).
    NOTE: employee_count source is ambiguous — it may come from EPFO returns (registered
    employees only) or GST/MCA data (all employees). The implied wage calculation assumes
    all counted employees are EPFO-registered. If the count includes non-EPFO workers,
    the implied wage will be understated and may trigger false suspicious_low flags.
    """
    implied_at_24pct = amount / (employee_count * 0.24)
    implied_at_12pct = amount / (employee_count * 0.12)

    plausible_24 = C.EPFO_MIN_MONTHLY_WAGE * 0.8 <= implied_at_24pct <= C.EPFO_MAX_MONTHLY_WAGE * 0.8
    plausible_12 = C.EPFO_MIN_MONTHLY_WAGE * 0.8 <= implied_at_12pct <= C.EPFO_MAX_MONTHLY_WAGE * 0.8

    if plausible_24 and not plausible_12:
        return 0.24, implied_at_24pct, "total"
    if plausible_12 and not plausible_24:
        return 0.12, implied_at_12pct, "employer_only"
    if plausible_24 and plausible_12:
        return 0.24, implied_at_24pct, "total"
    if abs(implied_at_12pct - C.EPFO_MIN_MONTHLY_WAGE) < abs(implied_at_24pct - C.EPFO_MIN_MONTHLY_WAGE):
        return 0.12, implied_at_12pct, "employer_only"
    return 0.24, implied_at_24pct, "total"


def check_epfo_plausibility(epfo_employee_count, epfo_contribution_amount):
    if not epfo_employee_count or not epfo_contribution_amount:
        return {
            "flag": "unavailable",
            "message": "EPFO data not available — no plausibility check performed",
        }
    if epfo_employee_count <= 0 or epfo_contribution_amount <= 0:
        return {
            "flag": "unavailable",
            "message": "EPFO data incomplete (count or contribution is zero)",
        }

    rate_used, implied_wage, contribution_type = _detect_contribution_rate(epfo_contribution_amount, epfo_employee_count)

    if implied_wage < C.EPFO_MIN_MONTHLY_WAGE:
        severity = "critical" if implied_wage < C.EPFO_MIN_MONTHLY_WAGE * C.EPFO_SUSPICIOUS_LOW_THRESHOLD else "warning"
        return {
            "flag": f"suspicious_low_{severity}",
            "implied_wage": round(implied_wage, 2),
            "employee_count": epfo_employee_count,
            "contribution_type": contribution_type,
            "message": (
                f"Implied monthly wage (Rs {implied_wage:,.0f}) is below minimum "
                f"(Rs {C.EPFO_MIN_MONTHLY_WAGE:,.0f}) for {epfo_employee_count} employees "
                f"(using {contribution_type} rate). "
                + ("Possible data error or misreporting." if severity == "critical"
                   else "Check if some employees are part-time or contractual.")
            ),
        }
    if implied_wage > C.EPFO_MAX_MONTHLY_WAGE:
        ratio = implied_wage / C.EPFO_MAX_MONTHLY_WAGE
        severity = "critical" if ratio > C.EPFO_SUSPICIOUS_HIGH_THRESHOLD else "warning"
        return {
            "flag": f"suspicious_high_{severity}",
            "implied_wage": round(implied_wage, 2),
            "employee_count": epfo_employee_count,
            "contribution_type": contribution_type,
            "message": (
                f"Implied monthly wage (Rs {implied_wage:,.0f}) exceeds maximum "
                f"(Rs {C.EPFO_MAX_MONTHLY_WAGE:,.0f}) for {epfo_employee_count} employees "
                f"(using {contribution_type} rate). "
                + ("Possible data error — EPFO cap exceeded by 50%+." if severity == "critical"
                   else "Check if some employees are in higher wage brackets.")
            ),
        }
    return {
        "flag": "plausible",
        "implied_wage": round(implied_wage, 2),
        "employee_count": epfo_employee_count,
        "contribution_type": contribution_type,
        "message": f"EPFO data is plausible (implied wage Rs {implied_wage:,.0f}, using {contribution_type} rate)",
    }
