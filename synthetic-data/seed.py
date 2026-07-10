#!/usr/bin/env python3
"""
Read profiles_labeled.csv → INSERT INTO customer_profile via psycopg2.
Idempotent: INSERT ON CONFLICT DO NOTHING.

Usage: python seed.py [--csv output/profiles_labeled.csv]
"""

import argparse
import csv
import os
from pathlib import Path

import psycopg2


def get_connection():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=int(os.environ.get("PGPORT", 5432)),
        dbname=os.environ.get("PGDATABASE", "fhss"),
        user=os.environ.get("PGUSER", "fhss"),
        password=os.environ.get("PGPASSWORD", "change_me_in_production"),
    )


def safe_null(val):
    if val is None or val == "" or val == "None":
        return None
    return val


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="output/profiles_labeled.csv")
    args = parser.parse_args()

    csv_path = Path(args.csv)

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Loaded {len(rows)} labeled profiles from {csv_path}")

    conn = get_connection()
    cur = conn.cursor()

    insert_sql = """
        INSERT INTO customer_profile (
            customer_id, business_name, owner_name, business_type, state,
            years_in_operation,
            gst_registered, gst_monthly_turnover_avg, gst_filing_regularity,
            upi_monthly_txn_count, upi_monthly_txn_value,
            electricity_monthly_units_avg, electricity_payment_delay_days_avg,
            epfo_contribution_regularity, epfo_employee_count, epfo_contribution_amount,
            water_monthly_consumption_kl, water_payment_delay_days_avg,
            fuel_monthly_spend_avg, fuel_spend_volatility,
            requested_loan_amount, is_blank_slate
        ) VALUES (
            %(customer_id)s, %(business_name)s, %(owner_name)s, %(business_type)s, %(state)s,
            %(years_in_operation)s,
            %(gst_registered)s, %(gst_monthly_turnover_avg)s, %(gst_filing_regularity)s,
            %(upi_monthly_txn_count)s, %(upi_monthly_txn_value)s,
            %(electricity_monthly_units_avg)s, %(electricity_payment_delay_days_avg)s,
            %(epfo_contribution_regularity)s, %(epfo_employee_count)s, %(epfo_contribution_amount)s,
            %(water_monthly_consumption_kl)s, %(water_payment_delay_days_avg)s,
            %(fuel_monthly_spend_avg)s, %(fuel_spend_volatility)s,
            %(requested_loan_amount)s, %(is_blank_slate)s
        ) ON CONFLICT (customer_id) DO NOTHING
    """

    inserted = 0
    skipped = 0

    for row in rows:
        params = {
            "customer_id": row["customer_id"],
            "business_name": row["business_name"],
            "owner_name": row.get("owner_name", ""),
            "business_type": row["business_type"],
            "state": row.get("state", ""),
            "years_in_operation": safe_null(row.get("years_in_operation")),
            "gst_registered": row.get("gst_registered", "false").lower() in ("true", "1", "yes"),
            "gst_monthly_turnover_avg": safe_null(row.get("gst_monthly_turnover_avg")),
            "gst_filing_regularity": safe_null(row.get("gst_filing_regularity")),
            "upi_monthly_txn_count": safe_null(row.get("upi_monthly_txn_count")),
            "upi_monthly_txn_value": safe_null(row.get("upi_monthly_txn_value")),
            "electricity_monthly_units_avg": safe_null(row.get("electricity_monthly_units_avg")),
            "electricity_payment_delay_days_avg": safe_null(row.get("electricity_payment_delay_days_avg")),
            "epfo_contribution_regularity": safe_null(row.get("epfo_contribution_regularity")),
            "epfo_employee_count": safe_null(row.get("epfo_employee_count")),
            "epfo_contribution_amount": safe_null(row.get("epfo_contribution_amount")),
            "water_monthly_consumption_kl": safe_null(row.get("water_monthly_consumption_kl")),
            "water_payment_delay_days_avg": safe_null(row.get("water_payment_delay_days_avg")),
            "fuel_monthly_spend_avg": safe_null(row.get("fuel_monthly_spend_avg")),
            "fuel_spend_volatility": safe_null(row.get("fuel_spend_volatility")),
            "requested_loan_amount": safe_null(row.get("requested_loan_amount")),
            "is_blank_slate": row.get("is_blank_slate", "false").lower() in ("true", "1", "yes"),
        }

        try:
            cur.execute(insert_sql, params)
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ERROR inserting {row['customer_id']}: {e}")
            skipped += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"Inserted: {inserted}, Skipped: {skipped}")
    print("Done.")


if __name__ == "__main__":
    main()
