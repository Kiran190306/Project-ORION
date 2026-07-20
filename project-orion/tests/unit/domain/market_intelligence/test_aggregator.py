"""Tests for MultiProviderAggregator."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.market_intelligence.aggregator import (
    AggregatedTick,
    MultiProviderAggregator,
    ProviderTick,
)
from libraries.domain.market_intelligence.anomaly import AnomalyDetector, AnomalyResult
from libraries.domain.market_intelligence.consensus import ConsensusEngine, ConsensusResult
from libraries.domain.market_intelligence.liquidity import LiquidityAnalyzer
from libraries.domain.market_intelligence.spread_analyzer import SpreadAnalyzer
from libraries.domain.market_intelligence.synchronization import SynchronizationEngine
from libraries.domain.market_intelligence.timestamp_alignment import TimestampAlignmentEngine
from libraries.domain.market_intelligence.volatility import VolatilityEngine


class TestMultiProviderAggregator:
    def test_process_tick_returns_aggregated_data(self) -> None:
        async def exercise() -> None:
            aggregator = MultiProviderAggregator(
                consensus_engine=ConsensusEngine(),
                anomaly_detector=AnomalyDetector(),
                volatility_engine=VolatilityEngine(),
                liquidity_analyzer=LiquidityAnalyzer(),
                spread_analyzer=SpreadAnalyzer(),
                timestamp_aligner=TimestampAlignmentEngine(),
                synchronizer=SynchronizationEngine(),
            )
            result = await aggregator.process_tick(
                provider="mt5",
                symbol="EUR/USD",
                bid=Decimal("1.1050"),
                ask=Decimal("1.1052"),
            )
            assert result is not None
            assert result.symbol == "EUR/USD"
            assert result.consensus_bid is not None

        asyncio.run(exercise())

    def test_multiple_providers_aggregated(self) -> None:
        async def exercise() -> None:
            aggregator = MultiProviderAggregator(
                consensus_engine=ConsensusEngine(),
                anomaly_detector=AnomalyDetector(),
                volatility_engine=VolatilityEngine(),
                liquidity_analyzer=LiquidityAnalyzer(),
                spread_analyzer=SpreadAnalyzer(),
                timestamp_aligner=TimestampAlignmentEngine(),
                synchronizer=SynchronizationEngine(),
            )

            for provider, bid, ask in [
                ("mt5", 1.1050, 1.1052),
                ("oanda", 1.1051, 1.1053),
            ]:
                await aggregator.process_tick(
                    provider=provider,
                    symbol="EUR/USD",
                    bid=Decimal(str(bid)),
                    ask=Decimal(str(ask)),
                )

            data = await aggregator.get_aggregated_data("EUR/USD")
            assert data is not None
            assert data.provider_count >= 1

        asyncio.run(exercise())

    def test_providers_set(self) -> None:
        async def exercise() -> None:
            aggregator = MultiProviderAggregator(
                consensus_engine=ConsensusEngine(),
                anomaly_detector=AnomalyDetector(),
                volatility_engine=VolatilityEngine(),
                liquidity_analyzer=LiquidityAnalyzer(),
                spread_analyzer=SpreadAnalyzer(),
                timestamp_aligner=TimestampAlignmentEngine(),
                synchronizer=SynchronizationEngine(),
            )

            await aggregator.process_tick(
                provider="mt5",
                symbol="EUR/USD",
                bid=Decimal("1.10"),
                ask=Decimal("1.11"),
            )
            assert "mt5" in aggregator.providers

        asyncio.run(exercise())

    def test_total_ticks_tracking(self) -> None:
        async def exercise() -> None:
            aggregator = MultiProviderAggregator(
                consensus_engine=ConsensusEngine(),
                anomaly_detector=AnomalyDetector(),
                volatility_engine=VolatilityEngine(),
                liquidity_analyzer=LiquidityAnalyzer(),
                spread_analyzer=SpreadAnalyzer(),
                timestamp_aligner=TimestampAlignmentEngine(),
                synchronizer=SynchronizationEngine(),
            )

            for _ in range(5):
                await aggregator.process_tick(
                    provider="mt5",
                    symbol="EUR/USD",
                    bid=Decimal("1.10"),
                    ask=Decimal("1.11"),
                )
            assert aggregator.total_ticks_received == 5

        asyncio.run(exercise())

    def test_get_aggregated_data_no_data(self) -> None:
        async def exercise() -> None:
            aggregator = MultiProviderAggregator(
                consensus_engine=ConsensusEngine(),
                anomaly_detector=AnomalyDetector(),
                volatility_engine=VolatilityEngine(),
                liquidity_analyzer=LiquidityAnalyzer(),
                spread_analyzer=SpreadAnalyzer(),
                timestamp_aligner=TimestampAlignmentEngine(),
                synchronizer=SynchronizationEngine(),
            )
            data = await aggregator.get_aggregated_data("EUR/USD")
            assert data is None

        asyncio.run(exercise())

    def test_clear(self) -> None:
        async def exercise() -> None:
            aggregator = MultiProviderAggregator(
                consensus_engine=ConsensusEngine(),
                anomaly_detector=AnomalyDetector(),
                volatility_engine=VolatilityEngine(),
                liquidity_analyzer=LiquidityAnalyzer(),
                spread_analyzer=SpreadAnalyzer(),
                timestamp_aligner=TimestampAlignmentEngine(),
                synchronizer=SynchronizationEngine(),
            )

            await aggregator.process_tick(
                provider="mt5",
                symbol="EUR/USD",
                bid=Decimal("1.10"),
                ask=Decimal("1.11"),
            )
            await aggregator.clear()
            assert aggregator.total_ticks_received == 0

        asyncio.run(exercise())

    def test_provider_tick_conversion(self) -> None:
        tick = ProviderTick(
            provider="mt5",
            symbol="EUR/USD",
            bid=Decimal("1.1050"),
            ask=Decimal("1.1052"),
            volume=Decimal("100"),
            timestamp=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            latency_ms=5.0,
            sequence=1,
        )
        data = tick.to_provider_tick_data()
        assert data.provider == "mt5"
        assert data.bid == Decimal("1.1050")
        assert data.volume == Decimal("100")
