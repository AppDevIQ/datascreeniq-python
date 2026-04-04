"""
DataScreenIQ — Airflow Integration: Quality Gate DAG

A complete Airflow DAG that screens extracted data through DataScreenIQ
before loading it to the warehouse. If the data is BLOCKED, the pipeline
stops and sends an alert.

Setup:
    1. pip install datascreeniq apache-airflow
    2. Set the DATASCREENIQ_API_KEY environment variable (or Airflow Variable)
    3. Copy this file to your dags/ folder
    4. Customise extract_data() and load_to_warehouse() for your pipeline

Get a free API key (500K rows/month): https://datascreeniq.com
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable

import datascreeniq as dsiq
from datascreeniq.exceptions import DataQualityError


default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="etl_with_quality_gate",
    default_args=default_args,
    description="ETL pipeline with DataScreenIQ quality screening before load",
    schedule="0 6 * * *",       # daily at 6am
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["data-quality", "datascreeniq", "etl"],
) as dag:

    @task()
    def extract_data() -> list[dict]:
        """
        Extract data from your source.
        Replace this with your actual extraction logic.
        """
        # Example: fetch from an API, read from S3, query a database, etc.
        import json

        # Simulated extraction — replace with your real source
        rows = [
            {"order_id": "ORD-001", "amount": 99.50,  "email": "alice@corp.com", "status": "paid"},
            {"order_id": "ORD-002", "amount": 150.00, "email": "bob@corp.com",   "status": "paid"},
            {"order_id": "ORD-003", "amount": 75.00,  "email": None,             "status": "pending"},
            {"order_id": "ORD-004", "amount": 220.50, "email": "carol@corp.com", "status": "paid"},
        ]

        print(f"Extracted {len(rows)} rows")
        return rows

    @task()
    def quality_gate(rows: list[dict]) -> dict:
        """
        Screen extracted data through DataScreenIQ.
        Raises an exception if data is BLOCKED, stopping the pipeline.
        Returns the quality report for downstream tasks.
        """
        # Get API key from Airflow Variable or environment
        api_key = Variable.get("DATASCREENIQ_API_KEY", default_var=None)
        client = dsiq.Client(api_key)  # falls back to env var if None

        report = client.screen(rows, source="orders")

        print(f"Quality report: {report.summary()}")
        print(f"  Status:       {report.status}")
        print(f"  Health:       {report.health_pct}")
        print(f"  Rows:         {report.rows_received}")
        print(f"  Latency:      {report.latency_ms}ms")

        if report.is_blocked:
            raise DataQualityError(
                f"Data quality gate FAILED for 'orders': {report.summary()}",
                report=report,
            )

        if report.is_warn:
            print(f"⚠️ Quality warnings detected — proceeding with caution")
            if report.type_mismatches:
                print(f"  Type mismatches: {report.type_mismatches}")
            if report.null_rates:
                print(f"  Null rates: {report.null_rates}")

        return report.to_dict()

    @task()
    def load_to_warehouse(rows: list[dict], report: dict):
        """
        Load clean data to your warehouse.
        Only runs if quality_gate passed.
        Replace this with your actual load logic.
        """
        status = report.get("status", "UNKNOWN")
        print(f"Loading {len(rows)} rows to warehouse (quality: {status})")

        # Example: write to BigQuery, Snowflake, Postgres, S3, etc.
        # bigquery_client.insert_rows_json(table, rows)

        print(f"✅ Loaded {len(rows)} rows successfully")

    @task(trigger_rule="one_failed")
    def alert_on_failure():
        """
        Send alert when the quality gate blocks data.
        Customise with your alerting: Slack, PagerDuty, email, etc.
        """
        print("🚨 Quality gate BLOCKED the pipeline — sending alert")
        # Example:
        # slack.post_message("#data-alerts", "Pipeline blocked by DataScreenIQ")
        # pagerduty.trigger("Data quality failure in orders pipeline")

    # ── DAG flow ──
    extracted = extract_data()
    report = quality_gate(extracted)
    load_to_warehouse(extracted, report)
    alert_on_failure()
