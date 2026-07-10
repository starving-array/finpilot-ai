import json
import random
from datetime import datetime, timedelta, timezone

random.seed(42)


def generate_electricity_data(completeness: float) -> dict:
    if random.random() > completeness:
        return {}

    num_months = random.randint(3, 24) if random.random() < completeness else 0
    if num_months == 0:
        return {}

    bills = []
    for m in range(num_months):
        consumption = round(random.uniform(100, 10000), 2)
        bills.append({
            "month": f"2024-{(m % 12) + 1:02d}",
            "kwh": consumption,
            "amount": round(consumption * random.uniform(5, 12), 2),
            "paid_on_time": random.random() < 0.8,
        })

    consumptions = [b["kwh"] for b in bills]
    mean_c = sum(consumptions) / len(consumptions)
    variance = sum((c - mean_c) ** 2 for c in consumptions) / len(consumptions)

    return {
        "bills": bills,
        "avg_monthly_consumption": round(mean_c, 2),
        "consumption_cv": round((variance ** 0.5) / mean_c, 4) if mean_c > 0 else 0,
        "payment_delay_avg_days": round(random.uniform(0, 45), 2),
        "seasonal_amplitude": round(random.uniform(0.05, 0.4), 4),
        "payment_regularity": round(sum(1 for b in bills if b["paid_on_time"]) / len(bills), 4),
    }


def generate_water_data(completeness: float) -> dict:
    if random.random() > completeness:
        return {}

    num_months = random.randint(3, 24)
    consumptions = [round(random.uniform(10, 500), 2) for _ in range(num_months)]
    mean_w = sum(consumptions) / len(consumptions)

    return {
        "avg_monthly_consumption": round(mean_w, 2),
        "consumption_stability": round(1.0 - (max(consumptions) - min(consumptions)) / mean_w, 4) if mean_w > 0 else 0,
        "commercial_ratio": round(random.uniform(0.1, 0.9), 4),
        "payment_regularity": round(random.uniform(0.5, 1.0), 4),
    }


def generate_epfo_data(vintage_months: int, completeness: float) -> dict:
    if random.random() > completeness or vintage_months < 12:
        return {}

    num_months = min(vintage_months, 24)
    contributions = []
    employees = []
    for m in range(num_months):
        emp_count = random.randint(1, 100)
        employees.append(emp_count)
        contributions.append({
            "month": f"2024-{(m % 12) + 1:02d}",
            "employee_count": emp_count,
            "total_contribution": round(emp_count * random.uniform(5000, 25000), 2),
            "filed_on_time": random.random() < 0.85,
        })

    avg_emp = sum(employees) / len(employees)
    return {
        "contributions": contributions,
        "contribution_regularity": round(sum(1 for c in contributions if c["filed_on_time"]) / len(contributions), 4),
        "employee_count_trend_6m": round(employees[-1] - employees[-6], 2) if len(employees) >= 6 else 0,
        "avg_wage_growth": round(random.uniform(-0.05, 0.15), 4),
        "avg_employee_count": round(avg_emp, 0),
    }


def generate_fuel_data(completeness: float) -> dict:
    if random.random() > completeness:
        return {}

    num_months = random.randint(3, 24)
    liters = [round(random.uniform(50, 5000), 2) for _ in range(num_months)]
    amounts = [round(l * random.uniform(90, 110), 2) for l in liters]
    mean_l = sum(liters) / len(liters)

    return {
        "monthly_liters": liters,
        "monthly_amounts": amounts,
        "expense_regularity": round(1.0 - (max(amounts) - min(amounts)) / max(sum(amounts) / len(amounts), 1), 4),
        "liters_per_month_cv": round((sum((l - mean_l) ** 2 for l in liters) / len(liters)) ** 0.5 / mean_l, 4) if mean_l > 0 else 0,
        "fleet_size_proxy": round(mean_l / 500, 0),
    }
