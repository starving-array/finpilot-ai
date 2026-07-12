from . import constants as C


def compute_capacity_flag(
    requested_loan_amount,
    gst_monthly_turnover_avg,
    electricity_monthly_units_avg,
    business_type,
):
    """
    NOTE: ELEC_PROXY_REVENUE_BASE (₹5,00,000) in constants.py is an arbitrary estimate.
    The formula proxy_revenue = (units / percentile) * base is not empirically calibrated.
    When source='electricity_proxy', the ratio should be treated as a rough heuristic,
    not a precise capacity measurement. Prefer GST-based revenue when available.
    """
    if not requested_loan_amount or requested_loan_amount <= 0:
        return {"flag": "unavailable", "message": "No loan amount provided"}

    loan = float(requested_loan_amount)

    if gst_monthly_turnover_avg and float(gst_monthly_turnover_avg) > 0:
        annual_revenue = float(gst_monthly_turnover_avg) * 12.0
        ratio = loan / annual_revenue if annual_revenue > 0 else float("inf")
        source = "gst"
    elif electricity_monthly_units_avg and float(electricity_monthly_units_avg) > 0:
        percentile = C.ELEC_90TH_PERCENTILE.get(business_type, C.DEFAULT_ELEC_PERCENTILE)
        proxy_revenue = float(electricity_monthly_units_avg) / percentile * C.ELEC_PROXY_REVENUE_BASE
        ratio = loan / proxy_revenue if proxy_revenue > 0 else float("inf")
        source = "electricity_proxy"
    else:
        return {
            "flag": "insufficient_data",
            "message": "Cannot assess capacity — no turnover or electricity data",
        }

    if ratio > C.LOAN_TO_ANNUAL_REVENUE_CAP:
        severity = "high_risk" if ratio > C.LOAN_HIGH_RISK_RATIO else "caution"
        message = (
            f"Loan amount (Rs {loan:,.0f}) is {ratio:.1f}x annual {'revenue' if source == 'gst' else 'proxy revenue'} "
            f"(threshold: {C.LOAN_TO_ANNUAL_REVENUE_CAP:.0%}). "
            + ("This exceeds a safe capacity level." if severity == "high_risk"
               else "Close to the capacity threshold — consider reducing loan amount.")
        )
        return {
            "flag": severity,
            "loan_to_revenue_ratio": round(ratio, 4),
            "source": source,
            "message": message,
        }

    return {
        "flag": "normal",
        "loan_to_revenue_ratio": round(ratio, 4),
        "source": source,
        "message": f"Loan amount is well within capacity ({ratio:.1f}x annual {source})",
    }
