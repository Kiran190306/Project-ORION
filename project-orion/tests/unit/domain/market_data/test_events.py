"""Tests for EPIC-014 Market Data domain events."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.market_data.events import (
    BarEvent,
    CorporateActionEvent,
    EconomicEventEvent,
    MarketDataEvent,
    MarketDataEventType,
    OHLCVEvent,
    OrderBookEvent,
    ProviderEvent,
    SessionEvent,
    TickEvent,
)
from libraries.domain.market_data.models import (
    Bar,
    BarType,
    BookLevel,
    CorporateAction,
    CorporateActionType,
    EconomicEvent,
    EconomicEventImportance,
    MarketSession,
    MarketSessionType,
    OHLCV,
    OrderBookSnapshot,
    Tick,
    TickPriceType,
)


class TestMarketDataEventType:
    """Test MarketDataEventType enum."""

    def test_enum_values(self) -> None:
        assert MarketDataEventType.TICK_RECEIVED == "tick_received"
        assert MarketDataEventType.BAR_COMPLETED == "bar_completed"
        assert MarketDataEventType.BAR_UPDATED == "bar_updated"
        assert MarketDataEventType.ORDER_BOOK_SNAPSHOT == "order_book_snapshot"
        assert MarketDataEventType.ORDER_BOOK_UPDATE == "order_book_update"
        assert MarketDataEventType.MARKET_SESSION_OPEN == "market_session_open"
        assert MarketDataEventType.MARKET_SESSION_CLOSE == "market_session_close"
        assert MarketDataEventType.CORPORATE_ACTION == "corporate_action"
        assert MarketDataEventType.ECONOMIC_EVENT == "economic_event"
        assert MarketDataEventType.PROVIDER_CONNECTED == "provider_connected"
        assert MarketDataEventType.PROVIDER_DISCONNECTED == "provider_disconnected"
        assert MarketDataEventType.PROVIDER_ERROR == "provider_error"
        assert MarketDataEventType.SUBSCRIBED == "subscribed"
        assert MarketDataEventType.UNSUBSCRIBED == "unsubscribed"


class TestMarketDataEvent:
    """Test base MarketDataEvent."""

    def test_default_construction(self) -> None:
        event = MarketDataEvent(
            event_type=MarketDataEventType.TICK_RECEIVED,
            symbol="EURUSD",
        )
        assert event.event_type == MarketDataEventType.TICK_RECEIVED
        assert event.symbol == "EURUSD"
        assert isinstance(event.timestamp, datetime)
        assert event.metadata == {}

    def test_custom_timestamp(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        event = MarketDataEvent(
            event_type=MarketDataEventType.BAR_COMPLETED,
            symbol="EURUSD",
            timestamp=ts,
        )
        assert event.timestamp == ts

    def test_custom_metadata(self) -> None:
        event = MarketDataEvent(
            event_type=MarketDataEventType.TICK_RECEIVED,
            symbol="EURUSD",
            metadata={"source": "oanda"},
        )
        assert event.metadata == {"source": "oanda"}

    def test_frozen(self) -> None:
        event = MarketDataEvent(
            event_type=MarketDataEventType.TICK_RECEIVED,
            symbol="EURUSD",
        )
        with pytest.raises(AttributeError):
            event.symbol = "GBPUSD"  # type: ignore[misc]


class TestTickEvent:
    """Test TickEvent model."""

    def test_construction(self) -> None:
        ts = datetime.now(timezone.utc)
        tick = Tick(
            symbol="EURUSD",
            price=Decimal("1.12345"),
            volume=Decimal("1000000"),
            timestamp=ts,
        )
        event = TickEvent(tick=tick)
        assert event.event_type == MarketDataEventType.TICK_RECEIVED
        assert event.symbol == "EURUSD"
        assert event.timestamp == ts
        assert event.tick == tick

    def test_frozen(self) -> None:
        ts = datetime.now(timezone.utc)
        tick = Tick(
            symbol="EURUSD",
            price=Decimal("1.12"),
            volume=Decimal("1000"),
            timestamp=ts,
        )
        event = TickEvent(tick=tick)
        with pytest.raises(AttributeError):
            event.tick = tick  # type: ignore[misc]


class TestBarEvent:
    """Test BarEvent model."""

    def test_completed_bar(self) -> None:
        ts = datetime.now(timezone.utc)
        ohlcv = OHLCV(
            symbol="EURUSD",
            timestamp=ts,
            open=Decimal("1.10"),
            high=Decimal("1.11"),
            low=Decimal("1.09"),
            close=Decimal("1.105"),
            volume=Decimal("1000"),
        )
        bar = Bar(
            symbol="EURUSD",
            bar_type=BarType.M5,
            timestamp=ts,
            ohlcv=ohlcv,
        )
        event = BarEvent(bar=bar, is_complete=True)
        assert event.event_type == MarketDataEventType.BAR_COMPLETED
        assert event.is_complete is True

    def test_updated_bar(self) -> None:
        ts = datetime.now(timezone.utc)
        ohlcv = OHLCV(
            symbol="EURUSD",
            timestamp=ts,
            open=Decimal("1.10"),
            high=Decimal("1.11"),
            low=Decimal("1.09"),
            close=Decimal("1.105"),
            volume=Decimal("1000"),
        )
        bar = Bar(
            symbol="EURUSD",
            bar_type=BarType.M5,
            timestamp=ts,
            ohlcv=ohlcv,
        )
        event = BarEvent(bar=bar, is_complete=False)
        assert event.event_type == MarketDataEventType.BAR_UPDATED
        assert event.is_complete is False

    def test_symbol_from_bar(self) -> None:
        ts = datetime.now(timezone.utc)
        ohlcv = OHLCV(
            symbol="GBPUSD",
            timestamp=ts,
            open=Decimal("1.25"),
            high=Decimal("1.26"),
            low=Decimal("1.24"),
            close=Decimal("1.255"),
            volume=Decimal("500"),
        )
        bar = Bar(
            symbol="GBPUSD",
            bar_type=BarType.H1,
            timestamp=ts,
            ohlcv=ohlcv,
        )
        event = BarEvent(bar=bar)
        assert event.symbol == "GBPUSD"


class TestOHLCVEvent:
    """Test OHLCVEvent model."""

    def test_construction(self) -> None:
        ts = datetime.now(timezone.utc)
        ohlcv = OHLCV(
            symbol="EURUSD",
            timestamp=ts,
            open=Decimal("1.10"),
            high=Decimal("1.11"),
            low=Decimal("1.09"),
            close=Decimal("1.105"),
            volume=Decimal("1000"),
        )
        event = OHLCVEvent(ohlcv=ohlcv)
        assert event.event_type == MarketDataEventType.BAR_UPDATED
        assert event.ohlcv == ohlcv
        assert event.symbol == "EURUSD"


class TestOrderBookEvent:
    """Test OrderBookEvent model."""

    def test_snapshot_event(self) -> None:
        ts = datetime.now(timezone.utc)
        snap = OrderBookSnapshot(
            symbol="EURUSD",
            timestamp=ts,
            snapshot_type="snapshot",
        )
        event = OrderBookEvent(snapshot=snap)
        assert event.event_type == MarketDataEventType.ORDER_BOOK_SNAPSHOT

    def test_incremental_event(self) -> None:
        ts = datetime.now(timezone.utc)
        snap = OrderBookSnapshot(
            symbol="EURUSD",
            timestamp=ts,
            snapshot_type="incremental",
            sequence=42,
        )
        event = OrderBookEvent(snapshot=snap)
        assert event.event_type == MarketDataEventType.ORDER_BOOK_UPDATE


class TestSessionEvent:
    """Test SessionEvent model."""

    def test_open_event(self) -> None:
        open_ts = datetime.now(timezone.utc)
        close_ts = datetime.now(timezone.utc)
        session = MarketSession(
            session_type=MarketSessionType.LONDON,
            symbol="EURUSD",
            open_time=open_ts,
            close_time=close_ts,
        )
        event = SessionEvent(session=session, is_open=True)
        assert event.event_type == MarketDataEventType.MARKET_SESSION_OPEN
        assert event.timestamp == open_ts

    def test_close_event(self) -> None:
        open_ts = datetime.now(timezone.utc)
        close_ts = datetime.now(timezone.utc)
        session = MarketSession(
            session_type=MarketSessionType.LONDON,
            symbol="EURUSD",
            open_time=open_ts,
            close_time=close_ts,
        )
        event = SessionEvent(session=session, is_open=False)
        assert event.event_type == MarketDataEventType.MARKET_SESSION_CLOSE
        assert event.timestamp == close_ts


class TestCorporateActionEvent:
    """Test CorporateActionEvent model."""

    def test_construction(self) -> None:
        ann_date = datetime.now(timezone.utc)
        eff_date = datetime.now(timezone.utc)
        action = CorporateAction(
            symbol="AAPL",
            action_type=CorporateActionType.DIVIDEND,
            announcement_date=ann_date,
            effective_date=eff_date,
        )
        event = CorporateActionEvent(action=action)
        assert event.event_type == MarketDataEventType.CORPORATE_ACTION
        assert event.symbol == "AAPL"
        assert event.timestamp == ann_date


class TestEconomicEventEvent:
    """Test EconomicEventEvent model."""

    def test_construction(self) -> None:
        ts = datetime.now(timezone.utc)
        econ = EconomicEvent(
            event_id="NFP-202401",
            title="Non-Farm Payrolls",
            timestamp=ts,
            currency="USD",
        )
        event = EconomicEventEvent(event=econ)
        assert event.event_type == MarketDataEventType.ECONOMIC_EVENT
        assert event.symbol == "USD"
        assert event.timestamp == ts


class TestProviderEvent:
    """Test ProviderEvent model."""

    def test_connected_event(self) -> None:
        event = ProviderEvent(
            event_type=MarketDataEventType.PROVIDER_CONNECTED,
            symbol="EURUSD",
            provider_name="oanda",
        )
        assert event.event_type == MarketDataEventType.PROVIDER_CONNECTED
        assert event.provider_name == "oanda"
        assert event.error_message == ""

    def test_error_event(self) -> None:
        event = ProviderEvent(
            event_type=MarketDataEventType.PROVIDER_ERROR,
            symbol="EURUSD",
            provider_name="oanda",
            error_message="Connection timeout",
        )
        assert event.error_message == "Connection timeout"


class TestEventImmutability:
    """Test all event dataclasses are frozen."""

    @pytest.mark.parametrize(
        "event_class,kwargs",
        [
            (
                TickEvent,
                {
                    "tick": Tick(
                        symbol="EURUSD",
                        price=Decimal("1.12"),
                        volume=Decimal("1000"),
                        timestamp=datetime.now(timezone.utc),
                    ),
                },
            ),
            (
                OHLCVEvent,
                {
                    "ohlcv": OHLCV(
                        symbol="EURUSD",
                        timestamp=datetime.now(timezone.utc),
                        open=Decimal("1.10"),
                        high=Decimal("1.11"),
                        low=Decimal("1.09"),
                        close=Decimal("1.105"),
                        volume=Decimal("1000"),
                    ),
                },
            ),
        ],
    )
    def test_event_is_frozen(self, event_class, kwargs) -> None:
        import dataclasses

        instance = event_class(**kwargs)
        assert dataclasses.is_dataclass(instance)
        assert instance.__dataclass_params__.frozen is True

    def test_all_events_are_market_data_events(self) -> None:
        ts = datetime.now(timezone.utc)

        tick = Tick(
            symbol="EURUSD",
            price=Decimal("1.12"),
            volume=Decimal("1000"),
            timestamp=ts,
        )
        assert isinstance(TickEvent(tick=tick), MarketDataEvent)

        ohlcv = OHLCV(
            symbol="EURUSD",
            timestamp=ts,
            open=Decimal("1.10"),
            high=Decimal("1.11"),
            low=Decimal("1.09"),
            close=Decimal("1.105"),
            volume=Decimal("1000"),
        )
        bar = Bar(symbol="EURUSD", bar_type=BarType.M5, timestamp=ts, ohlcv=ohlcv)
        assert isinstance(BarEvent(bar=bar), MarketDataEvent)
        assert isinstance(OHLCVEvent(ohlcv=ohlcv), MarketDataEvent)

