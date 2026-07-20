"""Health monitoring for the event streaming layer.

Exposes comprehensive health status including queue depth, connected
providers, last tick timestamps, throughput, latency, errors, and
buffer usage.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class HealthStatus:
    """Immutable health status snapshot."""

    healthy: bool
    queue_depth: int
    queue_max_size: int
    connected_providers: int
    last_tick_time: str | None
    ticks_per_second: float
    events_per_second: float
    queue_latency_ms: float
    processing_latency_ms: float
    buffer_usage_pct: float
    total_errors: int
    cache_hit_rate: float
    providers: dict[str, bool]
    details: dict[str, Any] = field(default_factory=dict)
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "healthy": self.healthy,
            "queue_depth": self.queue_depth,
            "queue_max_size": self.queue_max_size,
            "connected_providers": self.connected_providers,
            "last_tick_time": self.last_tick_time,
            "ticks_per_second": self.ticks_per_second,
            "events_per_second": self.events_per_second,
            "queue_latency_ms": self.queue_latency_ms,
            "processing_latency_ms": self.processing_latency_ms,
            "buffer_usage_pct": self.buffer_usage_pct,
            "total_errors": self.total_errors,
            "cache_hit_rate": self.cache_hit_rate,
            "providers": self.providers,
            "details": self.details,
            "checked_at": self.checked_at,
        }


class StreamHealth:
    """Health monitor for the streaming layer.

    Aggregates health information from all streaming components and
    provides a unified health status report.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._queue_depth: int = 0
        self._queue_max_size: int = 0
        self._connected_providers: set[str] = set()
        self._disconnected_providers: set[str] = set()
        self._last_tick_time: datetime | None = None
        self._ticks_per_second: float = 0.0
        self._events_per_second: float = 0.0
        self._queue_latency_ms: float = 0.0
        self._processing_latency_ms: float = 0.0
        self._buffer_usage_pct: float = 0.0
        self._total_errors: int = 0
        self._cache_hit_rate: float = 0.0
        self._tick_count: int = 0
        self._tick_window_start: float = 0.0
        self._event_count: int = 0
        self._event_window_start: float = 0.0

    async def set_queue_depth(self, depth: int, max_size: int) -> None:
        """Update queue depth information."""
        async with self._lock:
            self._queue_depth = depth
            self._queue_max_size = max_size
            self._buffer_usage_pct = (depth / max_size * 100) if max_size > 0 else 0.0

    async def set_provider_connected(self, provider: str) -> None:
        """Mark a provider as connected."""
        async with self._lock:
            self._connected_providers.add(provider)
            self._disconnected_providers.discard(provider)

    async def set_provider_disconnected(self, provider: str) -> None:
        """Mark a provider as disconnected."""
        async with self._lock:
            self._disconnected_providers.add(provider)
            self._connected_providers.discard(provider)

    async def record_tick(self) -> None:
        """Record a tick receipt for throughput calculation."""
        async with self._lock:
            self._last_tick_time = datetime.now(timezone.utc)
            self._tick_count += 1

    async def record_event(self) -> None:
        """Record an event dispatch for throughput calculation."""
        async with self._lock:
            self._event_count += 1

    async def record_error(self) -> None:
        """Record an error occurrence."""
        async with self._lock:
            self._total_errors += 1

    async def set_cache_hit_rate(self, hit_rate: float) -> None:
        """Update the cache hit rate."""
        async with self._lock:
            self._cache_hit_rate = hit_rate

    async def set_queue_latency(self, latency_ms: float) -> None:
        """Update queue latency measurement."""
        async with self._lock:
            self._queue_latency_ms = latency_ms

    async def set_processing_latency(self, latency_ms: float) -> None:
        """Update processing latency measurement."""
        async with self._lock:
            self._processing_latency_ms = latency_ms

    async def get_health(self) -> HealthStatus:
        """Return a comprehensive health status snapshot."""
        async with self._lock:
            # Compute throughput
            import time

            now = time.monotonic()

            if self._tick_window_start == 0.0:
                self._tick_window_start = now
            tick_elapsed = now - self._tick_window_start
            if tick_elapsed >= 1.0:
                self._ticks_per_second = (
                    self._tick_count / tick_elapsed if tick_elapsed > 0 else 0.0
                )
                self._tick_count = 0
                self._tick_window_start = now

            if self._event_window_start == 0.0:
                self._event_window_start = now
            event_elapsed = now - self._event_window_start
            if event_elapsed >= 1.0:
                self._events_per_second = (
                    self._event_count / event_elapsed if event_elapsed > 0 else 0.0
                )
                self._event_count = 0
                self._event_window_start = now

            providers: dict[str, bool] = {}
            for p in self._connected_providers:
                providers[p] = True
            for p in self._disconnected_providers:
                providers[p] = False

            total_providers = len(self._connected_providers) + len(self._disconnected_providers)
            healthy = (
                self._queue_depth < self._queue_max_size * 0.9 if self._queue_max_size > 0 else True
            ) and self._total_errors < 100

            return HealthStatus(
                healthy=healthy,
                queue_depth=self._queue_depth,
                queue_max_size=self._queue_max_size,
                connected_providers=len(self._connected_providers),
                last_tick_time=(self._last_tick_time.isoformat() if self._last_tick_time else None),
                ticks_per_second=self._ticks_per_second,
                events_per_second=self._events_per_second,
                queue_latency_ms=self._queue_latency_ms,
                processing_latency_ms=self._processing_latency_ms,
                buffer_usage_pct=self._buffer_usage_pct,
                total_errors=self._total_errors,
                cache_hit_rate=self._cache_hit_rate,
                providers=providers,
            )

    async def reset(self) -> None:
        """Reset all health metrics."""
        async with self._lock:
            self._queue_depth = 0
            self._queue_max_size = 0
            self._connected_providers.clear()
            self._disconnected_providers.clear()
            self._last_tick_time = None
            self._ticks_per_second = 0.0
            self._events_per_second = 0.0
            self._queue_latency_ms = 0.0
            self._processing_latency_ms = 0.0
            self._buffer_usage_pct = 0.0
            self._total_errors = 0
            self._cache_hit_rate = 0.0
            self._tick_count = 0
            self._tick_window_start = 0.0
            self._event_count = 0
            self._event_window_start = 0.0
