#!/usr/bin/env python3
"""
Generate 350 flat customer profiles for FinPilot AI.
~30% blank-slate (thin or absent GST + UPI).
Deterministic: random.seed(42) — regenerable, identical output.
"""
import csv
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

TOTAL = 350
BLANK_SLATE_TARGET = 0.30

DATE_START = datetime(2023, 1, 1)
DATE_END = datetime(2024, 6, 30)
DATE_SPAN_DAYS = (DATE_END - DATE_START).days

BUSINESS_TYPES = [
    "manufacturing", "logistics", "retail", "services", "trading",
    "food_and_beverage", "agriculture", "construction",
]

SECTOR_DISTRIBUTION = {
    "manufacturing": 0.18,
    "logistics": 0.10,
    "retail": 0.18,
    "services": 0.12,
    "trading": 0.12,
    "food_and_beverage": 0.10,
    "agriculture": 0.10,
    "construction": 0.10,
}

COVERAGE_DROP_RATE = 0.20

INDIAN_STATES = [
    "Maharashtra", "Gujarat", "Tamil Nadu", "Karnataka", "Telangana",
    "Uttar Pradesh", "Rajasthan", "Madhya Pradesh", "West Bengal", "Delhi",
]

FIRST_NAMES = [
    "Amit", "Rajesh", "Sunil", "Vikram", "Suresh", "Mahesh", "Ravi",
    "Sanjay", "Vijay", "Anil", "Deepak", "Prakash", "Manoj", "Rakesh",
    "Arun", "Nitin", "Gaurav", "Kunal", "Harsh", "Rohan",
    "Priya", "Anita", "Neha", "Pooja", "Sneha", "Kavita", "Meena",
    "Rekha", "Asha", "Shweta",
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Gupta", "Singh", "Kumar", "Yadav",
    "Jain", "Agarwal", "Shah", "Das", "Reddy", "Nair", "Menon",
    "Joshi", "Deshmukh", "Kulkarni", "Pillai", "Naidu", "Bose",
]


def pick_business_type():
    r = random.random()
    cumulative = 0.0
    for bt, prob in SECTOR_DISTRIBUTION.items():
        cumulative += prob
        if r < cumulative:
            return bt
    return "retail"


def generate_electricity(business_type):
    ranges = {
        "manufacturing": (2000, 8000), "logistics": (300, 2000),
        "retail": (500, 3000), "services": (200, 1500),
        "trading": (300, 2000), "food_and_beverage": (500, 4000),
        "agriculture": (300, 3000), "construction": (100, 1200),
    }
    lo, hi = ranges.get(business_type, (300, 2000))
    units = round(random.uniform(lo, hi), 1)
    delay = round(random.uniform(0, 30), 1)
    return units, delay


def generate_water(business_type):
    ranges = {
        "manufacturing": (15, 80), "logistics": (5, 25),
        "retail": (3, 20), "services": (2, 15),
        "trading": (3, 20), "food_and_beverage": (10, 60),
        "agriculture": (20, 100), "construction": (5, 40),
    }
    lo, hi = ranges.get(business_type, (5, 25))
    consumption = round(random.uniform(lo, hi), 1)
    delay = round(random.uniform(0, 25), 1)
    return consumption, delay


def generate_epfo(business_type):
    ranges = {
        "manufacturing": (5, 80), "logistics": (3, 40),
        "retail": (2, 25), "services": (3, 60),
        "trading": (2, 20), "food_and_beverage": (3, 50),
        "agriculture": (1, 15), "construction": (2, 40),
    }
    lo, hi = ranges.get(business_type, (2, 30))
    count = random.randint(lo, hi)
    regularity = round(random.uniform(0.3, 1.0), 2)
    avg_wage = random.uniform(10000, 50000)
    contribution = round(count * avg_wage * 0.24, 2)
    return regularity, count, contribution


def generate_fuel(business_type):
    ranges = {
        "manufacturing": (5000, 50000), "logistics": (30000, 200000),
        "retail": (2000, 15000), "services": (1000, 5000),
        "trading": (5000, 30000), "food_and_beverage": (5000, 40000),
        "agriculture": (10000, 80000), "construction": (20000, 100000),
    }
    lo, hi = ranges.get(business_type, (5000, 30000))
    spend = round(random.uniform(lo, hi), 2)

    if business_type == "logistics":
        cv = round(random.uniform(0.10, 0.55), 2)
    elif business_type in ("manufacturing", "agriculture", "construction"):
        cv = round(random.uniform(0.08, 0.45), 2)
    else:
        cv = round(random.uniform(0.05, 0.30), 2)
    return spend, cv


def generate_gst_data(blank_slate):
    if blank_slate:
        if random.random() < 0.4:
            return True, round(random.uniform(2000, 12000), 2), round(random.uniform(0.3, 0.8), 2)
        else:
            return False, None, None
    registered = True
    turnover = round(random.uniform(20000, 5000000), 2)
    regularity = round(random.uniform(0.4, 1.0), 2)
    return registered, turnover, regularity


def generate_upi_data(blank_slate):
    if blank_slate:
        if random.random() < 0.3:
            return random.randint(3, 8), round(random.uniform(1000, 8000), 2)
        else:
            return None, None
    count = random.randint(10, 500)
    value = round(random.uniform(10000, 500000), 2)
    return count, value


def random_profile_date():
    offset = random.randint(0, DATE_SPAN_DAYS)
    dt = DATE_START + timedelta(days=offset)
    return dt.strftime("%Y-%m")


def maybe_drop_alt_data():
    """Randomly decide to drop each alternative data group with COVERAGE_DROP_RATE probability."""
    return {
        "electricity": random.random() > COVERAGE_DROP_RATE,
        "water": random.random() > COVERAGE_DROP_RATE,
        "epfo": random.random() > COVERAGE_DROP_RATE,
        "fuel": random.random() > COVERAGE_DROP_RATE,
    }


def generate_profile(index):
    customer_id = f"CUST{index:05d}"
    blank_slate = index <= int(TOTAL * BLANK_SLATE_TARGET)

    business_type = pick_business_type()
    state = random.choice(INDIAN_STATES)
    years_in_operation = round(random.uniform(0.5, 25.0), 1)
    profile_date = random_profile_date()

    gst_reg, gst_turnover, gst_regularity = generate_gst_data(blank_slate)
    upi_count, upi_value = generate_upi_data(blank_slate)

    present = maybe_drop_alt_data()

    if present["electricity"]:
        elec_units, elec_delay = generate_electricity(business_type)
    else:
        elec_units, elec_delay = None, None

    if present["water"]:
        water_cons, water_delay = generate_water(business_type)
    else:
        water_cons, water_delay = None, None

    if present["epfo"]:
        epfo_reg, epfo_count, epfo_amount = generate_epfo(business_type)
    else:
        epfo_reg, epfo_count, epfo_amount = None, None, None

    if present["fuel"]:
        fuel_spend, fuel_cv = generate_fuel(business_type)
    else:
        fuel_spend, fuel_cv = None, None

    if not blank_slate and years_in_operation > 2:
        loan = round(random.uniform(100000, 5000000), 2)
    else:
        loan = round(random.uniform(50000, 1500000), 2)

    return {
        "customer_id": customer_id,
        "business_type": business_type,
        "state": state,
        "years_in_operation": years_in_operation,
        "profile_date": profile_date,
        "gst_registered": gst_reg,
        "gst_monthly_turnover_avg": gst_turnover,
        "gst_filing_regularity": gst_regularity,
        "upi_monthly_txn_count": upi_count,
        "upi_monthly_txn_value": upi_value,
        "electricity_monthly_units_avg": elec_units,
        "electricity_payment_delay_days_avg": elec_delay,
        "epfo_contribution_regularity": epfo_reg,
        "epfo_employee_count": epfo_count,
        "epfo_contribution_amount": epfo_amount,
        "water_monthly_consumption_kl": water_cons,
        "water_payment_delay_days_avg": water_delay,
        "fuel_monthly_spend_avg": fuel_spend,
        "fuel_spend_volatility": fuel_cv,
        "requested_loan_amount": loan,
        "is_blank_slate": blank_slate,
    }


def main():
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    profiles = [generate_profile(i + 1) for i in range(TOTAL)]

    fieldnames = [
        "customer_id", "business_type", "state",
        "years_in_operation", "profile_date",
        "gst_registered", "gst_monthly_turnover_avg", "gst_filing_regularity",
        "upi_monthly_txn_count", "upi_monthly_txn_value",
        "electricity_monthly_units_avg", "electricity_payment_delay_days_avg",
        "epfo_contribution_regularity", "epfo_employee_count", "epfo_contribution_amount",
        "water_monthly_consumption_kl", "water_payment_delay_days_avg",
        "fuel_monthly_spend_avg", "fuel_spend_volatility",
        "requested_loan_amount", "is_blank_slate",
    ]

    output_path = output_dir / "profiles.csv"
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(profiles)

    blank_count = sum(1 for p in profiles if p["is_blank_slate"])
    print(f"Generated {TOTAL} profiles -> {output_path}")
    print(f"  Blank-slate: {blank_count}/{TOTAL} ({blank_count/TOTAL*100:.1f}%)")
    print(f"  Non-blank:   {TOTAL - blank_count}/{TOTAL} ({(TOTAL-blank_count)/TOTAL*100:.1f}%)")

    covered = sum(1 for p in profiles if p["electricity_monthly_units_avg"] is not None)
    print(f"  With electricity: {covered}/{TOTAL} ({covered/TOTAL*100:.1f}%)")
    covered = sum(1 for p in profiles if p["epfo_contribution_regularity"] is not None)
    print(f"  With EPFO:       {covered}/{TOTAL} ({covered/TOTAL*100:.1f}%)")
    covered = sum(1 for p in profiles if p["water_monthly_consumption_kl"] is not None)
    print(f"  With water:      {covered}/{TOTAL} ({covered/TOTAL*100:.1f}%)")
    covered = sum(1 for p in profiles if p["fuel_monthly_spend_avg"] is not None)
    print(f"  With fuel:       {covered}/{TOTAL} ({covered/TOTAL*100:.1f}%)")

    type_dist = {}
    for p in profiles:
        bt = p["business_type"]
        type_dist[bt] = type_dist.get(bt, 0) + 1
    print(f"\n  Sector distribution:")
    for bt, count in sorted(type_dist.items()):
        print(f"    {bt}: {count} ({count/TOTAL*100:.1f}%)")


if __name__ == "__main__":
    main()
