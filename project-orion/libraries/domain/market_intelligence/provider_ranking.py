"""Provider ranking engine for multi-provider selection."""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from libraries.domain.market_intelligence.statistics import RollingStatistics, StatisticsConfig


class RankingCriteria(StrEnum):
    """Criteria for ranking providers."""

    LATENCY = "latency"
    UPTIME = "uptime"
    SPREAD_QUALITY = "spread_quality"
    STABILITY = "stability"
    COMPOSITE = "composite"


@dataclass(frozen=True, slots=True)
class RankedProvider:
    """A provider with its ranking scores."""

    provider: str
    rank: int
    composite_score: float
    latency_score: float
    uptime_score: float
    spread_quality_score: float
    stability_score: float
    criteria: RankingCriteria
    sample_count: int
    ranked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ProviderRankingEngine:
    """Ranks providers based on latency, uptime, spread quality, and stability.

    Uses a composite scoring system with configurable weights.
    Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        latency_weight: float = 0.3,
        uptime_weight: float = 0.3,
        spread_weight: float = 0.2,
        stability_weight: float = 0.2,
        statistics_window: int = 100,
    ) -> None:
        if not math.isclose(latency_weight + uptime_weight + spread_weight + stability_weight, 1.0):
            raise ValueError("Weights must sum to 1.0")

        self._latency_weight = latency_weight
        self._uptime_weight = uptime_weight
        self._spread_weight = spread_weight
        self._stability_weight = stability_weight

        self._lock = asyncio.Lock()
        self._stats_config = StatisticsConfig(window_size=statistics_window)
        self._latency_stats: dict[str, RollingStatistics] = {}
        self._spread_stats: dict[str, RollingStatistics] = {}
        self._uptime: dict[str, float] = {}
        self._provider_starts: dict[str, float] = {}
        self._total_ticks: dict[str, int] = {}

    async def record_latency(self, provider: str, latency_ms: float) -> None:
        """Record a latency measurement for a provider."""
        async with self._lock:
            if provider not in self._latency_stats:
                self._latency_stats[provider] = RollingStatistics(self._stats_config)
            await self._latency_stats[provider].add(latency_ms)

    async def record_spread(self, provider: str, spread: float) -> None:
        """Record a spread measurement for a provider."""
        async with self._lock:
            if provider not in self._spread_stats:
                self._spread_stats[provider] = RollingStatistics(self._stats_config)
            await self._spread_stats[provider].add(spread)
            self._total_ticks[provider] = self._total_ticks.get(provider, 0) + 1

    async def record_uptime(self, provider: str) -> None:
        """Record provider uptime start."""
        async with self._lock:
            import time

            self._provider_starts[provider] = time.monotonic()

    def _normalize_score(
        self,
        value: float,
        inverse: bool = False,
        default: float = 0.5,
    ) -> float:
        """Normalize a value to a 0-1 score.

        If inverse=True, lower values score higher (e.g. latency).
        """
        if value <= 0:
            return default
        if inverse:
            return round(math.exp(-value / 100.0), 4)
        return round(min(1.0, value / 100.0), 4)

    async def rank(
        self,
        providers: list[str] | None = None,
        criteria: RankingCriteria = RankingCriteria.COMPOSITE,
    ) -> list[RankedProvider]:
        """Rank providers based on the specified criteria.

        Args:
            providers: Optional list of providers to rank. All if None.
            criteria: Ranking criteria to use.

        Returns:
            Sorted list of RankedProvider (best first).
        """
        async with self._lock:
            all_providers = providers or list(
                set(list(self._latency_stats.keys()) + list(self._spread_stats.keys()))
            )

            if not all_providers:
                return []

            results: list[RankedProvider] = []
            for provider in all_providers:
                lat_stats = self._latency_stats.get(provider)
                if lat_stats is None:
                    lat_stats = RollingStatistics(self._stats_config)
                lat_snap = await lat_stats.get_snapshot()

                sprd_stats = self._spread_stats.get(provider)
                if sprd_stats is None:
                    sprd_stats = RollingStatistics(self._stats_config)
                sprd_snap = await sprd_stats.get_snapshot()

                # Latency score (lower is better)
                latency_score = self._normalize_score(lat_snap.mean, inverse=True, default=0.5)

                # Uptime score (higher is better)
                import time

                uptime_seconds = time.monotonic() - self._provider_starts.get(
                    provider, time.monotonic()
                )
                uptime_score = min(1.0, uptime_seconds / 3600.0)  # Normalize to 1 hour

                # Spread quality score (lower spread = higher score)
                spread_score = 1.0 - self._normalize_score(
                    sprd_snap.mean, inverse=True, default=0.5
                )

                # Stability score (lower std = more stable)
                stability_score = 1.0 - self._normalize_score(
                    sprd_snap.std, inverse=False, default=0.5
                )

                # Composite score
                composite = (
                    latency_score * self._latency_weight
                    + uptime_score * self._uptime_weight
                    + spread_score * self._spread_weight
                    + stability_score * self._stability_weight
                )

                sample_count = max(lat_snap.count, sprd_snap.count)

                # Determine which score to use for ranking
                if criteria == RankingCriteria.LATENCY:
                    rank_score = latency_score
                elif criteria == RankingCriteria.UPTIME:
                    rank_score = uptime_score
                elif criteria == RankingCriteria.SPREAD_QUALITY:
                    rank_score = spread_score
                elif criteria == RankingCriteria.STABILITY:
                    rank_score = stability_score
                else:
                    rank_score = composite

                results.append(
                    RankedProvider(
                        provider=provider,
                        rank=0,  # Will be set after sorting
                        composite_score=round(composite, 4),
                        latency_score=round(latency_score, 4),
                        uptime_score=round(uptime_score, 4),
                        spread_quality_score=round(spread_score, 4),
                        stability_score=round(stability_score, 4),
                        criteria=criteria,
                        sample_count=sample_count,
                    )
                )

            # Sort by score descending
            if criteria == RankingCriteria.LATENCY:
                results.sort(key=lambda r: r.latency_score, reverse=True)
            elif criteria == RankingCriteria.UPTIME:
                results.sort(key=lambda r: r.uptime_score, reverse=True)
            elif criteria == RankingCriteria.SPREAD_QUALITY:
                results.sort(key=lambda r: r.spread_quality_score, reverse=True)
            elif criteria == RankingCriteria.STABILITY:
                results.sort(key=lambda r: r.stability_score, reverse=True)
            else:
                results.sort(key=lambda r: r.composite_score, reverse=True)

            # Assign ranks
            for i, r in enumerate(results):
                object.__setattr__(r, "rank", i + 1)

            return results

    async def get_best_provider(
        self,
        providers: list[str] | None = None,
        criteria: RankingCriteria = RankingCriteria.COMPOSITE,
    ) -> str | None:
        """Get the best provider based on criteria."""
        ranked = await self.rank(providers, criteria)
        return ranked[0].provider if ranked else None

    async def clear(self) -> None:
        """Clear all collected data."""
        async with self._lock:
            self._latency_stats.clear()
            self._spread_stats.clear()
            self._uptime.clear()
            self._provider_starts.clear()
            self._total_ticks.clear()
