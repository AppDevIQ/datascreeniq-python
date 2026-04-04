"""
DataScreenIQ — dbt Integration: Post-Run Quality Screen

Screen the output of any dbt model after it runs.
Catches schema drift, null spikes, and type mismatches in your
transformed data before downstream consumers see it.

Setup:
    1. pip install datascreeniq pandas sqlalchemy
    2. Set DATASCREENIQ_API_KEY environment variable
    3. Run: python screen_dbt_model.py --model stg_orders --limit 10000

Usage in dbt:
    Add to your dbt_project.yml as a post-hook, or run manually
    after `dbt run` in your CI/CD pipeline.

Get a free API key (500K rows/month): https://datascreeniq.com
"""

import argparse
import sys
import os

import pandas as pd
import datascreeniq as dsiq
from datascreeniq.exceptions import DataQualityError


def screen_model(
    model_name: str,
    connection_string: str = None,
    limit: int = 10_000,
    fail_on_block: bool = True,
) -> dict:
    """
    Screen a dbt model's output through DataScreenIQ.

    Args:
        model_name:        Name of the dbt model (table/view name)
        connection_string: SQLAlchemy connection string. If None, reads
                          from DBT_DATABASE_URL or DATABASE_URL env var.
        limit:            Max rows to sample for screening (default: 10,000)
        fail_on_block:    If True, raises DataQualityError on BLOCK

    Returns:
        Quality report as dict
    """
    # Resolve connection string
    conn_str = (
        connection_string
        or os.getenv("DBT_DATABASE_URL")
        or os.getenv("DATABASE_URL")
    )
    if not conn_str:
        print("❌ No database connection string provided.")
        print("Set DBT_DATABASE_URL or DATABASE_URL, or pass --connection-string")
        sys.exit(1)

    # Read model output
    print(f"Reading {model_name} (limit {limit:,} rows)...")
    from sqlalchemy import create_engine
    engine = create_engine(conn_str)
    df = pd.read_sql(f"SELECT * FROM {model_name} LIMIT {limit}", engine)
    print(f"  Read {len(df):,} rows, {len(df.columns)} columns")

    if df.empty:
        print(f"⚠️ Model {model_name} returned 0 rows — skipping")
        return {"status": "SKIP", "reason": "empty model"}

    # Screen through DataScreenIQ
    client = dsiq.Client()
    report = client.screen_dataframe(df, source=model_name)

    print(f"\n{report.summary()}")
    print(f"  Request ID: {report.request_id}")

    if report.type_mismatches:
        print(f"  Type mismatches: {report.type_mismatches}")
    if report.null_rates:
        print(f"  Null rates: {report.null_rates}")
    if report.has_drift:
        print(f"  Drift events: {report.drift_count}")
        for event in report.drift:
            print(f"    • {event.get('kind')}: {event.get('field')} — {event.get('detail')}")

    # Fail on block
    if fail_on_block and report.is_blocked:
        raise DataQualityError(
            f"dbt model '{model_name}' BLOCKED: {report.summary()}",
            report=report,
        )

    return report.to_dict()


def screen_multiple_models(models: list[str], **kwargs) -> dict:
    """Screen multiple dbt models. Returns summary."""
    results = {}
    blocked = []

    for model in models:
        try:
            result = screen_model(model, **kwargs)
            results[model] = result
            if result.get("status") == "BLOCK":
                blocked.append(model)
        except DataQualityError as e:
            results[model] = {"status": "BLOCK", "error": str(e)}
            blocked.append(model)
        except Exception as e:
            results[model] = {"status": "ERROR", "error": str(e)}
            print(f"❌ Error screening {model}: {e}")

    print(f"\n{'='*60}")
    print(f"dbt Quality Gate Summary: {len(results)} models screened")
    print(f"  Blocked: {len(blocked)}")
    if blocked:
        print(f"  → {', '.join(blocked)}")
    print(f"{'='*60}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Screen dbt model output through DataScreenIQ"
    )
    parser.add_argument(
        "--model", "-m",
        required=True,
        nargs="+",
        help="dbt model name(s) to screen (e.g. stg_orders fct_revenue)",
    )
    parser.add_argument(
        "--connection-string", "-c",
        default=None,
        help="SQLAlchemy connection string (default: DBT_DATABASE_URL env var)",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10_000,
        help="Max rows to sample per model (default: 10,000)",
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Don't fail on BLOCK — just warn",
    )
    args = parser.parse_args()

    if len(args.model) == 1:
        screen_model(
            args.model[0],
            connection_string=args.connection_string,
            limit=args.limit,
            fail_on_block=not args.warn_only,
        )
    else:
        screen_multiple_models(
            args.model,
            connection_string=args.connection_string,
            limit=args.limit,
            fail_on_block=not args.warn_only,
        )
