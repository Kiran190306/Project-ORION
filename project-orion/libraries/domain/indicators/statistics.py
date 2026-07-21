"""Indicator Statistics.

Tracks execution performance metrics for indicators:
- Execution count and latency
- Cache hit ratio
- Average calculation time
- Warmup count
- Last execution timestamp

Thread-safe via asyncio.Lock. No global state.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class IndicatorStats:
    """Per-indicator statistics snapshot."""

    name: str
    execution_count: int = 0
    total_latency: float = 0.0  # Total calculation time in seconds
    max_latency: float = 0.0
    min_latency: float = float("inf")
    cache_hits: int = 0
    cache_misses: int = 0
    warmup_count: int = 0
    last_execution: datetime | None = None
    error_count: int = 0
    last_error: str | None = None

    @property
    def avg_latency(self) -> float:
        """Average calculation time in milliseconds."""
        if self.execution_count == 0:
            return 0.0
        return (self.total_latency / self.execution_count) * 1000.0

    @property
    def cache_hit_ratio(self) -> float:
        """Cache hit ratio 0.0-1.0."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    def to_dict(self) -> dict[str, Any]:
        """Serialize statistics to a dictionary."""
        return {
            "name": self.name,
            "execution_count": self.execution_count,
            "avg_latency_ms": round(self.avg_latency, 4),
            "max_latency_ms": round(self.max_latency * 1000.0, 4),
            "min_latency_ms": round(
                self.min_latency * 1000.0 if self.min_latency != float("inf") else 0.0,
                4,
            ),
            "total_latency_s": round(self.total_latency, 4),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_ratio": round(self.cache_hit_ratio, 4),
            "warmup_count": self.warmup_count,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "error_count": self.error_count,
            "last_error": self.last_error,
        }


class IndicatorStatistics:
    """Tracks execution statistics for indicators.

    Collects and reports performance metrics.
    Each instance is independent - no global state.
    """

    def __init__(self) -> None:
        self._stats: dict[str, IndicatorStats] = {}
        self._lock = asyncio.Lock()

    async def record_execution(
        self,
        name: str,
        latency: float,
        cache_hit: bool = False,
        error: str | None = None,
    ) -> None:
        """Record an indicator execution.

        Args:
            name: Indicator name.
            latency: Execution time in seconds.
            cache_hit: Whether the result was served from cache.
            error: Error message if execution failed.
        """
        async with self._lock:
            stats = self._stats.setdefault(name, IndicatorStats(name=name))
            stats.execution_count += 1
            stats.total_latency += latency
            stats.max_latency = max(stats.max_latency, latency)
            stats.min_latency = min(stats.min_latency, latency)
            stats.last_execution = datetime.now(timezone.utc)

            if cache_hit:
                stats.cache_hits += 1
            else:
                stats.cache_misses += 1

            if error:
                stats.error_count += 1
                stats.last_error = error

    async def record_warmup(self, name: str) -> None:
        """Record a warmup execution.

        Args:
            name: Indicator name.
        """
        async with self._lock:
            stats = self._stats.setdefault(name, IndicatorStats(name=name))
            stats.warmup_count += 1

    async def get_stats(self, name: str) -> IndicatorStats | None:
        """Get stats for a specific indicator.

        Args:
            name: Indicator name.

        Returns:
            IndicatorStats if found, None otherwise.
        """
        async with self._lock:
            stats = self._stats.get(name)
            if stats is None:
                return None
            # Return a copy to preserve immutability
            return IndicatorStats(
                name=stats.name,
                execution_count=stats.execution_count,
                total_latency=stats.total_latency,
                max_latency=stats.max_latency,
                min_latency=stats.min_latency,
                cache_hits=stats.cache_hits,
                cache_misses=stats.cache_misses,
                warmup_count=stats.warmup_count,
                last_execution=stats.last_execution,
                error_count=stats.error_count,
                last_error=stats.last_error,
            )

    async def get_all_stats(self) -> dict[str, IndicatorStats]:
        """Get stats for all indicators.

        Returns:
            Dictionary mapping indicator name to stats.
        """
        async with self._lock:
            return {
                name: IndicatorStats(
                    name=s.name,
                    execution_count=s.execution_count,
                    total_latency=s.total_latency,
                    max_latency=s.max_latency,
                    min_latency=s.min_latency,
                    cache_hits=s.cache_hits,
                    cache_misses=s.cache_misses,
                    warmup_count=s.warmup_count,
                    last_execution=s.last_execution,
                    error_count=s.error_count,
                    last_error=s.last_error,
                )
                for name, s in self._stats.items()
            }

    async def reset(self, name: str | None = None) -> None:
        """Reset statistics for an indicator or all indicators.

        Args:
            name: Indicator name. If None, resets all.
        """
        async with self._lock:
            if name:
                self._stats.pop(name, None)
            else:
                self._stats.clear()

    async def summary(self) -> dict[str, Any]:
        """Get a summary of all statistics.

        Returns:
            Dictionary with aggregate metrics.
        """
        async with self._lock:
            if not self._stats:
                return {
                    "total_executions": 0,
                    "total_indicators": 0,
                    "avg_latency_ms": 0.0,
                    "overall_cache_hit_ratio": 0.0,
                    "total_errors": 0,
                }

            total_execs = sum(s.execution_count for s in self._stats.values())
            total_latency = sum(s.total_latency for s in self._stats.values())
            total_hits = sum(s.cache_hits for s in self._stats.values())
            total_misses = sum(s.cache_misses for s in self._stats.values())
            total_errors = sum(s.error_count for s in self._stats.values())

            return {
                "total_executions": total_execs,
                "total_indicators": len(self._stats),
                "avg_latency_ms": round(
                    (total_latency / total_execs * 1000.0) if total_execs > 0 else 0.0,
                    4,
                ),
                "overall_cache_hit_ratio": round(
                    (
                        total_hits / (total_hits + total_misses)
                        if (total_hits + total_misses) > 0
                        else 0.0
                    ),
                    4,
                ),
                "total_errors": total_errors,
            }
