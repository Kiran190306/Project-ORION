"""Liquidity analysis engine for multi-provider market data."""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any

from libraries.domain.market_intelligence.models import ProviderTickData
from libraries.domain.market_intelligence.statistics import RollingStatistics, StatisticsConfig


class SpreadQuality(StrEnum):
    """Classification of spread quality."""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    ILLIQUID = "illiquid"


@dataclass(frozen=True, slots=True)
class ProviderConfidence:
    """Confidence score for a single provider."""

    provider: str
    score: float
    spread_quality: SpreadQuality
    liquidity_score: float
    sample_count: int


@dataclass(frozen=True, slots=True)
class LiquidityMetrics:
    """Aggregated liquidity metrics for a symbol."""

    symbol: str
    overall_liquidity_score: float
    average_spread: Decimal
    median_spread: Decimal
    spread_quality: SpreadQuality
    provider_confidence_scores: tuple[ProviderConfidence, ...]
    active_provider_count: int
    spread_std: float
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class LiquidityAnalyzer:
    """Analyzes liquidity across multiple providers.

    Computes spread quality, liquidity scores, and provider confidence.
    Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        excellent_spread_pips: float = 0.5,
        good_spread_pips: float = 1.0,
        fair_spread_pips: float = 2.0,
        stats_window: int = 100,
        pip_size: Decimal | None = None,
    ) -> None:
        self._excellent_spread = Decimal(str(excellent_spread_pips))
        self._good_spread = Decimal(str(good_spread_pips))
        self._fair_spread = Decimal(str(fair_spread_pips))
        self._pip_size = pip_size or Decimal("0.0001")
        self._lock = asyncio.Lock()
        self._provider_spreads: dict[str, RollingStatistics] = {}
        self._symbol_spreads: dict[str, RollingStatistics] = {}
        self._stats_config = StatisticsConfig(window_size=stats_window)

    def _spread_to_pips(self, spread: Decimal) -> Decimal:
        """Convert a raw spread value to pips."""
        return spread / self._pip_size if self._pip_size > Decimal("0") else Decimal("0")

    def _classify_spread(self, spread: Decimal) -> SpreadQuality:
        """Classify spread quality based on configured thresholds (in pips)."""
        spread_pips = self._spread_to_pips(spread)
        if spread_pips <= self._excellent_spread:
            return SpreadQuality.EXCELLENT
        elif spread_pips <= self._good_spread:
            return SpreadQuality.GOOD
        elif spread_pips <= self._fair_spread:
            return SpreadQuality.FAIR
        elif spread_pips <= self._fair_spread * Decimal("2"):
            return SpreadQuality.POOR
        else:
            return SpreadQuality.ILLIQUID

    def _liquidity_from_spread(self, spread: Decimal) -> float:
        """Compute liquidity score from spread. Higher is more liquid."""
        if spread <= Decimal("0"):
            return 1.0
        # Score decays exponentially with spread
        return round(math.exp(-float(spread) * 2.0), 4)

    async def record_tick(self, tick: ProviderTickData) -> None:
        """Record a tick for liquidity analysis."""
        async with self._lock:
            spread = tick.spread()
            prov_key = f"{tick.provider}:{tick.symbol}"

            if prov_key not in self._provider_spreads:
                self._provider_spreads[prov_key] = RollingStatistics(self._stats_config)
            await self._provider_spreads[prov_key].add(float(spread))

            if tick.symbol not in self._symbol_spreads:
                self._symbol_spreads[tick.symbol] = RollingStatistics(self._stats_config)
            await self._symbol_spreads[tick.symbol].add(float(spread))

    async def analyze(self, symbol: str) -> LiquidityMetrics:
        """Analyze liquidity for a symbol across all providers."""
        async with self._lock:
            symbol_stats = self._symbol_spreads.get(symbol)
            if symbol_stats is None:
                return LiquidityMetrics(
                    symbol=symbol,
                    overall_liquidity_score=0.0,
                    average_spread=Decimal("0"),
                    median_spread=Decimal("0"),
                    spread_quality=SpreadQuality.ILLIQUID,
                    provider_confidence_scores=(),
                    active_provider_count=0,
                    spread_std=0.0,
                )

            snap = await symbol_stats.get_snapshot()
            avg_spread = Decimal(str(snap.mean))
            med_spread = Decimal(str(snap.median))

            # Provider confidence scores
            provider_scores: list[ProviderConfidence] = []
            for key, stats in self._provider_spreads.items():
                if key.endswith(f":{symbol}"):
                    provider = key.split(":")[0]
                    psnap = await stats.get_snapshot()
                    pspread = Decimal(str(psnap.mean))
                    pscore = self._liquidity_from_spread(pspread)
                    provider_scores.append(
                        ProviderConfidence(
                            provider=provider,
                            score=pscore,
                            spread_quality=self._classify_spread(pspread),
                            liquidity_score=pscore,
                            sample_count=psnap.count,
                        )
                    )

            quality = self._classify_spread(avg_spread)
            overall_score = self._liquidity_from_spread(avg_spread)

            return LiquidityMetrics(
                symbol=symbol,
                overall_liquidity_score=overall_score,
                average_spread=avg_spread,
                median_spread=med_spread,
                spread_quality=quality,
                provider_confidence_scores=tuple(provider_scores),
                active_provider_count=len(provider_scores),
                spread_std=snap.std,
            )

    async def get_provider_confidence(
        self,
        provider: str,
        symbol: str,
    ) -> ProviderConfidence | None:
        """Get confidence score for a specific provider/symbol."""
        async with self._lock:
            stats = self._provider_spreads.get(f"{provider}:{symbol}")
            if stats is None:
                return None
            snap = await stats.get_snapshot()
            spread = Decimal(str(snap.mean))
            score = self._liquidity_from_spread(spread)
            return ProviderConfidence(
                provider=provider,
                score=score,
                spread_quality=self._classify_spread(spread),
                liquidity_score=score,
                sample_count=snap.count,
            )

    async def clear(self) -> None:
        """Clear all collected data."""
        async with self._lock:
            self._provider_spreads.clear()
            self._symbol_spreads.clear()
