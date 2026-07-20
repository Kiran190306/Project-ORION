"""Consensus engine for multi-provider price aggregation."""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any

from libraries.domain.market_intelligence.models import ProviderTickData


class DisagreementLevel(StrEnum):
    """Level of disagreement among providers."""

    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    NONE = "none"


class ProviderStatus(StrEnum):
    """Status of a provider in the consensus calculation."""

    ACTIVE = "active"
    STALE = "stale"
    DELAYED = "delayed"
    DISAGREEING = "disagreeing"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class ConsensusPrice:
    """A consensus price produced by the consensus engine."""

    symbol: str
    bid: Decimal
    ask: Decimal
    mid: Decimal
    spread: Decimal
    provider_count: int
    active_providers: tuple[str, ...]
    disagreement_level: DisagreementLevel
    bid_variance: float
    ask_variance: float
    produced_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class ConsensusResult:
    """Full result of consensus calculation."""

    price: ConsensusPrice
    provider_statuses: dict[str, ProviderStatus]
    excluded_providers: list[str]
    consensus_bid: Decimal
    consensus_ask: Decimal
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConsensusEngine:
    """Computes consensus prices across multiple providers.

    Compares prices across providers, detects disagreements, stale/delayed/missing
    providers, and produces a robust consensus price.
    Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        max_price_deviation_pct: float = 0.1,
        max_timestamp_delay_seconds: float = 2.0,
        max_stale_seconds: float = 5.0,
        min_providers_for_consensus: int = 1,
    ) -> None:
        if max_price_deviation_pct <= 0:
            raise ValueError("max_price_deviation_pct must be positive")
        if max_timestamp_delay_seconds <= 0:
            raise ValueError("max_timestamp_delay_seconds must be positive")
        if max_stale_seconds <= 0:
            raise ValueError("max_stale_seconds must be positive")
        if min_providers_for_consensus <= 0:
            raise ValueError("min_providers_for_consensus must be positive")

        self._max_deviation = Decimal(str(max_price_deviation_pct / 100.0))
        self._max_delay_seconds = max_timestamp_delay_seconds
        self._max_stale_seconds = max_stale_seconds
        self._min_providers = min_providers_for_consensus
        self._lock = asyncio.Lock()
        self._recent_ticks: dict[str, list[ProviderTickData]] = {}

    async def record_tick(self, tick: ProviderTickData) -> None:
        """Record a tick for consensus calculation."""
        async with self._lock:
            if tick.symbol not in self._recent_ticks:
                self._recent_ticks[tick.symbol] = []
            self._recent_ticks[tick.symbol].append(tick)

            # Keep only recent ticks within the stale window
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._max_stale_seconds)
            self._recent_ticks[tick.symbol] = [
                t
                for t in self._recent_ticks[tick.symbol]
                if t.timestamp > cutoff or t is tick  # always keep the new one
            ]

            # Limit max stored per symbol
            if len(self._recent_ticks[tick.symbol]) > 1000:
                self._recent_ticks[tick.symbol] = self._recent_ticks[tick.symbol][-1000:]

    async def compute_consensus(self, symbol: str) -> ConsensusResult | None:
        """Compute consensus price for a symbol.

        Returns None if insufficient data.
        """
        async with self._lock:
            ticks = self._recent_ticks.get(symbol, [])
            now = datetime.now(timezone.utc)

            if not ticks:
                return None

            # Group by provider, take latest tick per provider
            provider_ticks: dict[str, ProviderTickData] = {}
            for t in ticks:
                if (
                    t.provider not in provider_ticks
                    or t.timestamp > provider_ticks[t.provider].timestamp
                ):
                    provider_ticks[t.provider] = t

            # Classify providers
            provider_statuses: dict[str, ProviderStatus] = {}
            for provider, tick in provider_ticks.items():
                age = (now - tick.timestamp).total_seconds()
                if age > self._max_stale_seconds:
                    provider_statuses[provider] = ProviderStatus.MISSING
                elif age > self._max_delay_seconds:
                    provider_statuses[provider] = ProviderStatus.DELAYED
                else:
                    provider_statuses[provider] = ProviderStatus.ACTIVE

            # Compute mean bid/ask for deviation check
            active_ticks = [
                t
                for t in provider_ticks.values()
                if provider_statuses[t.provider] == ProviderStatus.ACTIVE
            ]

            if len(active_ticks) < self._min_providers:
                # Fall back to all non-missing providers
                active_ticks = [
                    t
                    for t in provider_ticks.values()
                    if provider_statuses[t.provider] != ProviderStatus.MISSING
                ]
                if len(active_ticks) < self._min_providers:
                    return None

            # Compute weighted consensus (equal weight)
            bids = [t.bid for t in active_ticks]
            asks = [t.ask for t in active_ticks]
            mean_bid = sum(bids) / len(bids)
            mean_ask = sum(asks) / len(asks)

            # Detect disagreeing providers
            excluded: list[str] = []
            agreeing_ticks: list[ProviderTickData] = []
            for t in active_ticks:
                bid_dev = abs(t.bid - mean_bid) / mean_bid if mean_bid > 0 else Decimal("0")
                ask_dev = abs(t.ask - mean_ask) / mean_ask if mean_ask > 0 else Decimal("0")
                if bid_dev > self._max_deviation or ask_dev > self._max_deviation:
                    excluded.append(t.provider)
                    provider_statuses[t.provider] = ProviderStatus.DISAGREEING
                else:
                    agreeing_ticks.append(t)

            # Recompute consensus without disagreeing providers
            if agreeing_ticks:
                consensus_bid = sum(t.bid for t in agreeing_ticks) / len(agreeing_ticks)
                consensus_ask = sum(t.ask for t in agreeing_ticks) / len(agreeing_ticks)
            else:
                consensus_bid = mean_bid
                consensus_ask = mean_ask

            consensus_mid = (consensus_bid + consensus_ask) / Decimal("2")
            consensus_spread = consensus_ask - consensus_bid

            # Compute bid/ask variance
            bid_values = [float(t.bid) for t in active_ticks]
            ask_values = [float(t.ask) for t in active_ticks]
            bid_mean_f = float(mean_bid)
            ask_mean_f = float(mean_ask)
            bid_var = (
                sum((v - bid_mean_f) ** 2 for v in bid_values) / len(bid_values)
                if bid_values
                else 0.0
            )
            ask_var = (
                sum((v - ask_mean_f) ** 2 for v in ask_values) / len(ask_values)
                if ask_values
                else 0.0
            )

            # Determine disagreement level
            disagree_count = len(excluded)
            total_active = len(active_ticks)
            if total_active == 0:
                level = DisagreementLevel.NONE
            elif disagree_count / total_active >= 0.5:
                level = DisagreementLevel.HIGH
            elif disagree_count / total_active >= 0.25:
                level = DisagreementLevel.MODERATE
            elif disagree_count > 0:
                level = DisagreementLevel.LOW
            else:
                level = DisagreementLevel.NONE

            consensus_price = ConsensusPrice(
                symbol=symbol,
                bid=consensus_bid,
                ask=consensus_ask,
                mid=consensus_mid,
                spread=consensus_spread,
                provider_count=len(active_ticks),
                active_providers=tuple(t.provider for t in active_ticks),
                disagreement_level=level,
                bid_variance=round(bid_var, 6),
                ask_variance=round(ask_var, 6),
            )

            return ConsensusResult(
                price=consensus_price,
                provider_statuses=provider_statuses,
                excluded_providers=excluded,
                consensus_bid=consensus_bid,
                consensus_ask=consensus_ask,
            )

    async def get_provider_statuses(self, symbol: str) -> dict[str, ProviderStatus]:
        """Get current status of all providers for a symbol."""
        result = await self.compute_consensus(symbol)
        if result is None:
            return {}
        return result.provider_statuses

    async def clear(self) -> None:
        """Clear all collected data."""
        async with self._lock:
            self._recent_ticks.clear()
