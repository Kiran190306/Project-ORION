"""Tests for EPIC-014 Market Data exception hierarchy."""

from __future__ import annotations

import pytest

from libraries.domain.market_data.exceptions import (
    DataUnavailableError,
    EconomicCalendarError,
    InvalidTickError,
    MarketDataError,
    ProviderConnectionError,
    ProviderDisconnectedError,
    SessionLookupError,
    SubscriptionError,
    SymbolNotFoundError,
    UnsupportedBarTypeError,
)


class TestExceptionHierarchy:
    """Test the exception hierarchy structure."""

    def test_market_data_error_base(self) -> None:
        assert issubclass(MarketDataError, Exception)
        err = MarketDataError("test error")
        assert str(err) == "test error"

    def test_provider_connection_error_hierarchy(self) -> None:
        assert issubclass(ProviderConnectionError, MarketDataError)

    def test_provider_disconnected_error_hierarchy(self) -> None:
        assert issubclass(ProviderDisconnectedError, MarketDataError)

    def test_symbol_not_found_error_hierarchy(self) -> None:
        assert issubclass(SymbolNotFoundError, MarketDataError)

    def test_data_unavailable_error_hierarchy(self) -> None:
        assert issubclass(DataUnavailableError, MarketDataError)

    def test_invalid_tick_error_hierarchy(self) -> None:
        assert issubclass(InvalidTickError, MarketDataError)

    def test_subscription_error_hierarchy(self) -> None:
        assert issubclass(SubscriptionError, MarketDataError)

    def test_unsupported_bar_type_error_hierarchy(self) -> None:
        assert issubclass(UnsupportedBarTypeError, MarketDataError)

    def test_session_lookup_error_hierarchy(self) -> None:
        assert issubclass(SessionLookupError, MarketDataError)

    def test_economic_calendar_error_hierarchy(self) -> None:
        assert issubclass(EconomicCalendarError, MarketDataError)

    def test_all_exceptions_catchable_by_base(self) -> None:
        exceptions = [
            MarketDataError(),
            ProviderConnectionError(),
            ProviderDisconnectedError(),
            SymbolNotFoundError(),
            DataUnavailableError(),
            InvalidTickError(),
            SubscriptionError(),
            UnsupportedBarTypeError(),
            SessionLookupError(),
            EconomicCalendarError(),
        ]
        for exc in exceptions:
            assert isinstance(exc, MarketDataError)
            assert isinstance(exc, Exception)

    def test_exception_message_preserved(self) -> None:
        msg = "specific error message"
        err = MarketDataError(msg)
        assert str(err) == msg
        assert repr(msg) in repr(err)

    def test_exception_without_message(self) -> None:
        err = MarketDataError()
        assert str(err) == ""

    def test_error_raise_and_catch_base(self) -> None:
        with pytest.raises(MarketDataError):
            raise ProviderConnectionError("connection failed")

        with pytest.raises(MarketDataError):
            raise SymbolNotFoundError("symbol not found")

        with pytest.raises(MarketDataError):
            raise InvalidTickError("invalid tick")

    def test_error_raise_and_catch_specific(self) -> None:
        with pytest.raises(ProviderConnectionError):
            raise ProviderConnectionError("bad connection")

        with pytest.raises(SymbolNotFoundError):
            raise SymbolNotFoundError("missing symbol")

        with pytest.raises(InvalidTickError):
            raise InvalidTickError("bad tick")

    def test_provider_connection_error_message(self) -> None:
        err = ProviderConnectionError("Failed to connect to broker")
        assert "connect" in str(err)

    def test_symbol_not_found_error_message(self) -> None:
        err = SymbolNotFoundError("Symbol EURUSD not found in provider")
        assert "EURUSD" in str(err)

    def test_invalid_tick_error_message(self) -> None:
        err = InvalidTickError("Tick price exceeds maximum")
        assert "maximum" in str(err)

    def test_subscription_error_message(self) -> None:
        err = SubscriptionError("Cannot subscribe to empty symbol list")
        assert "subscribe" in str(err)

    def test_unsupported_bar_type_message(self) -> None:
        err = UnsupportedBarTypeError("Bar type '2h' is not supported")
        assert "2h" in str(err)

