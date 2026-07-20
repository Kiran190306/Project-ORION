"""Tests for TimestampAlignmentEngine."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from libraries.domain.market_intelligence.timestamp_alignment import (
    AlignmentStrategy,
    TimestampAlignmentEngine,
)


class TestTimestampAlignmentEngine:
    def test_align_exact_strategy(self) -> None:
        async def exercise() -> None:
            engine = TimestampAlignmentEngine(strategy=AlignmentStrategy.EXACT)
            now = datetime.now(timezone.utc)
            aligned = await engine.align_tick(
                provider="mt5",
                symbol="EUR/USD",
                provider_timestamp=now,
                local_received_at=now,
                bid=1.1050,
                ask=1.1052,
            )
            assert aligned.provider == "mt5"
            assert aligned.strategy == AlignmentStrategy.EXACT
            assert aligned.offset_ms == 0.0

        asyncio.run(exercise())

    def test_align_nearest_with_drift(self) -> None:
        async def exercise() -> None:
            engine = TimestampAlignmentEngine(strategy=AlignmentStrategy.NEAREST)
            now = datetime.now(timezone.utc)
            # Provider time is 50ms behind local time
            provider_ts = now - timedelta(milliseconds=50)

            aligned = await engine.align_tick(
                provider="oanda",
                symbol="GBP/USD",
                provider_timestamp=provider_ts,
                local_received_at=now,
                bid=1.30,
                ask=1.31,
            )
            assert aligned.provider == "oanda"
            assert aligned.offset_ms != 0.0

        asyncio.run(exercise())

    def test_average_strategy(self) -> None:
        async def exercise() -> None:
            engine = TimestampAlignmentEngine(strategy=AlignmentStrategy.AVERAGE)
            now = datetime.now(timezone.utc)
            provider_ts = now - timedelta(milliseconds=100)

            aligned = await engine.align_tick(
                provider="binance",
                symbol="BTC/USD",
                provider_timestamp=provider_ts,
                local_received_at=now,
                bid=50000.0,
                ask=50001.0,
            )
            assert aligned.strategy == AlignmentStrategy.AVERAGE

        asyncio.run(exercise())

    def test_interpolate_strategy(self) -> None:
        async def exercise() -> None:
            engine = TimestampAlignmentEngine(strategy=AlignmentStrategy.INTERPOLATE)
            now = datetime.now(timezone.utc)
            provider_ts = now - timedelta(milliseconds=200)

            aligned = await engine.align_tick(
                provider="mt5",
                symbol="EUR/USD",
                provider_timestamp=provider_ts,
                local_received_at=now,
                bid=1.1050,
                ask=1.1052,
            )
            assert aligned.strategy == AlignmentStrategy.INTERPOLATE

        asyncio.run(exercise())

    def test_drift_tracking(self) -> None:
        async def exercise() -> None:
            engine = TimestampAlignmentEngine()
            now = datetime.now(timezone.utc)

            for i in range(5):
                provider_ts = now - timedelta(milliseconds=10 * i)
                await engine.align_tick(
                    provider="mt5",
                    symbol="EUR/USD",
                    provider_timestamp=provider_ts,
                    local_received_at=now,
                    bid=1.10,
                    ask=1.11,
                )

            drift = await engine.get_drift("mt5")
            assert drift != 0.0

            drifts = await engine.get_all_drifts()
            assert "mt5" in drifts

        asyncio.run(exercise())

    def test_reset_drift(self) -> None:
        async def exercise() -> None:
            engine = TimestampAlignmentEngine()
            now = datetime.now(timezone.utc)

            await engine.align_tick(
                provider="mt5",
                symbol="EUR/USD",
                provider_timestamp=now - timedelta(milliseconds=50),
                local_received_at=now,
                bid=1.10,
                ask=1.11,
            )

            assert await engine.get_drift("mt5") != 0.0
            await engine.reset_drift("mt5")
            assert await engine.get_drift("mt5") == 0.0

        asyncio.run(exercise())

    def test_validates_max_offset(self) -> None:
        with pytest.raises(ValueError):
            TimestampAlignmentEngine(max_offset_ms=0)
