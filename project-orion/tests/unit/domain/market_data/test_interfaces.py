"""Contract tests for EPIC-014 Market Data Protocol interfaces."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pytest

from libraries.domain.market_data.interfaces import (
    BarBuilderPort,
    CorporateActionProviderPort,
    EconomicCalendarPort,
    HistoricalDataProviderPort,
    MarketDataConsumerPort,
    MarketSnapshotProviderPort,
    OrderBookProviderPort,
    SessionCalendarPort,
    TickDataProviderPort,
)


class TestProtocolInterfaces:
    """Test all protocol interfaces are properly defined."""

    @pytest.mark.parametrize(
        "protocol_cls",
        [
            TickDataProviderPort,
            HistoricalDataProviderPort,
            OrderBookProviderPort,
            SessionCalendarPort,
            CorporateActionProviderPort,
            EconomicCalendarPort,
            MarketDataConsumerPort,
            BarBuilderPort,
            MarketSnapshotProviderPort,
        ],
    )
    def test_protocol_is_runtime_checkable(self, protocol_cls) -> None:
        assert issubclass(protocol_cls, Protocol)
        assert hasattr(protocol_cls, "__instancecheck__")

    def test_tick_data_provider_has_required_methods(self) -> None:
        assert hasattr(TickDataProviderPort, "subscribe")
        assert hasattr(TickDataProviderPort, "unsubscribe")
        assert hasattr(TickDataProviderPort, "stream")
        assert hasattr(TickDataProviderPort, "latest_tick")
        assert hasattr(TickDataProviderPort, "is_connected")

    def test_historical_data_provider_has_required_methods(self) -> None:
        assert hasattr(HistoricalDataProviderPort, "load_bars")
        assert hasattr(HistoricalDataProviderPort, "load_ticks")
        assert hasattr(HistoricalDataProviderPort, "validate_availability")
        assert hasattr(HistoricalDataProviderPort, "available_symbols")
        assert hasattr(HistoricalDataProviderPort, "available_bar_types")
        assert hasattr(HistoricalDataProviderPort, "date_range")

    def test_order_book_provider_has_required_methods(self) -> None:
        assert hasattr(OrderBookProviderPort, "subscribe")
        assert hasattr(OrderBookProviderPort, "unsubscribe")
        assert hasattr(OrderBookProviderPort, "stream")
        assert hasattr(OrderBookProviderPort, "snapshot")

    def test_session_calendar_has_required_methods(self) -> None:
        assert hasattr(SessionCalendarPort, "active_sessions")
        assert hasattr(SessionCalendarPort, "is_market_open")
        assert hasattr(SessionCalendarPort, "next_session_open")
        assert hasattr(SessionCalendarPort, "next_session_close")

    def test_corporate_action_provider_has_required_methods(self) -> None:
        assert hasattr(CorporateActionProviderPort, "get_actions")
        assert hasattr(CorporateActionProviderPort, "get_upcoming_actions")

    def test_economic_calendar_has_required_methods(self) -> None:
        assert hasattr(EconomicCalendarPort, "get_events")
        assert hasattr(EconomicCalendarPort, "get_high_impact_events")

    def test_market_data_consumer_has_required_methods(self) -> None:
        assert hasattr(MarketDataConsumerPort, "on_tick")
        assert hasattr(MarketDataConsumerPort, "on_bar")
        assert hasattr(MarketDataConsumerPort, "on_order_book")

    def test_bar_builder_has_required_methods(self) -> None:
        assert hasattr(BarBuilderPort, "add_tick")
        assert hasattr(BarBuilderPort, "current_bar")

    def test_market_snapshot_provider_has_required_methods(self) -> None:
        assert hasattr(MarketSnapshotProviderPort, "snapshot")
        assert hasattr(MarketSnapshotProviderPort, "latest")
        assert hasattr(MarketSnapshotProviderPort, "stream")

    def test_tick_data_provider_method_signatures(self) -> None:
        import inspect
        import typing

        hints = typing.get_type_hints(TickDataProviderPort.subscribe)
        assert "symbols" in hints
        assert hints["symbols"] == list[str]

        sig = inspect.signature(TickDataProviderPort.latest_tick)
        assert "symbol" in sig.parameters

        hints = typing.get_type_hints(TickDataProviderPort.is_connected)
        assert hints.get("return") is bool

    def test_historical_data_provider_method_signatures(self) -> None:
        import inspect

        sig = inspect.signature(HistoricalDataProviderPort.load_bars)
        params = sig.parameters
        assert "symbol" in params
        assert "bar_type" in params
        assert "start" in params
        assert "end" in params

    def test_order_book_provider_method_signatures(self) -> None:
        import inspect

        sig = inspect.signature(OrderBookProviderPort.subscribe)
        params = sig.parameters
        assert "symbols" in params
        assert "depth" in params
        assert params["depth"].default == 10

    def test_session_calendar_method_signatures(self) -> None:
        import inspect

        sig = inspect.signature(SessionCalendarPort.active_sessions)
        assert "symbol" in sig.parameters
        assert "instant" in sig.parameters

        sig = inspect.signature(SessionCalendarPort.is_market_open)
        assert "symbol" in sig.parameters

    def test_market_data_consumer_method_signatures(self) -> None:
        import inspect

        for method_name in ("on_tick", "on_bar", "on_order_book"):
            sig = inspect.signature(getattr(MarketDataConsumerPort, method_name))
            params = sig.parameters
            # All have at least one parameter (self not counted)
            assert len([p for p in params if p != "return"]) >= 1


class TestProtocolAliases:
    """Test backward-compatible aliases and exports."""

    def test_market_snapshot_provider_port_is_exported(self) -> None:
        from libraries.domain.market_data import MarketSnapshotProviderPort

        assert MarketSnapshotProviderPort is MarketSnapshotProviderPort

    def test_all_protocols_accessible_from_init(self) -> None:
        from libraries.domain.market_data import (
            BarBuilderPort,
            CorporateActionProviderPort,
            EconomicCalendarPort,
            HistoricalDataProviderPort,
            MarketDataConsumerPort,
            MarketSnapshotProviderPort,
            OrderBookProviderPort,
            SessionCalendarPort,
            TickDataProviderPort,
        )

        assert TickDataProviderPort is TickDataProviderPort
        assert HistoricalDataProviderPort is HistoricalDataProviderPort
        assert OrderBookProviderPort is OrderBookProviderPort
        assert SessionCalendarPort is SessionCalendarPort
        assert CorporateActionProviderPort is CorporateActionProviderPort
        assert EconomicCalendarPort is EconomicCalendarPort
        assert MarketDataConsumerPort is MarketDataConsumerPort
        assert BarBuilderPort is BarBuilderPort
        assert MarketSnapshotProviderPort is MarketSnapshotProviderPort

