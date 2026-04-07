# DataScreenIQ Python SDK

<p align="center">
  <img src="https://img.shields.io/pypi/v/datascreeniq?color=0b5c42&label=PyPI&logo=pypi&logoColor=white" alt="PyPI version">
  <img src="https://img.shields.io/pypi/pyversions/datascreeniq?color=0b5c42" alt="Python 3.8+">
  <img src="https://img.shields.io/pypi/dm/datascreeniq?color=0b5c42&label=installs%2Fmonth" alt="Monthly installs">
  <img src="https://img.shields.io/badge/license-MIT-0b5c42" alt="MIT License">
  <img src="https://img.shields.io/badge/response-<10ms-059669" alt="Sub-10ms">
</p>

<p align="center">
  <a href="https://colab.research.google.com/github/AppDevIQ/datascreeniq-python/blob/main/examples/integrations/colab/datascreeniq_demo.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"></a>
</p>

---

[![GitHub stars](https://img.shields.io/github/stars/AppDevIQ/datascreeniq-python?style=social)](https://github.com/AppDevIQ/datascreeniq-python/stargazers)

If you find this useful, please ⭐ the repo — it helps support the project and improves our visibility in API directories.

---

<p align="center">
  <b>Stop bad data before it enters your pipeline.</b><br>
  Real-time schema drift detection and data quality screening — returns PASS / WARN / BLOCK in milli seconds.
</p>

---

## The problem

Your pipeline ran successfully last night. The dashboard is broken this morning.

Somewhere between your upstream API and your database, a field went null, a type changed, a schema drifted, or a timestamp went stale — and nothing caught it. Data quality tools are almost always batch-based. They run *after* the `INSERT`. By the time Great Expectations or dbt tests flag an issue, bad rows have been in production for hours.

DataScreenIQ moves the check to the ingest boundary — **before storage, before transformation, before damage.**

```
Your API → DataScreenIQ → PASS ✓ → Database
                        → WARN ⚠ → Quarantine / flag
                        → BLOCK ✗ → Dead-letter queue
```

---
 
## 🚀 Requires an API key (free, instant)

DataScreenIQ is an **API‑backed screening engine**.  
You need a free API key to run your first screen.

👉 **Get your key in under 30 seconds:**  
**https://datascreeniq.com**

✅ Free tier: **500,000 rows / month**  
✅ No credit card required

---

## 🚨 See it in action (no setup)

Run this immediately:

```python
import datascreeniq as dsiq

client = dsiq.DemoClient()

result = client.screen([
    {"email": "ok@corp.com", "amount": 100},
    {"email": None, "amount": "broken"}
])

print(result.summary())
```

### You’ll get:

```
🚨 BLOCK | Health: 34% | Type mismatch: amount | Null rate: email=67% (7ms)
```

👉 This is what happens in production pipelines without protection.

![DataScreenIQ SDK screening a batch from the terminal](DatascreenIQ.gif)
*Screening a data batch with the Python SDK — type mismatch and null spike detected, BLOCK verdict in 7ms*

--- 

## What happens if you don’t set an API key?

```python
import datascreeniq as dsiq
dsiq.Client().screen(rows)
```

❌ Raises:

```
AuthenticationError: Missing API key.
Get one free at https://datascreeniq.com
```

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

---

## What gets detected

The engine runs a **single-pass column analysis** on a deterministically-sampled subset of your rows. Every check is computed in-memory — no data is written anywhere.

### Column-level checks (per field, per batch)

| Check | What it catches | Default threshold |
|-------|----------------|-------------------|
| **Null rate** | Fields with too many missing values | WARN ≥ 30%, BLOCK ≥ 70% |
| **Type mismatch** | Fields where values aren't a consistent type | WARN ≥ 5%, BLOCK ≥ 20% |
| **Empty string rate** | Fields full of `""` instead of `null` | WARN ≥ 30%, BLOCK ≥ 60% |
| **Duplicate rate** | Cardinality collapse — rows repeating unexpectedly | WARN > 10% |
| **Outliers (IQR)** | Numeric values beyond 1.5× interquartile range | Reported |
| **Percentiles** | p25 / p50 / p75 / p95 for every numeric field | Reported |
| **Distinct count** | Approximate unique values via HyperLogLog (±2%) | Reported |
| **Enum tracking** | Low-cardinality string fields tracked for new values | Reported |
| **Timestamp detection** | ISO 8601 / date fields auto-detected | Reported |
| **Timestamp staleness** | Most recent timestamp older than expected | WARN ≥ 24h, BLOCK ≥ 72h |

### Drift detection (compared against your baseline)

After the first batch, every subsequent batch is compared against your stored schema and baselines:

| Drift kind | What triggers it | Severity |
|-----------|-----------------|---------|
| `field_added` | New field not in previous schema | WARN |
| `field_removed` | Known field missing from this batch | WARN |
| `type_changed` | Field type changed (e.g. `number` → `string`) | BLOCK |
| `null_spike` | Null rate increased >20% from baseline | WARN / BLOCK |
| `empty_string_spike` | Empty string rate spiked | WARN / BLOCK |
| `new_enum_value` | New value appeared in a low-cardinality field | WARN |
| `row_count_anomaly` | Batch size deviates >3× from historical average | WARN / BLOCK |
| `timestamp_stale` | Most recent timestamp is unexpectedly old | WARN / BLOCK |

### Verdict logic

```
Any BLOCK-severity drift event       → BLOCK
Health score < 0.5                   → BLOCK
Health score < 0.8 or any WARN event → WARN
Everything clean                     → PASS
```

---

## Full response structure

```json
{
  "status": "BLOCK",
  "health_score": 0.34,
  "decision": {
    "action": "BLOCK",
    "reason": "Type mismatch in: 'amount'; High null rate in 'email' (67%)"
  },
  "schema": {
    "order_id": { "type": "string",  "confidence": 1.0 },
    "amount":   { "type": "number",  "confidence": 0.67 },
    "email":    { "type": "string",  "confidence": 1.0 }
  },
  "schema_fingerprint": "a3f8c2...",
  "drift": [
    {
      "field": "user_age",
      "kind": "field_added",
      "severity": "warn",
      "detail": "New field \"user_age\" (type: number) not in previous schema"
    }
  ],
  "issues": {
    "type_mismatches": {
      "amount": {
        "expected": "number",
        "found": ["string"],
        "sample_value": "broken",
        "rate": 0.33,
        "severity": "critical"
      }
    },
    "null_rates": {
      "email": { "actual": 0.67, "threshold": 0.3, "severity": "critical" }
    }
  },
  "stats": {
    "rows_received": 3,
    "rows_sampled": 3,
    "sample_ratio": 1.0,
    "sample_version": "v2",
    "source": "orders"
  },
  "latency_ms": 7,
  "timestamp": "2025-06-01T09:14:22.000Z"
}
```

**Response headers** also carry key signals for lightweight pipeline integration:

```
X-DataScreenIQ-Status:   BLOCK
X-DataScreenIQ-Health:   0.34
X-DataScreenIQ-Latency:  7ms
X-RateLimit-Plan:        developer
X-RateLimit-Remaining:   498234
```

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
    screen_data(rows, source="orders")   # raises DataQualityError if BLOCK
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
report = client.screen_file("orders.xlsx", source="orders", sheet=0)  # requires [excel]
report = client.screen_file("events.json", source="events")
report = client.screen_file("feed.xml",    source="feed")
```

### CSV via raw HTTP (no SDK)

```bash
curl -X POST https://api.datascreeniq.com/v1/screen \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: text/csv" \
  -H "X-Source: orders" \
  --data-binary @orders.csv
```
---

## Run the DataScreenIQ API in Postman

[![Run in Postman](https://run.pstmn.io/button.svg)](https://www.postman.com/vignesh-datascreeniq-3090309/datascreeniq-s-workspace/)

---

## ⚡ Try instantly (no setup)

👉 [![Run in Hoppscotch](https://img.shields.io/badge/Run%20in-Hoppscotch-0b5c42?logo=hoppscotch&logoColor=white)](https://hoppscotch.io/?method=POST&url=https%3A%2F%2Fapi.datascreeniq.com%2Fv1%2Fscreen&headers=%5B%7B%22key%22%3A%22X-API-Key%22%2C%22value%22%3A%22YOUR_API_KEY_HERE%22%7D%2C%7B%22key%22%3A%22Content-Type%22%2C%22value%22%3A%22application%2Fjson%22%7D%5D&body=%7B%22source%22%3A%22orders%22%2C%22rows%22%3A%5B%7B%22order_id%22%3A%22ORD-001%22%2C%22amount%22%3A99.5%2C%22email%22%3A%22alice%40corp.com%22%7D%2C%7B%22order_id%22%3A%22ORD-002%22%2C%22amount%22%3A150.0%2C%22email%22%3A%22bob%40corp.com%22%7D%5D%7D)

1. Paste your API key, Update the JSON from below in the Body
2. Click Send
3. See PASS / WARN / BLOCK instantly

```JSON
{
  "source": "orders",
  "rows": [
    {
      "order_id": "ORD-001",
      "amount": 99.5,
      "email": "alice@corp.com"
    },
    {
      "order_id": "ORD-002",
      "amount": 150.0,
      "email": "bob@corp.com"
    }
  ]
}
```
---

## Large files — auto chunking

Files over 10,000 rows are automatically split and screened in parallel. Results are merged into a single `ScreenReport`:

```python
# 1M-row file — runs as parallel batches, one merged result
report = client.screen_file("events.csv", source="events")
print(f"Screened {report.rows_received:,} rows in {report.latency_ms}ms")
```

---

## Configurable thresholds

### Per-source threshold overrides

A single global threshold applied to every source is rarely right. `payments.amount`
should BLOCK at 1% null. `events.user_agent` might be fine at 40% null. Applying the
same rule to both creates alert fatigue on one pipeline and silent failures on another.

DataScreenIQ supports a four-level priority chain:

```
1. Inline threshold in API request    → highest priority (per-call override)
2. Saved per-source override          → set in the dashboard Thresholds tab
3. Global account defaults            → your account-wide settings
4. System defaults                    → fallback if nothing else is set
```

**Option 1 — Inline per request:**

```python
# Tight rules for financial data
report = client.screen(
    rows,
    source="payments",
    options={
        "thresholds": {
            "null_rate_warn":      0.01,  # WARN if > 1% nulls
            "null_rate_block":     0.02,  # BLOCK if > 2% nulls
            "type_mismatch_warn":  0.0,   # WARN on any type mismatch
            "type_mismatch_block": 0.01,  # BLOCK if > 1% mismatch
        }
    }
)

# Relaxed rules for event tracking (high null rate is normal here)
report = client.screen(
    rows,
    source="events",
    options={
        "thresholds": {
            "null_rate_warn":  0.50,  # user_agent nulls are expected
            "null_rate_block": 0.80,
        }
    }
)
```

**Option 2 — Saved per-source overrides (dashboard):**

Set thresholds once in the dashboard **Thresholds** tab, scoped to a specific source.
Every future call to `source="payments"` automatically applies those saved thresholds,
falling back to global defaults for anything not explicitly overridden. No code change needed.

Inline thresholds always win over saved thresholds — useful for backfills, migrations,
or testing new values before committing them.

### All configurable threshold keys

| Key | Default | Description |
|-----|---------|-------------|
| `null_rate_warn` | `0.3` | WARN if null rate exceeds this |
| `null_rate_block` | `0.7` | BLOCK if null rate exceeds this |
| `type_mismatch_warn` | `0.05` | WARN if type mismatch rate exceeds this |
| `type_mismatch_block` | `0.2` | BLOCK if type mismatch rate exceeds this |
| `empty_string_warn` | `0.2` | WARN if empty string rate exceeds this |
| `empty_string_block` | `0.5` | BLOCK if empty string rate exceeds this |
| `duplicate_warn` | `0.1` | WARN if duplicate rate exceeds this |
| `duplicate_block` | `0.5` | BLOCK if duplicate rate exceeds this |
| `health_warn` | `0.8` | WARN if health score falls below this |
| `health_block` | `0.5` | BLOCK if health score falls below this |
| `timestamp_stale_warn_hours` | `24` | WARN if most recent timestamp is older than this |
| `timestamp_stale_block_hours` | `72` | BLOCK if most recent timestamp is older than this |

---

## The ScreenReport object

```python
# Verdict
report.status           # "PASS" | "WARN" | "BLOCK"
report.is_pass          # bool
report.is_warn          # bool
report.is_blocked       # bool
report.health_score     # float 0.0 – 1.0
report.health_pct       # "94.5%"

# Issues (from actual response fields)
report.issues           # full issues dict
report.type_mismatches  # list of field names with type problems
report.null_rates       # dict of field → null rate (only fields above threshold)
report.outlier_fields   # list of field names with outliers

# Schema drift
report.drift            # list of DriftEvent dicts
report.drift_count      # int
report.has_drift        # bool

# Sampling metadata (auditable)
report.rows_received    # int — total rows in your batch
report.rows_sampled     # int — rows actually analysed
report.sample_ratio     # float — fraction sampled
report.sample_version   # "v2" — sampling strategy version
report.latency_ms       # int
report.batch_id         # str (uuid, same as request_id)
report.timestamp        # ISO 8601 string

# Output
report.summary()        # human-readable one-liner
report.to_dict()        # full API response as dict
```

---

## Error handling

```python
from datascreeniq.exceptions import (
    AuthenticationError,   # invalid or missing API key
    PlanLimitError,        # monthly row limit exceeded — response includes upgrade_url
    RateLimitError,        # too many concurrent requests
    ValidationError,       # bad payload (missing source, empty rows, >100K rows)
    APIError,              # unexpected server error
    DataQualityError,      # raised by .raise_on_block() — has .report attribute
)

try:
    report = client.screen(rows, source="orders")
except AuthenticationError:
    print("Invalid API key — check DATASCREENIQ_API_KEY")
except PlanLimitError as e:
    print(f"Monthly limit reached — upgrade at {e.upgrade_url}")
except ValidationError as e:
    print(f"Bad payload: {e}")   # e.g. rows > 100,000 limit
```

---

## Configuration

```bash
# Recommended: environment variable
export DATASCREENIQ_API_KEY="dsiq_live_..."
```

```python
client = dsiq.Client()              # reads DATASCREENIQ_API_KEY from env
client = dsiq.Client("dsiq_live_...") # explicit key
client = dsiq.Client(timeout=10)    # custom timeout in seconds (default: 30)
```

---

## Privacy

DataScreenIQ runs on **Cloudflare Workers** — a serverless edge runtime with no filesystem access. Your raw payload is processed entirely in-memory and physically cannot be written to disk at the edge layer.

What we store (permanently): schema fingerprints (SHA-256 hashes), null rates, type distributions, and quality scores — aggregated statistics only. No row-level data, no field values, no PII, ever.

→ [Full privacy architecture](https://datascreeniq.com/privacy)

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

## Requirements

- Python 3.8+
- `requests` (auto-installed)
- `pandas` — optional, for `screen_dataframe()`
- `openpyxl` — optional, for Excel files

---

## See also

- [Examples](./examples/) — Airflow DAG, Prefect flow, pandas pipeline, dbt hook
- [API reference](https://datascreeniq.com/docs)
- [Privacy architecture](https://datascreeniq.com/privacy)
- [PyPI package](https://pypi.org/project/datascreeniq/)
- [Changelog](https://github.com/AppDevIQ/datascreeniq-python/releases)
- [Integration examples](./examples/integrations/) — GitHub Action, Airflow, dbt, Prefect, Google Colab

Questions → [app@datascreeniq.com](mailto:app@datascreeniq.com) or [open an issue](https://github.com/AppDevIQ/datascreeniq-python/issues)

---

## License

MIT © DataScreenIQ
