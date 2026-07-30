"""Tests for EPIC-014 Market Data domain models."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

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
    OrderBook,
    OrderBookSnapshot,
    Quote,
    Tick,
    TickData,
    TickPriceType,
    Trade,
    TradeTick,
)


# ═══════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════


class TestEnums:
    """Test all StrEnum values."""

    def test_tick_price_type_values(self) -> None:
        assert TickPriceType.TRADE == "trade"
        assert TickPriceType.BID == "bid"
        assert TickPriceType.ASK == "ask"
        assert TickPriceType.MID == "mid"

    def test_bar_type_values(self) -> None:
        assert BarType.M1 == "1m"
        assert BarType.M5 == "5m"
        assert BarType.M15 == "15m"
        assert BarType.M30 == "30m"
        assert BarType.H1 == "1h"
        assert BarType.H4 == "4h"
        assert BarType.D1 == "1d"
        assert BarType.W1 == "1w"
        assert BarType.MN1 == "1mo"

    def test_market_session_type_values(self) -> None:
        assert MarketSessionType.ASIAN == "asian"
        assert MarketSessionType.EUROPEAN == "european"
        assert MarketSessionType.NORTH_AMERICAN == "north_american"
        assert MarketSessionType.LONDON == "london"
        assert MarketSessionType.TOKYO == "tokyo"
        assert MarketSessionType.SYDNEY == "sydney"
        assert MarketSessionType.NEW_YORK == "new_york"
        assert MarketSessionType.OVERNIGHT == "overnight"
        assert MarketSessionType.CLOSED == "closed"

    def test_corporate_action_type_values(self) -> None:
        assert CorporateActionType.DIVIDEND == "dividend"
        assert CorporateActionType.STOCK_SPLIT == "stock_split"
        assert CorporateActionType.REVERSE_SPLIT == "reverse_split"
        assert CorporateActionType.MERGER == "merger"
        assert CorporateActionType.RIGHTS_ISSUE == "rights_issue"
        assert CorporateActionType.SPIN_OFF == "spin_off"
        assert CorporateActionType.NAME_CHANGE == "name_change"
        assert CorporateActionType.SYMBOL_CHANGE == "symbol_change"

    def test_economic_event_importance_values(self) -> None:
        assert EconomicEventImportance.LOW == "low"
        assert EconomicEventImportance.MEDIUM == "medium"
        assert EconomicEventImportance.HIGH == "high"
        assert EconomicEventImportance.NON_FARM == "non_farm"


# ═══════════════════════════════════════════════════════════════════════
# Tick
# ═══════════════════════════════════════════════════════════════════════


class TestTick:
    """Test Tick model."""

    def test_default_construction(self) -> None:
        ts = datetime.now(timezone.utc)
        tick = Tick(
            symbol="EURUSD",
            price=Decimal("1.12345"),
            volume=Decimal("1000000"),
            timestamp=ts,
        )
        assert tick.symbol == "EURUSD"
        assert tick.price == Decimal("1.12345")
        assert tick.volume == Decimal("1000000")
        assert tick.timestamp == ts
        assert tick.price_type == TickPriceType.TRADE
        assert tick.bid is None
        assert tick.ask is None
        assert tick.exchange_timestamp is None
        assert tick.provider == ""
        assert tick.metadata == {}

    def test_full_construction(self) -> None:
        ts = datetime.now(timezone.utc)
        tick = Tick(
            symbol="GBPUSD",
            price=Decimal("1.25000"),
            volume=Decimal("500000"),
            timestamp=ts,
            price_type=TickPriceType.BID,
            bid=Decimal("1.24990"),
            ask=Decimal("1.25010"),
            exchange_timestamp=ts,
            provider="oanda",
            metadata={"source": "live"},
        )
        assert tick.symbol == "GBPUSD"
        assert tick.price_type == TickPriceType.BID
        assert tick.bid == Decimal("1.24990")
        assert tick.ask == Decimal("1.25010")
        assert tick.provider == "oanda"
        assert tick.metadata == {"source": "live"}

    def test_frozen(self) -> None:
        ts = datetime.now(timezone.utc)
        tick = Tick(
            symbol="EURUSD",
            price=Decimal("1.10"),
            volume=Decimal("1000"),
            timestamp=ts,
        )
        with pytest.raises(AttributeError):
            tick.symbol = "GBPUSD"  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════
# TickData
# ═══════════════════════════════════════════════════════════════════════


class TestTickData:
    """Test TickData model."""

    def test_default_construction(self) -> None:
        td = TickData(symbol="EURUSD")
        assert td.symbol == "EURUSD"
        assert td.ticks == ()
        assert isinstance(td.timestamp, datetime)

    def test_with_ticks(self) -> None:
        ts = datetime.now(timezone.utc)
        tick1 = Tick(
            symbol="EURUSD",
            price=Decimal("1.10"),
            volume=Decimal("1000"),
            timestamp=ts,
        )
        tick2 = Tick(
            symbol="EURUSD",
            price=Decimal("1.11"),
            volume=Decimal("2000"),
            timestamp=ts,
        )
        td = TickData(symbol="EURUSD", ticks=(tick1, tick2))
        assert len(td.ticks) == 2

    def test_frozen(self) -> None:
        td = TickData(symbol="EURUSD")
        with pytest.raises(AttributeError):
            td.symbol = "GBPUSD"  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════
# TradeTick
# ═══════════════════════════════════════════════════════════════════════


class TestTradeTick:
    """Test TradeTick model."""

    def test_default_construction(self) -> None:
        ts = datetime.now(timezone.utc)
        tt = TradeTick(
            symbol="EURUSD",
            price=Decimal("1.12345"),
            volume=Decimal("100000"),
            timestamp=ts,
        )
        assert tt.symbol == "EURUSD"
        assert tt.price == Decimal("1.12345")
        assert tt.side == ""
        assert tt.aggressor == ""
        assert tt.bid is None
        assert tt.ask is None

    def test_full_construction(self) -> None:
        ts = datetime.now(timezone.utc)
        tt = TradeTick(
            symbol="EURUSD",
            price=Decimal("1.12345"),
            volume=Decimal("100000"),
            timestamp=ts,
            side="buy",
            aggressor="buyer",
            bid=Decimal("1.12340"),
            ask=Decimal("1.12350"),
        )
        assert tt.side == "buy"
        assert tt.aggressor == "buyer"

    def test_frozen(self) -> None:
        ts = datetime.now(timezone.utc)
        tt = TradeTick(
            symbol="EURUSD",
            price=Decimal("1.10"),
            volume=Decimal("1000"),
            timestamp=ts,
        )
        with pytest.raises(AttributeError):
            tt.price = Decimal("1.20")  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════
# Quote
# ═══════════════════════════════════════════════════════════════════════


class TestQuote:
    """Test Quote model."""

    def test_default_construction(self) -> None:
        ts = datetime.now(timezone.utc)
        quote = Quote(
            symbol="EURUSD",
            bid=Decimal("1.12340"),
            ask=Decimal("1.12350"),
            timestamp=ts,
        )
        assert quote.symbol == "EURUSD"
        assert quote.bid == Decimal("1.12340")
        assert quote.ask == Decimal("1.12350")
        assert quote.bid_volume is None
        assert quote.ask_volume is None
        assert quote.provider == ""

    def test_with_volumes(self) -> None:
        ts = datetime.now(timezone.utc)
        quote = Quote(
            symbol="EURUSD",
            bid=Decimal("1.12340"),
            ask=Decimal("1.12350"),
            timestamp=ts,
            bid_volume=Decimal("1000000"),
            ask_volume=Decimal("2000000"),
        )
        assert quote.bid_volume == Decimal("1000000")
        assert quote.ask_volume == Decimal("2000000")

    def test_frozen(self) -> None:
        ts = datetime.now(timezone.utc)
        quote = Quote(
            symbol="EURUSD",
            bid=Decimal("1.12"),
            ask=Decimal("1.13"),
            timestamp=ts,
        )
        with pytest.raises(AttributeError):
            quote.bid = Decimal("1.14")  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════
# Trade
# ═══════════════════════════════════════════════════════════════════════


class TestTrade:
    """Test Trade model."""

    def test_default_construction(self) -> None:
        ts = datetime.now(timezone.utc)
        trade = Trade(
            trade_id="t1",
            symbol="EURUSD",
            price=Decimal("1.12345"),
            volume=Decimal("100000"),
            timestamp=ts,
        )
        assert trade.trade_id == "t1"
        assert trade.symbol == "EURUSD"
        assert trade.price == Decimal("1.12345")
        assert trade.side == ""
        assert trade.commission is None

    def test_full_construction(self) -> None:
        ts = datetime.now(timezone.utc)
        trade = Trade(
            trade_id="t2",
            symbol="GBPUSD",
            price=Decimal("1.25000"),
            volume=Decimal("50000"),
            timestamp=ts,
            side="sell",
            aggressor="seller",
            commission=Decimal("5.00"),
        )
        assert trade.side == "sell"
        assert trade.commission == Decimal("5.00")

    def test_metadata(self) -> None:
        ts = datetime.now(timezone.utc)
        trade = Trade(
            trade_id="t3",
            symbol="EURUSD",
            price=Decimal("1.10"),
            volume=Decimal("1000"),
            timestamp=ts,
            metadata={"strategy": "momentum"},
        )
        assert trade.metadata == {"strategy": "momentum"}

    def test_frozen(self) -> None:
        ts = datetime.now(timezone.utc)
        trade = Trade(
            trade_id="t1",
            symbol="EURUSD",
            price=Decimal("1.10"),
            volume=Decimal("1000"),
            timestamp=ts,
        )
        with pytest.raises(AttributeError):
            trade.trade_id = "t2"  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════
# OHLCV
# ═══════════════════════════════════════════════════════════════════════


class TestOHLCV:
    """Test OHLCV model."""

    def test_default_construction(self) -> None:
        ts = datetime.now(timezone.utc)
        ohlcv = OHLCV(
            symbol="EURUSD",
            timestamp=ts,
            open=Decimal("1.10000"),
            high=Decimal("1.11000"),
            low=Decimal("1.09000"),
            close=Decimal("1.10500"),
            volume=Decimal("1000000"),
        )
        assert ohlcv.symbol == "EURUSD"
        assert ohlcv.open == Decimal("1.10000")
        assert ohlcv.high == Decimal("1.11000")
        assert ohlcv.low == Decimal("1.09000")
        assert ohlcv.close == Decimal("1.10500")
        assert ohlcv.volume == Decimal("1000000")
        assert ohlcv.tick_volume is None
        assert ohlcv.spread is None
        assert ohlcv.bar_type == BarType.M1

    def test_full_construction(self) -> None:
        ts = datetime.now(timezone.utc)
        ohlcv = OHLCV(
            symbol="EURUSD",
            timestamp=ts,
            open=Decimal("1.10000"),
            high=Decimal("1.11000"),
            low=Decimal("1.09000"),
            close=Decimal("1.10500"),
            volume=Decimal("1000000"),
            tick_volume=Decimal("5000"),
            spread=Decimal("0.0001"),
            bar_type=BarType.H1,
        )
        assert ohlcv.tick_volume == Decimal("5000")
        assert ohlcv.spread == Decimal("0.0001")
        assert ohlcv.bar_type == BarType.H1

    def test_frozen(self) -> None:
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
        with pytest.raises(AttributeError):
            ohlcv.open = Decimal("1.12")  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════
# Bar
# ═══════════════════════════════════════════════════════════════════════


class TestBar:
    """Test Bar model."""

    def test_default_construction(self) -> None:
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
        assert bar.symbol == "EURUSD"
        assert bar.bar_type == BarType.M5
        assert bar.ohlcv == ohlcv
        assert bar.vwap is None
        assert bar.count == 0

    def test_with_vwap(self) -> None:
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
            vwap=Decimal("1.1030"),
            count=250,
        )
        assert bar.vwap == Decimal("1.1030")
        assert bar.count == 250

    def test_frozen(self) -> None:
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
        with pytest.raises(AttributeError):
            bar.vwap = Decimal("1.11")  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════
# BookLevel
# ═══════════════════════════════════════════════════════════════════════


class TestBookLevel:
    """Test BookLevel model."""

    def test_default_construction(self) -> None:
        level = BookLevel(price=Decimal("1.12345"), volume=Decimal("1000000"))
        assert level.price == Decimal("1.12345")
        assert level.volume == Decimal("1000000")
        assert level.order_count == 0

    def test_with_order_count(self) -> None:
        level = BookLevel(
            price=Decimal("1.12345"),
            volume=Decimal("1000000"),
            order_count=5,
        )
        assert level.order_count == 5

    def test_frozen(self) -> None:
        level = BookLevel(price=Decimal("1.12"), volume=Decimal("1000"))
        with pytest.raises(AttributeError):
            level.price = Decimal("1.13")  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════
# OrderBook
# ═══════════════════════════════════════════════════════════════════════


class TestOrderBook:
    """Test OrderBook model."""

    def test_default_construction(self) -> None:
        ts = datetime.now(timezone.utc)
        ob = OrderBook(symbol="EURUSD", timestamp=ts)
        assert ob.symbol == "EURUSD"
        assert ob.bids == ()
        assert ob.asks == ()
        assert ob.depth == 0

    def test_with_levels(self) -> None:
        ts = datetime.now(timezone.utc)
        bid = BookLevel(price=Decimal("1.12340"), volume=Decimal("1000000"))
        ask = BookLevel(price=Decimal("1.12350"), volume=Decimal("500000"))
        ob = OrderBook(
            symbol="EURUSD",
            timestamp=ts,
            bids=(bid,),
            asks=(ask,),
            depth=1,
        )
        assert len(ob.bids) == 1
        assert len(ob.asks) == 1
        assert ob.depth == 1

    def test_frozen(self) -> None:
        ts = datetime.now(timezone.utc)
        ob = OrderBook(symbol="EURUSD", timestamp=ts)
        with pytest.raises(AttributeError):
            ob.symbol = "GBPUSD"  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════
# OrderBookSnapshot
# ═══════════════════════════════════════════════════════════════════════


class TestOrderBookSnapshot:
    """Test OrderBookSnapshot model."""

    def test_default_construction(self) -> None:
        ts = datetime.now(timezone.utc)
        snap = OrderBookSnapshot(symbol="EURUSD", timestamp=ts)
        assert snap.symbol == "EURUSD"
        assert snap.bids == ()
        assert snap.asks == ()
        assert snap.sequence == 0
        assert snap.snapshot_type == "snapshot"

    def test_incremental_type(self) -> None:
        ts = datetime.now(timezone.utc)
        snap = OrderBookSnapshot(
            symbol="EURUSD",
            timestamp=ts,
            snapshot_type="incremental",
            sequence=42,
        )
        assert snap.snapshot_type == "incremental"
        assert snap.sequence == 42

    def test_frozen(self) -> None:
        ts = datetime.now(timezone.utc)
        snap = OrderBookSnapshot(symbol="EURUSD", timestamp=ts)
        with pytest.raises(AttributeError):
            snap.sequence = 1  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════
# MarketSession
# ═══════════════════════════════════════════════════════════════════════


class TestMarketSession:
    """Test MarketSession model."""

    def test_default_construction(self) -> None:
        open_ts = datetime.now(timezone.utc)
        close_ts = datetime.now(timezone.utc)
        session = MarketSession(
            session_type=MarketSessionType.LONDON,
            symbol="EURUSD",
            open_time=open_ts,
            close_time=close_ts,
        )
        assert session.session_type == MarketSessionType.LONDON
        assert session.symbol == "EURUSD"
        assert session.open_time == open_ts
        assert session.close_time == close_ts
        assert session.description == ""

    def test_with_description(self) -> None:
        open_ts = datetime.now(timezone.utc)
        close_ts = datetime.now(timezone.utc)
        session = MarketSession(
            session_type=MarketSessionType.ASIAN,
            symbol="USDJPY",
            open_time=open_ts,
            close_time=close_ts,
            description="Asian session",
        )
        assert session.description == "Asian session"

    def test_frozen(self) -> None:
        open_ts = datetime.now(timezone.utc)
        close_ts = datetime.now(timezone.utc)
        session = MarketSession(
            session_type=MarketSessionType.LONDON,
            symbol="EURUSD",
            open_time=open_ts,
            close_time=close_ts,
        )
        with pytest.raises(AttributeError):
            session.symbol = "GBPUSD"  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════
# CorporateAction
# ═══════════════════════════════════════════════════════════════════════


class TestCorporateAction:
    """Test CorporateAction model."""

    def test_default_construction(self) -> None:
        ann_date = datetime.now(timezone.utc)
        eff_date = datetime.now(timezone.utc)
        ca = CorporateAction(
            symbol="AAPL",
            action_type=CorporateActionType.DIVIDEND,
            announcement_date=ann_date,
            effective_date=eff_date,
        )
        assert ca.symbol == "AAPL"
        assert ca.action_type == CorporateActionType.DIVIDEND
        assert ca.announcement_date == ann_date
        assert ca.effective_date == eff_date
        assert ca.description == ""
        assert ca.ratio is None
        assert ca.dividend_amount is None

    def test_stock_split(self) -> None:
        ann_date = datetime.now(timezone.utc)
        eff_date = datetime.now(timezone.utc)
        ca = CorporateAction(
            symbol="AAPL",
            action_type=CorporateActionType.STOCK_SPLIT,
            announcement_date=ann_date,
            effective_date=eff_date,
            ratio=Decimal("4"),
            description="4:1 stock split",
        )
        assert ca.ratio == Decimal("4")
        assert ca.description == "4:1 stock split"

    def test_dividend(self) -> None:
        ann_date = datetime.now(timezone.utc)
        eff_date = datetime.now(timezone.utc)
        ca = CorporateAction(
            symbol="MSFT",
            action_type=CorporateActionType.DIVIDEND,
            announcement_date=ann_date,
            effective_date=eff_date,
            dividend_amount=Decimal("0.75"),
            description="Quarterly dividend",
        )
        assert ca.dividend_amount == Decimal("0.75")

    def test_frozen(self) -> None:
        ann_date = datetime.now(timezone.utc)
        eff_date = datetime.now(timezone.utc)
        ca = CorporateAction(
            symbol="AAPL",
            action_type=CorporateActionType.DIVIDEND,
            announcement_date=ann_date,
            effective_date=eff_date,
        )
        with pytest.raises(AttributeError):
            ca.symbol = "MSFT"  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════
# EconomicEvent
# ═══════════════════════════════════════════════════════════════════════


class TestEconomicEvent:
    """Test EconomicEvent model."""

    def test_default_construction(self) -> None:
        ts = datetime.now(timezone.utc)
        event = EconomicEvent(
            event_id="NFP-202401",
            title="Non-Farm Payrolls",
            timestamp=ts,
        )
        assert event.event_id == "NFP-202401"
        assert event.title == "Non-Farm Payrolls"
        assert event.timestamp == ts
        assert event.importance == EconomicEventImportance.MEDIUM
        assert event.currency == ""
        assert event.actual == ""
        assert event.forecast == ""
        assert event.previous == ""

    def test_full_construction(self) -> None:
        ts = datetime.now(timezone.utc)
        event = EconomicEvent(
            event_id="CPI-202401",
            title="CPI MoM",
            timestamp=ts,
            importance=EconomicEventImportance.HIGH,
            currency="USD",
            actual="0.3%",
            forecast="0.2%",
            previous="0.1%",
            description="Consumer Price Index monthly change",
        )
        assert event.importance == EconomicEventImportance.HIGH
        assert event.currency == "USD"
        assert event.actual == "0.3%"
        assert event.forecast == "0.2%"
        assert event.previous == "0.1%"

    def test_metadata(self) -> None:
        ts = datetime.now(timezone.utc)
        event = EconomicEvent(
            event_id="FOMC-202401",
            title="FOMC Rate Decision",
            timestamp=ts,
            metadata={"source": "reuters"},
        )
        assert event.metadata == {"source": "reuters"}

    def test_frozen(self) -> None:
        ts = datetime.now(timezone.utc)
        event = EconomicEvent(
            event_id="NFP-202401",
            title="Non-Farm Payrolls",
            timestamp=ts,
        )
        with pytest.raises(AttributeError):
            event.title = "CPI"  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════
# Dataclass Immutability
# ═══════════════════════════════════════════════════════════════════════


class TestDataclassImmutability:
    """Test all dataclass models are frozen."""

    @pytest.mark.parametrize(
        "model_class,kwargs",
        [
            (
                Tick,
                {
                    "symbol": "EURUSD",
                    "price": Decimal("1.10"),
                    "volume": Decimal("1000"),
                    "timestamp": datetime.now(timezone.utc),
                },
            ),
            (
                TickData,
                {"symbol": "EURUSD"},
            ),
            (
                TradeTick,
                {
                    "symbol": "EURUSD",
                    "price": Decimal("1.10"),
                    "volume": Decimal("1000"),
                    "timestamp": datetime.now(timezone.utc),
                },
            ),
            (
                Quote,
                {
                    "symbol": "EURUSD",
                    "bid": Decimal("1.12"),
                    "ask": Decimal("1.13"),
                    "timestamp": datetime.now(timezone.utc),
                },
            ),
            (
                Trade,
                {
                    "trade_id": "t1",
                    "symbol": "EURUSD",
                    "price": Decimal("1.10"),
                    "volume": Decimal("1000"),
                    "timestamp": datetime.now(timezone.utc),
                },
            ),
            (
                OHLCV,
                {
                    "symbol": "EURUSD",
                    "timestamp": datetime.now(timezone.utc),
                    "open": Decimal("1.10"),
                    "high": Decimal("1.11"),
                    "low": Decimal("1.09"),
                    "close": Decimal("1.105"),
                    "volume": Decimal("1000"),
                },
            ),
            (
                BookLevel,
                {"price": Decimal("1.12"), "volume": Decimal("1000")},
            ),
            (
                OrderBook,
                {"symbol": "EURUSD", "timestamp": datetime.now(timezone.utc)},
            ),
            (
                OrderBookSnapshot,
                {"symbol": "EURUSD", "timestamp": datetime.now(timezone.utc)},
            ),
            (
                MarketSession,
                {
                    "session_type": MarketSessionType.LONDON,
                    "symbol": "EURUSD",
                    "open_time": datetime.now(timezone.utc),
                    "close_time": datetime.now(timezone.utc),
                },
            ),
            (
                CorporateAction,
                {
                    "symbol": "AAPL",
                    "action_type": CorporateActionType.DIVIDEND,
                    "announcement_date": datetime.now(timezone.utc),
                    "effective_date": datetime.now(timezone.utc),
                },
            ),
            (
                EconomicEvent,
                {
                    "event_id": "NFP-202401",
                    "title": "NFP",
                    "timestamp": datetime.now(timezone.utc),
                },
            ),
        ],
    )
    def test_dataclass_is_frozen(self, model_class, kwargs) -> None:
        import dataclasses

        instance = model_class(**kwargs)
        assert dataclasses.is_dataclass(instance)
        assert instance.__dataclass_params__.frozen is True

    @pytest.mark.parametrize(
        "model_class,kwargs",
        [
            (
                Tick,
                {
                    "symbol": "EURUSD",
                    "price": Decimal("1.10"),
                    "volume": Decimal("1000"),
                    "timestamp": datetime.now(timezone.utc),
                },
            ),
            (
                TickData,
                {"symbol": "EURUSD"},
            ),
            (
                TradeTick,
                {
                    "symbol": "EURUSD",
                    "price": Decimal("1.10"),
                    "volume": Decimal("1000"),
                    "timestamp": datetime.now(timezone.utc),
                },
            ),
            (
                Quote,
                {
                    "symbol": "EURUSD",
                    "bid": Decimal("1.12"),
                    "ask": Decimal("1.13"),
                    "timestamp": datetime.now(timezone.utc),
                },
            ),
            (
                Trade,
                {
                    "trade_id": "t1",
                    "symbol": "EURUSD",
                    "price": Decimal("1.10"),
                    "volume": Decimal("1000"),
                    "timestamp": datetime.now(timezone.utc),
                },
            ),
            (
                OHLCV,
                {
                    "symbol": "EURUSD",
                    "timestamp": datetime.now(timezone.utc),
                    "open": Decimal("1.10"),
                    "high": Decimal("1.11"),
                    "low": Decimal("1.09"),
                    "close": Decimal("1.105"),
                    "volume": Decimal("1000"),
                },
            ),
            (
                Bar,
                {
                    "symbol": "EURUSD",
                    "bar_type": BarType.M5,
                    "timestamp": datetime.now(timezone.utc),
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
            (
                BookLevel,
                {"price": Decimal("1.12"), "volume": Decimal("1000")},
            ),
        ],
    )
    def test_dataclass_has_slots(self, model_class, kwargs) -> None:
        import dataclasses

        instance = model_class(**kwargs)
        assert dataclasses.is_dataclass(instance)
        assert hasattr(instance, "__slots__")

