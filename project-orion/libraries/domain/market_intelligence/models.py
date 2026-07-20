"""Immutable data models for the Market Intelligence engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class ProviderTickData:
    """Raw tick data received from a single provider."""

    provider: str
    symbol: str
    bid: Decimal
    ask: Decimal
    volume: Decimal | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: float = 0.0
    sequence: int | None = None

    def spread(self) -> Decimal:
        """Calculate the bid-ask spread."""
        return self.ask - self.bid

    def mid_price(self) -> Decimal:
        """Calculate the mid price."""
        return (self.bid + self.ask) / Decimal("2")


@dataclass(frozen=True, slots=True)
class AggregatedProviderData:
    """Aggregated market data from all providers for a symbol."""

    symbol: str
    ticks: tuple[ProviderTickData, ...] = ()
    consensus_bid: Decimal | None = None
    consensus_ask: Decimal | None = None
    consensus_mid: Decimal | None = None
    provider_count: int = 0
    active_providers: tuple[str, ...] = ()
    aggregated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def consensus_spread(self) -> Decimal | None:
        if self.consensus_bid is not None and self.consensus_ask is not None:
            return self.consensus_ask - self.consensus_bid
        return None


@dataclass(frozen=True, slots=True)
class LatencySnapshot:
    """Latency measurements for a single provider."""

    provider: str
    current_ms: float = 0.0
    average_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    sample_count: int = 0
    measured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class MarketIntelligenceSnapshot:
    """Complete snapshot of market intelligence for a symbol."""

    symbol: str
    aggregated_data: AggregatedProviderData | None = None
    consensus: Any | None = None  # ConsensusResult
    volatility: Any | None = None  # VolatilityMetrics
    liquidity: Any | None = None  # LiquidityMetrics
    spread_analysis: Any | None = None  # SpreadAnalysis
    anomalies: tuple[Any, ...] = ()
    quality: Any | None = None  # PriceQuality
    provider_rankings: tuple[Any, ...] = ()
    latency_snapshots: tuple[LatencySnapshot, ...] = ()
    failover_status: Any | None = None  # FailoverDecision
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
