# DataScreenIQ — Integrations

Ready-to-copy integrations that plug DataScreenIQ into your existing tools. Each integration is a complete, working example you can drop into your project.

## Integrations

| Integration | What it does | Setup time |
|------------|-------------|------------|
| [**GitHub Action**](./github-action/) | Screen CSV/JSON files on every PR. Block merges when data quality fails. | 2 min |
| [**Airflow DAG**](./airflow/) | Quality gate task between extract and load. Stops pipeline on BLOCK. | 5 min |
| [**dbt post-hook**](./dbt/) | Screen model output after `dbt run`. Catch drift in transformed data. | 5 min |
| [**Prefect flow**](./prefect/) | Quality gate flow with alerting on BLOCK. | 5 min |
| [**Google Colab**](./colab/) | Interactive notebook — try DataScreenIQ in 60 seconds. | 1 min |

## Quick start

```bash
pip install datascreeniq
export DATASCREENIQ_API_KEY=dsiq_live_...
```

Get a free API key (500K rows/month, no credit card): [datascreeniq.com](https://datascreeniq.com)

## How it fits

```
Your source → Extract → DataScreenIQ → PASS ✓ → Load → Warehouse
                                      → WARN ⚠ → Load + alert
                                      → BLOCK ✗ → Dead-letter queue
```

DataScreenIQ is not a replacement for dbt tests or Great Expectations. It fills a different gap: the **pre-storage screening layer** that catches problems before they propagate.

## Links

- [Python SDK (PyPI)](https://pypi.org/project/datascreeniq/)
- [API reference](https://datascreeniq.com/api-reference.html)
- [GitHub](https://github.com/AppDevIQ/datascreeniq-python)
- [Documentation](https://datascreeniq.com/docs)
