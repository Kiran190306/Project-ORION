"""Market snapshot cache for the event streaming layer.

Provides thread-safe caching of latest market data snapshots including
ticks, OHLC candles, and spreads with TTL-based expiry.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from libraries.infrastructure.event_stream.event_types import (
    CacheHitRateEvent,
    EventStreamEvent,
)


@dataclass(frozen=True, slots=True)
class CachedSnapshot:
    """Immutable cached market snapshot with metadata."""

    payload: dict[str, Any]
    cached_at: datetime
    ttl_seconds: float


@dataclass(frozen=True, slots=True)
class CacheMetrics:
    """Snapshot of cache performance metrics."""

    hits: int
    misses: int
    hit_rate: float
    entries: int
    expired_entries: int


class MarketSnapshotCache:
    """Thread-safe cache for market data snapshots.

    Supports:
    - Latest tick per symbol
    - Latest OHLC per symbol/timeframe
    - Latest spread per symbol
    - TTL-based expiry
    - Hit/miss tracking
    """

    def __init__(self, default_ttl_seconds: float = 5.0) -> None:
        if default_ttl_seconds <= 0:
            raise ValueError("default_ttl_seconds must be positive")
        self._default_ttl_seconds = default_ttl_seconds
        self._ticks: dict[str, CachedSnapshot] = {}
        self._ohlc: dict[str, dict[str, CachedSnapshot]] = {}
        self._spreads: dict[str, CachedSnapshot] = {}
        self._lock = asyncio.Lock()
        self._hits: int = 0
        self._misses: int = 0
        self._expired_entries: int = 0

    @property
    def default_ttl_seconds(self) -> float:
        return self._default_ttl_seconds

    # ─── Latest Tick ──────────────────────────────────────────

    async def set_latest_tick(
        self,
        symbol: str,
        tick_data: dict[str, Any],
        ttl_seconds: float | None = None,
    ) -> None:
        """Cache the latest tick for a symbol.

        Args:
            symbol: Trading symbol.
            tick_data: Tick payload data.
            ttl_seconds: Optional TTL override (uses default if None).
        """
        async with self._lock:
            self._ticks[symbol.upper()] = CachedSnapshot(
                payload=tick_data,
                cached_at=datetime.now(timezone.utc),
                ttl_seconds=ttl_seconds or self._default_ttl_seconds,
            )

    async def get_latest_tick(self, symbol: str) -> dict[str, Any] | None:
        """Retrieve the latest cached tick for a symbol.

        Args:
            symbol: Trading symbol.

        Returns:
            Tick data if found and not expired, None otherwise.
        """
        async with self._lock:
            snapshot = self._ticks.get(symbol.upper())
            if snapshot is None:
                self._misses += 1
                return None
            if self._is_expired(snapshot):
                del self._ticks[symbol.upper()]
                self._expired_entries += 1
                self._misses += 1
                return None
            self._hits += 1
            return snapshot.payload

    async def has_latest_tick(self, symbol: str) -> bool:
        """Check if a valid cached tick exists for a symbol."""
        async with self._lock:
            snapshot = self._ticks.get(symbol.upper())
            if snapshot is None:
                return False
            if self._is_expired(snapshot):
                return False
            return True

    # ─── Latest OHLC ──────────────────────────────────────────

    async def set_latest_ohlc(
        self,
        symbol: str,
        timeframe: str,
        ohlc_data: dict[str, Any],
        ttl_seconds: float | None = None,
    ) -> None:
        """Cache the latest OHLC candle for a symbol/timeframe."""
        async with self._lock:
            symbol_key = symbol.upper()
            if symbol_key not in self._ohlc:
                self._ohlc[symbol_key] = {}
            self._ohlc[symbol_key][timeframe] = CachedSnapshot(
                payload=ohlc_data,
                cached_at=datetime.now(timezone.utc),
                ttl_seconds=ttl_seconds or self._default_ttl_seconds,
            )

    async def get_latest_ohlc(
        self,
        symbol: str,
        timeframe: str,
    ) -> dict[str, Any] | None:
        """Retrieve the latest cached OHLC for a symbol/timeframe."""
        async with self._lock:
            symbol_key = symbol.upper()
            symbol_ohlc = self._ohlc.get(symbol_key)
            if symbol_ohlc is None:
                self._misses += 1
                return None
            snapshot = symbol_ohlc.get(timeframe)
            if snapshot is None:
                self._misses += 1
                return None
            if self._is_expired(snapshot):
                del symbol_ohlc[timeframe]
                if not symbol_ohlc:
                    del self._ohlc[symbol_key]
                self._expired_entries += 1
                self._misses += 1
                return None
            self._hits += 1
            return snapshot.payload

    # ─── Latest Spread ────────────────────────────────────────

    async def set_latest_spread(
        self,
        symbol: str,
        spread_data: dict[str, Any],
        ttl_seconds: float | None = None,
    ) -> None:
        """Cache the latest spread for a symbol."""
        async with self._lock:
            self._spreads[symbol.upper()] = CachedSnapshot(
                payload=spread_data,
                cached_at=datetime.now(timezone.utc),
                ttl_seconds=ttl_seconds or self._default_ttl_seconds,
            )

    async def get_latest_spread(self, symbol: str) -> dict[str, Any] | None:
        """Retrieve the latest cached spread for a symbol."""
        async with self._lock:
            snapshot = self._spreads.get(symbol.upper())
            if snapshot is None:
                self._misses += 1
                return None
            if self._is_expired(snapshot):
                del self._spreads[symbol.upper()]
                self._expired_entries += 1
                self._misses += 1
                return None
            self._hits += 1
            return snapshot.payload

    # ─── Cache Management ─────────────────────────────────────

    async def invalidate_symbol(self, symbol: str) -> int:
        """Invalidate all cached entries for a symbol.

        Args:
            symbol: Symbol to invalidate.

        Returns:
            Number of entries invalidated.
        """
        async with self._lock:
            key = symbol.upper()
            count = 0
            count += 1 if self._ticks.pop(key, None) is not None else 0
            count += 1 if self._spreads.pop(key, None) is not None else 0
            if key in self._ohlc:
                count += len(self._ohlc[key])
                del self._ohlc[key]
            return count

    async def clear(self) -> int:
        """Clear all cached entries.

        Returns:
            Total number of entries cleared.
        """
        async with self._lock:
            count = (
                len(self._ticks)
                + len(self._spreads)
                + sum(len(timeframes) for timeframes in self._ohlc.values())
            )
            self._ticks.clear()
            self._ohlc.clear()
            self._spreads.clear()
            return count

    async def get_metrics(self) -> CacheMetrics:
        """Return current cache performance metrics."""
        async with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            entries = (
                len(self._ticks)
                + len(self._spreads)
                + sum(len(timeframes) for timeframes in self._ohlc.values())
            )
            return CacheMetrics(
                hits=self._hits,
                misses=self._misses,
                hit_rate=hit_rate,
                entries=entries,
                expired_entries=self._expired_entries,
            )

    async def get_hit_rate_event(self) -> CacheHitRateEvent:
        """Return a CacheHitRateEvent with current metrics."""
        metrics = await self.get_metrics()
        return CacheHitRateEvent.create(
            cache_name="market_snapshot",
            hits=metrics.hits,
            misses=metrics.misses,
        )

    def _is_expired(self, snapshot: CachedSnapshot) -> bool:
        """Check if a cached snapshot has expired."""
        age = datetime.now(timezone.utc) - snapshot.cached_at
        return age > timedelta(seconds=snapshot.ttl_seconds)
