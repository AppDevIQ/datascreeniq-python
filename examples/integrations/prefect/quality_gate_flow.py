"""
DataScreenIQ — Prefect Integration: Quality Gate Flow

A Prefect flow that screens extracted data through DataScreenIQ
before loading it to the warehouse.

Setup:
    1. pip install datascreeniq prefect
    2. Set DATASCREENIQ_API_KEY environment variable
    3. Run: python quality_gate_flow.py

Get a free API key (500K rows/month): https://datascreeniq.com
"""

from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from datetime import timedelta

import datascreeniq as dsiq
from datascreeniq.exceptions import DataQualityError


@task(retries=2, retry_delay_seconds=30)
def extract_data(source_name: str) -> list[dict]:
    """
    Extract data from your source.
    Replace with your actual extraction logic.
    """
    logger = get_run_logger()

    # Simulated extraction — replace with your real source
    rows = [
        {"order_id": "ORD-001", "amount": 99.50,  "email": "alice@corp.com", "status": "paid"},
        {"order_id": "ORD-002", "amount": 150.00, "email": "bob@corp.com",   "status": "paid"},
        {"order_id": "ORD-003", "amount": 75.00,  "email": None,             "status": "pending"},
        {"order_id": "ORD-004", "amount": 220.50, "email": "carol@corp.com", "status": "paid"},
    ]

    logger.info(f"Extracted {len(rows)} rows from '{source_name}'")
    return rows


@task(retries=1)
def screen_data(rows: list[dict], source_name: str) -> dict:
    """
    Screen data through DataScreenIQ.
    Raises DataQualityError if data is BLOCKED.
    """
    logger = get_run_logger()

    client = dsiq.Client()  # reads DATASCREENIQ_API_KEY from env
    report = client.screen(rows, source=source_name)

    logger.info(f"Quality: {report.summary()}")

    if report.is_blocked:
        logger.error(f"🚨 BLOCKED: {report.summary()}")
        raise DataQualityError(
            f"Data quality gate FAILED for '{source_name}': {report.summary()}",
            report=report,
        )

    if report.is_warn:
        logger.warning(f"⚠️ Warnings: {report.summary()}")
        if report.type_mismatches:
            logger.warning(f"  Type mismatches: {report.type_mismatches}")
        if report.null_rates:
            logger.warning(f"  Null rates: {report.null_rates}")

    return report.to_dict()


@task(retries=2, retry_delay_seconds=10)
def load_to_warehouse(rows: list[dict], source_name: str, report: dict):
    """
    Load clean data to the warehouse.
    Only runs if screen_data passed.
    """
    logger = get_run_logger()
    status = report.get("status", "UNKNOWN")
    logger.info(f"Loading {len(rows)} rows to warehouse (quality: {status})")

    # Replace with your actual load logic:
    # bigquery_client.insert_rows_json(table, rows)
    # snowflake_cursor.executemany(insert_sql, rows)

    logger.info(f"✅ Loaded {len(rows)} rows successfully")


@task
def send_alert(source_name: str, error: str):
    """Send alert on quality failure."""
    logger = get_run_logger()
    logger.error(f"🚨 Alerting: {source_name} — {error}")
    # Customise: Slack, PagerDuty, email, etc.
    # slack.post_message("#data-alerts", f"Pipeline blocked: {source_name}")


@flow(name="etl-with-quality-gate", log_prints=True)
def etl_pipeline(source_name: str = "orders"):
    """
    ETL pipeline with DataScreenIQ quality gate.

    Flow:
        extract → screen → load
                    ↓ (on BLOCK)
                  alert
    """
    rows = extract_data(source_name)

    try:
        report = screen_data(rows, source_name)
        load_to_warehouse(rows, source_name, report)
        print(f"✅ Pipeline complete for '{source_name}'")

    except DataQualityError as e:
        send_alert(source_name, str(e))
        raise  # re-raise so Prefect marks the flow as failed


@flow(name="multi-source-etl", log_prints=True)
def multi_source_pipeline(sources: list[str] = None):
    """Screen and load data from multiple sources."""
    sources = sources or ["orders", "events", "users"]

    for source in sources:
        etl_pipeline(source_name=source)

    print(f"✅ All {len(sources)} sources processed")


if __name__ == "__main__":
    etl_pipeline(source_name="orders")
