"""
DataScreenIQ — Response models (premium polished version)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional


class ScreenReport:
    """
    Quality report returned by the DataScreenIQ API.

    Attributes:
        status:            "PASS", "WARN", or "BLOCK"
        health_score:      Float 0.0–1.0 (1.0 = perfect quality)
        issues:            Dict of detected issues
        drift:             List of schema drift events
        stats:             Row count and sampling stats
        schema_fingerprint: Hash of the schema for this batch
        latency_ms:        API processing time in milliseconds
        batch_id:          Unique ID for this screening batch
        timestamp:         ISO timestamp of the screening
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        self._raw = data

        # Core identifiers
        self.request_id = data.get("request_id", data.get("batch_id", ""))
        self.batch_id = self.request_id
        self.timestamp = data.get("timestamp", "")

        # Status and health
        self.status = data.get("status", "PASS")
        self.health_score = float(data.get("health_score", 1.0))

        # Details
        self.decision = data.get("decision", {})
        self.schema = data.get("schema", {})
        self.issues = data.get("issues", {})
        self.drift = data.get("drift", [])
        self.stats = data.get("stats", {})
        self.schema_fingerprint = data.get("schema_fingerprint", "")
        self.latency_ms = data.get("latency_ms", 0)

    # ── Convenience properties ──────────────────────────────

    @property
    def is_pass(self) -> bool:
        """True if data passed all quality checks."""
        return self.status == "PASS"

    @property
    def is_warn(self) -> bool:
        """True if data has quality warnings."""
        return self.status == "WARN"

    @property
    def is_blocked(self) -> bool:
        """True if data was blocked due to critical quality issues."""
        return self.status == "BLOCK"

    @property
    def health_pct(self) -> str:
        """Health score as a percentage string e.g. '94.5%'."""
        return f"{self.health_score * 100:.1f}%"

    @property
    def rows_received(self) -> int:
        """Total rows received by the API."""
        return self.stats.get("rows_received", 0)

    @property
    def rows_sampled(self) -> int:
        """Total rows sampled by the API."""
        return self.stats.get("rows_sampled", 0)

    @property
    def drift_count(self) -> int:
        """Number of drift events."""
        return len(self.drift)

    # ── Null rates (normalized) ─────────────────────────────

    @property
    def null_rates(self) -> Dict[str, float]:
        """
        Dict of column → null rate (0.0–1.0) for columns above threshold.

        Supports:
        - {col: 0.5}
        - {col: {"actual": 0.5}}
        - {col: {"value": 0.5}}
        - {col: {"nulls": X, "total": Y}}
        """
        raw = self.issues.get("null_rates", {})
        result: Dict[str, float] = {}

        for col, val in raw.items():
            if isinstance(val, dict):
                if "nulls" in val and "total" in val:
                    total = max(val.get("total", 1), 1)
                    result[col] = float(val.get("nulls", 0)) / float(total)
                elif "actual" in val:
                    result[col] = float(val["actual"])
                elif "value" in val:
                    result[col] = float(val["value"])
                else:
                    result[col] = 0.0
            else:
                try:
                    result[col] = float(val)
                except Exception:
                    result[col] = 0.0

        return result

    @property
    def null_rate_details(self) -> Dict[str, Any]:
        """Full null rate details including actual, threshold, severity."""
        return self.issues.get("null_rates", {})

    # ── Type mismatches ─────────────────────────────────────

    @property
    def type_mismatches(self) -> List[str]:
        """
        List of columns with type mismatch issues.

        Supports:
        - {"amount": {...}, "price": {...}}
        - ["amount", "price"]
        """
        raw = self.issues.get("type_mismatches", {})
        if isinstance(raw, dict):
            return list(raw.keys())
        return raw if isinstance(raw, list) else []

    @property
    def type_mismatch_details(self) -> Dict[str, Any]:
        """Full type mismatch details including expected, found, sample_value, severity."""
        raw = self.issues.get("type_mismatches", {})
        return raw if isinstance(raw, dict) else {}

    # ── Outliers & drift ────────────────────────────────────

    @property
    def outlier_fields(self) -> List[str]:
        """List of columns with outlier issues."""
        raw = self.issues.get("outlier_fields", [])
        return raw if isinstance(raw, list) else []

    @property
    def has_drift(self) -> bool:
        """True if any schema drift was detected."""
        return len(self.drift) > 0

    # ── Merge multiple chunk reports into one ───────────────

    @classmethod
    def merge(cls, reports: List["ScreenReport"]) -> "ScreenReport":
        """Merge reports from chunked screening into a single report."""
        if not reports:
            raise ValueError("No reports to merge.")
        if len(reports) == 1:
            return reports[0]

        # Worst status wins
        statuses = [r.status for r in reports]
        if "BLOCK" in statuses:
            status = "BLOCK"
        elif "WARN" in statuses:
            status = "WARN"
        else:
            status = "PASS"

        # Average health score weighted by row count
        total_rows = sum(r.rows_received for r in reports) or 1
        health = (
            sum(r.health_score * r.rows_received for r in reports) / float(total_rows)
        )

        # Merge issues
        merged_issues: Dict[str, Any] = {
            "null_rates": {},
            "type_mismatches": [],
            "empty_string_rates": {},
            "duplicate_fields": [],
            "outlier_fields": [],
            "row_count_anomaly": False,
            "new_enum_values": {},
        }
        all_drift: List[Any] = []

        for r in reports:
            # Null rates — average across chunks
            for col, rate in r.null_rates.items():
                if col in merged_issues["null_rates"]:
                    merged_issues["null_rates"][col] = (
                        merged_issues["null_rates"][col] + rate
                    ) / 2.0
                else:
                    merged_issues["null_rates"][col] = rate

            # Lists — union
            for key in ("type_mismatches", "duplicate_fields", "outlier_fields"):
                items = r.issues.get(key, [])
                if isinstance(items, dict):
                    items = list(items.keys())
                for item in items:
                    if item not in merged_issues[key]:
                        merged_issues[key].append(item)

            if r.issues.get("row_count_anomaly"):
                merged_issues["row_count_anomaly"] = True

            # Drift — deduplicate by field+kind
            for event in r.drift:
                if not isinstance(event, dict):
                    continue
                key = (event.get("field"), event.get("kind"))
                if not any(
                    (e.get("field"), e.get("kind")) == key for e in all_drift
                ):
                    all_drift.append(event)

        merged_data = {
            "status": status,
            "health_score": round(health, 4),
            "issues": merged_issues,
            "drift": all_drift,
            "stats": {
                "rows_received": sum(r.rows_received for r in reports),
                "rows_sampled": sum(r.rows_sampled for r in reports),
                "sample_ratio": reports[0].stats.get("sample_ratio", 1.0),
                "sample_version": reports[0].stats.get("sample_version", "v2"),
            },
            "schema_fingerprint": reports[-1].schema_fingerprint,
            "latency_ms": sum(r.latency_ms for r in reports),
            "batch_id": reports[0].batch_id,
            "timestamp": reports[0].timestamp,
        }

        return cls(merged_data)

    # ── Display ─────────────────────────────────────────────

    def summary(self) -> str:
        """Human-readable one-line summary."""
        icon = "✅" if self.is_pass else "⚠️" if self.is_warn else "🚨"
        parts: List[str] = [f"{icon} {self.status} | Health: {self.health_pct}"]
        parts.append(f"Rows: {self.rows_received:,}")

        if self.drift_count:
            parts.append(f"Drift: {self.drift_count} event(s)")

        if self.type_mismatches:
            parts.append(f"Type mismatches: {', '.join(self.type_mismatches)}")

        if self.null_rates:
            try:
                top = max(self.null_rates, key=self.null_rates.get)
                rate = float(self.null_rates.get(top, 0.0))
                parts.append(f"Null rate: {top}={rate:.0%}")
            except Exception:
                parts.append("Null rate: (unavailable)")

        if self.outlier_fields:
            parts.append(f"Outliers: {', '.join(self.outlier_fields)}")

        parts.append(f"({self.latency_ms}ms)")
        return " | ".join(parts)

    def raise_on_block(self, message: Optional[str] = None) -> "ScreenReport":
        """
        Raise DataQualityError if status is BLOCK.
        Useful for pipeline guard clauses.

        Example:
            report = client.screen(rows, source="orders")
            report.raise_on_block()  # raises if blocked
            # safe to proceed
        """
        from .exceptions import DataQualityError

        if self.is_blocked:
            msg = message or (
                f"Data blocked: health={self.health_pct}, "
                f"issues={list(self.issues.keys())}"
            )
            raise DataQualityError(msg, report=self)
        return self

    # ── Introspection ──────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Return the raw API response as a dict."""
        return self._raw

    def __repr__(self) -> str:
        return (
            f"ScreenReport(status='{self.status}', "
            f"health={self.health_pct}, "
            f"rows={self.rows_received:,}, "
            f"drift={self.drift_count})"
        )


class ScreenError:
    """Returned when the API returns an error response."""

    def __init__(self, data: Dict[str, Any], status_code: int) -> None:
        self.message = data.get("message", "Unknown error")
        self.code = data.get("code", "UNKNOWN")
        self.status_code = status_code

    def __repr__(self) -> str:
        return f"ScreenError(code='{self.code}', message='{self.message}')"