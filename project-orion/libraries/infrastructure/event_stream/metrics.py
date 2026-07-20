"""Metrics collection for the event streaming layer.

Collects comprehensive streaming metrics including ticks/sec, events/sec,
queue latency, processing latency, provider uptime, disconnect/reconnect
counts, buffer drops, and cache hit ratio.

Follows the same pattern as broker_connectors/metrics.py.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class MetricSample:
    """A single metric data point."""

    kind: str
    name: str
    value: float | int | None
    tags: dict[str, str] | None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True, slots=True)
class StreamMetricSnapshot:
    """Complete snapshot of streaming metrics."""

    ticks_per_second: float
    events_per_second: float
    queue_latency_ms: float
    processing_latency_ms: float
    provider_uptime_seconds: dict[str, float]
    disconnect_count: int
    reconnect_count: int
    buffer_drops: int
    cache_hit_ratio: float
    total_published: int
    total_subscribed: int
    total_errors: int
    total_dead_letter: int
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StreamMetricsCollector:
    """Collects streaming layer metrics.

    All operations are thread-safe and async-compatible.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._samples: list[MetricSample] = []
        self._max_samples: int = 10000

        # Counters
        self._tick_count: int = 0
        self._event_count: int = 0
        self._disconnect_count: int = 0
        self._reconnect_count: int = 0
        self._buffer_drops: int = 0
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._total_published: int = 0
        self._total_subscribed: int = 0
        self._total_errors: int = 0
        self._total_dead_letter: int = 0

        # Latency tracking
        self._queue_latencies: list[float] = []
        self._processing_latencies: list[float] = []

        # Provider uptime tracking
        self._provider_start_times: dict[str, float] = {}
        self._provider_disconnect_count: dict[str, int] = {}
        self._provider_reconnect_count: dict[str, int] = {}

        # Throughput windows
        self._tick_window_start: float = 0.0
        self._tick_window_count: int = 0
        self._event_window_start: float = 0.0
        self._event_window_count: int = 0

    # ─── Recording Methods ────────────────────────────────────

    async def record_tick(self) -> None:
        """Record a received tick."""
        async with self._lock:
            now = time.monotonic()
            if self._tick_window_start == 0.0:
                self._tick_window_start = now
            self._tick_window_count += 1
            self._tick_count += 1

    async def record_event(self) -> None:
        """Record a dispatched event."""
        async with self._lock:
            now = time.monotonic()
            if self._event_window_start == 0.0:
                self._event_window_start = now
            self._event_window_count += 1
            self._event_count += 1

    async def record_queue_latency(self, latency_ms: float) -> None:
        """Record queue latency in milliseconds."""
        async with self._lock:
            self._queue_latencies.append(latency_ms)
            if len(self._queue_latencies) > 1000:
                self._queue_latencies = self._queue_latencies[-1000:]

    async def record_processing_latency(self, latency_ms: float) -> None:
        """Record processing latency in milliseconds."""
        async with self._lock:
            self._processing_latencies.append(latency_ms)
            if len(self._processing_latencies) > 1000:
                self._processing_latencies = self._processing_latencies[-1000:]

    async def record_disconnect(self, provider: str) -> None:
        """Record a provider disconnection."""
        async with self._lock:
            self._disconnect_count += 1
            self._provider_disconnect_count[provider] = (
                self._provider_disconnect_count.get(provider, 0) + 1
            )

    async def record_reconnect(self, provider: str) -> None:
        """Record a provider reconnection."""
        async with self._lock:
            self._reconnect_count += 1
            self._provider_reconnect_count[provider] = (
                self._provider_reconnect_count.get(provider, 0) + 1
            )
            self._provider_start_times[provider] = time.monotonic()

    async def record_buffer_drop(self) -> None:
        """Record a buffer drop event."""
        async with self._lock:
            self._buffer_drops += 1

    async def record_cache_hit(self) -> None:
        """Record a cache hit."""
        async with self._lock:
            self._cache_hits += 1

    async def record_cache_miss(self) -> None:
        """Record a cache miss."""
        async with self._lock:
            self._cache_misses += 1

    async def record_publish(self) -> None:
        """Record a published snapshot."""
        async with self._lock:
            self._total_published += 1

    async def record_subscribe(self) -> None:
        """Record a subscriber registration."""
        async with self._lock:
            self._total_subscribed += 1

    async def record_error(self) -> None:
        """Record an error occurrence."""
        async with self._lock:
            self._total_errors += 1

    async def record_dead_letter(self) -> None:
        """Record a dead-letter event."""
        async with self._lock:
            self._total_dead_letter += 1

    async def record_provider_start(self, provider: str) -> None:
        """Record provider start time for uptime tracking."""
        async with self._lock:
            self._provider_start_times[provider] = time.monotonic()
            self._provider_disconnect_count.setdefault(provider, 0)
            self._provider_reconnect_count.setdefault(provider, 0)

    # ─── Snapshot ─────────────────────────────────────────────

    async def snapshot(self) -> StreamMetricSnapshot:
        """Return a complete snapshot of current metrics."""
        async with self._lock:
            now = time.monotonic()

            # Compute throughput
            ticks_per_second = 0.0
            if self._tick_window_start > 0:
                elapsed = now - self._tick_window_start
                if elapsed >= 1.0:
                    ticks_per_second = self._tick_window_count / elapsed

            events_per_second = 0.0
            if self._event_window_start > 0:
                elapsed = now - self._event_window_start
                if elapsed >= 1.0:
                    events_per_second = self._event_window_count / elapsed

            # Average latencies
            queue_latency_ms = (
                sum(self._queue_latencies) / len(self._queue_latencies)
                if self._queue_latencies
                else 0.0
            )
            processing_latency_ms = (
                sum(self._processing_latencies) / len(self._processing_latencies)
                if self._processing_latencies
                else 0.0
            )

            # Provider uptime
            provider_uptime: dict[str, float] = {}
            for provider, start_time in self._provider_start_times.items():
                provider_uptime[provider] = now - start_time

            # Cache hit ratio
            total_cache = self._cache_hits + self._cache_misses
            cache_hit_ratio = self._cache_hits / total_cache if total_cache > 0 else 0.0

            return StreamMetricSnapshot(
                ticks_per_second=round(ticks_per_second, 2),
                events_per_second=round(events_per_second, 2),
                queue_latency_ms=round(queue_latency_ms, 2),
                processing_latency_ms=round(processing_latency_ms, 2),
                provider_uptime_seconds={k: round(v, 2) for k, v in provider_uptime.items()},
                disconnect_count=self._disconnect_count,
                reconnect_count=self._reconnect_count,
                buffer_drops=self._buffer_drops,
                cache_hit_ratio=round(cache_hit_ratio, 4),
                total_published=self._total_published,
                total_subscribed=self._total_subscribed,
                total_errors=self._total_errors,
                total_dead_letter=self._total_dead_letter,
            )

    async def reset(self) -> None:
        """Reset all metrics to their initial state."""
        async with self._lock:
            self._samples.clear()
            self._tick_count = 0
            self._event_count = 0
            self._disconnect_count = 0
            self._reconnect_count = 0
            self._buffer_drops = 0
            self._cache_hits = 0
            self._cache_misses = 0
            self._total_published = 0
            self._total_subscribed = 0
            self._total_errors = 0
            self._total_dead_letter = 0
            self._queue_latencies.clear()
            self._processing_latencies.clear()
            self._provider_start_times.clear()
            self._provider_disconnect_count.clear()
            self._provider_reconnect_count.clear()
            self._tick_window_start = 0.0
            self._tick_window_count = 0
            self._event_window_start = 0.0
            self._event_window_count = 0

    def get_samples(self) -> list[MetricSample]:
        """Return and clear recorded metric samples."""
        samples = list(self._samples)
        self._samples.clear()
        return samples

    def record_sample(
        self,
        kind: str,
        name: str,
        value: float | int | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Record an ad-hoc metric sample."""
        self._samples.append(MetricSample(kind=kind, name=name, value=value, tags=tags))
        if len(self._samples) > self._max_samples:
            self._samples = self._samples[-self._max_samples :]
