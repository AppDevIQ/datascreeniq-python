# DataScreenIQ Python SDK

[![PyPI version](https://badge.fury.io/py/datascreeniq.svg)](https://pypi.org/project/datascreeniq/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Pipelines don’t fail — they silently corrupt data.

DataScreenIQ acts as a gate before your database, detecting schema drift,
missing values, and type mismatches in real time.

Real-time data quality screening at the edge. Screen any data payload and get **PASS / WARN / BLOCK** in milli seconds .

```python
import datascreeniq as dsiq

client = dsiq.Client("dsiq_live_...")
report = client.screen(rows, source="orders")

print(report.status)       # BLOCK
print(report.health_pct)   # 34.0%
print(report.issues)       # {"type_mismatches": ["amount"], "null_rates": {"email": 0.5}}
```

---

## Installation

```bash
pip install datascreeniq
```

With pandas support:
```bash
pip install datascreeniq[pandas]
```

With Excel support:
```bash
pip install datascreeniq[excel]
```

Everything:
```bash
pip install datascreeniq[all]
```

---

## Quick start

Get a free API key at [datascreeniq.com](https://datascreeniq.com) — 500K rows/month free.

```python
import datascreeniq as dsiq

client = dsiq.Client("dsiq_live_...")

rows = [
    {"order_id": "ORD-001", "amount": 99.50,    "email": "alice@corp.com"},
    {"order_id": "ORD-002", "amount": "broken", "email": None},
    {"order_id": "ORD-003", "amount": 75.00,    "email": None},
]

report = client.screen(rows, source="orders")

print(report.status)        # BLOCK
print(report.health_pct)    # 34.0%
print(report.type_mismatches)  # ["amount"]
print(report.null_rates)       # {"email": 0.5}
print(report.summary())
# 🚨 BLOCK | Health: 34.0% | Rows: 3 | Type mismatches: amount | Null rate: email=50% | (9ms)
```

---

## API key

Set as environment variable (recommended):

```bash
export DATASCREENIQ_API_KEY="dsiq_live_..."
```

```python
client = dsiq.Client()  # reads from env automatically
```

Or pass directly:
```python
client = dsiq.Client("dsiq_live_...")
```

---

## Usage

### Screen a list of dicts

```python
report = client.screen(rows, source="orders")
```

### Screen a CSV file

```python
report = client.screen_file("orders.csv", source="orders")
```

### Screen an Excel file

```python
# pip install datascreeniq[excel]
report = client.screen_file("orders.xlsx", source="orders", sheet=0)
```

### Screen a pandas DataFrame

```python
# pip install datascreeniq[pandas]
import pandas as pd

df = pd.read_csv("orders.csv")
report = client.screen_dataframe(df, source="orders")
```

### Screen a JSON or XML file

```python
report = client.screen_file("orders.json", source="orders")
report = client.screen_file("orders.xml",  source="orders")
```

---

## The ScreenReport object

```python
report.status           # "PASS" | "WARN" | "BLOCK"
report.health_score     # float 0.0 – 1.0
report.health_pct       # "94.5%"

report.is_pass          # True / False
report.is_warn          # True / False
report.is_blocked       # True / False

report.issues           # full issues dict
report.type_mismatches  # ["amount", "price"]
report.null_rates       # {"email": 0.50}
report.outlier_fields   # ["amount"]

report.drift            # list of drift events
report.drift_count      # int
report.has_drift        # True / False

report.rows_received    # int
report.rows_sampled     # int
report.latency_ms       # int
report.batch_id         # str
report.timestamp        # ISO string

report.summary()        # human-readable one-liner
report.to_dict()        # raw API response
```

---

## Pipeline integration

### Raise on block

```python
from datascreeniq.exceptions import DataQualityError

try:
    client.screen(rows, source="orders").raise_on_block()
    # only reaches here if PASS or WARN
    load_to_warehouse(rows)

except DataQualityError as e:
    print(f"Blocked: {e}")
    print(f"Issues:  {e.report.issues}")
    send_to_dead_letter_queue(rows)
```

### Airflow task

```python
from airflow.decorators import task
import datascreeniq as dsiq

@task
def quality_gate(rows: list, source: str) -> dict:
    client = dsiq.Client()   # reads DATASCREENIQ_API_KEY from env
    report = client.screen(rows, source=source)
    if report.is_blocked:
        raise ValueError(f"Data blocked: {report.summary()}")
    return report.to_dict()
```

### Prefect flow

```python
from prefect import flow, task
import datascreeniq as dsiq

@task
def screen_data(rows, source):
    return dsiq.Client().screen(rows, source=source).raise_on_block()

@flow
def my_pipeline():
    rows = extract_from_source()
    screen_data(rows, source="orders")   # blocks flow if quality fails
    load_to_warehouse(rows)
```

### dbt post-hook

```python
import pandas as pd
import datascreeniq as dsiq

def screen_dbt_model(model_name: str, conn):
    df = pd.read_sql(f"SELECT * FROM {model_name} LIMIT 10000", conn)
    return dsiq.Client().screen_dataframe(df, source=model_name).raise_on_block()
```

---

## Large files — auto chunking

Files with more than 10,000 rows are automatically split into chunks and screened in parallel. Results are merged into a single report:

```python
# 1M row file — 100 API calls, one merged report
report = client.screen_file("events.csv", source="events")
print(f"Screened {report.rows_received:,} rows")
```

---

## Error handling

```python
from datascreeniq.exceptions import (
    AuthenticationError,   # invalid API key
    PlanLimitError,        # monthly row limit exceeded
    RateLimitError,        # too many requests
    ValidationError,       # bad payload
    APIError,              # server error
    DataQualityError,      # raised by .raise_on_block()
)

try:
    report = client.screen(rows, source="orders")
except AuthenticationError:
    print("Check your API key")
except PlanLimitError:
    print("Monthly limit reached — upgrade at datascreeniq.com")
except PlanLimitError as e:
    print(f"Rate limited: {e}")
```

---

## Pricing

| Plan | Price | Rows / month |
|------|-------|-------------|
| Developer | Free | 500K |
| Starter | $19/mo | 5M |
| Growth | $79/mo | 50M |
| Scale | $199/mo | 500M |

[Get your free API key →](https://datascreeniq.com)

---

## Requirements

- Python 3.8+
- `requests` (auto-installed)
- `pandas` — optional, for `screen_dataframe()`
- `openpyxl` — optional, for Excel files

---

## Links

- [Documentation](https://datascreeniq.com/docs)
- [API Reference](https://datascreeniq.com/docs#api)
- [Dashboard](https://datascreeniq.com/dashboard)
- [GitHub Issues](https://github.com/datascreeniq/datascreeniq-python/issues)

---

## License

MIT
