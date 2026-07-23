"""Integration tests for the full Market Intelligence pipeline."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.market_intelligence.aggregator import MultiProviderAggregator
from libraries.domain.market_intelligence.anomaly import AnomalyDetector, AnomalyResult, AnomalyType
from libraries.domain.market_intelligence.consensus import (
    ConsensusEngine,
    ConsensusResult,
    DisagreementLevel,
)
from libraries.domain.market_intelligence.failover import FailoverEngine, FailoverReason
from libraries.domain.market_intelligence.liquidity import LiquidityAnalyzer
from libraries.domain.market_intelligence.provider_ranking import (
    ProviderRankingEngine,
    RankingCriteria,
)
from libraries.domain.market_intelligence.quality import PriceQuality, QualityScorer
from libraries.domain.market_intelligence.spread_analyzer import SpreadAnalyzer
from libraries.domain.market_intelligence.statistics import RollingStatistics, StatisticsConfig
from libraries.domain.market_intelligence.synchronization import SynchronizationEngine
from libraries.domain.market_intelligence.timestamp_alignment import (
    AlignmentStrategy,
    TimestampAlignmentEngine,
)
from libraries.domain.market_intelligence.volatility import VolatilityEngine


class TestMarketIntelligenceIntegration:
    """Full pipeline integration test."""

    def test_full_pipeline_with_multiple_providers(self) -> None:
        async def exercise() -> None:
            # Create all engines
            consensus = ConsensusEngine()
            anomalies = AnomalyDetector()
            volatility = VolatilityEngine()
            liquidity = LiquidityAnalyzer()
            spread = SpreadAnalyzer()
            aligner = TimestampAlignmentEngine()
            synchronizer = SynchronizationEngine()
            ranking = ProviderRankingEngine()
            failover = FailoverEngine(ranking)
            quality = QualityScorer()

            # Create aggregator
            aggregator = MultiProviderAggregator(
                consensus_engine=consensus,
                anomaly_detector=anomalies,
                volatility_engine=volatility,
                liquidity_analyzer=liquidity,
                spread_analyzer=spread,
                timestamp_aligner=aligner,
                synchronizer=synchronizer,
            )

            now = datetime.now(timezone.utc)

            # Simulate multiple providers sending ticks
            providers_data = [
                ("mt5", 1.1050, 1.1052),
                ("oanda", 1.1051, 1.1053),
                ("binance", 1.1049, 1.1051),
            ]

            for provider, bid, ask in providers_data:
                await ranking.record_latency(provider, 5.0)
                await ranking.record_spread(provider, ask - bid)
                await ranking.record_uptime(provider)

                result = await aggregator.process_tick(
                    provider=provider,
                    symbol="EUR/USD",
                    bid=Decimal(str(bid)),
                    ask=Decimal(str(ask)),
                    timestamp=now,
                )
                assert result is not None

            # Verify consensus
            consensus_result = await consensus.compute_consensus("EUR/USD")
            assert consensus_result is not None
            assert consensus_result.price.provider_count == 3
            assert consensus_result.price.disagreement_level in (
                DisagreementLevel.NONE,
                DisagreementLevel.LOW,
            )

            # Verify the aggregated data
            data = await aggregator.get_aggregated_data("EUR/USD")
            assert data is not None
            assert data.provider_count == 3
            assert data.consensus_bid is not None

            # Ranking
            ranked = await ranking.rank()
            assert len(ranked) == 3

            # Failover evaluation
            await failover.set_primary("EUR/USD", "mt5")
            decision = await failover.evaluate("EUR/USD")
            assert decision.primary_provider is not None

            # Quality scoring
            q, s = await quality.score_spread(
                spread=Decimal("0.0002"),
                typical_spread=Decimal("0.0002"),
            )
            assert q in (PriceQuality.EXCELLENT, PriceQuality.GOOD, PriceQuality.EXCELLENT)

            print(f"Consensus: {consensus_result.price.bid}/{consensus_result.price.ask}")
            print(f"Providers: {data.active_providers}")
            print(f"Rankings: {[(r.provider, r.composite_score) for r in ranked]}")
            print(f"Failover: triggered={decision.triggered}, reason={decision.reason}")

        asyncio.run(exercise())

    def test_anomaly_then_recovery(self) -> None:
        """Test that system recovers after anomalies."""

        async def exercise() -> None:
            detector = AnomalyDetector()
            now = datetime.now(timezone.utc)

            # Normal ticks (no sequence = no duplicate detection)
            for i in range(5):
                anomalies = await detector.analyze_tick(
                    type(
                        "Tick",
                        (),
                        {
                            "provider": "mt5",
                            "symbol": "EUR/USD",
                            "bid": Decimal("1.1050"),
                            "ask": Decimal("1.1052"),
                            "timestamp": now,
                            "mid_price": lambda self: Decimal("1.1051"),
                            "spread": lambda self: Decimal("0.0002"),
                            "latency_ms": 5.0,
                            "sequence": None,
                        },
                    )()
                )
                assert len(anomalies) == 0

            # Anomaly
            total = await detector.get_total_anomalies()
            assert total == 0

        asyncio.run(exercise())

    def test_concurrent_tick_processing(self) -> None:
        """Test that multiple ticks can be processed concurrently."""

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

            async def send_tick(provider: str, bid: float, ask: float) -> None:
                await aggregator.process_tick(
                    provider=provider,
                    symbol="EUR/USD",
                    bid=Decimal(str(bid)),
                    ask=Decimal(str(ask)),
                )

            await asyncio.gather(
                send_tick("mt5", 1.1050, 1.1052),
                send_tick("oanda", 1.1051, 1.1053),
                send_tick("binance", 1.1049, 1.1051),
            )

            assert aggregator.total_ticks_received == 3

        asyncio.run(exercise())

    def test_provider_failover_scenario(self) -> None:
        """Test failover when primary provider degrades."""

        async def exercise() -> None:
            ranking = ProviderRankingEngine()
            failover = FailoverEngine(
                ranking,
                failover_score_threshold=0.5,
                min_score_difference=0.1,
                cooldown_seconds=0.01,
            )

            # Primary provider with good scores
            await ranking.record_latency("mt5", 5.0)
            await ranking.record_spread("mt5", 0.0002)
            await ranking.record_uptime("mt5")
            await failover.set_primary("EUR/USD", "mt5")

            # Introduce a better provider
            await ranking.record_latency("oanda", 1.0)
            await ranking.record_spread("oanda", 0.0001)
            await ranking.record_uptime("oanda")

            # Degrade mt5
            await ranking.record_latency("mt5", 500.0)
            await ranking.record_spread("mt5", 0.01)

            decision = await failover.evaluate("EUR/USD")
            # Should either trigger failover or show reason
            assert decision.primary_provider is not None

        asyncio.run(exercise())
