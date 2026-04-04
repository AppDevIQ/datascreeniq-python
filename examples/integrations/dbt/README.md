# DataScreenIQ — dbt Integration

Screen dbt model output through DataScreenIQ after `dbt run`. Catches schema drift, null spikes, and type mismatches in your transformed data.

## Setup

```bash
pip install datascreeniq pandas sqlalchemy
export DATASCREENIQ_API_KEY=dsiq_live_...
export DBT_DATABASE_URL=postgresql://user:pass@host:5432/analytics
```

## Usage

Screen a single model:

```bash
python screen_dbt_model.py --model stg_orders
```

Screen multiple models:

```bash
python screen_dbt_model.py --model stg_orders fct_revenue dim_customers
```

Warn only (don't fail on BLOCK):

```bash
python screen_dbt_model.py --model stg_orders --warn-only
```

## CI/CD integration

Add to your dbt CI pipeline after `dbt run`:

```yaml
# .github/workflows/dbt.yml
- name: Run dbt
  run: dbt run

- name: Quality gate
  env:
    DATASCREENIQ_API_KEY: ${{ secrets.DATASCREENIQ_API_KEY }}
    DBT_DATABASE_URL: ${{ secrets.DATABASE_URL }}
  run: python screen_dbt_model.py --model stg_orders fct_revenue
```

## Behaviour

| Quality result | Action |
|---------------|--------|
| **PASS** | Exits 0 |
| **WARN** | Exits 0, warnings printed |
| **BLOCK** | Exits 1 (unless `--warn-only`) |
