"""Validation utilities for the Market Data Abstraction Layer.

Provides pure functions for validating market data primitives: prices,
symbols, timestamps, bar types, and order book levels. All validators
raise domain-specific exceptions on failure.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.market_data.exceptions import (
    InvalidTickError,
    SymbolNotFoundError,
    UnsupportedBarTypeError,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MIN_PRICE = Decimal("0.00000001")
_MAX_PRICE = Decimal("999999999.99999999")
_MIN_VOLUME = Decimal("0")
_MAX_VOLUME = Decimal("9999999999999.99999999")
_MAX_SYMBOL_LENGTH = 50
_SUPPORTED_BAR_TYPES: frozenset[str] = frozenset({
    "1m", "5m", "15m", "30m",
    "1h", "4h",
    "1d", "1w", "1mo",
})

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_price(value: Decimal, field_name: str = "price") -> Decimal:
    """Validate a price value is within acceptable bounds.

    Args:
        value: The price to validate.
        field_name: Name of the field for error messages.

    Returns:
        The validated price.

    Raises:
        InvalidTickError: If price is out of range or has wrong precision.
    """
    if not isinstance(value, Decimal):
        raise InvalidTickError(f"{field_name} must be a Decimal, got {type(value).__name__}")
    if value < _MIN_PRICE:
        raise InvalidTickError(f"{field_name} ({value}) is below minimum ({_MIN_PRICE})")
    if value > _MAX_PRICE:
        raise InvalidTickError(f"{field_name} ({value}) exceeds maximum ({_MAX_PRICE})")
    return value


def validate_volume(value: Decimal, field_name: str = "volume") -> Decimal:
    """Validate a volume value is within acceptable bounds.

    Args:
        value: The volume to validate.
        field_name: Name of the field for error messages.

    Returns:
        The validated volume.

    Raises:
        InvalidTickError: If volume is negative or exceeds maximum.
    """
    if not isinstance(value, Decimal):
        raise InvalidTickError(f"{field_name} must be a Decimal, got {type(value).__name__}")
    if value <= _MIN_VOLUME and value != _MIN_VOLUME:
        raise InvalidTickError(f"{field_name} ({value}) is negative")
    if value > _MAX_VOLUME:
        raise InvalidTickError(f"{field_name} ({value}) exceeds maximum ({_MAX_VOLUME})")
    return value


def validate_symbol(symbol: str) -> str:
    """Validate a financial instrument symbol.

    Args:
        symbol: The symbol to validate (e.g. EURUSD, AAPL).

    Returns:
        The validated symbol in standardised form (uppercase, stripped).

    Raises:
        SymbolNotFoundError: If the symbol is empty or too long.
    """
    if not isinstance(symbol, str):
        raise SymbolNotFoundError(f"Symbol must be a string, got {type(symbol).__name__}")
    cleaned = symbol.strip().upper()
    if not cleaned:
        raise SymbolNotFoundError("Symbol cannot be empty")
    if len(cleaned) > _MAX_SYMBOL_LENGTH:
        raise SymbolNotFoundError(
            f"Symbol length {len(cleaned)} exceeds maximum {_MAX_SYMBOL_LENGTH}"
        )
    return cleaned


def validate_timestamp(
    value: datetime | None,
    field_name: str = "timestamp",
    allow_future: bool = False,
) -> datetime:
    """Validate a timestamp is not None and optionally not in the future.

    Args:
        value: The timestamp to validate.
        field_name: Name of the field for error messages.
        allow_future: If True, allow timestamps in the future.

    Returns:
        The validated timestamp.

    Raises:
        InvalidTickError: If timestamp is None or in the future (when
            ``allow_future`` is False).
    """
    if value is None:
        raise InvalidTickError(f"{field_name} must not be None")
    if not isinstance(value, datetime):
        raise InvalidTickError(
            f"{field_name} must be a datetime, got {type(value).__name__}"
        )
    if not allow_future and value > datetime.now(timezone.utc):
        raise InvalidTickError(f"{field_name} ({value}) is in the future")
    return value


def validate_bar_type(bar_type: str) -> str:
    """Validate a bar type string is supported.

    Args:
        bar_type: The bar type string (e.g. '1m', '1h', '1d').

    Returns:
        The validated bar type.

    Raises:
        UnsupportedBarTypeError: If the bar type is not supported.
    """
    if not isinstance(bar_type, str):
        raise UnsupportedBarTypeError(
            f"Bar type must be a string, got {type(bar_type).__name__}"
        )
    normalized = bar_type.strip().lower()
    if normalized not in _SUPPORTED_BAR_TYPES:
        raise UnsupportedBarTypeError(
            f"Unsupported bar type '{bar_type}'. "
            f"Supported types: {', '.join(sorted(_SUPPORTED_BAR_TYPES))}"
        )
    return normalized


def validate_optional_price(
    value: Decimal | None,
    field_name: str = "price",
) -> Decimal | None:
    """Validate an optional price value, skipping if None."""
    if value is None:
        return None
    return validate_price(value, field_name)


def validate_tick_fields(
    *,
    symbol: str = "",
    price: Decimal | None = None,
    volume: Decimal | None = None,
    timestamp: datetime | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Validate common tick fields and return cleaned values.

    This is a convenience wrapper that validates the most common
    tick fields in one call. Additional keyword arguments are
    returned as-is.

    Args:
        symbol: The tick symbol.
        price: The tick price.
        volume: The tick volume.
        timestamp: The tick timestamp.
        **kwargs: Additional fields to pass through.

    Returns:
        A dict of cleaned/validated fields.
    """
    result: dict[str, Any] = {}
    if symbol:
        result["symbol"] = validate_symbol(symbol)
    if price is not None:
        result["price"] = validate_price(price)
    if volume is not None:
        result["volume"] = validate_volume(volume)
    if timestamp is not None:
        result["timestamp"] = validate_timestamp(timestamp)
    result.update(kwargs)
    return result
