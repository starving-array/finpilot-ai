#!/usr/bin/env python3
"""
Seeds PostgreSQL database with generated synthetic data.
Reads from output/customers.json and inserts into the FHSS schema.
"""

import json
import hashlib
import os
import uuid as uuid_lib
from pathlib import Path
from datetime import datetime, timezone

try:
    import psycopg2
except ImportError:
    print("psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)


DB_CONFIG = {
    "host": os.environ.get("PGHOST", "localhost"),
    "port": int(os.environ.get("PGPORT", "5432")),
    "dbname": os.environ.get("PGDATABASE", "fhss"),
    "user": os.environ.get("PGUSER", "fhss"),
    "password": os.environ.get("PGPASSWORD", "change_me_in_production"),
}

BATCH_SIZE = 25


def compute_hash(data: dict) -> str:
    raw = json.dumps(data, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def insert_customers(conn, customers: list[dict]) -> dict:
    cursor = conn.cursor()
    id_map = {}  # pan -> customer_id

    sql = """
        INSERT INTO customer (customer_id, pan, cin, name, kyc_status,
                              traditional_data, alternative_data, version,
                              created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 1, NOW(), NOW())
        ON CONFLICT (pan) WHERE deleted_at IS NULL
        DO UPDATE SET name = EXCLUDED.name, updated_at = NOW()
        RETURNING customer_id
    """

    for batch_start in range(0, len(customers), BATCH_SIZE):
        batch = customers[batch_start:batch_start + BATCH_SIZE]
        for c in batch:
            profile = c["customer"]
            customer_id = str(uuid_lib.uuid4())
            cursor.execute(sql, (
                customer_id,
                profile["pan"],
                profile.get("cin"),
                profile["name"],
                profile["kyc_status"],
                json.dumps(c["traditional_data"]),
                json.dumps(c["alternative_data"]),
            ))
            row = cursor.fetchone()
            actual_id = row[0] if row else customer_id
            id_map[profile["pan"]] = str(actual_id)

    conn.commit()
    print(f"Inserted/updated {len(customers)} customers")
    return id_map


def insert_feature_snapshots(conn, customers: list[dict], id_map: dict):
    cursor = conn.cursor()
    count = 0

    sql = """
        INSERT INTO feature_snapshot (snapshot_id, customer_id, feature_vector,
                                      schema_version, computation_version,
                                      completeness_score, blank_slate_mode, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
    """

    for c in customers:
        profile = c["customer"]
        customer_id = id_map.get(profile["pan"])
        if not customer_id:
            continue

        cursor.execute(sql, (
            str(uuid_lib.uuid4()),
            customer_id,
            json.dumps(c["features"]),
            "1.0",
            "1.0.0",
            c["completeness"]["overall"],
            c["completeness"]["blank_slate_mode"],
        ))
        count += 1

    conn.commit()
    print(f"Inserted {count} feature snapshots")


def insert_predictions(conn, customers: list[dict], id_map: dict):
    cursor = conn.cursor()
    count = 0

    sql = """
        INSERT INTO prediction (prediction_id, customer_id, request_id, category,
                                probabilities, confidence, model_version,
                                blank_slate_mode, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (request_id) DO NOTHING
    """

    for c in customers:
        profile = c["customer"]
        customer_id = id_map.get(profile["pan"])
        if not customer_id or not c["labels"]["consensus_label"]:
            continue

        probs = c["labels"]["label_scores"]
        cursor.execute(sql, (
            str(uuid_lib.uuid4()),
            customer_id,
            str(uuid_lib.uuid4()),
            c["labels"]["consensus_label"],
            json.dumps(probs),
            c["labels"]["label_confidence"] * 100,
            "1.0.0",
            c["completeness"]["blank_slate_mode"],
        ))
        count += 1

    conn.commit()
    print(f"Inserted {count} predictions")


def insert_audit_logs(conn, customers: list[dict], id_map: dict):
    cursor = conn.cursor()
    count = 0

    sql = """
        INSERT INTO audit_log (log_id, request_id, customer_id, timestamp, actor,
                               action, input_hash, output_hash)
        VALUES (%s, %s, %s, NOW(), %s, %s, %s, %s)
    """

    actions = ["CUSTOMER_CREATED", "DATA_INGESTED", "FEATURES_COMPUTED", "SCORING_COMPLETED"]

    for c in customers:
        profile = c["customer"]
        customer_id = id_map.get(profile["pan"])
        if not customer_id:
            continue

        for action in actions:
            cursor.execute(sql, (
                str(uuid_lib.uuid4()),
                str(uuid_lib.uuid4()),
                customer_id,
                "system",
                action,
                compute_hash({"action": action, "pan": profile["pan"]}),
                compute_hash(c["features"]),
            ))
            count += 1

    conn.commit()
    print(f"Inserted {count} audit log entries")


def main():
    customers_file = Path(__file__).parent / "output" / "customers.json"
    if not customers_file.exists():
        print(f"Error: {customers_file} not found. Run generate_all.py first.")
        return

    with open(customers_file) as f:
        customers = json.load(f)

    print(f"Loading {len(customers)} customers into database...")
    print(f"  Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"  Database: {DB_CONFIG['dbname']}")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Make sure PostgreSQL is running and accessible.")
        return

    try:
        id_map = insert_customers(conn, customers)
        insert_feature_snapshots(conn, customers, id_map)
        insert_predictions(conn, customers, id_map)
        insert_audit_logs(conn, customers, id_map)
        print("\nDatabase seeding complete!")
    except Exception as e:
        conn.rollback()
        print(f"Error during seeding: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    main()
