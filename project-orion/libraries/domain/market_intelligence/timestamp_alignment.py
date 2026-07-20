"""Timestamp alignment engine for multi-provider synchronization."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any


class AlignmentStrategy(StrEnum):
    """Strategy for aligning timestamps across providers."""

    EXACT = "exact"
    NEAREST = "nearest"
    INTERPOLATE = "interpolate"
    AVERAGE = "average"


@dataclass(frozen=True, slots=True)
class AlignedTick:
    """A timestamp-aligned tick from a provider."""

    provider: str
    symbol: str
    original_timestamp: datetime
    aligned_timestamp: datetime
    bid: float
    ask: float
    offset_ms: float
    strategy: AlignmentStrategy


class TimestampAlignmentEngine:
    """Aligns timestamps from multiple providers for fair comparison.

    Handles clock drift, network delays, and different timestamp sources.
    Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        max_offset_ms: float = 100.0,
        strategy: AlignmentStrategy = AlignmentStrategy.NEAREST,
    ) -> None:
        if max_offset_ms <= 0:
            raise ValueError("max_offset_ms must be positive")
        self._max_offset_ms = max_offset_ms
        self._strategy = strategy
        self._lock = asyncio.Lock()
        self._clock_drifts: dict[str, float] = {}
        self._total_drift_adjustments: int = 0

    @property
    def max_offset_ms(self) -> float:
        return self._max_offset_ms

    @property
    def strategy(self) -> AlignmentStrategy:
        return self._strategy

    async def align_tick(
        self,
        provider: str,
        symbol: str,
        provider_timestamp: datetime,
        local_received_at: datetime,
        bid: float,
        ask: float,
    ) -> AlignedTick:
        """Align a single tick timestamp.

        Computes clock drift offset and produces an aligned timestamp.
        """
        async with self._lock:
            # Compute drift: difference between provider time and local time
            drift = (provider_timestamp - local_received_at).total_seconds() * 1000.0

            # Update rolling drift estimate
            if provider in self._clock_drifts:
                alpha = 0.3
                prev = self._clock_drifts[provider]
                self._clock_drifts[provider] = alpha * drift + (1 - alpha) * prev
            else:
                self._clock_drifts[provider] = drift

            self._total_drift_adjustments += 1

            # Apply alignment
            drift_ms = self._clock_drifts[provider]

            if self._strategy == AlignmentStrategy.EXACT:
                # Use the provider timestamp as-is (assumes synchronized clocks)
                aligned_ts = provider_timestamp
                offset = 0.0
            elif self._strategy == AlignmentStrategy.NEAREST:
                # Adjust by drift estimate
                adjusted = provider_timestamp - timedelta(milliseconds=drift_ms)
                aligned_ts = adjusted
                offset = drift_ms
            elif self._strategy == AlignmentStrategy.AVERAGE:
                # Average of provider and local time
                avg_dt = provider_timestamp + (local_received_at - provider_timestamp) / 2
                aligned_ts = avg_dt
                offset = drift_ms / 2.0
            else:  # INTERPOLATE
                # Interpolate between provider and local time
                weight = 0.5
                interpolated = (
                    provider_timestamp + (local_received_at - provider_timestamp) * weight
                )
                aligned_ts = interpolated
                offset = drift_ms * weight

            return AlignedTick(
                provider=provider,
                symbol=symbol,
                original_timestamp=provider_timestamp,
                aligned_timestamp=aligned_ts,
                bid=bid,
                ask=ask,
                offset_ms=round(offset, 3),
                strategy=self._strategy,
            )

    async def get_drift(self, provider: str) -> float:
        """Return the estimated clock drift for a provider in ms."""
        async with self._lock:
            return self._clock_drifts.get(provider, 0.0)

    async def reset_drift(self, provider: str) -> None:
        """Reset drift estimate for a provider."""
        async with self._lock:
            self._clock_drifts.pop(provider, None)

    async def get_all_drifts(self) -> dict[str, float]:
        """Return all drift estimates."""
        async with self._lock:
            return dict(self._clock_drifts)
