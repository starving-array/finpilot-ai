import math
from .config import settings

MIN_MONTHLY_WAGE = settings.epfo_min_monthly_wage
MAX_MONTHLY_WAGE = settings.epfo_max_monthly_wage
EPFO_EMPLOYER_CONTRIBUTION_RATE = settings.epfo_employer_contribution_rate
EPFO_EMPLOYEE_CONTRIBUTION_RATE = settings.epfo_employee_contribution_rate
TOTAL_EPFO_RATE = EPFO_EMPLOYER_CONTRIBUTION_RATE + EPFO_EMPLOYEE_CONTRIBUTION_RATE


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
    implied_wage = epfo_contribution_amount / (epfo_employee_count * TOTAL_EPFO_RATE)

    if implied_wage < MIN_MONTHLY_WAGE:
        severity = "critical" if implied_wage < MIN_MONTHLY_WAGE * 0.5 else "warning"
        return {
            "flag": f"suspicious_low_{severity}",
            "implied_wage": round(implied_wage, 2),
            "employee_count": epfo_employee_count,
            "message": (
                f"Implied monthly wage (Rs {implied_wage:,.0f}) is below minimum "
                f"(Rs {MIN_MONTHLY_WAGE:,.0f}) for {epfo_employee_count} employees. "
                + ("Possible data error or misreporting." if severity == "critical"
                   else "Check if some employees are part-time or contractual.")
            ),
        }
    if implied_wage > MAX_MONTHLY_WAGE:
        ratio = implied_wage / MAX_MONTHLY_WAGE
        severity = "critical" if ratio > 1.5 else "warning"
        return {
            "flag": f"suspicious_high_{severity}",
            "implied_wage": round(implied_wage, 2),
            "employee_count": epfo_employee_count,
            "message": (
                f"Implied monthly wage (Rs {implied_wage:,.0f}) exceeds maximum "
                f"(Rs {MAX_MONTHLY_WAGE:,.0f}) for {epfo_employee_count} employees. "
                + ("Possible data error — EPFO cap exceeded by 50%+." if severity == "critical"
                   else "Check if some employees are in higher wage brackets.")
            ),
        }
    return {
        "flag": "plausible",
        "implied_wage": round(implied_wage, 2),
        "employee_count": epfo_employee_count,
        "message": f"EPFO data is plausible (implied wage Rs {implied_wage:,.0f})",
    }
