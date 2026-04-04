# DataScreenIQ — Airflow Integration

A complete Airflow DAG that screens extracted data through DataScreenIQ before loading it to the warehouse.

## Flow

```
extract_data → quality_gate → load_to_warehouse
                    ↓ (on BLOCK)
              alert_on_failure
```

## Setup

```bash
pip install datascreeniq apache-airflow
```

Set your API key as an Airflow Variable:

```bash
airflow variables set DATASCREENIQ_API_KEY dsiq_live_...
```

Or as an environment variable:

```bash
export DATASCREENIQ_API_KEY=dsiq_live_...
```

Copy `quality_gate_dag.py` to your `dags/` folder and customise the `extract_data()` and `load_to_warehouse()` tasks.

## Behaviour

| Quality result | Pipeline action |
|---------------|----------------|
| **PASS** | Proceeds to load |
| **WARN** | Proceeds with warnings logged |
| **BLOCK** | Stops pipeline, triggers alert task |

## Get a free API key

[datascreeniq.com](https://datascreeniq.com) — 500K rows/month, no credit card required.
