"""
DataScreenIQ Python SDK
~~~~~~~~~~~~~~~~~~~~~~~

Real-time data quality screening at the edge.
Screen any data payload and get PASS / WARN / BLOCK in under 10ms.

Basic usage:

    import datascreeniq as dsiq

    client = dsiq.Client("dsiq_live_...")

    report = client.screen([
        {"order_id": "ORD-001", "amount": 99.50, "email": "alice@corp.com"},
        {"order_id": "ORD-002", "amount": "broken", "email": None},
    ], source="orders")

    print(report.status)        # BLOCK
    print(report.health_score)  # 0.58
    print(report.issues)        # {"type_mismatches": ["amount"], ...}

"""

from __future__ import annotations

import os
import csv
import json
import sys
from typing import Any, Dict, List, Optional, Union, Iterator
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import __version__
from .models import ScreenReport
from .exceptions import (
    DataScreenIQError,
    AuthenticationError,
    RateLimitError,
    PlanLimitError,
    ValidationError,
    APIError,
)

__all__ = ["Client"]

DEFAULT_BASE_URL = "https://api.datascreeniq.com"
DEFAULT_TIMEOUT  = 30        # seconds
DEFAULT_CHUNK    = 10_000    # rows per request
MAX_RETRIES      = 3


class Client:
    """
    DataScreenIQ API client.

    Args:
        api_key:    Your API key (dsiq_live_...). If omitted, reads
                    DATASCREENIQ_API_KEY environment variable.
        base_url:   Override the API base URL (useful for testing).
        timeout:    Request timeout in seconds. Default 30.
        chunk_size: Max rows per API call when auto-chunking. Default 10,000.
        verify:     SSL verification override.
                    True  = verify (default behaviour)
                    False = skip verification (not recommended)
                    str   = path to a custom CA bundle (.pem file)

    Corporate networks (Zscaler, Netskope, Cisco Umbrella, etc.):
        If you see SSL certificate errors, install the truststore extra:
            pip install datascreeniq[truststore]
        This makes the SDK use your OS certificate store automatically.
        No code changes required.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        chunk_size: int = DEFAULT_CHUNK,
        verify: Optional[Union[bool, str]] = None,
    ) -> None:
        # Normalise API key
        self.api_key    = (api_key or os.environ.get("DATASCREENIQ_API_KEY", "")).strip()
        self.base_url   = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.timeout    = timeout
        self.chunk_size = chunk_size
        self.verify     = verify

        # Build session (auth is checked lazily in _post_screen so the
        # Client object can be constructed for health checks without a key)
        self._session = self._build_session()

    # ──────────────────────────────────────────────────────────
    #  Public methods
    # ──────────────────────────────────────────────────────────

    def screen(
        self,
        rows: List[Dict[str, Any]],
        *,
        source: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> ScreenReport:
        """
        Screen a list of row dicts and return a quality report.

        Args:
            rows:    List of dicts — each dict is one row.
            source:  Pipeline or table name (e.g. "orders", "events").
            options: Optional thresholds / settings dict.

        Returns:
            ScreenReport with .status, .health_score, .issues, .drift etc.

        Raises:
            AuthenticationError: Invalid or missing API key.
            PlanLimitError:      Monthly row limit exceeded.
            RateLimitError:      Too many requests.
            ValidationError:     Bad payload.
            APIError:            Unexpected API error.

        Example:
            >>> report = client.screen(rows, source="orders")
            >>> if report.is_blocked:
            ...     raise ValueError(f"Data blocked: {report.issues}")
        """
        if not rows:
            raise ValidationError("rows must be a non-empty list.")
        if not source:
            raise ValidationError("source is required.")

        # Auto-chunk large payloads
        if len(rows) > self.chunk_size:
            return self._screen_chunked(rows, source=source, options=options)

        return self._post_screen(rows, source=source, options=options)

    def screen_file(
        self,
        path: Union[str, Path],
        *,
        source: Optional[str] = None,
        sheet: Union[int, str] = 0,
        options: Optional[Dict[str, Any]] = None,
    ) -> ScreenReport:
        """
        Screen a CSV, Excel, JSON or XML file.

        Args:
            path:    Path to the file.
            source:  Pipeline name. Defaults to the filename stem.
            sheet:   Sheet index or name for Excel files.
            options: Optional thresholds dict.

        Returns:
            ScreenReport

        Example:
            >>> report = client.screen_file("orders.csv", source="orders")
            >>> print(report.status)
        """
        path = Path(path)
        if not path.exists():
            raise ValidationError(f"File not found: {path}")

        source = source or path.stem
        ext    = path.suffix.lower()

        if ext == ".csv":
            rows = self._parse_csv(path)
        elif ext in (".xlsx", ".xls"):
            rows = self._parse_excel(path, sheet=sheet)
        elif ext == ".json":
            rows = self._parse_json(path)
        elif ext == ".xml":
            rows = self._parse_xml(path)
        else:
            raise ValidationError(
                f"Unsupported file type '{ext}'. "
                "Supported: .csv, .xlsx, .xls, .json, .xml"
            )

        if not rows:
            raise ValidationError(f"No data rows found in {path.name}")

        return self.screen(rows, source=source, options=options)

    def screen_dataframe(
        self,
        df: Any,
        *,
        source: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> ScreenReport:
        """
        Screen a pandas DataFrame.

        Args:
            df:      pandas DataFrame.
            source:  Pipeline or table name.
            options: Optional thresholds dict.

        Returns:
            ScreenReport

        Example:
            >>> import pandas as pd
            >>> df = pd.read_csv("orders.csv")
            >>> report = client.screen_dataframe(df, source="orders")
        """
        try:
            rows = df.where(df.notna(), None).to_dict(orient="records")
        except AttributeError:
            raise ValidationError(
                "df must be a pandas DataFrame. "
                "Install pandas: pip install datascreeniq[pandas]"
            )
        return self.screen(rows, source=source, options=options)

    def health(self) -> Dict[str, Any]:
        """Check API health. Returns dict with status and version."""
        resp = self._session.get(
            f"{self.base_url}/v1/health",
            timeout=self.timeout,
        )
        return resp.json()

    def reset_baseline(self, source: Optional[str] = None) -> Dict[str, Any]:
        """
        Reset the schema baseline for a source so the next screen call
        treats it as a fresh dataset.

        Args:
            source: Source name to reset (e.g. "orders").
                    If None, resets ALL sources for your account.

        Returns:
            Dict with ok, reset, message fields.

        Example:
            >>> client.reset_baseline("orders")
            >>> report = client.screen(rows, source="orders")  # fresh baseline
        """
        url = (
            f"{self.base_url}/v1/schema/{source}"
            if source
            else f"{self.base_url}/v1/schema"
        )
        resp = self._session.delete(url, timeout=self.timeout)

        if resp.status_code == 401:
            raise AuthenticationError("Invalid API key.")
        if not resp.ok:
            raise APIError(f"Reset failed (HTTP {resp.status_code})")

        return resp.json()

    # ──────────────────────────────────────────────────────────
    #  Chunked screening for large datasets
    # ──────────────────────────────────────────────────────────

    def _screen_chunked(
        self,
        rows: List[Dict[str, Any]],
        *,
        source: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> ScreenReport:
        """Split large payloads into chunks and merge reports."""
        chunks  = list(self._chunks(rows, self.chunk_size))
        n       = len(chunks)
        reports = []

        for i, chunk in enumerate(chunks):
            opts = {**(options or {}), "batch_index": i, "total_batches": n}
            reports.append(self._post_screen(chunk, source=source, options=opts))

        return ScreenReport.merge(reports)

    def _chunks(self, lst: List[Any], size: int) -> Iterator[List[Any]]:
        for i in range(0, len(lst), size):
            yield lst[i:i + size]

    # ──────────────────────────────────────────────────────────
    #  HTTP layer
    # ──────────────────────────────────────────────────────────

    def _post_screen(
        self,
        rows: List[Dict[str, Any]],
        *,
        source: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> ScreenReport:

        # Auth check — friendly message with next steps
        if not self.api_key:
            raise AuthenticationError(
                "\n❌ No API key provided.\n\n"
                "Get your free API key (500K rows/month):\n"
                "👉 https://datascreeniq.com\n\n"
                "Then pass it directly:\n"
                "    client = dsiq.Client('dsiq_live_...')\n\n"
                "Or set the environment variable:\n"
                "    export DATASCREENIQ_API_KEY=dsiq_live_...\n"
            )

        payload: Dict[str, Any] = {"source": source, "rows": rows}
        if options:
            payload["options"] = options

        try:
            resp = self._session.post(
                f"{self.base_url}/v1/screen",
                json=payload,
                timeout=self.timeout,
            )

        except requests.exceptions.SSLError as e:
            raise RuntimeError(
                "\n❌ SSL certificate verification failed.\n\n"
                "You are likely on a corporate network with SSL inspection\n"
                "(Zscaler, Netskope, Cisco Umbrella, Palo Alto Prisma, etc.).\n\n"
                "Fix it in 30 seconds:\n"
                "    pip install datascreeniq[truststore]\n\n"
                "Then retry — no code changes needed.\n\n"
                "Alternative options:\n"
                "    Set REQUESTS_CA_BUNDLE=/path/to/corp-cert.pem\n"
                "    Or: Client(api_key=..., verify='/path/to/corp-cert.pem')\n\n"
                f"Technical detail: {e}"
            ) from e

        except requests.exceptions.ProxyError as e:
            raise RuntimeError(
                "\n❌ Proxy error connecting to the API.\n\n"
                "Check your HTTP_PROXY / HTTPS_PROXY environment variables.\n"
                f"Technical detail: {e}"
            ) from e

        except requests.exceptions.Timeout:
            raise RuntimeError(
                f"\n❌ Request timed out after {self.timeout}s.\n\n"
                "Increase the timeout:\n"
                "    client = dsiq.Client(api_key=..., timeout=60)\n"
            )

        except requests.exceptions.RequestException as e:
            raise RuntimeError(
                f"\n❌ Request failed: {e}"
            ) from e

        return self._handle_response(resp)

    def _handle_response(self, resp: requests.Response) -> ScreenReport:
        try:
            data = resp.json()
        except ValueError:
            raise APIError(f"Invalid JSON response (HTTP {resp.status_code})")

        if resp.status_code == 401:
            raise AuthenticationError(data.get("message", "Invalid API key."))

        if resp.status_code == 429:
            code = data.get("error", data.get("code", ""))
            if code in ("rate_limit_exceeded", "PLAN_LIMIT_EXCEEDED"):
                msg = data.get("message", "Monthly row limit exceeded.")
                url = data.get("upgrade_url", "https://datascreeniq.com/dashboard")
                raise PlanLimitError(f"{msg}\nUpgrade at: {url}")
            raise RateLimitError(data.get("message", "Rate limit exceeded."))

        if resp.status_code == 400:
            raise ValidationError(data.get("message", "Invalid request."))

        if resp.status_code >= 500:
            raise APIError(
                f"Server error (HTTP {resp.status_code}): "
                f"{data.get('message', 'please try again')}"
            )

        if not resp.ok:
            raise APIError(
                f"API error (HTTP {resp.status_code}): {data.get('message', '')}"
            )

        return ScreenReport(data)

    # ──────────────────────────────────────────────────────────
    #  Session builder
    # ──────────────────────────────────────────────────────────

    def _build_session(self) -> requests.Session:
        session = requests.Session()

        # Core headers
        session.headers.update({
            "X-API-Key":    self.api_key,
            "Content-Type": "application/json",
            "User-Agent":   f"datascreeniq-python/{__version__}",
        })

        # Respect system proxy env vars (HTTP_PROXY / HTTPS_PROXY)
        session.trust_env = True

        # Retry strategy
        retry = Retry(
            total=MAX_RETRIES,
            backoff_factor=0.5,
            status_forcelist=[502, 503, 504],
            allowed_methods=["POST", "GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://",  adapter)

        # ── SSL handling (priority order) ──────────────────────

        # 1. Explicit verify= override from Client(verify=...) wins
        if self.verify is not None:
            session.verify = self.verify
            return session

        # 2. Environment CA bundle (enterprise standard)
        ca_bundle = (
            os.getenv("DATASCREENIQ_CA_BUNDLE")
            or os.getenv("REQUESTS_CA_BUNDLE")
        )
        if ca_bundle:
            session.verify = ca_bundle
            return session

        # 3. truststore — best modern solution, cross-platform
        #    install with: pip install datascreeniq[truststore]
        try:
            import truststore
            truststore.inject_into_ssl()
            session.verify = True
            return session
        except ImportError:
            pass

        # 4. certifi-win32 — Windows corporate fallback
        #    install with: pip install datascreeniq[windows]
        if sys.platform == "win32":
            try:
                import certifi_win32  # patches certifi.where() to use Windows cert store
                import certifi
                session.verify = certifi.where()
                return session
            except ImportError:
                pass

        # 5. Default — requests bundled certifi (works on most networks)
        session.verify = True
        return session

    # ──────────────────────────────────────────────────────────
    #  File parsers
    # ──────────────────────────────────────────────────────────

    def _parse_csv(self, path: Path) -> List[Dict[str, Any]]:
        rows = []
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned: Dict[str, Any] = {}
                for k, v in row.items():
                    v = v.strip() if isinstance(v, str) else v
                    if v == "" or v is None:
                        cleaned[k] = None
                    elif v.lower() in ("null", "none", "na", "n/a"):
                        cleaned[k] = None
                    elif v.lower() == "true":
                        cleaned[k] = True
                    elif v.lower() == "false":
                        cleaned[k] = False
                    else:
                        try:
                            cleaned[k] = int(v) if "." not in v else float(v)
                        except (ValueError, AttributeError):
                            cleaned[k] = v
                rows.append(cleaned)
        return rows

    def _parse_excel(
        self, path: Path, sheet: Union[int, str] = 0
    ) -> List[Dict[str, Any]]:
        try:
            import openpyxl
        except ImportError:
            raise ValidationError(
                "openpyxl required for Excel files. "
                "Install it: pip install datascreeniq[excel]"
            )
        wb        = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws        = wb.worksheets[sheet] if isinstance(sheet, int) else wb[sheet]
        rows_iter = ws.iter_rows(values_only=True)
        headers   = [
            str(h) if h is not None else f"col_{i}"
            for i, h in enumerate(next(rows_iter, []))
        ]
        rows = []
        for row in rows_iter:
            if all(v is None for v in row):
                continue
            obj: Dict[str, Any] = {}
            for h, v in zip(headers, row):
                obj[h] = v.isoformat() if hasattr(v, "isoformat") else v
            rows.append(obj)
        wb.close()
        return rows

    def _parse_json(self, path: Path) -> List[Dict[str, Any]]:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("data", "rows", "records", "items", "results", "events"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            return [data]
        raise ValidationError("JSON must contain an array of records.")

    def _parse_xml(self, path: Path) -> List[Dict[str, Any]]:
        import xml.etree.ElementTree as ET

        tree = ET.parse(path)
        root = tree.getroot()

        tag_counts: Dict[str, int] = {}
        for child in root.iter():
            tag_counts[child.tag] = tag_counts.get(child.tag, 0) + 1

        if not tag_counts:
            raise ValidationError("No XML elements found.")

        tag_counts.pop(root.tag, None)
        record_tag = max(tag_counts, key=lambda t: tag_counts[t])

        rows = []
        for el in root.findall(f".//{record_tag}"):
            row: Dict[str, Any] = dict(el.attrib)
            for child in el:
                if len(child) == 0:
                    row[child.tag] = child.text.strip() if child.text else None
                else:
                    for attr, val in child.attrib.items():
                        row[f"{child.tag}.{attr}"] = val
                    for leaf in child:
                        if len(leaf) == 0:
                            row[f"{child.tag}.{leaf.tag}"] = (
                                leaf.text.strip() if leaf.text else None
                            )
            rows.append(row)
        return rows

    # ──────────────────────────────────────────────────────────
    #  Context manager support
    # ──────────────────────────────────────────────────────────

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *args: Any) -> None:
        self._session.close()

    def __repr__(self) -> str:
        key_preview = self.api_key[:16] + "..." if self.api_key else "none"
        return f"DataScreenIQ(api_key='{key_preview}')"
