"""Tests for provider payload parsing."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.market import RawTick
from libraries.infrastructure.broker_connectors.parsers import (
    parse_generic_bid_ask_tick,
    parse_provider_dict_tick,
)


class TestParseGenericBidAskTick:
    def test_parse_minimal_fields(self) -> None:
        ts = datetime(2026, 1, 5, 10, 0, 0, tzinfo=timezone.utc)
        tick = parse_generic_bid_ask_tick(
            provider="mt5",
            symbol="EUR/USD",
            timestamp=ts,
            bid="1.10004",
            ask="1.10016",
        )
        assert tick.symbol == "EUR/USD"
        assert tick.timestamp == ts
        assert tick.bid == Decimal("1.10004")
        assert tick.ask == Decimal("1.10016")
        assert tick.source == "mt5"
        assert tick.bid_size is None
        assert tick.ask_size is None
        assert tick.sequence is None

    def test_parse_with_optional_fields(self) -> None:
        ts = datetime(2026, 1, 5, 10, 0, 0, tzinfo=timezone.utc)
        tick = parse_generic_bid_ask_tick(
            provider="oanda",
            symbol="GBP/USD",
            timestamp=ts,
            bid="1.25000",
            ask="1.25010",
            bid_size="1000000",
            ask_size="2000000",
            sequence=42,
        )
        assert tick.bid_size == Decimal("1000000")
        assert tick.ask_size == Decimal("2000000")
        assert tick.sequence == 42

    def test_parse_integer_timestamp(self) -> None:
        # Unix timestamp in seconds
        tick = parse_generic_bid_ask_tick(
            provider="mt5",
            symbol="USD/JPY",
            timestamp=1736000000,
            bid="150.10",
            ask="150.20",
        )
        assert tick.timestamp.tzinfo is not None
        assert tick.timestamp.year >= 2025

    def test_parse_iso_string_timestamp(self) -> None:
        tick = parse_generic_bid_ask_tick(
            provider="mt5",
            symbol="USD/JPY",
            timestamp="2026-01-05T10:00:00Z",
            bid="150.10",
            ask="150.20",
        )
        assert tick.timestamp.year == 2026
        assert tick.timestamp.tzinfo is not None

    def test_parse_naive_datetime_timestamp(self) -> None:
        naive = datetime(2026, 1, 5, 10, 0, 0)
        tick = parse_generic_bid_ask_tick(
            provider="mt5",
            symbol="EUR/USD",
            timestamp=naive,
            bid="1.10",
            ask="1.11",
        )
        # Should be treated as UTC
        assert tick.timestamp.tzinfo is not None
        assert tick.timestamp.tzinfo.utcoffset(tick.timestamp) == timezone.utc.utcoffset(tick.timestamp)  # type: ignore[union-attr]

    def test_parse_string_timestamp_with_z(self) -> None:
        tick = parse_generic_bid_ask_tick(
            provider="binance",
            symbol="BTC/USDT",
            timestamp="2026-01-05T10:00:00Z",
            bid="50000.00",
            ask="50001.00",
        )
        assert tick.timestamp.tzinfo is not None

    def test_invalid_timestamp_type(self) -> None:
        with pytest.raises(TypeError, match="Unsupported timestamp"):
            parse_generic_bid_ask_tick(
                provider="mt5",
                symbol="EUR/USD",
                timestamp=[],  # type: ignore[arg-type]
                bid="1.10",
                ask="1.11",
            )


class TestParseProviderDictTick:
    def test_parse_valid_dict(self) -> None:
        ts = "2026-01-05T10:00:00Z"
        tick = parse_provider_dict_tick(
            "mt5",
            {
                "symbol": "EURUSD",
                "timestamp": ts,
                "bid": "1.10004",
                "ask": "1.10016",
                "bid_size": "500000",
                "ask_size": "700000",
                "sequence": 7,
            },
        )
        assert isinstance(tick, RawTick)
        assert tick.symbol == "EURUSD"
        assert tick.source == "mt5"
        assert tick.bid == Decimal("1.10004")
        assert tick.ask == Decimal("1.10016")
        assert tick.sequence == 7

    def test_parse_optional_fields_missing(self) -> None:
        ts = "2026-01-05T10:00:00Z"
        tick = parse_provider_dict_tick(
            "oanda",
            {
                "symbol": "GBP/USD",
                "timestamp": ts,
                "bid": "1.25000",
                "ask": "1.25010",
            },
        )
        assert tick.bid_size is None
        assert tick.ask_size is None
        assert tick.sequence is None

    def test_parse_non_dict_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="payload must be a dict"):
            parse_provider_dict_tick("mt5", "not_a_dict")  # type: ignore[arg-type]
