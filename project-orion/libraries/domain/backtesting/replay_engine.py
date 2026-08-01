"""Replay engine for backtesting.

Provides deterministic replay of historical market data including
tick replay, candle replay, order replay, trade replay, and market replay.
Supports speed control, pause, resume, seek, and reverse replay.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.backtesting.event_scheduler import EventScheduler, ScheduledEvent
from libraries.domain.backtesting.exceptions import ReplayError, ReplaySeekError, ReplayStateError
from libraries.domain.backtesting.historical_data import HistoricalDataProvider
from libraries.domain.backtesting.models import ReplayMode, ReplayState, Timeframe


@dataclass(frozen=True, slots=True)
class ReplayEngineConfig:
    """Configuration for the replay engine."""

    replay_mode: ReplayMode = ReplayMode.CANDLE
    timeframe: Timeframe = Timeframe.M1
    speed_multiplier: float = 1.0
    start_date: datetime | None = None
    end_date: datetime | None = None
    symbols: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


class ReplayEventHandler:
    """Handler for replay events."""

    async def on_candle(
        self,
        symbol: str,
        timestamp: datetime,
        open_price: Decimal,
        high: Decimal,
        low: Decimal,
        close: Decimal,
        volume: Decimal,
    ) -> None: ...

    async def on_tick(
        self,
        symbol: str,
        timestamp: datetime,
        bid: Decimal,
        ask: Decimal,
    ) -> None: ...

    async def on_order(self, order_data: dict[str, Any]) -> None: ...

    async def on_trade(self, trade_data: dict[str, Any]) -> None: ...

    async def on_event(self, event: ScheduledEvent) -> None: ...


class ReplayEngine:
    """Engine for deterministic replay of historical data.

    Supports multiple replay modes with full control over playback.
    """

    def __init__(
        self,
        config: ReplayEngineConfig | None = None,
        data_provider: HistoricalDataProvider | None = None,
        event_scheduler: EventScheduler | None = None,
    ) -> None:
        """Initialize replay engine.

        Args:
            config: Replay engine configuration.
            data_provider: Historical data provider.
            event_scheduler: Event scheduler for scenario events.
        """
        self._config = config or ReplayEngineConfig()
        self._data_provider = data_provider
        self._event_scheduler = event_scheduler or EventScheduler()
        self._state = ReplayState.IDLE
        self._position = 0
        self._data: list[dict[str, Any]] = []
        self._current_timestamp: datetime | None = None
        self._speed: float = self._config.speed_multiplier
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._stop_requested = False
        self._handlers: list[ReplayEventHandler] = []
        self._reverse = False

    @property
    def state(self) -> ReplayState:
        return self._state

    @property
    def position(self) -> int:
        return self._position

    @property
    def total_items(self) -> int:
        return len(self._data)

    @property
    def progress(self) -> float:
        if not self._data:
            return 0.0
        return self._position / len(self._data)

    @property
    def current_timestamp(self) -> datetime | None:
        return self._current_timestamp

    def add_handler(self, handler: ReplayEventHandler) -> None:
        """Add a replay event handler.

        Args:
            handler: Handler to add.
        """
        self._handlers.append(handler)

    def remove_handler(self, handler: ReplayEventHandler) -> None:
        """Remove a replay event handler.

        Args:
            handler: Handler to remove.
        """
        if handler in self._handlers:
            self._handlers.remove(handler)

    async def load_data(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> None:
        """Load data for replay.

        Args:
            symbol: Trading symbol.
            start: Start timestamp.
            end: End timestamp.
        """
        if not self._data_provider:
            raise ReplayError("No data provider configured")

        cfg = self._config
        start_dt = start or cfg.start_date or datetime.now(timezone.utc) - timedelta(days=30)
        end_dt = end or cfg.end_date or datetime.now(timezone.utc)

        if cfg.replay_mode == ReplayMode.CANDLE:
            candles = await self._data_provider.load_candles(
                symbol, cfg.timeframe, start_dt.date(), end_dt.date()
            )
            self._data = candles
        elif cfg.replay_mode == ReplayMode.TICK:
            ticks = await self._data_provider.load_ticks(symbol, start_dt.date(), end_dt.date())
            self._data = ticks
        else:
            raise ReplayError(f"Unsupported replay mode: {cfg.replay_mode}")

        self._data.sort(key=lambda x: x["timestamp"])
        self._position = 0
        self._state = ReplayState.IDLE

    async def start(self) -> None:
        """Start replay."""
        if self._state == ReplayState.PLAYING:
            return
        if not self._data:
            raise ReplayError("No data loaded for replay")

        self._state = ReplayState.PLAYING
        self._stop_requested = False
        self._pause_event.set()

    async def play(self) -> None:
        """Run the replay loop."""
        await self.start()

        while self._state == ReplayState.PLAYING and not self._stop_requested:
            await self._pause_event.wait()

            if self._position >= len(self._data) or self._position < 0:
                self._state = ReplayState.COMPLETED
                break

            item = self._data[self._position]
            self._current_timestamp = item["timestamp"]

            await self._dispatch_item(item)

            if self._reverse:
                self._position -= 1
            else:
                self._position += 1

            # Speed control
            if self._speed > 0:
                await asyncio.sleep(0.001 / self._speed)

    async def pause(self) -> None:
        """Pause replay."""
        if self._state != ReplayState.PLAYING:
            raise ReplayStateError("Cannot pause: not playing")
        self._state = ReplayState.PAUSED
        self._pause_event.clear()

    async def resume(self) -> None:
        """Resume replay."""
        if self._state != ReplayState.PAUSED:
            raise ReplayStateError("Cannot resume: not paused")
        self._state = ReplayState.PLAYING
        self._pause_event.set()

    async def stop(self) -> None:
        """Stop replay."""
        self._state = ReplayState.STOPPED
        self._stop_requested = True
        self._pause_event.set()

    async def seek(self, timestamp: datetime) -> bool:
        """Seek to a specific timestamp.

        Args:
            timestamp: Target timestamp.

        Returns:
            True if seek was successful.
        """
        if not self._data:
            raise ReplaySeekError("No data loaded")

        for i, item in enumerate(self._data):
            if item["timestamp"] >= timestamp:
                self._position = i
                self._current_timestamp = timestamp
                return True

        return False

    def set_speed(self, multiplier: float) -> None:
        """Set replay speed multiplier.

        Args:
            multiplier: Speed multiplier (1.0 = real-time).
        """
        if multiplier <= 0:
            raise ReplayError(f"Invalid speed: {multiplier}")
        self._speed = multiplier

    def set_reverse(self, enabled: bool) -> None:
        """Enable or disable reverse replay.

        Args:
            enabled: True for reverse replay.
        """
        self._reverse = enabled

    async def reset(self) -> None:
        """Reset replay to initial state."""
        self._state = ReplayState.IDLE
        self._position = 0
        self._current_timestamp = None
        self._stop_requested = False
        self._pause_event.set()

    async def _dispatch_item(self, item: dict[str, Any]) -> None:
        """Dispatch a data item to all handlers.

        Args:
            item: Data item to dispatch.
        """
        cfg = self._config

        # Check for scheduled events
        if self._current_timestamp and self._event_scheduler:
            events = self._event_scheduler.get_events_at(self._current_timestamp)
            for event in events:
                for handler in self._handlers:
                    await handler.on_event(event)

        if cfg.replay_mode == ReplayMode.CANDLE:
            for handler in self._handlers:
                await handler.on_candle(
                    symbol=item.get("symbol", ""),
                    timestamp=item["timestamp"],
                    open_price=item["open"],
                    high=item["high"],
                    low=item["low"],
                    close=item["close"],
                    volume=item.get("volume", Decimal("0")),
                )
        elif cfg.replay_mode == ReplayMode.TICK:
            for handler in self._handlers:
                await handler.on_tick(
                    symbol=item.get("symbol", ""),
                    timestamp=item["timestamp"],
                    bid=item["bid"],
                    ask=item["ask"],
                )
