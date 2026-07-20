"""Provider synchronization engine for real-time data alignment."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from libraries.domain.market_intelligence.models import ProviderTickData


@dataclass(frozen=True, slots=True)
class ProviderSynchronizationState:
    """Current synchronization state for a provider."""

    provider: str
    symbol: str
    last_timestamp: datetime | None = None
    last_sequence: int | None = None
    gap_detected: bool = False
    gap_duration_ms: float = 0.0
    sequence_gap_count: int = 0
    clock_offset_ms: float = 0.0
    is_synchronized: bool = False
    last_sync_time: datetime | None = None


class SynchronizationEngine:
    """Ensures tick data from multiple providers is properly synchronized.

    Detects gaps, sequence breaks, and out-of-order delivery.
    Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        max_timestamp_gap_ms: float = 500.0,
        max_sequence_gap: int = 1,
    ) -> None:
        if max_timestamp_gap_ms <= 0:
            raise ValueError("max_timestamp_gap_ms must be positive")
        if max_sequence_gap <= 0:
            raise ValueError("max_sequence_gap must be positive")
        self._max_timestamp_gap_ms = max_timestamp_gap_ms
        self._max_sequence_gap = max_sequence_gap
        self._lock = asyncio.Lock()
        self._states: dict[str, ProviderSynchronizationState] = {}
        self._total_gaps_detected: int = 0
        self._total_out_of_order: int = 0

    @property
    def max_timestamp_gap_ms(self) -> float:
        return self._max_timestamp_gap_ms

    @property
    def max_sequence_gap(self) -> int:
        return self._max_sequence_gap

    async def process_tick(
        self,
        tick: ProviderTickData,
    ) -> ProviderSynchronizationState:
        """Process a tick and return the updated sync state.

        Detects gaps, sequence breaks, and out-of-order delivery.
        """
        key = f"{tick.provider}:{tick.symbol}"
        async with self._lock:
            current = self._states.get(key)

            if current is None:
                state = ProviderSynchronizationState(
                    provider=tick.provider,
                    symbol=tick.symbol,
                    last_timestamp=tick.timestamp,
                    last_sequence=tick.sequence,
                    is_synchronized=True,
                    last_sync_time=datetime.now(timezone.utc),
                )
                self._states[key] = state
                return state

            gap_detected = False
            gap_duration_ms = 0.0
            sequence_gap_count = current.sequence_gap_count

            # Check timestamp gap
            if current.last_timestamp is not None:
                ts_diff = (tick.timestamp - current.last_timestamp).total_seconds() * 1000.0
                if ts_diff > self._max_timestamp_gap_ms:
                    gap_detected = True
                    gap_duration_ms = ts_diff
                    self._total_gaps_detected += 1

                # Check out-of-order delivery
                if ts_diff < 0:
                    self._total_out_of_order += 1

            # Check sequence gap
            if (
                tick.sequence is not None
                and current.last_sequence is not None
                and tick.sequence <= current.last_sequence
            ):
                sequence_gap_count += 1

            state = ProviderSynchronizationState(
                provider=tick.provider,
                symbol=tick.symbol,
                last_timestamp=tick.timestamp,
                last_sequence=tick.sequence,
                gap_detected=gap_detected,
                gap_duration_ms=round(gap_duration_ms, 3),
                sequence_gap_count=sequence_gap_count,
                clock_offset_ms=tick.latency_ms,
                is_synchronized=not gap_detected,
                last_sync_time=(
                    datetime.now(timezone.utc) if not gap_detected else current.last_sync_time
                ),
            )
            self._states[key] = state
            return state

    async def get_state(
        self,
        provider: str,
        symbol: str,
    ) -> ProviderSynchronizationState | None:
        """Get the current sync state for a provider/symbol pair."""
        async with self._lock:
            return self._states.get(f"{provider}:{symbol}")

    async def get_all_states(self) -> list[ProviderSynchronizationState]:
        """Return all current synchronization states."""
        async with self._lock:
            return list(self._states.values())

    async def is_synchronized(self, provider: str, symbol: str) -> bool:
        """Check if a provider/symbol is currently synchronized."""
        state = await self.get_state(provider, symbol)
        return state.is_synchronized if state else True

    async def reset(self) -> None:
        """Reset the synchronization engine."""
        async with self._lock:
            self._states.clear()
            self._total_gaps_detected = 0
            self._total_out_of_order = 0
