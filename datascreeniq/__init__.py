"""
DataScreenIQ Python SDK
~~~~~~~~~~~~~~~~~~~~~~~

Real-time data quality screening at the edge.

    import datascreeniq as dsiq

    client = dsiq.Client("dsiq_live_...")
    report = client.screen(rows, source="orders")

    print(report.status)        # PASS | WARN | BLOCK
    print(report.health_score)  # 0.0 – 1.0
    print(report.issues)        # detected quality issues

"""

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

__version__ = "1.0.3"
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
