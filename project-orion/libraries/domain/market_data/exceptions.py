"""Domain exceptions for the Market Data Abstraction Layer."""

from __future__ import annotations


class MarketDataError(Exception):
    """Base exception for all market data errors."""


class ProviderConnectionError(MarketDataError):
    """Raised when connection to a data provider fails."""


class ProviderDisconnectedError(MarketDataError):
    """Raised when a data provider disconnects unexpectedly."""


class SymbolNotFoundError(MarketDataError):
    """Raised when a requested symbol is not found."""


class DataUnavailableError(MarketDataError):
    """Raised when requested historical data is not available."""


class InvalidTickError(MarketDataError):
    """Raised when a tick fails validation."""


class SubscriptionError(MarketDataError):
    """Raised when subscribing to a data feed fails."""


class UnsupportedBarTypeError(MarketDataError):
    """Raised when an unsupported bar type is requested."""


class SessionLookupError(MarketDataError):
    """Raised when market session data cannot be determined."""


class EconomicCalendarError(MarketDataError):
    """Raised when economic calendar data cannot be fetched."""
