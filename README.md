# DataScreenIQ Python SDK

<p align="center">
  <img src="https://img.shields.io/pypi/v/datascreeniq?color=0b5c42&label=PyPI&logo=pypi&logoColor=white" alt="PyPI version">
  <img src="https://img.shields.io/pypi/pyversions/datascreeniq?color=0b5c42" alt="Python 3.8+">
  <img src="https://img.shields.io/pypi/dm/datascreeniq?color=0b5c42&label=installs" alt="Monthly installs">
  <img src="https://img.shields.io/badge/license-MIT-0b5c42" alt="MIT License">
  <img src="https://img.shields.io/badge/response-<10ms-059669" alt="Sub-10ms">
</p>

<p align="center">
  <b>Most data pipelines don’t fail — they silently corrupt production data, break dashboards, and go unnoticed for days.</b><br>
  Real-time data quality screening at the edge. Screen any data payload and get **PASS / WARN / BLOCK** in milli seconds.
</p>

---

## The problem

Your pipeline ran successfully last night. The dashboard is broken this morning. Somewhere between your upstream API and your database, a field went null, a type changed, or a schema drifted — and nothing caught it.

DataScreenIQ sits between your data sources and your storage. Every payload is screened before it touches a database.

```
Your API → DataScreenIQ → PASS ✓ → Database
                        → WARN ⚠ → Quarantine
                        → BLOCK ✗ → Dead-letter queue
```

---

## Install

```bash
pip install datascreeniq
```

Optional extras:

```bash
pip install datascreeniq[pandas]   # screen DataFrames directly
pip install datascreeniq[excel]    # screen .xlsx files
pip install datascreeniq[all]      # everything
```

---

## 60-second quickstart

```python
import datascreeniq as dsiq

client = dsiq.Client("dsiq_live_...")   # get free key at datascreeniq.com

rows = [
    {"order_id": "ORD-001", "amount": 99.50,    "email": "alice@corp.com"},
    {"order_id": "ORD-002", "amount": "broken", "email": None},           # type mismatch
    {"order_id": "ORD-003", "amount": 75.00,    "email": None},           # null
]

report = client.screen(rows, source="orders")

print(report.status)          # BLOCK
print(report.health_pct)      # 34.0%
print(report.type_mismatches) # ["amount"]
print(report.null_rates)      # {"email": 0.67}
print(report.summary())
# 🚨 BLOCK | Health: 34.0% | Rows: 3 | Type mismatches: amount | Null rate: email=67% | (7ms)
```

**Response in ~7ms. No polling. No async setup.**

---

## What gets detected

| Signal | What it catches |
|--------|----------------|
| **Schema drift** | Fields added, removed, or renamed since last batch |
| **Type instability** | `amount` was `float`, now it's `"broken"` (string) |
| **Null rate spikes** | `email` completeness dropped from 100% → 33% |
| **Distribution shifts** | `amount` p95 jumped from $500 to $148,000 |
| **Duplicate cardinality** | `order_id` distinct count collapsed — likely duplication |

Detection is statistical and runs in-memory at the edge. Raw data is **never stored**.

---

## Pipeline integration

### Block bad data from reaching your database

```python
from datascreeniq.exceptions import DataQualityError

try:
    client.screen(rows, source="orders").raise_on_block()
    load_to_warehouse(rows)                    # only runs on PASS or WARN

except DataQualityError as e:
    send_to_dead_letter_queue(rows)
    alert_team(f"Pipeline blocked: {e.report.summary()}")
```

### Apache Airflow

```python
from airflow.decorators import task
import datascreeniq as dsiq

@task
def quality_gate(rows: list, source: str) -> dict:
    report = dsiq.Client().screen(rows, source=source)
    if report.is_blocked:
        raise ValueError(f"Data quality gate failed: {report.summary()}")
    return report.to_dict()
```

### Prefect

```python
from prefect import flow, task
import datascreeniq as dsiq

@task
def screen_data(rows, source):
    dsiq.Client().screen(rows, source=source).raise_on_block()

@flow
def etl_pipeline():
    rows = extract_from_source()
    screen_data(rows, source="orders")   # raises if blocked
    load_to_warehouse(rows)
```

### pandas DataFrame

```python
import pandas as pd
import datascreeniq as dsiq

df = pd.read_csv("orders.csv")
report = dsiq.Client().screen_dataframe(df, source="orders")
print(report.summary())
```

### dbt post-hook

```python
import pandas as pd
import datascreeniq as dsiq

def screen_dbt_model(model_name: str, conn):
    df = pd.read_sql(f"SELECT * FROM {model_name} LIMIT 10000", conn)
    dsiq.Client().screen_dataframe(df, source=model_name).raise_on_block()
```

### CSV / Excel / JSON / XML files

```python
report = client.screen_file("orders.csv",  source="orders")
report = client.screen_file("orders.xlsx", source="orders", sheet=0)  # [excel]
report = client.screen_file("events.json", source="events")
report = client.screen_file("feed.xml",    source="feed")
```

---

## Large files — auto chunking

Files over 10,000 rows are automatically split and screened in parallel. Results are merged into a single report:

```python
# 1M-row file — runs as 100 parallel API calls, one merged ScreenReport
report = client.screen_file("events.csv", source="events")
print(f"Screened {report.rows_received:,} rows in {report.latency_ms}ms")
```

---

## The ScreenReport object

```python
# Decision
report.status           # "PASS" | "WARN" | "BLOCK"
report.is_pass          # bool
report.is_warn          # bool
report.is_blocked       # bool
report.health_score     # 0.0 – 1.0
report.health_pct       # "94.5%"

# Issues
report.issues           # full issues dict
report.type_mismatches  # ["amount", "price"]
report.null_rates       # {"email": 0.50, "phone": 0.12}
report.outlier_fields   # ["amount"]

# Schema drift
report.drift            # list of drift events
report.drift_count      # int
report.has_drift        # bool

# Metadata
report.rows_received    # int
report.rows_sampled     # int
report.latency_ms       # int
report.batch_id         # str (uuid)
report.timestamp        # ISO 8601 string
report.sample_version   # "v2" — auditable sampling strategy

# Output
report.summary()        # human-readable one-liner
report.to_dict()        # full API response as dict
```

---

## Error handling

```python
from datascreeniq.exceptions import (
    AuthenticationError,   # invalid or missing API key
    PlanLimitError,        # monthly row limit exceeded
    RateLimitError,        # too many requests — retry with backoff
    ValidationError,       # malformed payload
    APIError,              # unexpected server error
    DataQualityError,      # raised by .raise_on_block()
)

try:
    report = client.screen(rows, source="orders")
except AuthenticationError:
    print("Invalid API key — check DATASCREENIQ_API_KEY")
except PlanLimitError:
    print("Monthly limit reached — upgrade at datascreeniq.com/pricing")
except RateLimitError as e:
    print(f"Rate limited — retry after {e.retry_after}s")
```

---

## Configuration

```python
# From environment variable (recommended for production)
export DATASCREENIQ_API_KEY="dsiq_live_..."

client = dsiq.Client()   # reads env automatically
```

```python
# Explicit key
client = dsiq.Client("dsiq_live_...")

# Custom timeout (default: 30s)
client = dsiq.Client(timeout=10)
```

---

## Privacy

DataScreenIQ processes data **in-memory only** at the edge (Cloudflare Workers). Raw payload values are discarded immediately after statistical analysis. We retain only aggregated quality signals — null rates, type distributions, schema hashes. No row-level data, no PII, ever.

→ [Full privacy architecture](https://datascreeniq.com/privacy)

---

## Why this exists

Data quality tools are almost always batch-based — they run *after* data is already in your warehouse. By the time Great Expectations or dbt tests flag an issue, bad rows have been in production for hours.

DataScreenIQ moves validation to the ingest boundary. The check happens before `INSERT`, before transformation, before the dashboard query that returns NaN at 9am.

---

## Pricing

| Plan | Price | Rows / month |
|------|-------|-------------|
| Developer | **Free** | 500K |
| Starter | $19/mo | 5M |
| Growth | $79/mo | 50M |
| Scale | $199/mo | 500M+ |

[Get a free API key →](https://datascreeniq.com)

---

## See also

- [Examples directory](./examples/) — Airflow DAG, Prefect flow, pandas pipeline, dbt hook
- [Full API reference](https://datascreeniq.com/docs)
- [Privacy architecture](https://datascreeniq.com/privacy)
- [PyPI package](https://pypi.org/project/datascreeniq/)

Questions or issues → [api@datascreeniq.com](mailto:api@datascreeniq.com) or [open an issue](https://github.com/AppDevIQ/datascreeniq-python/issues)

---

## License

MIT © DataScreenIQ
