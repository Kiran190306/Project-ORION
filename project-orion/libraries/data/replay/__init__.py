"""
Replay Module

Module Description:
This module provides replay engine foundation for data platform.
It handles deterministic replay of historical data for backtesting.

Implementation Checklist:
- [ ] Replay controller
- [ ] Tick generator
- [ ] Candle generator
- [ ] Speed controller
- [ ] Replay state management
- [ ] Replay checkpointing

Dependency Notes:
- Depends on: shared/ (errors), libraries/data/schemas/, libraries/data/datasets/
- Used by: backtesting/, paper-trading/
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Iterator, Optional, cast

from libraries.data.schemas import OHLC, Tick
from shared.errors import OrionError


class ReplayState(Enum):
    """Replay state enumeration."""

    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"


class ReplayError(OrionError):
    """Replay error."""

    pass


class ReplayController:
    """Controller for data replay."""

    def __init__(self) -> None:
        """Initialize replay controller."""
        self._state = ReplayState.IDLE
        self._current_position = 0
        self._data: list[Tick | OHLC] = []
        self._speed_multiplier = 1.0
        self._tick_callback: Optional[Callable[..., Any]] = None
        self._candle_callback: Optional[Callable[..., Any]] = None

    def load_data(self, data: list[Tick | OHLC]) -> None:
        """Load data for replay.

        Args:
            data: List of Tick or OHLC objects
        """
        self._data = sorted(data, key=lambda x: x.timestamp)
        self._current_position = 0
        self._state = ReplayState.IDLE

    def set_tick_callback(self, callback: Callable[..., Any]) -> None:
        """Set callback for tick events."""
        self._tick_callback = callback

    def set_candle_callback(self, callback: Callable[..., Any]) -> None:
        """Set callback for candle events."""
        self._candle_callback = callback

    def set_speed(self, multiplier: float) -> None:
        """Set replay speed multiplier.

        Args:
            multiplier: Speed multiplier (1.0 = real-time, 2.0 = 2x speed)
        """
        if multiplier <= 0:
            raise ReplayError(f"Invalid speed multiplier: {multiplier}")
        self._speed_multiplier = multiplier

    def start(self) -> None:
        """Start replay."""
        if self._state != ReplayState.IDLE and self._state != ReplayState.PAUSED:
            raise ReplayError(f"Cannot start replay from state: {self._state}")
        self._state = ReplayState.PLAYING

    def pause(self) -> None:
        """Pause replay."""
        if self._state != ReplayState.PLAYING:
            raise ReplayError(f"Cannot pause replay from state: {self._state}")
        self._state = ReplayState.PAUSED

    def stop(self) -> None:
        """Stop replay."""
        self._state = ReplayState.STOPPED
        self._current_position = 0

    def reset(self) -> None:
        """Reset replay to beginning."""
        self._state = ReplayState.IDLE
        self._current_position = 0

    def get_state(self) -> ReplayState:
        """Get current replay state."""
        return self._state

    def get_position(self) -> int:
        """Get current position in data."""
        return self._current_position

    def get_progress(self) -> float:
        """Get replay progress (0.0 to 1.0)."""
        if not self._data:
            return 0.0
        return self._current_position / len(self._data)

    def next(self) -> Tick | OHLC | None:
        """Get next data item."""
        if self._current_position >= len(self._data):
            self._state = ReplayState.COMPLETED
            return None

        item = self._data[self._current_position]
        self._current_position += 1

        # Call appropriate callback
        if isinstance(item, Tick) and self._tick_callback:
            self._tick_callback(item)
        elif isinstance(item, OHLC) and self._candle_callback:
            self._candle_callback(item)

        return item

    def seek(self, timestamp: datetime) -> bool:
        """Seek to specific timestamp."""
        # Find position with timestamp >= target
        for i, item in enumerate(self._data):
            if item.timestamp >= timestamp:
                self._current_position = i
                return True
        return False

    def checkpoint(self) -> dict[str, object]:
        """Create checkpoint of current replay state."""
        return {
            "state": self._state.value,
            "position": self._current_position,
            "speed_multiplier": self._speed_multiplier,
        }

    def restore_checkpoint(self, checkpoint: dict[str, object]) -> None:
        """Restore replay state from checkpoint."""
        self._state = ReplayState(cast(str, checkpoint["state"]))
        self._current_position = cast(int, checkpoint["position"])
        self._speed_multiplier = cast(float, checkpoint["speed_multiplier"])


class TickGenerator:
    """Generator for tick-based replay."""

    def __init__(self, ticks: list[Tick]) -> None:
        """Initialize tick generator.

        Args:
            ticks: List of Tick objects
        """
        self.ticks = sorted(ticks, key=lambda t: t.timestamp)
        self._index = 0

    def __iter__(self) -> Iterator[Tick]:
        """Iterate over ticks."""
        self._index = 0
        return self

    def __next__(self) -> Tick:
        """Get next tick."""
        if self._index >= len(self.ticks):
            raise StopIteration
        tick = self.ticks[self._index]
        self._index += 1
        return tick


class CandleGenerator:
    """Generator for candle-based replay."""

    def __init__(self, candles: list[OHLC]) -> None:
        """Initialize candle generator.

        Args:
            candles: List of OHLC objects
        """
        self.candles = sorted(candles, key=lambda c: c.timestamp)
        self._index = 0

    def __iter__(self) -> Iterator[OHLC]:
        """Iterate over candles."""
        self._index = 0
        return self

    def __next__(self) -> OHLC:
        """Get next candle."""
        if self._index >= len(self.candles):
            raise StopIteration
        candle = self.candles[self._index]
        self._index += 1
        return candle
