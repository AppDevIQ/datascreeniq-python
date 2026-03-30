"""
DataScreenIQ SDK — Tests
Run with: pytest tests/
"""

import pytest
from unittest.mock import patch, MagicMock
import json

import datascreeniq as dsiq
from datascreeniq.exceptions import (
    AuthenticationError,
    ValidationError,
    PlanLimitError,
    DataQualityError,
)
from datascreeniq.models import ScreenReport


# ── Fixtures ────────────────────────────────────────────────

SAMPLE_ROWS = [
    {"order_id": "ORD-001", "amount": 99.50,  "email": "alice@corp.com", "status": "paid"},
    {"order_id": "ORD-002", "amount": "broken","email": None,            "status": "paid"},
    {"order_id": "ORD-003", "amount": 75.00,  "email": None,            "status": "pending"},
    {"order_id": "ORD-004", "amount": 220.50, "email": "bob@corp.com",  "status": "paid"},
]

BLOCK_RESPONSE = {
    "status": "BLOCK",
    "health_score": 0.34,
    "schema_fingerprint": "abc123",
    "issues": {
        "type_mismatches":   ["amount"],
        "null_rates":        {"email": 0.50},
        "empty_string_rates": {},
        "duplicate_fields":  [],
        "outlier_fields":    [],
        "row_count_anomaly": False,
        "new_enum_values":   {},
    },
    "drift": [{"kind": "type_changed", "field": "amount", "detail": "mixed → number"}],
    "stats": {"rows_received": 4, "rows_sampled": 4, "sample_ratio": 1.0, "sample_version": "v2"},
    "latency_ms": 9,
    "batch_id": "batch_test_001",
    "timestamp": "2026-03-29T00:00:00Z",
}

PASS_RESPONSE = {
    "status": "PASS",
    "health_score": 0.98,
    "schema_fingerprint": "def456",
    "issues": {
        "type_mismatches": [], "null_rates": {},
        "empty_string_rates": {}, "duplicate_fields": [],
        "outlier_fields": [], "row_count_anomaly": False, "new_enum_values": {},
    },
    "drift": [],
    "stats": {"rows_received": 4, "rows_sampled": 4, "sample_ratio": 1.0, "sample_version": "v2"},
    "latency_ms": 7,
    "batch_id": "batch_test_002",
    "timestamp": "2026-03-29T00:00:00Z",
}


def make_client():
    return dsiq.Client("dsiq_live_testkey123")


def mock_response(data: dict, status_code: int = 200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.ok = status_code < 400
    mock.json.return_value = data
    return mock


# ── Client init tests ────────────────────────────────────────

def test_client_requires_api_key():
    with pytest.raises(AuthenticationError):
        dsiq.Client("")


def test_client_reads_env_var(monkeypatch):
    monkeypatch.setenv("DATASCREENIQ_API_KEY", "dsiq_live_envkey")
    client = dsiq.Client()
    assert client.api_key == "dsiq_live_envkey"


def test_client_repr():
    client = make_client()
    assert "dsiq_live_testke" in repr(client)


def test_client_context_manager():
    with dsiq.Client("dsiq_live_testkey123") as client:
        assert client.api_key == "dsiq_live_testkey123"


# ── Screen tests ─────────────────────────────────────────────

def test_screen_returns_block_report():
    client = make_client()
    with patch.object(client._session, "post", return_value=mock_response(BLOCK_RESPONSE)):
        report = client.screen(SAMPLE_ROWS, source="orders")

    assert isinstance(report, ScreenReport)
    assert report.status == "BLOCK"
    assert report.is_blocked
    assert not report.is_pass
    assert not report.is_warn
    assert report.health_score == 0.34
    assert report.health_pct == "34.0%"
    assert "amount" in report.type_mismatches
    assert report.null_rates["email"] == 0.50
    assert report.drift_count == 1
    assert report.rows_received == 4
    assert report.latency_ms == 9


def test_screen_returns_pass_report():
    client = make_client()
    with patch.object(client._session, "post", return_value=mock_response(PASS_RESPONSE)):
        report = client.screen(SAMPLE_ROWS, source="orders")

    assert report.is_pass
    assert report.health_score == 0.98
    assert not report.has_drift


def test_screen_validates_empty_rows():
    client = make_client()
    with pytest.raises(ValidationError):
        client.screen([], source="orders")


def test_screen_validates_missing_source():
    client = make_client()
    with pytest.raises(ValidationError):
        client.screen(SAMPLE_ROWS, source="")


def test_screen_raises_on_401():
    client = make_client()
    with patch.object(client._session, "post", return_value=mock_response(
        {"message": "Invalid API key.", "code": "AUTH_INVALID"}, 401
    )):
        with pytest.raises(AuthenticationError):
            client.screen(SAMPLE_ROWS, source="orders")


def test_screen_raises_on_plan_limit():
    client = make_client()
    with patch.object(client._session, "post", return_value=mock_response(
        {"message": "Monthly limit exceeded.", "code": "PLAN_LIMIT_EXCEEDED"}, 429
    )):
        with pytest.raises(PlanLimitError):
            client.screen(SAMPLE_ROWS, source="orders")


# ── raise_on_block tests ─────────────────────────────────────

def test_raise_on_block_raises():
    report = ScreenReport(BLOCK_RESPONSE)
    with pytest.raises(DataQualityError) as exc_info:
        report.raise_on_block()
    assert exc_info.value.report is report


def test_raise_on_block_passes_through():
    report = ScreenReport(PASS_RESPONSE)
    result = report.raise_on_block()
    assert result is report  # returns self for chaining


# ── ScreenReport merge tests ─────────────────────────────────

def test_merge_single_report():
    r = ScreenReport(PASS_RESPONSE)
    merged = ScreenReport.merge([r])
    assert merged.status == "PASS"


def test_merge_worst_status_wins():
    r1 = ScreenReport(PASS_RESPONSE)
    r2 = ScreenReport(BLOCK_RESPONSE)
    merged = ScreenReport.merge([r1, r2])
    assert merged.status == "BLOCK"


def test_merge_sums_rows():
    r1 = ScreenReport(PASS_RESPONSE)
    r2 = ScreenReport(PASS_RESPONSE)
    merged = ScreenReport.merge([r1, r2])
    assert merged.rows_received == 8


def test_merge_empty_raises():
    with pytest.raises(ValueError):
        ScreenReport.merge([])


# ── Report display ───────────────────────────────────────────

def test_report_summary_block():
    report = ScreenReport(BLOCK_RESPONSE)
    summary = report.summary()
    assert "BLOCK" in summary
    assert "34.0%" in summary
    assert "amount" in summary


def test_report_summary_pass():
    report = ScreenReport(PASS_RESPONSE)
    summary = report.summary()
    assert "PASS" in summary
    assert "98.0%" in summary


def test_report_to_dict():
    report = ScreenReport(BLOCK_RESPONSE)
    assert report.to_dict() == BLOCK_RESPONSE


def test_report_repr():
    report = ScreenReport(BLOCK_RESPONSE)
    assert "BLOCK" in repr(report)
    assert "34.0%" in repr(report)
