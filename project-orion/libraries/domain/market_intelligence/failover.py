"""Automatic provider failover engine."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from libraries.domain.market_intelligence.provider_ranking import (
    ProviderRankingEngine,
    RankedProvider,
    RankingCriteria,
)


class FailoverReason(StrEnum):
    """Reasons for provider failover."""

    HIGH_LATENCY = "high_latency"
    POOR_SPREAD = "poor_spread"
    CONNECTION_LOST = "connection_lost"
    STALE_DATA = "stale_data"
    ANOMALY_BURST = "anomaly_burst"
    DEGRADED_QUALITY = "degraded_quality"
    MANUAL = "manual"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class FailoverDecision:
    """Decision result from the failover engine."""

    symbol: str
    primary_provider: str
    fallback_provider: str | None
    reason: FailoverReason
    triggered: bool
    primary_score: float
    fallback_score: float | None
    details: dict[str, Any] = field(default_factory=dict)
    decided_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FailoverEngine:
    """Automatic failover engine for multi-provider setups.

    Monitors provider health and ranking, and triggers failover when
    the primary provider degrades below acceptable thresholds.
    Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        ranking_engine: ProviderRankingEngine,
        failover_score_threshold: float = 0.3,
        min_score_difference: float = 0.1,
        cooldown_seconds: float = 60.0,
    ) -> None:
        if failover_score_threshold <= 0:
            raise ValueError("failover_score_threshold must be positive")
        if min_score_difference <= 0:
            raise ValueError("min_score_difference must be positive")
        if cooldown_seconds <= 0:
            raise ValueError("cooldown_seconds must be positive")

        self._ranking = ranking_engine
        self._failover_threshold = failover_score_threshold
        self._min_diff = min_score_difference
        self._cooldown_seconds = cooldown_seconds

        self._lock = asyncio.Lock()
        self._primary_providers: dict[str, str] = {}
        self._last_failover: dict[str, datetime] = {}
        self._failover_history: list[FailoverDecision] = []
        self._total_failovers: int = 0

    async def set_primary(self, symbol: str, provider: str) -> None:
        """Set the primary provider for a symbol."""
        async with self._lock:
            self._primary_providers[symbol] = provider

    async def get_primary(self, symbol: str) -> str | None:
        """Get the current primary provider for a symbol."""
        async with self._lock:
            return self._primary_providers.get(symbol)

    async def evaluate(self, symbol: str) -> FailoverDecision:
        """Evaluate whether failover is needed for a symbol.

        Returns a FailoverDecision with the result.
        """
        async with self._lock:
            primary = self._primary_providers.get(symbol)

            if primary is None:
                # No primary set; pick the best
                ranked = await self._ranking.rank(criteria=RankingCriteria.COMPOSITE)
                if ranked:
                    best = ranked[0]
                    self._primary_providers[symbol] = best.provider
                    return FailoverDecision(
                        symbol=symbol,
                        primary_provider=best.provider,
                        fallback_provider=None,
                        reason=FailoverReason.NOT_APPLICABLE,
                        triggered=False,
                        primary_score=best.composite_score,
                        fallback_score=None,
                        details={"action": "initial_assignment"},
                    )
                return FailoverDecision(
                    symbol=symbol,
                    primary_provider="",
                    fallback_provider=None,
                    reason=FailoverReason.NOT_APPLICABLE,
                    triggered=False,
                    primary_score=0.0,
                    fallback_score=None,
                    details={"action": "no_providers"},
                )

            # Check cooldown
            last_fail = self._last_failover.get(symbol)
            if last_fail is not None:
                elapsed = (datetime.now(timezone.utc) - last_fail).total_seconds()
                if elapsed < self._cooldown_seconds:
                    return FailoverDecision(
                        symbol=symbol,
                        primary_provider=primary,
                        fallback_provider=None,
                        reason=FailoverReason.NOT_APPLICABLE,
                        triggered=False,
                        primary_score=0.0,
                        fallback_score=None,
                        details={"cooldown_remaining": round(self._cooldown_seconds - elapsed, 1)},
                    )

            # Rank providers
            ranked = await self._ranking.rank(criteria=RankingCriteria.COMPOSITE)

            if not ranked:
                return FailoverDecision(
                    symbol=symbol,
                    primary_provider=primary,
                    fallback_provider=None,
                    reason=FailoverReason.NOT_APPLICABLE,
                    triggered=False,
                    primary_score=0.0,
                    fallback_score=None,
                    details={"error": "no_rankings_available"},
                )

            # Find primary and best alternative
            primary_ranked: RankedProvider | None = None
            best_alternative: RankedProvider | None = None

            for r in ranked:
                if r.provider == primary:
                    primary_ranked = r
                elif (
                    best_alternative is None or r.composite_score > best_alternative.composite_score
                ):
                    best_alternative = r

            if primary_ranked is None:
                # Primary no longer ranked - failover
                if best_alternative:
                    self._primary_providers[symbol] = best_alternative.provider
                    self._last_failover[symbol] = datetime.now(timezone.utc)
                    self._total_failovers += 1
                    decision = FailoverDecision(
                        symbol=symbol,
                        primary_provider=primary,
                        fallback_provider=best_alternative.provider,
                        reason=FailoverReason.DEGRADED_QUALITY,
                        triggered=True,
                        primary_score=0.0,
                        fallback_score=best_alternative.composite_score,
                        details={"action": "primary_not_ranked"},
                    )
                    self._failover_history.append(decision)
                    return decision

                return FailoverDecision(
                    symbol=symbol,
                    primary_provider=primary,
                    fallback_provider=None,
                    reason=FailoverReason.NOT_APPLICABLE,
                    triggered=False,
                    primary_score=0.0,
                    fallback_score=None,
                    details={"action": "primary_not_found"},
                )

            # Check if primary score is below threshold
            if primary_ranked.composite_score < self._failover_threshold and best_alternative:
                score_diff = best_alternative.composite_score - primary_ranked.composite_score
                if score_diff >= self._min_diff:
                    self._primary_providers[symbol] = best_alternative.provider
                    self._last_failover[symbol] = datetime.now(timezone.utc)
                    self._total_failovers += 1

                    # Determine reason
                    if best_alternative.latency_score > primary_ranked.latency_score + 0.1:
                        reason = FailoverReason.HIGH_LATENCY
                    elif (
                        best_alternative.spread_quality_score
                        > primary_ranked.spread_quality_score + 0.1
                    ):
                        reason = FailoverReason.POOR_SPREAD
                    else:
                        reason = FailoverReason.DEGRADED_QUALITY

                    decision = FailoverDecision(
                        symbol=symbol,
                        primary_provider=primary,
                        fallback_provider=best_alternative.provider,
                        reason=reason,
                        triggered=True,
                        primary_score=primary_ranked.composite_score,
                        fallback_score=best_alternative.composite_score,
                        details={
                            "old_primary_score": primary_ranked.composite_score,
                            "new_primary_score": best_alternative.composite_score,
                            "score_diff": round(score_diff, 4),
                        },
                    )
                    self._failover_history.append(decision)
                    return decision

            # No failover needed
            return FailoverDecision(
                symbol=symbol,
                primary_provider=primary,
                fallback_provider=best_alternative.provider if best_alternative else None,
                reason=FailoverReason.NOT_APPLICABLE,
                triggered=False,
                primary_score=primary_ranked.composite_score,
                fallback_score=best_alternative.composite_score if best_alternative else None,
                details={"primary_rank": primary_ranked.rank},
            )

    async def get_failover_history(
        self,
        limit: int = 50,
    ) -> list[FailoverDecision]:
        """Get recent failover decisions."""
        async with self._lock:
            return list(self._failover_history[-limit:])

    async def get_total_failovers(self) -> int:
        """Get total number of failovers executed."""
        async with self._lock:
            return self._total_failovers

    async def reset(self) -> None:
        """Reset the failover engine."""
        async with self._lock:
            self._primary_providers.clear()
            self._last_failover.clear()
            self._failover_history.clear()
            self._total_failovers = 0
