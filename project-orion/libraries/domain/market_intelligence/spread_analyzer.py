"""Spread analysis engine for multi-provider bid-ask spread evaluation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.market_intelligence.models import ProviderTickData
from libraries.domain.market_intelligence.statistics import RollingStatistics, StatisticsConfig


@dataclass(frozen=True, slots=True)
class SpreadAnalysis:
    """Complete spread analysis for a symbol."""

    symbol: str
    average_spread: Decimal
    min_spread: Decimal
    max_spread: Decimal
    median_spread: Decimal
    current_spread: Decimal
    spread_volatility: float
    provider_spreads: dict[str, Decimal]
    best_provider: str | None
    worst_provider: str | None
    spread_pips: float
    sample_count: int
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SpreadAnalyzer:
    """Analyzes bid-ask spreads across multiple providers.

    Tracks spread statistics per provider and per symbol.
    Thread-safe via asyncio.Lock.
    """

    def __init__(self, window_size: int = 100, pip_size: Decimal | None = None) -> None:
        self._pip_size = pip_size or Decimal("0.0001")
        self._lock = asyncio.Lock()
        self._stats_config = StatisticsConfig(window_size=window_size)
        self._provider_stats: dict[str, RollingStatistics] = {}
        self._symbol_stats: dict[str, RollingStatistics] = {}
        self._current_spreads: dict[str, Decimal] = {}

    async def record_tick(self, tick: ProviderTickData) -> None:
        """Record a tick for spread analysis."""
        async with self._lock:
            spread = tick.spread()
            prov_key = f"{tick.provider}:{tick.symbol}"

            if prov_key not in self._provider_stats:
                self._provider_stats[prov_key] = RollingStatistics(self._stats_config)
            await self._provider_stats[prov_key].add(float(spread))

            if tick.symbol not in self._symbol_stats:
                self._symbol_stats[tick.symbol] = RollingStatistics(self._stats_config)
            await self._symbol_stats[tick.symbol].add(float(spread))

            self._current_spreads[prov_key] = spread

    async def analyze(self, symbol: str) -> SpreadAnalysis:
        """Analyze spreads for a symbol."""
        async with self._lock:
            symbol_stats = self._symbol_stats.get(symbol)

            if symbol_stats is None:
                return SpreadAnalysis(
                    symbol=symbol,
                    average_spread=Decimal("0"),
                    min_spread=Decimal("0"),
                    max_spread=Decimal("0"),
                    median_spread=Decimal("0"),
                    current_spread=Decimal("0"),
                    spread_volatility=0.0,
                    provider_spreads={},
                    best_provider=None,
                    worst_provider=None,
                    spread_pips=0.0,
                    sample_count=0,
                )

            snap = await symbol_stats.get_snapshot()

            provider_spreads: dict[str, Decimal] = {}
            for key, stats in self._provider_stats.items():
                if key.endswith(f":{symbol}"):
                    provider = key.split(":")[0]
                    psnap = await stats.get_snapshot()
                    provider_spreads[provider] = Decimal(str(psnap.mean))

            best_provider = (
                min(provider_spreads, key=provider_spreads.get) if provider_spreads else None
            )
            worst_provider = (
                max(provider_spreads, key=provider_spreads.get) if provider_spreads else None
            )

            current_spread = Decimal("0")
            if symbol in self._current_spreads:
                current_spread = self._current_spreads[symbol]

            avg_spread = Decimal(str(snap.mean))
            spread_pips = float(avg_spread / self._pip_size)

            return SpreadAnalysis(
                symbol=symbol,
                average_spread=avg_spread,
                min_spread=Decimal(str(snap.minimum)),
                max_spread=Decimal(str(snap.maximum)),
                median_spread=Decimal(str(snap.median)),
                current_spread=current_spread,
                spread_volatility=snap.std,
                provider_spreads=provider_spreads,
                best_provider=best_provider,
                worst_provider=worst_provider,
                spread_pips=round(spread_pips, 2),
                sample_count=snap.count,
            )

    async def get_provider_spread(self, provider: str, symbol: str) -> Decimal | None:
        """Get average spread for a specific provider/symbol."""
        async with self._lock:
            stats = self._provider_stats.get(f"{provider}:{symbol}")
            if stats is None:
                return None
            snap = await stats.get_snapshot()
            return Decimal(str(snap.mean))

    async def clear(self) -> None:
        """Clear all collected data."""
        async with self._lock:
            self._provider_stats.clear()
            self._symbol_stats.clear()
            self._current_spreads.clear()
