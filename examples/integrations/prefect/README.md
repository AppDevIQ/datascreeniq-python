# DataScreenIQ — Prefect Integration

A Prefect flow that screens extracted data through DataScreenIQ before loading to the warehouse.

## Setup

```bash
pip install datascreeniq prefect
export DATASCREENIQ_API_KEY=dsiq_live_...
```

## Run

```bash
python quality_gate_flow.py
```

Or deploy as a Prefect flow:

```bash
prefect deploy quality_gate_flow.py:etl_pipeline
```

## Flow

```
extract_data → screen_data → load_to_warehouse
                   ↓ (on BLOCK)
                send_alert
```

| Quality result | Flow action |
|---------------|-------------|
| **PASS** | Proceeds to load |
| **WARN** | Proceeds with warnings logged |
| **BLOCK** | Stops flow, sends alert, marks as failed |
