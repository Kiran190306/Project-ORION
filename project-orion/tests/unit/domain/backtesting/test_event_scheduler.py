"""Tests for EPIC-010 EventScheduler and scheduled events."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from libraries.domain.backtesting.event_scheduler import (
    BrokerDisconnectEvent,
    EventScheduler,
    FlashCrashEvent,
    GapOpenEvent,
    HighVolatilityEvent,
    LowLiquidityEvent,
    NewsEvent,
    ScheduledEvent,
    SpreadSpikeEvent,
)


class TestScheduledEventBase:
    """Test base ScheduledEvent class."""

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            ScheduledEvent(timestamp=datetime.now(timezone.utc))  # type: ignore[abstract]

    def test_base_fields(self):
        class TestEvent(ScheduledEvent):
            def apply(self, context):
                return context

        ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
        event = TestEvent(timestamp=ts, symbol="EURUSD", severity="high")
        assert event.timestamp == ts
        assert event.symbol == "EURUSD"
        assert event.severity == "high"
        assert event.metadata == {}


class TestHighVolatilityEvent:
    """Test HighVolatilityEvent."""

    def test_default_creation(self):
        ts = datetime.now(timezone.utc)
        event = HighVolatilityEvent(timestamp=ts)
        assert event.volatility_multiplier == 2.0
        assert event.duration_minutes == 60

    def test_custom_creation(self):
        ts = datetime.now(timezone.utc)
        event = HighVolatilityEvent(timestamp=ts, volatility_multiplier=3.0, duration_minutes=120)
        assert event.volatility_multiplier == 3.0
        assert event.duration_minutes == 120

    def test_apply_preserves_input(self):
        ts = datetime.now(timezone.utc)
        event = HighVolatilityEvent(timestamp=ts)
        ctx = {"volatility": 1.0, "some_other_key": "value"}
        result = event.apply(ctx)
        assert result["some_other_key"] == "value"
        assert result["volatility"] == 2.0
        assert result["event_active"] is True
        assert result["event_type"] == "high_volatility"
        # Original context should not be modified
        assert ctx["volatility"] == 1.0

    def test_apply_default_volatility(self):
        ts = datetime.now(timezone.utc)
        event = HighVolatilityEvent(timestamp=ts)
        ctx = {}
        result = event.apply(ctx)
        assert result["volatility"] == 2.0


class TestLowLiquidityEvent:
    """Test LowLiquidityEvent."""

    def test_default_creation(self):
        ts = datetime.now(timezone.utc)
        event = LowLiquidityEvent(timestamp=ts)
        assert event.liquidity_multiplier == 0.3
        assert event.duration_minutes == 30

    def test_apply_reduces_liquidity(self):
        ts = datetime.now(timezone.utc)
        event = LowLiquidityEvent(timestamp=ts)
        ctx = {"liquidity_score": 1.0}
        result = event.apply(ctx)
        assert result["liquidity_score"] == 0.3
        assert result["event_type"] == "low_liquidity"


class TestSpreadSpikeEvent:
    """Test SpreadSpikeEvent."""

    def test_default_creation(self):
        ts = datetime.now(timezone.utc)
        event = SpreadSpikeEvent(timestamp=ts)
        assert event.spread_multiplier == 5.0
        assert event.duration_minutes == 15

    def test_apply_increases_spread(self):
        ts = datetime.now(timezone.utc)
        event = SpreadSpikeEvent(timestamp=ts)
        ctx = {"spread_pips": 1.0}
        result = event.apply(ctx)
        assert result["spread_pips"] == 5.0

    def test_apply_default_spread(self):
        ts = datetime.now(timezone.utc)
        event = SpreadSpikeEvent(timestamp=ts)
        ctx = {}
        result = event.apply(ctx)
        assert result["spread_pips"] == 5.0


class TestFlashCrashEvent:
    """Test FlashCrashEvent."""

    def test_default_creation(self):
        ts = datetime.now(timezone.utc)
        event = FlashCrashEvent(timestamp=ts)
        assert event.price_drop_pct == 5.0
        assert event.recovery_minutes == 10

    def test_apply_sets_flash_crash(self):
        ts = datetime.now(timezone.utc)
        event = FlashCrashEvent(timestamp=ts)
        ctx = {}
        result = event.apply(ctx)
        assert result["flash_crash"] is True
        assert result["price_drop_pct"] == 5.0
        assert result["event_active"] is True


class TestNewsEvent:
    """Test NewsEvent."""

    def test_default_creation(self):
        ts = datetime.now(timezone.utc)
        event = NewsEvent(timestamp=ts)
        assert event.impact_duration_minutes == 30
        assert event.spread_widen_multiplier == 3.0

    def test_apply_widens_spread(self):
        ts = datetime.now(timezone.utc)
        event = NewsEvent(timestamp=ts)
        ctx = {"spread_pips": 2.0}
        result = event.apply(ctx)
        assert result["is_news_hour"] is True
        assert result["spread_pips"] == 6.0

    def test_apply_default_spread(self):
        ts = datetime.now(timezone.utc)
        event = NewsEvent(timestamp=ts)
        ctx = {}
        result = event.apply(ctx)
        assert result["spread_pips"] == 3.0


class TestBrokerDisconnectEvent:
    """Test BrokerDisconnectEvent."""

    def test_default_creation(self):
        ts = datetime.now(timezone.utc)
        event = BrokerDisconnectEvent(timestamp=ts)
        assert event.disconnect_duration_seconds == 60

    def test_apply_disconnects_broker(self):
        ts = datetime.now(timezone.utc)
        event = BrokerDisconnectEvent(timestamp=ts)
        ctx = {"broker_connected": True}
        result = event.apply(ctx)
        assert result["broker_connected"] is False
        assert result["event_type"] == "broker_disconnect"

    def test_apply_default_connected(self):
        ts = datetime.now(timezone.utc)
        event = BrokerDisconnectEvent(timestamp=ts)
        ctx = {}
        result = event.apply(ctx)
        assert result["broker_connected"] is False


class TestGapOpenEvent:
    """Test GapOpenEvent."""

    def test_default_creation(self):
        ts = datetime.now(timezone.utc)
        event = GapOpenEvent(timestamp=ts)
        assert event.gap_pips == 20.0
        assert event.direction == "up"

    def test_custom_direction(self):
        ts = datetime.now(timezone.utc)
        event = GapOpenEvent(timestamp=ts, direction="down")
        assert event.direction == "down"

    def test_apply_sets_gap(self):
        ts = datetime.now(timezone.utc)
        event = GapOpenEvent(timestamp=ts)
        ctx = {}
        result = event.apply(ctx)
        assert result["gap_open"] is True
        assert result["gap_pips"] == 20.0
        assert result["gap_direction"] == "up"

    def test_apply_down_direction(self):
        ts = datetime.now(timezone.utc)
        event = GapOpenEvent(timestamp=ts, direction="down")
        ctx = {}
        result = event.apply(ctx)
        assert result["gap_direction"] == "down"


class TestEventScheduler:
    """Test EventScheduler."""

    def test_empty_scheduler(self):
        scheduler = EventScheduler()
        assert scheduler.event_count == 0

    def test_add_single_event(self):
        scheduler = EventScheduler()
        ts = datetime.now(timezone.utc)
        event = HighVolatilityEvent(timestamp=ts)
        scheduler.add_event(event)
        assert scheduler.event_count == 1

    def test_add_multiple_events(self):
        scheduler = EventScheduler()
        ts = datetime.now(timezone.utc)
        scheduler.add_event(HighVolatilityEvent(timestamp=ts))
        scheduler.add_event(LowLiquidityEvent(timestamp=ts))
        scheduler.add_event(SpreadSpikeEvent(timestamp=ts))
        assert scheduler.event_count == 3

    def test_add_events_bulk(self):
        scheduler = EventScheduler()
        ts = datetime.now(timezone.utc)
        events = [
            HighVolatilityEvent(timestamp=ts),
            LowLiquidityEvent(timestamp=ts),
        ]
        scheduler.add_events(events)
        assert scheduler.event_count == 2

    def test_clear_events(self):
        scheduler = EventScheduler()
        ts = datetime.now(timezone.utc)
        scheduler.add_event(HighVolatilityEvent(timestamp=ts))
        scheduler.clear()
        assert scheduler.event_count == 0

    def test_event_count_property(self):
        scheduler = EventScheduler()
        assert scheduler.event_count == 0
        ts = datetime.now(timezone.utc)
        scheduler.add_event(HighVolatilityEvent(timestamp=ts))
        assert scheduler.event_count == 1

    def test_events_sorted_by_timestamp(self):
        scheduler = EventScheduler()
        ts1 = datetime(2023, 1, 1, tzinfo=timezone.utc)
        ts2 = datetime(2023, 1, 2, tzinfo=timezone.utc)
        ts3 = datetime(2023, 1, 3, tzinfo=timezone.utc)
        scheduler.add_event(HighVolatilityEvent(timestamp=ts3))
        scheduler.add_event(LowLiquidityEvent(timestamp=ts1))
        scheduler.add_event(SpreadSpikeEvent(timestamp=ts2))
        # get_upcoming_events should return sorted
        upcoming = scheduler.get_upcoming_events(datetime(2022, 1, 1, tzinfo=timezone.utc))
        assert len(upcoming) == 3
        assert upcoming[0].timestamp == ts1
        assert upcoming[1].timestamp == ts2
        assert upcoming[2].timestamp == ts3

    def test_get_events_at_exact(self):
        scheduler = EventScheduler()
        ts = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        scheduler.add_event(HighVolatilityEvent(timestamp=ts))
        events = scheduler.get_events_at(ts)
        assert len(events) == 1

    def test_get_events_at_with_tolerance(self):
        scheduler = EventScheduler()
        ts = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        scheduler.add_event(HighVolatilityEvent(timestamp=ts))
        # Within 1 second tolerance (default)
        near_ts = datetime(2023, 1, 1, 12, 0, 0, 500000, tzinfo=timezone.utc)
        events = scheduler.get_events_at(near_ts)
        assert len(events) == 1

    def test_get_events_at_beyond_tolerance(self):
        scheduler = EventScheduler()
        ts = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        scheduler.add_event(HighVolatilityEvent(timestamp=ts))
        far_ts = datetime(2023, 1, 1, 12, 1, 0, tzinfo=timezone.utc)  # 60 seconds away
        events = scheduler.get_events_at(far_ts)
        assert len(events) == 0

    def test_get_events_at_custom_tolerance(self):
        scheduler = EventScheduler()
        ts = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        scheduler.add_event(HighVolatilityEvent(timestamp=ts))
        near_ts = datetime(2023, 1, 1, 12, 0, 5, tzinfo=timezone.utc)  # 5 seconds away
        events = scheduler.get_events_at(near_ts, tolerance_seconds=10.0)
        assert len(events) == 1

    def test_get_upcoming_events_limit(self):
        scheduler = EventScheduler()
        ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
        for i in range(20):
            scheduler.add_event(HighVolatilityEvent(timestamp=ts + timedelta(hours=i)))
        upcoming = scheduler.get_upcoming_events(ts, limit=5)
        assert len(upcoming) == 5

    def test_get_upcoming_events_from_future(self):
        scheduler = EventScheduler()
        ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
        scheduler.add_event(HighVolatilityEvent(timestamp=ts))
        future = datetime(2024, 1, 1, tzinfo=timezone.utc)
        upcoming = scheduler.get_upcoming_events(future)
        assert len(upcoming) == 0

    def test_multiple_events_at_same_time(self):
        scheduler = EventScheduler()
        ts = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        scheduler.add_event(HighVolatilityEvent(timestamp=ts))
        scheduler.add_event(LowLiquidityEvent(timestamp=ts))
        scheduler.add_event(SpreadSpikeEvent(timestamp=ts))
        events = scheduler.get_events_at(ts)
        assert len(events) == 3

    def test_clear_then_add(self):
        scheduler = EventScheduler()
        ts = datetime.now(timezone.utc)
        scheduler.add_event(HighVolatilityEvent(timestamp=ts))
        scheduler.clear()
        assert scheduler.event_count == 0
        scheduler.add_event(HighVolatilityEvent(timestamp=ts))
        assert scheduler.event_count == 1

    def test_large_number_of_events(self):
        scheduler = EventScheduler()
        ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
        events = [HighVolatilityEvent(timestamp=ts + timedelta(minutes=i)) for i in range(1000)]
        scheduler.add_events(events)
        assert scheduler.event_count == 1000
        upcoming = scheduler.get_upcoming_events(ts)
        assert len(upcoming) == 10  # default limit

    def test_events_immutable(self):
        ts = datetime.now(timezone.utc)
        event = HighVolatilityEvent(timestamp=ts)
        with pytest.raises(AttributeError):
            event.volatility_multiplier = 5.0  # type: ignore[misc]


class TestEventTypesImmutability:
    """Test that all event types are frozen dataclasses."""

    def test_high_volatility_frozen(self):
        ts = datetime.now(timezone.utc)
        event = HighVolatilityEvent(timestamp=ts)
        with pytest.raises(AttributeError):
            event.volatility_multiplier = 3.0  # type: ignore[misc]

    def test_low_liquidity_frozen(self):
        ts = datetime.now(timezone.utc)
        event = LowLiquidityEvent(timestamp=ts)
        with pytest.raises(AttributeError):
            event.liquidity_multiplier = 0.5  # type: ignore[misc]

    def test_spread_spike_frozen(self):
        ts = datetime.now(timezone.utc)
        event = SpreadSpikeEvent(timestamp=ts)
        with pytest.raises(AttributeError):
            event.spread_multiplier = 2.0  # type: ignore[misc]

    def test_flash_crash_frozen(self):
        ts = datetime.now(timezone.utc)
        event = FlashCrashEvent(timestamp=ts)
        with pytest.raises(AttributeError):
            event.price_drop_pct = 10.0  # type: ignore[misc]

    def test_news_event_frozen(self):
        ts = datetime.now(timezone.utc)
        event = NewsEvent(timestamp=ts)
        with pytest.raises(AttributeError):
            event.impact_duration_minutes = 60  # type: ignore[misc]

    def test_broker_disconnect_frozen(self):
        ts = datetime.now(timezone.utc)
        event = BrokerDisconnectEvent(timestamp=ts)
        with pytest.raises(AttributeError):
            event.disconnect_duration_seconds = 120  # type: ignore[misc]

    def test_gap_open_frozen(self):
        ts = datetime.now(timezone.utc)
        event = GapOpenEvent(timestamp=ts)
        with pytest.raises(AttributeError):
            event.gap_pips = 30.0  # type: ignore[misc]
