"""Rolling statistics engine with configurable windows."""

from __future__ import annotations

import asyncio
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class StatisticsConfig:
    """Configuration for rolling statistics."""

    window_size: int = 100
    min_samples: int = 2


@dataclass(frozen=True, slots=True)
class StatisticsSnapshot:
    """Immutable snapshot of rolling statistics."""

    count: int
    mean: float
    std: float
    variance: float
    minimum: float
    maximum: float
    median: float
    p50: float
    p95: float
    p99: float
    sum: float
    last: float
    window_size: int


class RollingStatistics:
    """Maintain rolling statistics over a configurable window.

    Thread-safe via asyncio.Lock. Supports configurable window sizes.
    """

    def __init__(self, config: StatisticsConfig | None = None) -> None:
        self._config = config or StatisticsConfig()
        self._values: deque[float] = deque(maxlen=self._config.window_size)
        self._lock = asyncio.Lock()
        self._last_update: datetime | None = None
        self._total_sum: float = 0.0
        self._total_count: int = 0

    @property
    def config(self) -> StatisticsConfig:
        return self._config

    @property
    def count(self) -> int:
        return len(self._values)

    @property
    def total_count(self) -> int:
        return self._total_count

    async def add(self, value: float) -> None:
        """Add a value to the rolling window."""
        async with self._lock:
            if self._values and len(self._values) == self._values.maxlen:
                removed = self._values[0]
                self._total_sum -= removed
            self._values.append(value)
            self._total_sum += value
            self._total_count += 1
            self._last_update = datetime.now(timezone.utc)

    async def add_many(self, values: list[float]) -> None:
        """Add multiple values at once."""
        for v in values:
            await self.add(v)

    async def get_snapshot(self) -> StatisticsSnapshot:
        """Compute and return a statistics snapshot."""
        async with self._lock:
            vals = list(self._values)
            count = len(vals)

            if count == 0:
                return StatisticsSnapshot(
                    count=0,
                    mean=0.0,
                    std=0.0,
                    variance=0.0,
                    minimum=0.0,
                    maximum=0.0,
                    median=0.0,
                    p50=0.0,
                    p95=0.0,
                    p99=0.0,
                    sum=0.0,
                    last=0.0,
                    window_size=self._config.window_size,
                )

            sorted_vals = sorted(vals)
            mean = self._total_sum / count if count > 0 else 0.0

            variance = sum((x - mean) ** 2 for x in vals) / count
            std = math.sqrt(variance)

            minimum = sorted_vals[0]
            maximum = sorted_vals[-1]
            last = vals[-1]

            def percentile(sorted_data: list[float], p: float) -> float:
                k = (len(sorted_data) - 1) * p / 100.0
                f = math.floor(k)
                c = math.ceil(k)
                if f == c:
                    return sorted_data[int(k)]
                return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)

            median = percentile(sorted_vals, 50.0)
            p50 = percentile(sorted_vals, 50.0)
            p95 = percentile(sorted_vals, 95.0)
            p99 = percentile(sorted_vals, 99.0)

            return StatisticsSnapshot(
                count=count,
                mean=round(mean, 6),
                std=round(std, 6),
                variance=round(variance, 6),
                minimum=minimum,
                maximum=maximum,
                median=round(median, 6),
                p50=round(p50, 6),
                p95=round(p95, 6),
                p99=round(p99, 6),
                sum=round(self._total_sum, 6),
                last=last,
                window_size=self._config.window_size,
            )

    async def clear(self) -> None:
        """Clear all collected data."""
        async with self._lock:
            self._values.clear()
            self._total_sum = 0.0
            self._total_count = 0
            self._last_update = None

    async def is_significant(self, threshold: int = 2) -> bool:
        """Return whether we have at least threshold samples."""
        snap = await self.get_snapshot()
        return snap.count >= threshold

    async def z_score(self, value: float) -> float:
        """Compute the z-score of a value relative to the current distribution."""
        snap = await self.get_snapshot()
        if snap.count < 2 or snap.std == 0.0:
            return 0.0
        return (value - snap.mean) / snap.std
