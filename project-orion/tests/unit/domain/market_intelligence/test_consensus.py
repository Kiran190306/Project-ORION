"""Tests for ConsensusEngine."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from libraries.domain.market_intelligence.consensus import (
    ConsensusEngine,
    DisagreementLevel,
    ProviderStatus,
)
from libraries.domain.market_intelligence.models import ProviderTickData


class TestConsensusEngine:
    def test_initial_consensus_returns_none(self) -> None:
        async def exercise() -> None:
            engine = ConsensusEngine()
            result = await engine.compute_consensus("EUR/USD")
            assert result is None

        asyncio.run(exercise())

    def test_single_provider_consensus(self) -> None:
        async def exercise() -> None:
            engine = ConsensusEngine()
            tick = ProviderTickData(
                provider="mt5",
                symbol="EUR/USD",
                bid=Decimal("1.1050"),
                ask=Decimal("1.1052"),
                timestamp=datetime.now(timezone.utc),
            )
            await engine.record_tick(tick)
            result = await engine.compute_consensus("EUR/USD")
            assert result is not None
            assert result.price.provider_count == 1
            assert result.price.bid == Decimal("1.1050")
            assert result.price.ask == Decimal("1.1052")

        asyncio.run(exercise())

    def test_multiple_providers_consensus(self) -> None:
        async def exercise() -> None:
            engine = ConsensusEngine()
            now = datetime.now(timezone.utc)

            for provider, bid, ask in [
                ("mt5", "1.1050", "1.1052"),
                ("oanda", "1.1051", "1.1053"),
                ("binance", "1.1049", "1.1051"),
            ]:
                await engine.record_tick(
                    ProviderTickData(
                        provider=provider,
                        symbol="EUR/USD",
                        bid=Decimal(bid),
                        ask=Decimal(ask),
                        timestamp=now,
                    )
                )

            result = await engine.compute_consensus("EUR/USD")
            assert result is not None
            assert result.price.provider_count == 3
            assert result.price.disagreement_level == DisagreementLevel.NONE

        asyncio.run(exercise())

    def test_detects_disagreeing_provider(self) -> None:
        async def exercise() -> None:
            engine = ConsensusEngine(max_price_deviation_pct=0.1)
            now = datetime.now(timezone.utc)

            # Two providers agree
            for provider, bid, ask in [
                ("mt5", "1.1050", "1.1052"),
                ("oanda", "1.1051", "1.1053"),
            ]:
                await engine.record_tick(
                    ProviderTickData(
                        provider=provider,
                        symbol="EUR/USD",
                        bid=Decimal(bid),
                        ask=Decimal(ask),
                        timestamp=now,
                    )
                )

            # Third provider disagrees (price is 10% off)
            await engine.record_tick(
                ProviderTickData(
                    provider="binance",
                    symbol="EUR/USD",
                    bid=Decimal("1.20"),
                    ask=Decimal("1.22"),
                    timestamp=now,
                )
            )

            result = await engine.compute_consensus("EUR/USD")
            assert result is not None
            assert "binance" in result.excluded_providers

        asyncio.run(exercise())

    def test_stale_provider_detection(self) -> None:
        async def exercise() -> None:
            engine = ConsensusEngine(
                max_stale_seconds=0.1,
                max_timestamp_delay_seconds=0.05,
            )
            now = datetime.now(timezone.utc)

            # Fresh tick
            await engine.record_tick(
                ProviderTickData(
                    provider="mt5",
                    symbol="EUR/USD",
                    bid=Decimal("1.1050"),
                    ask=Decimal("1.1052"),
                    timestamp=now,
                )
            )

            # Stale tick
            await engine.record_tick(
                ProviderTickData(
                    provider="oanda",
                    symbol="EUR/USD",
                    bid=Decimal("1.1051"),
                    ask=Decimal("1.1053"),
                    timestamp=now - timedelta(seconds=1),
                )
            )

            result = await engine.compute_consensus("EUR/USD")
            assert result is not None
            # Oanda should be missing or delayed
            status = result.provider_statuses.get("oanda")
            assert status in (ProviderStatus.DELAYED, ProviderStatus.MISSING)

        asyncio.run(exercise())

    def test_get_provider_statuses(self) -> None:
        async def exercise() -> None:
            engine = ConsensusEngine()
            await engine.record_tick(
                ProviderTickData(
                    provider="mt5",
                    symbol="EUR/USD",
                    bid=Decimal("1.1050"),
                    ask=Decimal("1.1052"),
                    timestamp=datetime.now(timezone.utc),
                )
            )
            statuses = await engine.get_provider_statuses("EUR/USD")
            assert "mt5" in statuses
            assert statuses["mt5"] == ProviderStatus.ACTIVE

        asyncio.run(exercise())

    def test_clear(self) -> None:
        async def exercise() -> None:
            engine = ConsensusEngine()
            await engine.record_tick(
                ProviderTickData(
                    provider="mt5",
                    symbol="EUR/USD",
                    bid=Decimal("1.10"),
                    ask=Decimal("1.11"),
                    timestamp=datetime.now(timezone.utc),
                )
            )
            await engine.clear()
            assert await engine.compute_consensus("EUR/USD") is None

        asyncio.run(exercise())
