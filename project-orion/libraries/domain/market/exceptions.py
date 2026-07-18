"""Exceptions raised by the Market Data Engine."""

from __future__ import annotations

from typing import Any

from shared.errors import MarketError


class MarketDataEngineError(MarketError):
    """Base exception for Market Data Engine operations."""

    def __init__(
        self,
        message: str,
        code: str = "MARKET_DATA_ENGINE_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class InvalidMarketDataError(MarketDataEngineError):
    """Raised when a market-data record violates a domain invariant."""

    def __init__(self, message: str, field: str | None = None) -> None:
        details = {"field": field} if field is not None else None
        super().__init__(message, code="INVALID_MARKET_DATA", details=details)


class UnknownSymbolError(MarketDataEngineError):
    """Raised when a requested market symbol is not registered."""

    def __init__(self, symbol: str) -> None:
        super().__init__(
            f"Symbol is not registered: {symbol}",
            code="UNKNOWN_SYMBOL",
            details={"symbol": symbol},
        )


class DuplicateSymbolError(MarketDataEngineError):
    """Raised when a symbol or alias would replace an existing registration."""

    def __init__(self, symbol: str) -> None:
        super().__init__(
            f"Symbol or alias is already registered: {symbol}",
            code="DUPLICATE_SYMBOL",
            details={"symbol": symbol},
        )


class InvalidSessionError(MarketDataEngineError):
    """Raised when a trading-session definition is invalid."""

    def __init__(self, message: str, session_id: str | None = None) -> None:
        details = {"session_id": session_id} if session_id is not None else None
        super().__init__(message, code="INVALID_SESSION", details=details)


class EngineNotRunningError(MarketDataEngineError):
    """Raised when data is submitted to a stopped market-data manager."""

    def __init__(self) -> None:
        super().__init__("Market Data Manager is not running", code="ENGINE_NOT_RUNNING")
