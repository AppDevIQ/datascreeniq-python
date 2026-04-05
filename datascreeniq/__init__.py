"""
DataScreenIQ Python SDK
~~~~~~~~~~~~~~~~~~~~~~~

Real-time data quality screening for data pipelines.

Detect schema drift, null spikes, and type mismatches
before data reaches your database.

Quick start:

    import datascreeniq as dsiq

    client = dsiq.Client("dsiq_live_...")
    report = client.screen(rows, source="orders")

    print(report.status)        # PASS | WARN | BLOCK
    print(report.health_score)  # 0.0 – 1.0
    print(report.issues)        # detected quality issues

Demo (no API key needed):

    client = dsiq.DemoClient()
    report = client.screen(rows, source="demo")
    print(report.summary())

Docs: https://datascreeniq.com/docs
"""

from .version import __version__

from .client import Client
from .demo import DemoClient
from .models import ScreenReport
from .exceptions import (
    DataScreenIQError,
    AuthenticationError,
    RateLimitError,
    PlanLimitError,
    ValidationError,
    APIError,
    DataQualityError,
)

__all__ = [
    "Client",
    "DemoClient",
    "ScreenReport",
    "DataScreenIQError",
    "AuthenticationError",
    "RateLimitError",
    "PlanLimitError",
    "ValidationError",
    "APIError",
    "DataQualityError",
    "__version__",
]
