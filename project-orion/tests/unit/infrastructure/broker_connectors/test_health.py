"""Tests for health monitoring data structures."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.infrastructure.broker_connectors.health import ConnectorHealth


def test_connector_health_default_checked_at() -> None:
    before = datetime.now(timezone.utc).isoformat()
    health = ConnectorHealth(
        connector_name="mt5-1",
        running=True,
        transport_connected=True,
        last_error=None,
        last_tick_timestamp=None,
        reconnect_attempts=0,
    )
    after = datetime.now(timezone.utc).isoformat()
    assert before <= health.checked_at <= after


def test_connector_health_to_dict() -> None:
    health = ConnectorHealth(
        connector_name="oanda-1",
        running=True,
        transport_connected=False,
        last_error="connection timeout",
        last_tick_timestamp="2026-01-05T10:00:00+00:00",
        reconnect_attempts=3,
    )
    d = health.to_dict()
    assert d["connector_name"] == "oanda-1"
    assert d["running"] is True
    assert d["transport_connected"] is False
    assert d["last_error"] == "connection timeout"
    assert d["last_tick_timestamp"] == "2026-01-05T10:00:00+00:00"
    assert d["reconnect_attempts"] == 3
    assert "checked_at" in d


def test_connector_health_frozen_dataclass() -> None:
    health = ConnectorHealth(
        connector_name="binance-1",
        running=False,
        transport_connected=False,
        last_error=None,
        last_tick_timestamp=None,
        reconnect_attempts=0,
    )
    with pytest.raises(AttributeError):  # noqa: PT011
        health.running = True  # type: ignore[misc]
