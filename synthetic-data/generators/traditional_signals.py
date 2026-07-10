import json
import random
from datetime import datetime, timedelta, timezone

random.seed(42)


def generate_gst_data(vintage_months: int, completeness: float) -> dict:
    if random.random() > completeness or vintage_months < 6:
        return {}

    num_returns = min(vintage_months, 24) if random.random() < completeness else 0
    if num_returns == 0:
        return {}

    returns = []
    for m in range(num_returns):
        monthly_revenue = round(random.uniform(50000, 5000000), 2)
        returns.append({
            "period": f"2024-{(m % 12) + 1:02d}",
            "revenue": monthly_revenue,
            "tax_paid": round(monthly_revenue * random.uniform(0.05, 0.18), 2),
            "filed_on_time": random.random() < 0.85,
        })

    gstr1_vs_3b = round(random.uniform(0.85, 1.0), 4)
    nil_returns = sum(1 for r in returns if r["revenue"] < 1000)
    filing_delays = sum(1 for r in returns if not r["filed_on_time"])

    return {
        "returns": returns,
        "filing_regularity": round(1.0 - (filing_delays / max(len(returns), 1)), 4),
        "tax_growth_yoy": round(random.uniform(-0.2, 0.5), 4),
        "gstr1_vs_gstr3b_match": gstr1_vs_3b,
        "nil_return_ratio": round(nil_returns / max(len(returns), 1), 4),
        "compliance_score": round(random.uniform(0.4, 1.0), 4),
    }


def generate_upi_data(completeness: float) -> dict:
    if random.random() > completeness:
        return {}

    num_transactions = random.randint(10, 500) if random.random() < completeness else 0
    if num_transactions == 0:
        return {}

    transactions = []
    for _ in range(num_transactions):
        days_ago = random.randint(0, 90)
        transactions.append({
            "date": (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat(),
            "amount": round(random.uniform(100, 500000), 2),
            "type": random.choice(["INFLOW", "OUTFLOW"]),
            "merchant_category": random.choice([
                "Groceries", "Electronics", "Transport", "Utilities",
                "Rent", "Salary", "Raw Materials", "Miscellaneous",
            ]),
        })

    inflow = [t for t in transactions if t["type"] == "INFLOW"]
    outflow = [t for t in transactions if t["type"] == "OUTFLOW"]

    inflow_amounts = [t["amount"] for t in inflow]
    outflow_amounts = [t["amount"] for t in outflow]
    merchants = set(t["merchant_category"] for t in transactions)

    return {
        "transactions": transactions[:50],
        "txn_volume_30d": len([t for t in transactions if t["date"] > (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()]),
        "inflow_total_30d": round(sum(inflow_amounts) / max(len(inflow_amounts), 1) * min(len(inflow_amounts), 30), 2),
        "outflow_total_30d": round(sum(outflow_amounts) / max(len(outflow_amounts), 1) * min(len(outflow_amounts), 30), 2),
        "merchant_diversity": len(merchants),
        "inflow_outflow_ratio": round(sum(inflow_amounts) / max(sum(outflow_amounts), 1), 4),
        "active_days_ratio": round(random.uniform(0.3, 1.0), 4),
    }


def generate_bureau_data() -> dict:
    if random.random() < 0.15:
        return {}

    score = random.randint(300, 900)
    return {
        "bureau_score": score,
        "enquiry_count_90d": random.randint(0, 10),
        "delinquency_flag": random.random() < 0.12,
        "oldest_account_age_months": random.randint(6, 180),
        "credit_utilization": round(random.uniform(0.0, 1.0), 4),
        "total_trade_lines": random.randint(1, 15),
        "credit_mix_score": round(random.uniform(0.3, 1.0), 4),
    }
