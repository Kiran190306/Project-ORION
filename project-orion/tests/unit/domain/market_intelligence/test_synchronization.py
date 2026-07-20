"""Tests for SynchronizationEngine."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from libraries.domain.market_intelligence.models import ProviderTickData
from libraries.domain.market_intelligence.synchronization import SynchronizationEngine


class TestSynchronizationEngine:
    def test_initial_state_is_synchronized(self) -> None:
        async def exercise() -> None:
            engine = SynchronizationEngine()
            tick = ProviderTickData(
                provider="mt5",
                symbol="EUR/USD",
                bid=1.1050,
                ask=1.1052,
                timestamp=datetime.now(timezone.utc),
            )
            state = await engine.process_tick(tick)
            assert state.is_synchronized
            assert state.provider == "mt5"
            assert state.symbol == "EUR/USD"

        asyncio.run(exercise())

    def test_detects_timestamp_gap(self) -> None:
        async def exercise() -> None:
            engine = SynchronizationEngine(max_timestamp_gap_ms=100.0)
            now = datetime.now(timezone.utc)

            tick1 = ProviderTickData(
                provider="mt5",
                symbol="EUR/USD",
                bid=1.10,
                ask=1.11,
                timestamp=now,
            )
            await engine.process_tick(tick1)

            tick2 = ProviderTickData(
                provider="mt5",
                symbol="EUR/USD",
                bid=1.11,
                ask=1.12,
                timestamp=now + timedelta(seconds=1),
            )
            state = await engine.process_tick(tick2)
            assert state.gap_detected
            assert state.gap_duration_ms > 100.0

        asyncio.run(exercise())

    def test_detects_sequence_gap(self) -> None:
        async def exercise() -> None:
            engine = SynchronizationEngine()
            now = datetime.now(timezone.utc)

            tick1 = ProviderTickData(
                provider="mt5",
                symbol="EUR/USD",
                bid=1.10,
                ask=1.11,
                timestamp=now,
                sequence=1,
            )
            await engine.process_tick(tick1)

            tick2 = ProviderTickData(
                provider="mt5",
                symbol="EUR/USD",
                bid=1.11,
                ask=1.12,
                timestamp=now + timedelta(seconds=1),
                sequence=1,  # Same sequence = gap
            )
            state = await engine.process_tick(tick2)
            assert state.sequence_gap_count > 0

        asyncio.run(exercise())

    def test_multiple_providers_independent(self) -> None:
        async def exercise() -> None:
            engine = SynchronizationEngine()
            now = datetime.now(timezone.utc)

            mt5_tick = ProviderTickData(
                provider="mt5",
                symbol="EUR/USD",
                bid=1.10,
                ask=1.11,
                timestamp=now,
            )
            oanda_tick = ProviderTickData(
                provider="oanda",
                symbol="EUR/USD",
                bid=1.10,
                ask=1.11,
                timestamp=now,
            )

            s1 = await engine.process_tick(mt5_tick)
            s2 = await engine.process_tick(oanda_tick)
            assert s1.provider == "mt5"
            assert s2.provider == "oanda"

        asyncio.run(exercise())

    def test_is_synchronized_check(self) -> None:
        async def exercise() -> None:
            engine = SynchronizationEngine()
            now = datetime.now(timezone.utc)

            tick = ProviderTickData(
                provider="mt5",
                symbol="EUR/USD",
                bid=1.10,
                ask=1.11,
                timestamp=now,
            )
            await engine.process_tick(tick)
            assert await engine.is_synchronized("mt5", "EUR/USD")

        asyncio.run(exercise())

    def test_get_all_states(self) -> None:
        async def exercise() -> None:
            engine = SynchronizationEngine()
            now = datetime.now(timezone.utc)

            await engine.process_tick(
                ProviderTickData(
                    provider="mt5",
                    symbol="EUR/USD",
                    bid=1.10,
                    ask=1.11,
                    timestamp=now,
                )
            )
            await engine.process_tick(
                ProviderTickData(
                    provider="oanda",
                    symbol="EUR/USD",
                    bid=1.10,
                    ask=1.11,
                    timestamp=now,
                )
            )

            states = await engine.get_all_states()
            assert len(states) == 2

        asyncio.run(exercise())

    def test_reset(self) -> None:
        async def exercise() -> None:
            engine = SynchronizationEngine()
            now = datetime.now(timezone.utc)

            await engine.process_tick(
                ProviderTickData(
                    provider="mt5",
                    symbol="EUR/USD",
                    bid=1.10,
                    ask=1.11,
                    timestamp=now,
                )
            )
            await engine.reset()
            assert len(await engine.get_all_states()) == 0

        asyncio.run(exercise())
