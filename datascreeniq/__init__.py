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

Docs: https://datascreeniq.com/docs
"""

from importlib.metadata import version, PackageNotFoundError

from .client import Client
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

# -----------------------------
# Version (auto-sync with package)
# -----------------------------
try:
    __version__ = version("datascreeniq")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = [
    "Client",
    "ScreenReport",
    "DataScreenIQError",
    "AuthenticationError",
    "RateLimitError",
    "PlanLimitError",
    "ValidationError",
    "APIError",
    "DataQualityError",
]