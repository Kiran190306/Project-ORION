"""Anomaly detection engine for multi-provider market data."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any

from libraries.domain.market_intelligence.models import ProviderTickData
from libraries.domain.market_intelligence.statistics import RollingStatistics, StatisticsConfig


class AnomalyType(StrEnum):
    """Types of anomalies that can be detected."""

    BAD_TICK = "bad_tick"
    PRICE_SPIKE = "price_spike"
    DUPLICATE_TICK = "duplicate_tick"
    STALE_PRICE = "stale_price"
    CLOCK_DRIFT = "clock_drift"
    TIMESTAMP_ANOMALY = "timestamp_anomaly"
    SPREAD_EXPANSION = "spread_expansion"
    MISSING_PROVIDER = "missing_provider"
    SEQUENCE_BREAK = "sequence_break"


@dataclass(frozen=True, slots=True)
class AnomalyResult:
    """Result of anomaly detection."""

    anomaly_type: AnomalyType
    symbol: str
    provider: str
    severity: float  # 0.0 to 1.0
    description: str
    details: dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AnomalyDetector:
    """Detects anomalies in real-time multi-provider market data.

    Detects: bad ticks, price spikes, duplicates, stale prices,
    clock drift, timestamp anomalies, spread expansions.
    Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        price_spike_std_threshold: float = 4.0,
        stale_price_seconds: float = 5.0,
        max_clock_drift_ms: float = 500.0,
        spread_expansion_threshold: float = 5.0,
        min_spread_for_expansion: Decimal | None = None,
        statistics_window: int = 50,
    ) -> None:
        if price_spike_std_threshold <= 0:
            raise ValueError("price_spike_std_threshold must be positive")
        if stale_price_seconds <= 0:
            raise ValueError("stale_price_seconds must be positive")

        self._price_spike_threshold = price_spike_std_threshold
        self._stale_price_seconds = stale_price_seconds
        self._max_clock_drift_ms = max_clock_drift_ms
        self._spread_expansion_threshold = spread_expansion_threshold
        self._min_spread_for_expansion = min_spread_for_expansion or Decimal("0.0001")

        self._lock = asyncio.Lock()
        self._stats_config = StatisticsConfig(window_size=statistics_window)
        self._price_stats: dict[str, RollingStatistics] = {}
        self._spread_stats: dict[str, RollingStatistics] = {}
        self._last_tick: dict[str, ProviderTickData] = {}
        self._seen_sequences: dict[str, set[int]] = {}
        self._anomaly_log: dict[str, list[AnomalyResult]] = {}
        self._total_anomalies: int = 0

    async def analyze_tick(self, tick: ProviderTickData) -> list[AnomalyResult]:
        """Analyze a tick for all anomaly types.

        Returns a list of detected anomalies (empty if none).
        """
        anomalies: list[AnomalyResult] = []
        key = f"{tick.provider}:{tick.symbol}"

        async with self._lock:
            # Initialize stats if needed
            if key not in self._price_stats:
                self._price_stats[key] = RollingStatistics(self._stats_config)
                self._spread_stats[key] = RollingStatistics(self._stats_config)
            if key not in self._seen_sequences:
                self._seen_sequences[key] = set()

            mid_price = float(tick.mid_price())
            spread = float(tick.spread())

            await self._price_stats[key].add(mid_price)
            await self._spread_stats[key].add(spread)

            # 1. Bad tick detection (negative or zero prices)
            if tick.bid <= Decimal("0") or tick.ask <= Decimal("0"):
                anomalies.append(
                    AnomalyResult(
                        anomaly_type=AnomalyType.BAD_TICK,
                        symbol=tick.symbol,
                        provider=tick.provider,
                        severity=1.0,
                        description=f"Zero or negative price: bid={tick.bid}, ask={tick.ask}",
                        details={"bid": str(tick.bid), "ask": str(tick.ask)},
                    )
                )
                self._total_anomalies += 1

            # 2. Price spike detection
            price_snap = await self._price_stats[key].get_snapshot()
            if price_snap.count >= 3:
                z = (mid_price - price_snap.mean) / price_snap.std if price_snap.std > 0 else 0.0
                if abs(z) >= self._price_spike_threshold:
                    anomalies.append(
                        AnomalyResult(
                            anomaly_type=AnomalyType.PRICE_SPIKE,
                            symbol=tick.symbol,
                            provider=tick.provider,
                            severity=min(1.0, abs(z) / (self._price_spike_threshold * 2)),
                            description=f"Price spike detected: z-score={z:.2f}",
                            details={
                                "z_score": round(z, 2),
                                "mid": mid_price,
                                "mean": price_snap.mean,
                            },
                        )
                    )
                    self._total_anomalies += 1

            # 3. Duplicate tick detection
            if tick.sequence is not None:
                if tick.sequence in self._seen_sequences[key]:
                    anomalies.append(
                        AnomalyResult(
                            anomaly_type=AnomalyType.DUPLICATE_TICK,
                            symbol=tick.symbol,
                            provider=tick.provider,
                            severity=0.5,
                            description=f"Duplicate sequence: {tick.sequence}",
                            details={"sequence": tick.sequence},
                        )
                    )
                    self._total_anomalies += 1
                self._seen_sequences[key].add(tick.sequence)
                if len(self._seen_sequences[key]) > 10000:
                    self._seen_sequences[key].clear()

            # 4. Stale price detection
            last = self._last_tick.get(key)
            if last is not None:
                time_diff = (tick.timestamp - last.timestamp).total_seconds()
                if time_diff > self._stale_price_seconds:
                    anomalies.append(
                        AnomalyResult(
                            anomaly_type=AnomalyType.STALE_PRICE,
                            symbol=tick.symbol,
                            provider=tick.provider,
                            severity=min(1.0, time_diff / (self._stale_price_seconds * 2)),
                            description=f"Stale price: {time_diff:.1f}s since last tick",
                            details={"gap_seconds": round(time_diff, 2)},
                        )
                    )
                    self._total_anomalies += 1

            # 5. Clock drift / timestamp anomaly
            latency_ms = tick.latency_ms
            if latency_ms > self._max_clock_drift_ms:
                anomalies.append(
                    AnomalyResult(
                        anomaly_type=AnomalyType.CLOCK_DRIFT,
                        symbol=tick.symbol,
                        provider=tick.provider,
                        severity=min(1.0, latency_ms / (self._max_clock_drift_ms * 2)),
                        description=f"Clock drift detected: {latency_ms:.1f}ms latency",
                        details={"latency_ms": latency_ms},
                    )
                )
                self._total_anomalies += 1

            # 6. Spread expansion
            spread_snap = await self._spread_stats[key].get_snapshot()
            if spread_snap.count >= 3 and spread_snap.mean > 0:
                expansion = spread / spread_snap.mean
                if expansion >= self._spread_expansion_threshold:
                    anomalies.append(
                        AnomalyResult(
                            anomaly_type=AnomalyType.SPREAD_EXPANSION,
                            symbol=tick.symbol,
                            provider=tick.provider,
                            severity=min(1.0, expansion / (self._spread_expansion_threshold * 2)),
                            description=f"Spread expansion: {expansion:.1f}x normal",
                            details={
                                "expansion_ratio": round(expansion, 2),
                                "current": round(spread, 6),
                                "mean": round(spread_snap.mean, 6),
                            },
                        )
                    )
                    self._total_anomalies += 1

            # Update last tick
            self._last_tick[key] = tick

            # Log anomalies
            for a in anomalies:
                if tick.symbol not in self._anomaly_log:
                    self._anomaly_log[tick.symbol] = []
                self._anomaly_log[tick.symbol].append(a)
                if len(self._anomaly_log[tick.symbol]) > 100:
                    self._anomaly_log[tick.symbol].pop(0)

            return anomalies

    async def get_anomalies(
        self,
        symbol: str,
        limit: int = 50,
    ) -> list[AnomalyResult]:
        """Get recent anomalies for a symbol."""
        async with self._lock:
            anomalies = self._anomaly_log.get(symbol, [])
            return anomalies[-limit:]

    async def get_total_anomalies(self) -> int:
        """Get total number of anomalies detected."""
        async with self._lock:
            return self._total_anomalies

    async def clear(self) -> None:
        """Clear all collected data."""
        async with self._lock:
            self._price_stats.clear()
            self._spread_stats.clear()
            self._last_tick.clear()
            self._seen_sequences.clear()
            self._anomaly_log.clear()
            self._total_anomalies = 0
