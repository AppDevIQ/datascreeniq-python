# DataScreenIQ GitHub Action — Data Quality Gate

Screen CSV, JSON, and Excel files automatically on every pull request. Block merges when data quality fails.

## Setup

1. Get a free API key at [datascreeniq.com](https://datascreeniq.com) (500K rows/month)
2. Add it as a repository secret: **Settings → Secrets → New secret → `DATASCREENIQ_API_KEY`**
3. Copy `quality-gate.yml` to `.github/workflows/quality-gate.yml`
4. Push — the action runs automatically on PRs that touch data files

## What it does

- Detects changed `.csv`, `.json`, and `.xlsx` files in the PR
- Screens each file through DataScreenIQ's quality engine
- Checks null rates, type mismatches, outliers, schema drift
- **PASS** → PR check passes (green)
- **WARN** → PR check passes with warnings in the log
- **BLOCK** → PR check fails (red) — blocks merge until fixed
- Posts a comment on the PR linking to the full results

## Customise

Trigger on specific directories only:

```yaml
on:
  pull_request:
    paths:
      - 'data/**'        # only screen files in the data/ folder
      - 'seeds/**'        # dbt seeds
```

## Example output

```
Screening: data/orders.csv
🚨 BLOCK | Health: 34.0% | Rows: 1,200 | Type mismatches: amount | Null rate: email=67% | (9ms)

QUALITY GATE SUMMARY
✅ Passed:  2
⚠️  Warned:  1
🚨 Blocked: 1

❌ Quality gate FAILED — fix the issues above before merging.
```
