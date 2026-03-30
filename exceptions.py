"""
DataScreenIQ — Exceptions
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .models import ScreenReport


class DataScreenIQError(Exception):
    """Base exception for all DataScreenIQ errors."""
    pass


class AuthenticationError(DataScreenIQError):
    """Raised when the API key is missing or invalid."""
    pass


class RateLimitError(DataScreenIQError):
    """Raised when the request rate limit is exceeded."""
    pass


class PlanLimitError(DataScreenIQError):
    """Raised when the monthly row limit for your plan is exceeded."""
    pass


class ValidationError(DataScreenIQError):
    """Raised when the request payload is invalid."""
    pass


class APIError(DataScreenIQError):
    """Raised for unexpected API or server errors."""
    pass


class DataQualityError(DataScreenIQError):
    """
    Raised by ScreenReport.raise_on_block() when data is blocked.

    Attributes:
        report: The full ScreenReport that triggered the block.

    Example:
        try:
            client.screen(rows, source="orders").raise_on_block()
        except DataQualityError as e:
            print(e.report.issues)
    """

    def __init__(
        self,
        message: str,
        report: Optional["ScreenReport"] = None,
    ) -> None:
        super().__init__(message)
        self.report = report
