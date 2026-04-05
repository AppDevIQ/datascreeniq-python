"""
DataScreenIQ — Demo Client
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A local demo client that returns realistic simulated quality reports
without requiring an API key or network access.

Usage:
    import datascreeniq as dsiq
    client = dsiq.DemoClient()
    report = client.screen([
        {"email": "ok@corp.com", "amount": 100},
        {"email": None, "amount": "broken"}
    ], source="demo")
    print(report.summary())
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from .models import ScreenReport
from .version import __version__


class DemoClient:
    """
    Demo client that simulates DataScreenIQ screening locally.

    Runs basic quality checks (null rate, type mismatch, empty strings)
    on the provided data and returns a realistic ScreenReport — no API
    key, no network calls, no signup required.

    This gives you a feel for the API response format. For full
    screening (18 checks, drift detection, schema fingerprinting),
    get a free API key at https://datascreeniq.com

    Example:
        >>> import datascreeniq as dsiq
        >>> client = dsiq.DemoClient()
        >>> report = client.screen([
        ...     {"email": "ok@corp.com", "amount": 100},
        ...     {"email": None, "amount": "broken"}
        ... ], source="demo")
        >>> print(report.status)   # BLOCK
        >>> print(report.summary())
    """

    def __init__(self) -> None:
        self._demo = True

    def screen(
        self,
        rows: List[Dict[str, Any]],
        *,
        source: str = "demo",
        options: Optional[Dict[str, Any]] = None,
    ) -> ScreenReport:
        """
        Screen rows locally and return a simulated ScreenReport.

        Checks: null rates, type mismatches, empty strings.
        Does NOT include: drift detection, outlier detection,
        HyperLogLog, enum tracking, timestamp recency.

        For full checks, use Client() with a real API key.
        """
        if not rows:
            from .exceptions import ValidationError
            raise ValidationError("rows must be a non-empty list.")

        start = time.time()

        # Detect columns
        columns: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            for key, val in row.items():
                if key not in columns:
                    columns[key] = {
                        "values": [],
                        "types": [],
                        "nulls": 0,
                        "empties": 0,
                        "total": 0,
                    }
                col = columns[key]
                col["total"] += 1
                if val is None:
                    col["nulls"] += 1
                    col["types"].append("null")
                elif isinstance(val, bool):
                    col["types"].append("boolean")
                    col["values"].append(val)
                elif isinstance(val, (int, float)):
                    col["types"].append("number")
                    col["values"].append(val)
                elif isinstance(val, str):
                    if val.strip() == "":
                        col["empties"] += 1
                        col["types"].append("string")
                    else:
                        col["types"].append("string")
                    col["values"].append(val)
                else:
                    col["types"].append("object")
                    col["values"].append(val)

        n_rows = len(rows)
        issues: Dict[str, Any] = {}
        schema: Dict[str, Any] = {}
        decision_reasons: List[str] = []
        health_penalties: float = 0.0

        type_mismatches: Dict[str, Any] = {}
        null_rates: Dict[str, Any] = {}

        for col_name, col_data in columns.items():
            total = col_data["total"]
            if total == 0:
                continue

            # Determine dominant type (exclude null)
            non_null_types = [t for t in col_data["types"] if t != "null"]
            if not non_null_types:
                dominant = "null"
                confidence = 0.0
            else:
                type_counts: Dict[str, int] = {}
                for t in non_null_types:
                    type_counts[t] = type_counts.get(t, 0) + 1
                dominant = max(type_counts, key=type_counts.get)
                confidence = round(type_counts[dominant] / len(non_null_types), 2)

            schema[col_name] = {"type": dominant, "confidence": confidence}

            # Null rate check
            null_rate = col_data["nulls"] / total
            if null_rate > 0.3:
                null_rates[col_name] = {
                    "actual": round(null_rate, 2),
                    "threshold": 0.3,
                    "severity": "critical" if null_rate > 0.7 else "warning",
                }
                health_penalties += null_rate * 0.3
                decision_reasons.append(
                    f"High null rate in '{col_name}' ({null_rate * 100:.0f}%)"
                )

            # Type mismatch check
            if len(set(non_null_types)) > 1:
                mismatch_count = len(non_null_types) - (
                    max(type_counts.values()) if type_counts else 0
                )
                mismatch_rate = mismatch_count / len(non_null_types) if non_null_types else 0
                if mismatch_rate > 0.05:
                    # Find a sample bad value
                    sample_val = None
                    for v, t in zip(col_data["values"], non_null_types):
                        if t != dominant:
                            sample_val = v
                            break

                    type_mismatches[col_name] = {
                        "expected": dominant,
                        "found": [t for t in set(non_null_types) if t != dominant],
                        "sample_value": sample_val,
                        "rate": round(mismatch_rate, 2),
                        "severity": "critical" if mismatch_rate > 0.2 else "warning",
                    }
                    health_penalties += mismatch_rate * 0.4
                    decision_reasons.append(f"Type mismatch in: '{col_name}'")

            # Empty string check
            empty_rate = col_data["empties"] / total
            if empty_rate > 0.2:
                if "empty_string_rates" not in issues:
                    issues["empty_string_rates"] = {}
                issues["empty_string_rates"][col_name] = {
                    "value": round(empty_rate, 2),
                    "severity": "warning",
                }
                health_penalties += empty_rate * 0.1

        # Build issues
        if type_mismatches:
            issues["type_mismatches"] = type_mismatches
        if null_rates:
            issues["null_rates"] = null_rates

        # Calculate health score
        health_score = max(0.0, min(1.0, round(1.0 - health_penalties, 4)))

        # Determine verdict
        if health_score < 0.5 or any(
            v.get("severity") == "critical" for v in type_mismatches.values()
        ) or any(
            v.get("severity") == "critical" for v in null_rates.values()
        ):
            verdict = "BLOCK"
        elif health_score < 0.8 or type_mismatches or null_rates:
            verdict = "WARN"
        else:
            verdict = "PASS"

        if not decision_reasons:
            decision_reasons.append("All quality checks passed")

        # Build fingerprint
        fp_input = "|".join(
            f"{k}:{schema[k]['type']}" for k in sorted(schema.keys())
        )
        fingerprint = hashlib.sha256(fp_input.encode()).hexdigest()[:12]

        latency = round((time.time() - start) * 1000)

        report_data = {
            "request_id": f"demo_{hashlib.md5(str(rows[:3]).encode()).hexdigest()[:10]}",
            "status": verdict,
            "health_score": health_score,
            "decision": {
                "action": verdict,
                "reason": "; ".join(decision_reasons),
            },
            "schema": schema,
            "schema_fingerprint": fingerprint,
            "issues": issues,
            "drift": [],
            "stats": {
                "rows_received": n_rows,
                "rows_sampled": n_rows,
                "sample_ratio": 1.0,
                "sample_version": "demo",
                "source": source,
            },
            "latency_ms": latency,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "_demo": True,
            "_note": "Demo mode — for full screening (18 checks, drift detection, schema fingerprinting), get a free key at https://datascreeniq.com",
        }

        return ScreenReport(report_data)

    def screen_dataframe(
        self,
        df: Any,
        *,
        source: str = "demo",
        options: Optional[Dict[str, Any]] = None,
    ) -> ScreenReport:
        """Screen a pandas DataFrame locally."""
        try:
            rows = df.where(df.notna(), None).to_dict(orient="records")
        except AttributeError:
            from .exceptions import ValidationError
            raise ValidationError(
                "df must be a pandas DataFrame. "
                "Install pandas: pip install datascreeniq[pandas]"
            )
        return self.screen(rows, source=source, options=options)

    def screen_file(
        self,
        path: Union[str, Path],
        *,
        source: Optional[str] = None,
        sheet: Union[int, str] = 0,
        options: Optional[Dict[str, Any]] = None,
    ) -> ScreenReport:
        """Screen a CSV or JSON file locally."""
        import csv
        import json

        path = Path(path)
        source = source or path.stem
        ext = path.suffix.lower()

        if ext == ".csv":
            with open(path, newline="", encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
        elif ext == ".json":
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            rows = data if isinstance(data, list) else [data]
        else:
            from .exceptions import ValidationError
            raise ValidationError(f"Demo client supports .csv and .json only (got '{ext}')")

        return self.screen(rows, source=source, options=options)

    def __repr__(self) -> str:
        return "DemoClient(mode='local', checks=['null_rate', 'type_mismatch', 'empty_string'])"
