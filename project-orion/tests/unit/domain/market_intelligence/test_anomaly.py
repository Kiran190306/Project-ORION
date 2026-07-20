"""Tests for AnomalyDetector."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from libraries.domain.market_intelligence.anomaly import AnomalyDetector, AnomalyType
from libraries.domain.market_intelligence.models import ProviderTickData


def _make_tick(
    provider: str = "mt5",
    symbol: str = "EUR/USD",
    bid: str = "1.1050",
    ask: str = "1.1052",
    **kwargs: object,
) -> ProviderTickData:
    """Helper to create ProviderTickData with Decimal bid/ask."""
    return ProviderTickData(
        provider=provider,
        symbol=symbol,
        bid=Decimal(bid),
        ask=Decimal(ask),
        timestamp=kwargs.pop("timestamp", datetime.now(timezone.utc)),
        **kwargs,  # type: ignore[arg-type]
    )


class TestAnomalyDetector:
    def test_no_anomalies_for_normal_tick(self) -> None:
        async def exercise() -> None:
            detector = AnomalyDetector()
            tick = _make_tick()
            anomalies = await detector.analyze_tick(tick)
            assert len(anomalies) == 0

        asyncio.run(exercise())

    def test_detects_bad_tick(self) -> None:
        async def exercise() -> None:
            detector = AnomalyDetector()
            tick = _make_tick(bid="0")
            anomalies = await detector.analyze_tick(tick)
            assert any(a.anomaly_type == AnomalyType.BAD_TICK for a in anomalies)

        asyncio.run(exercise())

    def test_detects_duplicate_sequence(self) -> None:
        async def exercise() -> None:
            detector = AnomalyDetector()
            now = datetime.now(timezone.utc)

            tick1 = _make_tick(timestamp=now, sequence=1)
            tick2 = _make_tick(bid="1.1051", ask="1.1053", timestamp=now, sequence=1)

            await detector.analyze_tick(tick1)
            anomalies = await detector.analyze_tick(tick2)
            assert any(a.anomaly_type == AnomalyType.DUPLICATE_TICK for a in anomalies)

        asyncio.run(exercise())

    def test_detects_stale_price(self) -> None:
        async def exercise() -> None:
            detector = AnomalyDetector(stale_price_seconds=0.1)
            now = datetime.now(timezone.utc)

            tick1 = _make_tick(timestamp=now)
            await detector.analyze_tick(tick1)

            tick2 = _make_tick(bid="1.1051", ask="1.1053", timestamp=now + timedelta(seconds=1))
            anomalies = await detector.analyze_tick(tick2)
            assert any(a.anomaly_type == AnomalyType.STALE_PRICE for a in anomalies)

        asyncio.run(exercise())

    def test_detects_clock_drift(self) -> None:
        async def exercise() -> None:
            detector = AnomalyDetector(max_clock_drift_ms=10.0)
            tick = _make_tick(latency_ms=100.0)
            anomalies = await detector.analyze_tick(tick)
            assert any(a.anomaly_type == AnomalyType.CLOCK_DRIFT for a in anomalies)

        asyncio.run(exercise())

    def test_detects_spread_expansion(self) -> None:
        async def exercise() -> None:
            detector = AnomalyDetector(
                spread_expansion_threshold=3.0,
                statistics_window=10,
            )
            now = datetime.now(timezone.utc)

            # Normal ticks
            for _ in range(5):
                await detector.analyze_tick(_make_tick(timestamp=now))

            # Wide spread
            wide_tick = _make_tick(bid="1.10", ask="1.20", timestamp=now)
            anomalies = await detector.analyze_tick(wide_tick)
            assert any(a.anomaly_type == AnomalyType.SPREAD_EXPANSION for a in anomalies)

        asyncio.run(exercise())

    def test_get_anomalies(self) -> None:
        async def exercise() -> None:
            detector = AnomalyDetector()
            tick = _make_tick(bid="0")
            await detector.analyze_tick(tick)
            anomalies = await detector.get_anomalies("EUR/USD")
            assert len(anomalies) >= 1

        asyncio.run(exercise())

    def test_get_total_anomalies(self) -> None:
        async def exercise() -> None:
            detector = AnomalyDetector()
            tick = _make_tick(bid="0")
            await detector.analyze_tick(tick)
            total = await detector.get_total_anomalies()
            assert total >= 1

        asyncio.run(exercise())

    def test_clear(self) -> None:
        async def exercise() -> None:
            detector = AnomalyDetector()
            tick = _make_tick(bid="0")
            await detector.analyze_tick(tick)
            await detector.clear()
            assert await detector.get_total_anomalies() == 0

        asyncio.run(exercise())
