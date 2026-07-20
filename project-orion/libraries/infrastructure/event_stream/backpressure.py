"""Backpressure control for the event streaming layer.

Implements adaptive flow control to manage producer/consumer imbalance
using watermarks and dynamic throttling.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class BackpressureMode(StrEnum):
    """Operational mode for backpressure handling."""

    PAUSE_PRODUCER = "pause_producer"
    DROP_EVENTS = "drop_events"
    ADAPTIVE = "adaptive"


@dataclass(frozen=True, slots=True)
class FlowControlState:
    """Immutable snapshot of flow control state."""

    paused: bool
    current_depth: int
    high_water_mark: int
    low_water_mark: int
    mode: BackpressureMode
    total_pause_events: int
    total_resume_events: int
    total_throttled: int


class AdaptiveFlowController:
    """Adaptive flow control for managing producer/consumer imbalance.

    Monitors queue depth and automatically pauses/resumes producers
    based on configurable watermarks.

    Supports:
    - Pause producer when queue exceeds high water mark
    - Resume producer when queue drops below low water mark
    - Queue depth monitoring
    - Adaptive flow control (dynamic throttling)
    - Multiple backpressure modes
    """

    def __init__(
        self,
        high_water_mark: int = 8000,
        low_water_mark: int = 2000,
        mode: BackpressureMode = BackpressureMode.PAUSE_PRODUCER,
    ) -> None:
        if high_water_mark <= low_water_mark:
            raise ValueError("high_water_mark must be greater than low_water_mark")
        if low_water_mark < 0:
            raise ValueError("low_water_mark must be non-negative")
        if high_water_mark <= 0:
            raise ValueError("high_water_mark must be positive")

        self._high_water_mark = high_water_mark
        self._low_water_mark = low_water_mark
        self._mode = mode
        self._paused = False
        self._lock = asyncio.Lock()
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Initially not paused
        self._total_pause_events: int = 0
        self._total_resume_events: int = 0
        self._total_throttled: int = 0
        self._depth_readings: list[int] = []

    @property
    def high_water_mark(self) -> int:
        return self._high_water_mark

    @property
    def low_water_mark(self) -> int:
        return self._low_water_mark

    @property
    def mode(self) -> BackpressureMode:
        return self._mode

    @property
    def paused(self) -> bool:
        return self._paused

    async def update_depth(self, depth: int) -> None:
        """Update the monitored queue depth and adjust flow control.

        Args:
            depth: Current queue depth.
        """
        async with self._lock:
            self._depth_readings.append(depth)
            if len(self._depth_readings) > 100:
                self._depth_readings = self._depth_readings[-100:]

            if self._mode == BackpressureMode.DROP_EVENTS:
                return

            if self._mode == BackpressureMode.ADAPTIVE:
                await self._adaptive_control(depth)
                return

            # PAUSE_PRODUCER mode
            if depth >= self._high_water_mark and not self._paused:
                self._paused = True
                self._pause_event.clear()
                self._total_pause_events += 1
            elif depth <= self._low_water_mark and self._paused:
                self._paused = False
                self._pause_event.set()
                self._total_resume_events += 1

    async def _adaptive_control(self, depth: int) -> None:
        """Apply adaptive flow control based on queue depth.

        Uses a proportional control approach: the closer the depth is to
        the high water mark, the more aggressively we throttle.
        """
        if depth >= self._high_water_mark:
            if not self._paused:
                self._paused = True
                self._pause_event.clear()
                self._total_pause_events += 1
                self._total_throttled += 1
        elif depth <= self._low_water_mark:
            if self._paused:
                self._paused = False
                self._pause_event.set()
                self._total_resume_events += 1
        else:
            # Between watermarks: proportional throttling
            ratio = (depth - self._low_water_mark) / (self._high_water_mark - self._low_water_mark)
            if ratio > 0.7 and not self._paused:
                self._paused = True
                self._pause_event.clear()
                self._total_throttled += 1
            elif ratio < 0.3 and self._paused:
                self._paused = False
                self._pause_event.set()
                self._total_resume_events += 1

    async def wait_if_paused(self) -> None:
        """Block the producer if flow control is paused.

        This should be called by producers before sending an event.
        """
        if self._paused:
            self._total_throttled += 1
        await self._pause_event.wait()

    async def pause(self) -> None:
        """Manually pause the producer."""
        async with self._lock:
            if not self._paused:
                self._paused = True
                self._pause_event.clear()
                self._total_pause_events += 1

    async def resume(self) -> None:
        """Manually resume the producer."""
        async with self._lock:
            if self._paused:
                self._paused = False
                self._pause_event.set()
                self._total_resume_events += 1

    async def is_paused(self) -> bool:
        """Return whether producers are currently paused."""
        async with self._lock:
            return self._paused

    async def get_state(self) -> FlowControlState:
        """Return an immutable snapshot of the current flow control state."""
        async with self._lock:
            return FlowControlState(
                paused=self._paused,
                current_depth=self._depth_readings[-1] if self._depth_readings else 0,
                high_water_mark=self._high_water_mark,
                low_water_mark=self._low_water_mark,
                mode=self._mode,
                total_pause_events=self._total_pause_events,
                total_resume_events=self._total_resume_events,
                total_throttled=self._total_throttled,
            )

    async def compute_throttle_delay(self, depth: int) -> float:
        """Compute adaptive throttle delay based on queue depth.

        Returns:
            Delay in seconds (0 = no delay).
        """
        if depth >= self._high_water_mark:
            return 0.1
        if depth <= self._low_water_mark:
            return 0.0

        ratio = (depth - self._low_water_mark) / (self._high_water_mark - self._low_water_mark)
        return round(min(0.1, ratio * 0.05), 4)
