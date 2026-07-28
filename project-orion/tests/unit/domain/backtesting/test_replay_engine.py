"""Tests for EPIC-010 ReplayEngine — deterministic replay of historical data."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libraries.domain.backtesting.event_scheduler import EventScheduler, ScheduledEvent
from libraries.domain.backtesting.exceptions import (
    ReplayError,
    ReplaySeekError,
    ReplayStateError,
)
from libraries.domain.backtesting.historical_data import HistoricalDataProvider
from libraries.domain.backtesting.models import ReplayMode, ReplayState, Timeframe
from libraries.domain.backtesting.replay_engine import (
    ReplayEngine,
    ReplayEngineConfig,
    ReplayEventHandler,
)


class TestReplayEngineConfig:
    """Test ReplayEngineConfig defaults and validation."""

    def test_default_config(self):
        config = ReplayEngineConfig()
        assert config.replay_mode == ReplayMode.CANDLE
        assert config.timeframe == Timeframe.M1
        assert config.speed_multiplier == 1.0
        assert config.symbols == ()

    def test_custom_config(self):
        config = ReplayEngineConfig(
            replay_mode=ReplayMode.TICK,
            timeframe=Timeframe.H1,
            speed_multiplier=2.5,
            symbols=("EURUSD", "GBPUSD"),
        )
        assert config.replay_mode == ReplayMode.TICK
        assert config.speed_multiplier == 2.5
        assert config.symbols == ("EURUSD", "GBPUSD")

    def test_config_frozen(self):
        config = ReplayEngineConfig()
        with pytest.raises(AttributeError):
            config.replay_mode = ReplayMode.TICK  # type: ignore[misc]


class TestReplayEventHandler:
    """Test ReplayEventHandler base class."""

    @pytest.mark.asyncio
    async def test_on_candle_default(self):
        handler = ReplayEventHandler()
        ts = datetime.now(timezone.utc)
        await handler.on_candle(
            "EURUSD", ts, Decimal("1"), Decimal("2"), Decimal("3"), Decimal("4"), Decimal("1000")
        )

    @pytest.mark.asyncio
    async def test_on_tick_default(self):
        handler = ReplayEventHandler()
        ts = datetime.now(timezone.utc)
        await handler.on_tick("EURUSD", ts, Decimal("1.0990"), Decimal("1.1000"))

    @pytest.mark.asyncio
    async def test_on_order_default(self):
        handler = ReplayEventHandler()
        await handler.on_order({"order_id": "o1"})

    @pytest.mark.asyncio
    async def test_on_trade_default(self):
        handler = ReplayEventHandler()
        await handler.on_trade({"trade_id": "t1"})

    @pytest.mark.asyncio
    async def test_on_event_default(self):
        handler = ReplayEventHandler()
        event = MagicMock(spec=ScheduledEvent)
        await handler.on_event(event)


class TestReplayEngineInitialization:
    """Test replay engine creation."""

    def test_default_init(self):
        engine = ReplayEngine()
        assert engine.state == ReplayState.IDLE
        assert engine.position == 0
        assert engine.total_items == 0
        assert engine.progress == 0.0
        assert engine.current_timestamp is None

    def test_init_with_config(self):
        config = ReplayEngineConfig(speed_multiplier=5.0, symbols=("EURUSD",))
        engine = ReplayEngine(config)
        assert engine._speed == 5.0

    def test_init_with_data_provider(self):
        provider = MagicMock(spec=HistoricalDataProvider)
        engine = ReplayEngine(data_provider=provider)
        assert engine._data_provider is provider

    def test_init_with_event_scheduler(self):
        scheduler = EventScheduler()
        engine = ReplayEngine(event_scheduler=scheduler)
        assert engine._event_scheduler is scheduler

    def test_initial_state_values(self):
        engine = ReplayEngine()
        assert engine.state == ReplayState.IDLE
        assert engine.position == 0
        assert engine.total_items == 0
        assert engine.progress == 0.0
        assert engine.current_timestamp is None


class TestReplayEngineHandlerManagement:
    """Test adding/removing handlers."""

    def test_add_handler(self):
        engine = ReplayEngine()
        handler = ReplayEventHandler()
        engine.add_handler(handler)
        assert handler in engine._handlers

    def test_add_multiple_handlers(self):
        engine = ReplayEngine()
        h1 = ReplayEventHandler()
        h2 = ReplayEventHandler()
        engine.add_handler(h1)
        engine.add_handler(h2)
        assert len(engine._handlers) == 2

    def test_remove_handler(self):
        engine = ReplayEngine()
        handler = ReplayEventHandler()
        engine.add_handler(handler)
        assert len(engine._handlers) == 1
        engine.remove_handler(handler)
        assert len(engine._handlers) == 0

    def test_remove_nonexistent_handler(self):
        engine = ReplayEngine()
        handler = ReplayEventHandler()
        engine.remove_handler(handler)

    def test_handler_order_preserved(self):
        engine = ReplayEngine()
        h1 = ReplayEventHandler()
        h2 = ReplayEventHandler()
        engine.add_handler(h1)
        engine.add_handler(h2)
        assert engine._handlers == [h1, h2]


class TestReplayEngineDataLoading:
    """Test data loading functionality."""

    @pytest.mark.asyncio
    async def test_load_data_no_provider_raises_error(self):
        engine = ReplayEngine()
        with pytest.raises(ReplayError, match="No data provider configured"):
            await engine.load_data("EURUSD")

    @pytest.mark.asyncio
    async def test_load_candle_data_success(self):
        provider = AsyncMock(spec=HistoricalDataProvider)
        ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
        candles = [
            {
                "timestamp": ts,
                "open": Decimal("1.1000"),
                "high": Decimal("1.1050"),
                "low": Decimal("1.0950"),
                "close": Decimal("1.1020"),
                "volume": Decimal("1000"),
                "symbol": "EURUSD",
            },
        ]
        provider.load_candles.return_value = candles
        engine = ReplayEngine(data_provider=provider)
        await engine.load_data("EURUSD")
        assert engine.total_items == 1
        assert engine.position == 0
        assert engine.state == ReplayState.IDLE

    @pytest.mark.asyncio
    async def test_load_tick_data_success(self):
        provider = AsyncMock(spec=HistoricalDataProvider)
        ticks = [
            {
                "timestamp": datetime(2023, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
                "bid": Decimal("1.0990"),
                "ask": Decimal("1.1000"),
                "volume": Decimal("1"),
                "symbol": "EURUSD",
            },
        ]
        provider.load_ticks.return_value = ticks
        config = ReplayEngineConfig(replay_mode=ReplayMode.TICK)
        engine = ReplayEngine(config, data_provider=provider)
        await engine.load_data("EURUSD")
        assert engine.total_items == 1
        assert engine.position == 0

    @pytest.mark.asyncio
    async def test_load_data_sorts_by_timestamp(self):
        provider = AsyncMock(spec=HistoricalDataProvider)
        ts2 = datetime(2023, 1, 2, tzinfo=timezone.utc)
        ts1 = datetime(2023, 1, 1, tzinfo=timezone.utc)
        candles = [
            {
                "timestamp": ts2,
                "open": Decimal("1.1020"),
                "close": Decimal("1.1080"),
                "symbol": "EURUSD",
            },
            {
                "timestamp": ts1,
                "open": Decimal("1.1000"),
                "close": Decimal("1.1020"),
                "symbol": "EURUSD",
            },
        ]
        provider.load_candles.return_value = candles
        engine = ReplayEngine(data_provider=provider)
        await engine.load_data("EURUSD")
        assert engine._data[0]["timestamp"] < engine._data[1]["timestamp"]

    @pytest.mark.asyncio
    async def test_load_data_unsupported_mode_raises_error(self):
        provider = AsyncMock(spec=HistoricalDataProvider)
        config = ReplayEngineConfig(replay_mode="unsupported")
        engine = ReplayEngine(config, data_provider=provider)
        with pytest.raises(ReplayError, match="Unsupported replay mode"):
            await engine.load_data("EURUSD")


class TestReplayEngineStateMachine:
    """Test state transitions."""

    @pytest.mark.asyncio
    async def test_start_sets_playing(self):
        engine = ReplayEngine()
        engine._data = [{"timestamp": datetime.now(timezone.utc), "symbol": "EURUSD"}]
        await engine.start()
        assert engine.state == ReplayState.PLAYING

    @pytest.mark.asyncio
    async def test_start_twice_idempotent(self):
        engine = ReplayEngine()
        engine._data = [{"timestamp": datetime.now(timezone.utc), "symbol": "EURUSD"}]
        await engine.start()
        await engine.start()
        assert engine.state == ReplayState.PLAYING

    @pytest.mark.asyncio
    async def test_start_no_data_raises_error(self):
        engine = ReplayEngine()
        with pytest.raises(ReplayError, match="No data loaded for replay"):
            await engine.start()

    @pytest.mark.asyncio
    async def test_pause_transition(self):
        engine = ReplayEngine()
        engine._state = ReplayState.PLAYING
        await engine.pause()
        assert engine.state == ReplayState.PAUSED

    @pytest.mark.asyncio
    async def test_pause_when_idle_raises_error(self):
        engine = ReplayEngine()
        with pytest.raises(ReplayStateError, match="Cannot pause: not playing"):
            await engine.pause()

    @pytest.mark.asyncio
    async def test_resume_transition(self):
        engine = ReplayEngine()
        engine._state = ReplayState.PAUSED
        await engine.resume()
        assert engine.state == ReplayState.PLAYING

    @pytest.mark.asyncio
    async def test_resume_when_playing_raises_error(self):
        engine = ReplayEngine()
        engine._state = ReplayState.PLAYING
        with pytest.raises(ReplayStateError, match="Cannot resume: not paused"):
            await engine.resume()

    @pytest.mark.asyncio
    async def test_stop_transition(self):
        engine = ReplayEngine()
        engine._state = ReplayState.PLAYING
        await engine.stop()
        assert engine.state == ReplayState.STOPPED
        assert engine._stop_requested is True

    @pytest.mark.asyncio
    async def test_reset_state(self):
        engine = ReplayEngine()
        engine._state = ReplayState.PLAYING
        engine._position = 50
        engine._current_timestamp = datetime.now(timezone.utc)
        await engine.reset()
        assert engine.state == ReplayState.IDLE
        assert engine.position == 0
        assert engine.current_timestamp is None


class TestReplayEnginePlayback:
    """Test the play() method."""

    @pytest.mark.asyncio
    async def test_play_completes_with_data(self):
        ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
        engine = ReplayEngine()
        engine._data = [
            {
                "timestamp": ts,
                "symbol": "EURUSD",
                "open": Decimal("1"),
                "high": Decimal("2"),
                "low": Decimal("3"),
                "close": Decimal("4"),
                "volume": Decimal("100"),
            },
        ]
        await engine.play()
        assert engine.state == ReplayState.COMPLETED
        assert engine.position == 1

    @pytest.mark.asyncio
    async def test_play_with_zero_speed(self):
        ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
        engine = ReplayEngine()
        engine._data = [
            {
                "timestamp": ts,
                "symbol": "EURUSD",
                "open": Decimal("1"),
                "high": Decimal("2"),
                "low": Decimal("3"),
                "close": Decimal("4"),
                "volume": Decimal("100"),
            }
        ]
        engine._speed = 0
        await engine.play()
        assert engine.state == ReplayState.COMPLETED

    @pytest.mark.asyncio
    async def test_play_empty_data(self):
        engine = ReplayEngine()
        engine._data = []
        with pytest.raises(ReplayError, match="No data loaded for replay"):
            await engine.play()


class TestReplayEngineSeek:
    """Test seek functionality."""

    @pytest.mark.asyncio
    async def test_seek_to_timestamp(self):
        engine = ReplayEngine()
        ts1 = datetime(2023, 1, 1, tzinfo=timezone.utc)
        ts2 = datetime(2023, 1, 2, tzinfo=timezone.utc)
        engine._data = [{"timestamp": ts1}, {"timestamp": ts2}]
        result = await engine.seek(ts2)
        assert result is True
        assert engine.position == 1

    @pytest.mark.asyncio
    async def test_seek_beyond_data_returns_false(self):
        engine = ReplayEngine()
        engine._data = [{"timestamp": datetime(2023, 1, 1, tzinfo=timezone.utc)}]
        result = await engine.seek(datetime(2024, 1, 1, tzinfo=timezone.utc))
        assert result is False

    @pytest.mark.asyncio
    async def test_seek_no_data_raises_error(self):
        engine = ReplayEngine()
        with pytest.raises(ReplaySeekError, match="No data loaded"):
            await engine.seek(datetime.now(timezone.utc))


class TestReplayEngineSpeedControl:
    """Test speed multiplier."""

    def test_set_speed(self):
        engine = ReplayEngine()
        engine.set_speed(2.0)
        assert engine._speed == 2.0

    def test_set_speed_zero_raises_error(self):
        engine = ReplayEngine()
        with pytest.raises(ReplayError, match="Invalid speed"):
            engine.set_speed(0)

    def test_set_speed_negative_raises_error(self):
        engine = ReplayEngine()
        with pytest.raises(ReplayError, match="Invalid speed"):
            engine.set_speed(-1)


class TestReplayEngineEventDispatch:
    """Test event dispatch to handlers."""

    @pytest.mark.asyncio
    async def test_candle_dispatch_to_handler(self):
        handler = AsyncMock(spec=ReplayEventHandler)
        ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
        engine = ReplayEngine()
        engine.add_handler(handler)
        engine._data = [
            {
                "timestamp": ts,
                "symbol": "EURUSD",
                "open": Decimal("1.1000"),
                "high": Decimal("1.1050"),
                "low": Decimal("1.0950"),
                "close": Decimal("1.1020"),
                "volume": Decimal("1000"),
            },
        ]
        await engine.play()
        handler.on_candle.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_tick_dispatch_to_handler(self):
        handler = AsyncMock(spec=ReplayEventHandler)
        ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
        config = ReplayEngineConfig(replay_mode=ReplayMode.TICK)
        engine = ReplayEngine(config)
        engine.add_handler(handler)
        engine._data = [
            {
                "timestamp": ts,
                "symbol": "EURUSD",
                "bid": Decimal("1.0990"),
                "ask": Decimal("1.1000"),
            },
        ]
        await engine.play()
        handler.on_tick.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_multiple_handlers_receive_events(self):
        h1 = AsyncMock(spec=ReplayEventHandler)
        h2 = AsyncMock(spec=ReplayEventHandler)
        ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
        engine = ReplayEngine()
        engine.add_handler(h1)
        engine.add_handler(h2)
        engine._data = [
            {
                "timestamp": ts,
                "symbol": "EURUSD",
                "open": Decimal("1.1000"),
                "high": Decimal("1.1050"),
                "low": Decimal("1.0950"),
                "close": Decimal("1.1020"),
                "volume": Decimal("1000"),
            },
        ]
        await engine.play()
        h1.on_candle.assert_awaited_once()
        h2.on_candle.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dispatch_with_scheduled_events(self):
        handler = AsyncMock(spec=ReplayEventHandler)
        ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
        scheduler = EventScheduler()

        from libraries.domain.backtesting.event_scheduler import HighVolatilityEvent

        event = HighVolatilityEvent(timestamp=ts, volatility_multiplier=2.0)
        scheduler.add_event(event)

        engine = ReplayEngine(event_scheduler=scheduler)
        engine.add_handler(handler)
        engine._data = [
            {
                "timestamp": ts,
                "symbol": "EURUSD",
                "open": Decimal("1.1000"),
                "high": Decimal("1.1050"),
                "low": Decimal("1.0950"),
                "close": Decimal("1.1020"),
                "volume": Decimal("1000"),
            },
        ]
        await engine.play()
        handler.on_event.assert_awaited()


class TestReplayEngineEdgeCases:
    """Test edge cases."""

    @pytest.mark.asyncio
    async def test_single_item_play(self):
        ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
        engine = ReplayEngine()
        engine._data = [
            {
                "timestamp": ts,
                "symbol": "EURUSD",
                "open": Decimal("1"),
                "high": Decimal("2"),
                "low": Decimal("3"),
                "close": Decimal("4"),
                "volume": Decimal("100"),
            }
        ]
        await engine.play()
        assert engine.state == ReplayState.COMPLETED
        assert engine.position == 1

    @pytest.mark.asyncio
    async def test_large_replay_session(self):
        engine = ReplayEngine()
        ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
        engine._data = [
            {
                "timestamp": ts + timedelta(seconds=i),
                "symbol": "EURUSD",
                "open": Decimal("1"),
                "high": Decimal("2"),
                "low": Decimal("3"),
                "close": Decimal("4"),
                "volume": Decimal("100"),
            }
            for i in range(10000)
        ]
        await engine.play()
        assert engine.state == ReplayState.COMPLETED
        assert engine.position == 10000

    @pytest.mark.asyncio
    async def test_duplicate_timestamps(self):
        ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
        engine = ReplayEngine()
        engine._data = [
            {
                "timestamp": ts,
                "symbol": "EURUSD",
                "open": Decimal("1"),
                "high": Decimal("2"),
                "low": Decimal("3"),
                "close": Decimal("4"),
                "volume": Decimal("100"),
            },
            {
                "timestamp": ts,
                "symbol": "EURUSD",
                "open": Decimal("1"),
                "high": Decimal("2"),
                "low": Decimal("3"),
                "close": Decimal("5"),
                "volume": Decimal("200"),
            },
        ]
        await engine.play()
        assert engine.state == ReplayState.COMPLETED
