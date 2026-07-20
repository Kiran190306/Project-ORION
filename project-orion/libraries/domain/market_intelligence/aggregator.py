"""Multi-Provider Aggregation Engine.

Aggregates real-time market data from multiple brokers/providers
(MT5, OANDA, Binance, and future providers) into normalized ProviderTick
and AggregatedTick data structures.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.market_intelligence.anomaly import AnomalyDetector
from libraries.domain.market_intelligence.consensus import ConsensusEngine
from libraries.domain.market_intelligence.interfaces import (
    AnomalyHandler,
    ConsensusHandler,
    FailoverHandler,
    IntelligenceSink,
)
from libraries.domain.market_intelligence.liquidity import LiquidityAnalyzer
from libraries.domain.market_intelligence.models import AggregatedProviderData, ProviderTickData
from libraries.domain.market_intelligence.spread_analyzer import SpreadAnalyzer
from libraries.domain.market_intelligence.synchronization import SynchronizationEngine
from libraries.domain.market_intelligence.timestamp_alignment import TimestampAlignmentEngine
from libraries.domain.market_intelligence.volatility import VolatilityEngine


@dataclass(frozen=True, slots=True)
class ProviderTick:
    """Provider-originated tick data with metadata."""

    provider: str
    symbol: str
    bid: Decimal
    ask: Decimal
    volume: Decimal | None
    timestamp: datetime
    received_at: datetime
    latency_ms: float
    sequence: int | None

    def to_provider_tick_data(self) -> ProviderTickData:
        """Convert to ProviderTickData."""
        return ProviderTickData(
            provider=self.provider,
            symbol=self.symbol,
            bid=self.bid,
            ask=self.ask,
            volume=self.volume,
            timestamp=self.timestamp,
            received_at=self.received_at,
            latency_ms=self.latency_ms,
            sequence=self.sequence,
        )


@dataclass(frozen=True, slots=True)
class AggregatedTick:
    """Aggregated tick combining data from all providers."""

    symbol: str
    ticks: tuple[ProviderTick, ...]
    consensus_bid: Decimal | None
    consensus_ask: Decimal | None
    aggregated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MultiProviderAggregator:
    """Aggregates market data from multiple providers.

    Coordinates:
    - Provider tick ingestion
    - Timestamp alignment
    - Synchronization
    - Consensus computation
    - Anomaly detection
    - Volatility analysis
    - Liquidity analysis
    - Spread analysis

    All dependencies are injected for testability.
    Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        consensus_engine: ConsensusEngine,
        anomaly_detector: AnomalyDetector,
        volatility_engine: VolatilityEngine,
        liquidity_analyzer: LiquidityAnalyzer,
        spread_analyzer: SpreadAnalyzer,
        timestamp_aligner: TimestampAlignmentEngine,
        synchronizer: SynchronizationEngine,
        sink: IntelligenceSink | None = None,
        anomaly_handler: AnomalyHandler | None = None,
        consensus_handler: ConsensusHandler | None = None,
    ) -> None:
        self._consensus = consensus_engine
        self._anomaly = anomaly_detector
        self._volatility = volatility_engine
        self._liquidity = liquidity_analyzer
        self._spread = spread_analyzer
        self._aligner = timestamp_aligner
        self._synchronizer = synchronizer
        self._sink = sink
        self._anomaly_handler = anomaly_handler
        self._consensus_handler = consensus_handler

        self._lock = asyncio.Lock()
        self._total_ticks_received: int = 0
        self._total_anomalies: int = 0
        self._total_consensus_produced: int = 0
        self._providers: set[str] = set()

    @property
    def providers(self) -> frozenset[str]:
        """Return the set of known providers."""
        return frozenset(self._providers)

    @property
    def total_ticks_received(self) -> int:
        return self._total_ticks_received

    @property
    def total_anomalies(self) -> int:
        return self._total_anomalies

    @property
    def total_consensus_produced(self) -> int:
        return self._total_consensus_produced

    async def process_tick(
        self,
        provider: str,
        symbol: str,
        bid: Decimal,
        ask: Decimal,
        volume: Decimal | None = None,
        timestamp: datetime | None = None,
        sequence: int | None = None,
    ) -> AggregatedProviderData | None:
        """Process an incoming tick from a provider.

        Full pipeline: alignment -> sync -> record -> detect anomalies -> consensus.

        Args:
            provider: Provider identifier (e.g. "mt5", "oanda").
            symbol: Trading symbol (e.g. "EUR/USD").
            bid: Bid price.
            ask: Ask price.
            volume: Optional volume.
            timestamp: Optional provider timestamp (defaults to now).
            sequence: Optional provider sequence number.

        Returns:
            AggregatedProviderData if consensus was produced, None otherwise.
        """
        now = datetime.now(timezone.utc)
        ts = timestamp or now
        latency_ms = (now - ts).total_seconds() * 1000.0

        provider_tick = ProviderTick(
            provider=provider,
            symbol=symbol,
            bid=bid,
            ask=ask,
            volume=volume,
            timestamp=ts,
            received_at=now,
            latency_ms=latency_ms,
            sequence=sequence,
        )

        # Track provider
        async with self._lock:
            self._providers.add(provider)
            self._total_ticks_received += 1

        # 1. Timestamp alignment
        aligned = await self._aligner.align_tick(
            provider=provider,
            symbol=symbol,
            provider_timestamp=ts,
            local_received_at=now,
            bid=float(bid),
            ask=float(ask),
        )

        # 2. Synchronization check
        tick_data = provider_tick.to_provider_tick_data()
        sync_state = await self._synchronizer.process_tick(tick_data)

        # 3. Record in engines
        await self._consensus.record_tick(tick_data)
        await self._liquidity.record_tick(tick_data)
        await self._spread.record_tick(tick_data)
        await self._volatility.record_tick(tick_data)

        # 4. Anomaly detection
        anomalies = await self._anomaly.analyze_tick(tick_data)
        if anomalies:
            async with self._lock:
                self._total_anomalies += len(anomalies)
            if self._anomaly_handler:
                for anomaly in anomalies:
                    await self._anomaly_handler.on_anomaly_detected(symbol, anomaly)

        # 5. Compute consensus
        result = await self._consensus.compute_consensus(symbol)
        if result is not None:
            async with self._lock:
                self._total_consensus_produced += 1

            aggregated = AggregatedProviderData(
                symbol=symbol,
                ticks=(tick_data,),
                consensus_bid=result.consensus_bid,
                consensus_ask=result.consensus_ask,
                consensus_mid=result.price.mid,
                provider_count=result.price.provider_count,
                active_providers=result.price.active_providers,
            )

            if self._consensus_handler:
                await self._consensus_handler.on_consensus_update(symbol, result)

            if self._sink:
                await self._sink.on_aggregated_data(aggregated)

            return aggregated

        return None

    async def get_aggregated_data(self, symbol: str) -> AggregatedProviderData | None:
        """Get the latest aggregated data for a symbol."""
        result = await self._consensus.compute_consensus(symbol)
        if result is None:
            return None
        return AggregatedProviderData(
            symbol=symbol,
            ticks=(),
            consensus_bid=result.consensus_bid,
            consensus_ask=result.consensus_ask,
            consensus_mid=result.price.mid,
            provider_count=result.price.provider_count,
            active_providers=result.price.active_providers,
        )

    async def clear(self) -> None:
        """Clear all collected data across all engines."""
        async with self._lock:
            self._total_ticks_received = 0
            self._total_anomalies = 0
            self._total_consensus_produced = 0
            self._providers.clear()
        await self._consensus.clear()
        await self._anomaly.clear()
        await self._volatility.clear()
        await self._liquidity.clear()
        await self._spread.clear()
        await self._synchronizer.reset()
