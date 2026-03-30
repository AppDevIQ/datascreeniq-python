"""
DataScreenIQ SDK — Usage Examples
"""

import datascreeniq as dsiq
from datascreeniq.exceptions import DataQualityError, PlanLimitError

# ─────────────────────────────────────────────────────────────
# 1. Basic screening
# ─────────────────────────────────────────────────────────────

client = dsiq.Client("dsiq_live_...")   # or set DATASCREENIQ_API_KEY env var

rows = [
    {"order_id": "ORD-001", "amount": 99.50,    "email": "alice@corp.com", "status": "paid"},
    {"order_id": "ORD-002", "amount": "broken", "email": None,             "status": "paid"},
    {"order_id": "ORD-003", "amount": 75.00,    "email": None,             "status": "pending"},
    {"order_id": "ORD-004", "amount": 220.50,   "email": "bob@corp.com",   "status": "paid"},
]

report = client.screen(rows, source="orders")

print(report.status)        # BLOCK
print(report.health_pct)    # 34.0%
print(report.issues)        # {...}
print(report.summary())     # 🚨 BLOCK | Health: 34.0% | Rows: 4 | ...


# ─────────────────────────────────────────────────────────────
# 2. Pipeline guard — raise on block
# ─────────────────────────────────────────────────────────────

try:
    client.screen(rows, source="orders").raise_on_block()
    # only reaches here if PASS or WARN
    print("Data is clean — proceeding with pipeline")

except DataQualityError as e:
    print(f"Pipeline blocked: {e}")
    print(f"Issues: {e.report.issues}")
    # send to dead letter queue, alert team, etc.


# ─────────────────────────────────────────────────────────────
# 3. Screen a CSV file
# ─────────────────────────────────────────────────────────────

report = client.screen_file("orders.csv", source="orders")
print(f"{report.status} — {report.rows_received:,} rows screened")


# ─────────────────────────────────────────────────────────────
# 4. Screen an Excel file
# ─────────────────────────────────────────────────────────────

# pip install datascreeniq[excel]
report = client.screen_file("orders.xlsx", source="orders", sheet=0)
print(report.summary())


# ─────────────────────────────────────────────────────────────
# 5. Screen a pandas DataFrame
# ─────────────────────────────────────────────────────────────

# pip install datascreeniq[pandas]
import pandas as pd

df = pd.read_csv("orders.csv")
report = client.screen_dataframe(df, source="orders")

if report.is_blocked:
    print(f"Blocked columns: {report.type_mismatches}")
elif report.is_warn:
    print(f"Warnings: null rates = {report.null_rates}")
else:
    print("All clear — loading to warehouse")


# ─────────────────────────────────────────────────────────────
# 6. Large file — auto chunking (10K rows per request)
# ─────────────────────────────────────────────────────────────

# screen_file and screen() handle chunking automatically
# For 1M rows: 100 API calls, merged into one report
report = client.screen_file("events_1m.csv", source="events")
print(f"Screened {report.rows_received:,} rows — {report.status}")


# ─────────────────────────────────────────────────────────────
# 7. Airflow / Prefect pipeline integration
# ─────────────────────────────────────────────────────────────

def quality_gate(rows, source):
    """Drop this into any pipeline as a quality gate."""
    client = dsiq.Client()  # reads DATASCREENIQ_API_KEY from env
    report = client.screen(rows, source=source)

    if report.is_blocked:
        raise ValueError(
            f"Data quality gate FAILED for '{source}': "
            f"health={report.health_pct}, "
            f"issues={report.type_mismatches or report.null_rates}"
        )

    if report.is_warn:
        import logging
        logging.warning(
            f"Data quality WARNING for '{source}': {report.summary()}"
        )

    return report


# ─────────────────────────────────────────────────────────────
# 8. dbt post-hook style check
# ─────────────────────────────────────────────────────────────

def check_dbt_model(model_name: str, conn):
    """After dbt runs a model, screen the output."""
    import pandas as pd
    df = pd.read_sql(f"SELECT * FROM {model_name} LIMIT 10000", conn)
    client = dsiq.Client()
    return client.screen_dataframe(df, source=model_name).raise_on_block()


# ─────────────────────────────────────────────────────────────
# 9. Context manager — auto closes connection
# ─────────────────────────────────────────────────────────────

with dsiq.Client("dsiq_live_...") as client:
    report = client.screen(rows, source="orders")
    print(report.status)
# session closed automatically


# ─────────────────────────────────────────────────────────────
# 10. Plan limit handling
# ─────────────────────────────────────────────────────────────

from datascreeniq.exceptions import PlanLimitError

try:
    report = client.screen(rows, source="orders")
except PlanLimitError as e:
    print(f"Monthly limit reached: {e}")
    # alert, pause pipeline, notify team
