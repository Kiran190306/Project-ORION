"""Indicator Cache.

Provides caching for indicator results with:
- Rolling window support
- TTL-based expiry
- Symbol and timeframe scoped caching
- Incremental reuse (cache-aside pattern)

Thread-safe via asyncio.Lock. No global state - instances created via DI.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from libraries.domain.indicators.models import Bar, IndicatorResult


@dataclass(frozen=True, slots=True)
class IndicatorCacheConfig:
    """Configuration for the indicator cache."""

    default_ttl_seconds: int = 300  # 5 minutes
    max_entries_per_indicator: int = 1000
    enable_stats: bool = True
    cleanup_interval_seconds: int = 60


@dataclass
class CachedEntry:
    """A cached indicator result with metadata."""

    result: IndicatorResult
    cached_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: int = 300
    access_count: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        elapsed = (datetime.now(timezone.utc) - self.cached_at).total_seconds()
        return elapsed > self.ttl_seconds


class IndicatorCache:
    """Cache for indicator results.

    Caches IndicatorResult objects with configurable TTL, scoped
    by symbol and timeframe. Supports incremental reuse where
    cached results are returned when the underlying data hasn't changed.
    """

    def __init__(self, config: IndicatorCacheConfig | None = None) -> None:
        self._config = config or IndicatorCacheConfig()
        # Key structure: f"{symbol}:{timeframe}:{indicator_name}:{bar_timestamp}"
        self._cache: dict[str, CachedEntry] = {}
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
        self._last_cleanup = time.monotonic()

    def _make_key(
        self,
        indicator_name: str,
        symbol: str = "",
        timeframe: str = "",
        bar_key: str = "",
    ) -> str:
        return f"{symbol}:{timeframe}:{indicator_name}:{bar_key}"

    def _get_bar_key(self, bar: Bar) -> str:
        """Generate a cache key from a bar."""
        ts = (
            bar.timestamp.isoformat() if hasattr(bar.timestamp, "isoformat") else str(bar.timestamp)
        )
        return f"{ts}:{bar.close}:{bar.high}:{bar.low}:{bar.volume}"

    async def _cleanup_expired(self) -> None:
        """Remove expired entries from the cache."""
        now = time.monotonic()
        if now - self._last_cleanup < self._config.cleanup_interval_seconds:
            return
        self._last_cleanup = now

        async with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if entry.is_expired]
            for key in expired_keys:
                del self._cache[key]

    async def get(
        self,
        indicator_name: str,
        bar: Bar,
        symbol: str = "",
        timeframe: str = "",
    ) -> IndicatorResult | None:
        """Get a cached result for an indicator and bar.

        Args:
            indicator_name: Name of the indicator.
            bar: Current bar data.
            symbol: Trading symbol.
            timeframe: Timeframe string.

        Returns:
            Cached IndicatorResult if found and valid, None otherwise.
        """
        await self._cleanup_expired()

        key = self._make_key(
            indicator_name,
            symbol=symbol or bar.symbol,
            timeframe=timeframe,
            bar_key=self._get_bar_key(bar),
        )

        async with self._lock:
            entry = self._cache.get(key)
            if entry is None or entry.is_expired:
                self._misses += 1
                return None

            entry.access_count += 1
            self._hits += 1
            return entry.result

    async def set(
        self,
        indicator_name: str,
        bar: Bar,
        result: IndicatorResult,
        symbol: str = "",
        timeframe: str = "",
        ttl_seconds: int | None = None,
    ) -> None:
        """Cache a result for an indicator and bar.

        Args:
            indicator_name: Name of the indicator.
            bar: Current bar data.
            result: The indicator result to cache.
            symbol: Trading symbol.
            timeframe: Timeframe string.
            ttl_seconds: Optional TTL override (defaults to config).
        """
        key = self._make_key(
            indicator_name,
            symbol=symbol or bar.symbol,
            timeframe=timeframe,
            bar_key=self._get_bar_key(bar),
        )

        entry = CachedEntry(
            result=result,
            ttl_seconds=ttl_seconds or self._config.default_ttl_seconds,
        )

        async with self._lock:
            # Enforce max entries per indicator
            prefix = f"{symbol or bar.symbol}:{timeframe}:{indicator_name}:"
            indicator_keys = [k for k in self._cache if k.startswith(prefix)]

            if len(indicator_keys) >= self._config.max_entries_per_indicator:
                # Remove oldest entry
                oldest_key = min(
                    indicator_keys,
                    key=lambda k: self._cache[k].cached_at,
                )
                del self._cache[oldest_key]

            self._cache[key] = entry

    async def invalidate(
        self,
        indicator_name: str | None = None,
        symbol: str | None = None,
        timeframe: str | None = None,
    ) -> int:
        """Invalidate cached entries matching criteria.

        Args:
            indicator_name: Optional indicator name filter.
            symbol: Optional symbol filter.
            timeframe: Optional timeframe filter.

        Returns:
            Number of invalidated entries.
        """
        async with self._lock:
            keys_to_delete: list[str] = []
            for key in self._cache:
                parts = key.split(":")
                key_symbol = parts[0]
                key_timeframe = parts[1]
                key_indicator = parts[2]

                if indicator_name and key_indicator != indicator_name:
                    continue
                if symbol and key_symbol != symbol:
                    continue
                if timeframe and key_timeframe != timeframe:
                    continue
                keys_to_delete.append(key)

            for key in keys_to_delete:
                del self._cache[key]

            return len(keys_to_delete)

    async def clear(self) -> None:
        """Clear all cached entries."""
        async with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache metrics.
        """
        async with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio": round(self._hits / total, 4) if total > 0 else 0.0,
                "config": {
                    "default_ttl_seconds": self._config.default_ttl_seconds,
                    "max_entries_per_indicator": self._config.max_entries_per_indicator,
                },
            }

    async def get_entry_count(self) -> int:
        """Get the total number of cached entries."""
        async with self._lock:
            return len(self._cache)
