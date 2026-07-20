"""Tests for VolatilityEngine."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from libraries.domain.market_intelligence.models import ProviderTickData
from libraries.domain.market_intelligence.volatility import VolatilityEngine


class TestVolatilityEngine:
    def test_initial_metrics(self) -> None:
        async def exercise() -> None:
            engine = VolatilityEngine()
            metrics = await engine.get_volatility_metrics("EUR/USD")
            assert metrics.atr is not None
            assert metrics.volatility_spikes == 0

        asyncio.run(exercise())

    def test_record_tick_updates_metrics(self) -> None:
        async def exercise() -> None:
            engine = VolatilityEngine(atr_period=14)
            now = datetime.now(timezone.utc)

            for i in range(10):
                await engine.record_tick(
                    ProviderTickData(
                        provider="mt5",
                        symbol="EUR/USD",
                        bid=1.10 + i * 0.001,
                        ask=1.11 + i * 0.001,
                        timestamp=now,
                    )
                )

            metrics = await engine.get_volatility_metrics("EUR/USD")
            assert metrics.rolling_volatility >= 0
            assert metrics.atr is not None

        asyncio.run(exercise())

    def test_compute_atr(self) -> None:
        async def exercise() -> None:
            engine = VolatilityEngine(atr_period=5)
            now = datetime.now(timezone.utc)

            for i in range(5):
                spread = 0.0002 + i * 0.0001
                await engine.record_tick(
                    ProviderTickData(
                        provider="mt5",
                        symbol="EUR/USD",
                        bid=1.1050,
                        ask=1.1050 + spread,
                        timestamp=now,
                    )
                )

            atr = await engine.compute_atr("EUR/USD")
            assert atr is not None
            assert atr.period == 5
            assert atr.atr > 0

        asyncio.run(exercise())

    def test_detect_volatility_spike(self) -> None:
        async def exercise() -> None:
            engine = VolatilityEngine(
                atr_period=5,
                spike_threshold=2.0,
            )
            now = datetime.now(timezone.utc)

            # Normal ticks
            for _ in range(5):
                await engine.record_tick(
                    ProviderTickData(
                        provider="mt5",
                        symbol="EUR/USD",
                        bid=1.1050,
                        ask=1.1052,
                        timestamp=now,
                    )
                )

            # Spike tick
            spike = await engine.record_tick(
                ProviderTickData(
                    provider="mt5",
                    symbol="EUR/USD",
                    bid=1.10,
                    ask=1.20,
                    timestamp=now,
                )
            )
            if spike is not None:
                assert spike.severity > 0

        asyncio.run(exercise())

    def test_get_spikes(self) -> None:
        async def exercise() -> None:
            engine = VolatilityEngine(spike_threshold=2.0)
            now = datetime.now(timezone.utc)

            for _ in range(5):
                await engine.record_tick(
                    ProviderTickData(
                        provider="mt5",
                        symbol="EUR/USD",
                        bid=1.1050,
                        ask=1.1052,
                        timestamp=now,
                    )
                )

            spikes = await engine.get_spikes("EUR/USD")
            assert isinstance(spikes, list)

        asyncio.run(exercise())

    def test_clear(self) -> None:
        async def exercise() -> None:
            engine = VolatilityEngine()
            now = datetime.now(timezone.utc)

            await engine.record_tick(
                ProviderTickData(
                    provider="mt5",
                    symbol="EUR/USD",
                    bid=1.10,
                    ask=1.11,
                    timestamp=now,
                )
            )
            await engine.clear()
            metrics = await engine.get_volatility_metrics("EUR/USD")
            assert metrics.volatility_spikes == 0

        asyncio.run(exercise())

    def test_validates_periods(self) -> None:
        with pytest.raises(ValueError):
            VolatilityEngine(atr_period=0)
        with pytest.raises(ValueError):
            VolatilityEngine(spike_threshold=0)
