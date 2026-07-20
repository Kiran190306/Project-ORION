"""
Project ORION - Market Intelligence & Multi-Provider Aggregation Engine (EPIC-005 Sprint-4).

Real-time market intelligence layer that aggregates data from multiple brokers/providers,
computes consensus prices, analyzes liquidity and volatility, detects anomalies,
and manages automatic provider failover.

Relies on MarketDataManager for raw tick ingestion and StreamManager for event delivery.
"""

from __future__ import annotations

from libraries.domain.market_intelligence.aggregator import (
    AggregatedTick,
    MultiProviderAggregator,
    ProviderTick,
)
from libraries.domain.market_intelligence.anomaly import (
    AnomalyDetector,
    AnomalyResult,
    AnomalyType,
)
from libraries.domain.market_intelligence.consensus import (
    ConsensusEngine,
    ConsensusPrice,
    ConsensusResult,
    DisagreementLevel,
    ProviderStatus,
)
from libraries.domain.market_intelligence.failover import (
    FailoverDecision,
    FailoverEngine,
    FailoverReason,
)
from libraries.domain.market_intelligence.interfaces import (
    AnomalyHandler,
    ConsensusHandler,
    FailoverHandler,
    IntelligenceSink,
    ProviderHealthPort,
    ProviderLatencyTracker,
)
from libraries.domain.market_intelligence.liquidity import (
    LiquidityAnalyzer,
    LiquidityMetrics,
    ProviderConfidence,
    SpreadQuality,
)
from libraries.domain.market_intelligence.models import (
    AggregatedProviderData,
    LatencySnapshot,
    MarketIntelligenceSnapshot,
    ProviderTickData,
)
from libraries.domain.market_intelligence.provider_ranking import (
    ProviderRankingEngine,
    RankedProvider,
    RankingCriteria,
)
from libraries.domain.market_intelligence.quality import PriceQuality, QualityScorer
from libraries.domain.market_intelligence.spread_analyzer import (
    SpreadAnalysis,
    SpreadAnalyzer,
)
from libraries.domain.market_intelligence.statistics import (
    RollingStatistics,
    StatisticsConfig,
    StatisticsSnapshot,
)
from libraries.domain.market_intelligence.synchronization import (
    ProviderSynchronizationState,
    SynchronizationEngine,
)
from libraries.domain.market_intelligence.timestamp_alignment import (
    AlignedTick,
    AlignmentStrategy,
    TimestampAlignmentEngine,
)
from libraries.domain.market_intelligence.volatility import (
    ATRResult,
    VolatilityEngine,
    VolatilityMetrics,
    VolatilitySpike,
)

__all__ = [
    "AggregatedTick",
    "AggregatedProviderData",
    "AlignmentStrategy",
    "AlignedTick",
    "AnomalyDetector",
    "AnomalyHandler",
    "AnomalyResult",
    "AnomalyType",
    "ATRResult",
    "ConsensusEngine",
    "ConsensusHandler",
    "ConsensusPrice",
    "ConsensusResult",
    "DisagreementLevel",
    "FailoverDecision",
    "FailoverEngine",
    "FailoverHandler",
    "FailoverReason",
    "IntelligenceSink",
    "LatencySnapshot",
    "LiquidityAnalyzer",
    "LiquidityMetrics",
    "MarketIntelligenceSnapshot",
    "MultiProviderAggregator",
    "PriceQuality",
    "ProviderConfidence",
    "ProviderHealthPort",
    "ProviderLatencyTracker",
    "ProviderRankingEngine",
    "ProviderStatus",
    "ProviderTick",
    "ProviderTickData",
    "QualityScorer",
    "RankedProvider",
    "RankingCriteria",
    "RollingStatistics",
    "SpreadAnalysis",
    "SpreadAnalyzer",
    "SpreadQuality",
    "StatisticsConfig",
    "StatisticsSnapshot",
    "SynchronizationEngine",
    "ProviderSynchronizationState",
    "TimestampAlignmentEngine",
    "VolatilityEngine",
    "VolatilityMetrics",
    "VolatilitySpike",
]
