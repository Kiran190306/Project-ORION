"""Real-time volatility analysis engine."""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.market_intelligence.models import ProviderTickData
from libraries.domain.market_intelligence.statistics import RollingStatistics, StatisticsConfig


@dataclass(frozen=True, slots=True)
class ATRResult:
    """Average True Range calculation result."""

    symbol: str
    atr: Decimal
    atr_pct: float
    period: int
    current_high: Decimal
    current_low: Decimal
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class VolatilityMetrics:
    """Comprehensive volatility metrics for a symbol."""

    symbol: str
    atr: Decimal
    atr_pct: float
    rolling_volatility: float
    spread_expansion_ratio: float
    volatility_spikes: int
    z_score: float
    percentile: float
    is_high_volatility: bool
    mean_spread: Decimal
    std_spread: float
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class VolatilitySpike:
    """Detected volatility spike."""

    symbol: str
    severity: float
    spread_value: Decimal
    z_score: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    provider: str = ""


class VolatilityEngine:
    """Real-time volatility analysis engine.

    Computes ATR, rolling volatility, spread expansion, and detects
    volatility spikes. Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        atr_period: int = 14,
        volatility_window: int = 100,
        spike_threshold: float = 3.0,
        high_volatility_threshold: float = 2.0,
    ) -> None:
        if atr_period <= 0:
            raise ValueError("atr_period must be positive")
        if volatility_window <= 0:
            raise ValueError("volatility_window must be positive")
        if spike_threshold <= 0:
            raise ValueError("spike_threshold must be positive")

        self._atr_period = atr_period
        self._spike_threshold = spike_threshold
        self._high_volatility_threshold = high_volatility_threshold
        self._lock = asyncio.Lock()

        # Per-symbol state
        self._price_stats: dict[str, RollingStatistics] = {}
        self._spread_stats: dict[str, RollingStatistics] = {}
        self._price_highs: dict[str, Decimal] = {}
        self._price_lows: dict[str, Decimal] = {}
        self._true_ranges: dict[str, list[Decimal]] = {}
        self._spikes: dict[str, list[VolatilitySpike]] = {}

    async def record_tick(self, tick: ProviderTickData) -> VolatilitySpike | None:
        """Record a tick for volatility analysis.

        Returns a VolatilitySpike if one is detected, None otherwise.
        """
        async with self._lock:
            symbol = tick.symbol
            mid = tick.mid_price()

            # Price statistics
            if symbol not in self._price_stats:
                self._price_stats[symbol] = RollingStatistics(
                    StatisticsConfig(window_size=self._atr_period)
                )
            await self._price_stats[symbol].add(float(mid))

            # Spread statistics
            if symbol not in self._spread_stats:
                self._spread_stats[symbol] = RollingStatistics(
                    StatisticsConfig(window_size=self._atr_period)
                )
            await self._spread_stats[symbol].add(float(tick.spread()))

            # Track highs and lows for ATR
            if symbol not in self._price_highs or tick.bid > self._price_highs[symbol]:
                self._price_highs[symbol] = tick.bid
            if symbol not in self._price_lows or tick.ask < self._price_lows[symbol]:
                self._price_lows[symbol] = tick.ask

            # Compute true range
            if symbol not in self._true_ranges:
                self._true_ranges[symbol] = []
            tr = abs(float(tick.ask - tick.bid))
            self._true_ranges[symbol].append(Decimal(str(tr)))
            if len(self._true_ranges[symbol]) > self._atr_period:
                self._true_ranges[symbol].pop(0)

            # Check for volatility spike
            spread_snap = await self._spread_stats[symbol].get_snapshot()
            if spread_snap.count >= 3:
                z = (
                    (float(tick.spread()) - spread_snap.mean) / spread_snap.std
                    if spread_snap.std > 0
                    else 0.0
                )
                if abs(z) >= self._spike_threshold:
                    spike = VolatilitySpike(
                        symbol=symbol,
                        severity=round(abs(z), 2),
                        spread_value=tick.spread(),
                        z_score=round(z, 2),
                        provider=tick.provider,
                    )
                    if symbol not in self._spikes:
                        self._spikes[symbol] = []
                    self._spikes[symbol].append(spike)
                    if len(self._spikes[symbol]) > 100:
                        self._spikes[symbol].pop(0)
                    return spike

            return None

    async def compute_atr(self, symbol: str) -> ATRResult | None:
        """Compute Average True Range for a symbol."""
        async with self._lock:
            if symbol not in self._true_ranges or not self._true_ranges[symbol]:
                return None

            tr_values = self._true_ranges[symbol]
            atr_val = sum(tr_values) / len(tr_values) if tr_values else Decimal("0")

            price_snap = await self._price_stats[symbol].get_snapshot()
            atr_pct = float(atr_val) / price_snap.mean * 100.0 if price_snap.mean > 0 else 0.0

            return ATRResult(
                symbol=symbol,
                atr=atr_val,
                atr_pct=round(atr_pct, 4),
                period=self._atr_period,
                current_high=self._price_highs.get(symbol, Decimal("0")),
                current_low=self._price_lows.get(symbol, Decimal("0")),
            )

    async def get_volatility_metrics(self, symbol: str) -> VolatilityMetrics:
        """Get comprehensive volatility metrics for a symbol."""
        async with self._lock:
            spread_snap = await self._spread_stats.get(symbol, RollingStatistics()).get_snapshot()
            price_snap = await self._price_stats.get(symbol, RollingStatistics()).get_snapshot()

            atr_result = await self.compute_atr(symbol)
            atr_val = atr_result.atr if atr_result else Decimal("0")
            atr_pct = atr_result.atr_pct if atr_result else 0.0

            # Rolling volatility (coefficient of variation of spreads)
            rolling_vol = (
                (spread_snap.std / spread_snap.mean * 100.0) if spread_snap.mean > 0 else 0.0
            )

            # Spread expansion ratio
            expansion_ratio = (
                (float(spread_snap.maximum) / float(spread_snap.minimum))
                if spread_snap.minimum > 0
                else 1.0
            )

            # Volatility z-score
            z_score = (
                (spread_snap.last - spread_snap.mean) / spread_snap.std
                if spread_snap.std > 0
                else 0.0
            )

            # Percentile
            percentile = 50.0  # Simplified
            is_high = abs(z_score) >= self._high_volatility_threshold

            spikes = self._spikes.get(symbol, [])
            recent_spikes = sum(
                1 for s in spikes if s.timestamp > datetime.now(timezone.utc) - timedelta(hours=1)
            )

            return VolatilityMetrics(
                symbol=symbol,
                atr=atr_val,
                atr_pct=atr_pct,
                rolling_volatility=round(rolling_vol, 4),
                spread_expansion_ratio=round(expansion_ratio, 4),
                volatility_spikes=recent_spikes,
                z_score=round(z_score, 4),
                percentile=round(percentile, 2),
                is_high_volatility=is_high,
                mean_spread=Decimal(str(spread_snap.mean)),
                std_spread=spread_snap.std,
            )

    async def get_spikes(self, symbol: str, limit: int = 10) -> list[VolatilitySpike]:
        """Get recent volatility spikes for a symbol."""
        async with self._lock:
            spikes = self._spikes.get(symbol, [])
            return spikes[-limit:]

    async def clear(self) -> None:
        """Clear all collected data."""
        async with self._lock:
            self._price_stats.clear()
            self._spread_stats.clear()
            self._price_highs.clear()
            self._price_lows.clear()
            self._true_ranges.clear()
            self._spikes.clear()
