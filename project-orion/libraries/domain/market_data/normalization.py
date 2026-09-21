"""Canonical normalization utilities for Forex market data symbols and timeframes."""

from __future__ import annotations

from decimal import Decimal

from libraries.domain.market_data.exceptions import (
    SymbolNotFoundError,
    UnsupportedBarTypeError,
)
from libraries.domain.market_data.models import BarType, Instrument

_CANONICAL_INSTRUMENTS: dict[str, Instrument] = {
    "EUR/USD": Instrument(
        symbol="EUR/USD",
        base_currency="EUR",
        quote_currency="USD",
        pip_size=Decimal("0.0001"),
        tick_size=Decimal("0.00001"),
        display_name="Euro / US Dollar",
        is_active=True,
    ),
    "GBP/USD": Instrument(
        symbol="GBP/USD",
        base_currency="GBP",
        quote_currency="USD",
        pip_size=Decimal("0.0001"),
        tick_size=Decimal("0.00001"),
        display_name="British Pound / US Dollar",
        is_active=True,
    ),
    "USD/JPY": Instrument(
        symbol="USD/JPY",
        base_currency="USD",
        quote_currency="JPY",
        pip_size=Decimal("0.01"),
        tick_size=Decimal("0.001"),
        display_name="US Dollar / Japanese Yen",
        is_active=True,
    ),
    "USD/CHF": Instrument(
        symbol="USD/CHF",
        base_currency="USD",
        quote_currency="CHF",
        pip_size=Decimal("0.0001"),
        tick_size=Decimal("0.00001"),
        display_name="US Dollar / Swiss Franc",
        is_active=True,
    ),
    "AUD/USD": Instrument(
        symbol="AUD/USD",
        base_currency="AUD",
        quote_currency="USD",
        pip_size=Decimal("0.0001"),
        tick_size=Decimal("0.00001"),
        display_name="Australian Dollar / US Dollar",
        is_active=True,
    ),
    "USD/CAD": Instrument(
        symbol="USD/CAD",
        base_currency="USD",
        quote_currency="CAD",
        pip_size=Decimal("0.0001"),
        tick_size=Decimal("0.00001"),
        display_name="US Dollar / Canadian Dollar",
        is_active=True,
    ),
    "NZD/USD": Instrument(
        symbol="NZD/USD",
        base_currency="NZD",
        quote_currency="USD",
        pip_size=Decimal("0.0001"),
        tick_size=Decimal("0.00001"),
        display_name="New Zealand Dollar / US Dollar",
        is_active=True,
    ),
    "XAU/USD": Instrument(
        symbol="XAU/USD",
        base_currency="XAU",
        quote_currency="USD",
        pip_size=Decimal("0.10"),
        tick_size=Decimal("0.01"),
        display_name="Gold Spot / US Dollar",
        is_active=True,
    ),
}

_COMMON_SYMBOL_ALIASES: dict[str, str] = {
    "EURUSD": "EUR/USD",
    "EUR_USD": "EUR/USD",
    "EUR-USD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "GBP_USD": "GBP/USD",
    "GBP-USD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "USD_JPY": "USD/JPY",
    "USD-JPY": "USD/JPY",
    "USDCHF": "USD/CHF",
    "USD_CHF": "USD/CHF",
    "USD-CHF": "USD/CHF",
    "AUDUSD": "AUD/USD",
    "AUD_USD": "AUD/USD",
    "AUD-USD": "AUD/USD",
    "USDCAD": "USD/CAD",
    "USD_CAD": "USD/CAD",
    "USD-CAD": "USD/CAD",
    "NZDUSD": "NZD/USD",
    "NZD_USD": "NZD/USD",
    "NZD-USD": "NZD/USD",
    "XAUUSD": "XAU/USD",
    "XAU_USD": "XAU/USD",
    "XAU-USD": "XAU/USD",
}

_TIMEFRAME_MAP: dict[str, BarType] = {
    "1M": BarType.M1,
    "M1": BarType.M1,
    "1MIN": BarType.M1,
    "60": BarType.M1,
    "5M": BarType.M5,
    "M5": BarType.M5,
    "5MIN": BarType.M5,
    "300": BarType.M5,
    "15M": BarType.M15,
    "M15": BarType.M15,
    "15MIN": BarType.M15,
    "900": BarType.M15,
    "30M": BarType.M30,
    "M30": BarType.M30,
    "30MIN": BarType.M30,
    "1800": BarType.M30,
    "1H": BarType.H1,
    "H1": BarType.H1,
    "60MIN": BarType.H1,
    "3600": BarType.H1,
    "4H": BarType.H4,
    "H4": BarType.H4,
    "240MIN": BarType.H4,
    "14400": BarType.H4,
    "1D": BarType.D1,
    "D1": BarType.D1,
    "DAILY": BarType.D1,
    "86400": BarType.D1,
    "1W": BarType.W1,
    "W1": BarType.W1,
    "WEEKLY": BarType.W1,
    "1MO": BarType.MN1,
    "MN1": BarType.MN1,
    "MONTHLY": BarType.MN1,
}


def normalize_symbol(raw_symbol: str) -> str:
    """Normalize a raw financial symbol into canonical ORION representation.

    Examples:
        EURUSD -> EUR/USD
        EUR_USD -> EUR/USD
        eur/usd -> EUR/USD

    Raises:
        SymbolNotFoundError: If symbol is unrecognized, empty, or invalid.
    """
    if not isinstance(raw_symbol, str):
        raise SymbolNotFoundError(f"Symbol must be a string, got {type(raw_symbol).__name__}")

    cleaned = raw_symbol.strip().upper()
    if not cleaned:
        raise SymbolNotFoundError("Symbol cannot be empty")

    if cleaned in _CANONICAL_INSTRUMENTS:
        return cleaned

    if cleaned in _COMMON_SYMBOL_ALIASES:
        return _COMMON_SYMBOL_ALIASES[cleaned]

    # Attempt replacement of separators
    sanitized = cleaned.replace("-", "/").replace("_", "/")
    if sanitized in _CANONICAL_INSTRUMENTS:
        return sanitized

    # If it's a 6-character alphabetic pair not yet in registry, format as XXX/YYY
    if len(cleaned) == 6 and cleaned.isalpha():
        candidate = f"{cleaned[:3]}/{cleaned[3:]}"
        if candidate in _CANONICAL_INSTRUMENTS:
            return candidate

    raise SymbolNotFoundError(f"Unrecognized financial symbol: '{raw_symbol}'")


def normalize_timeframe(raw_timeframe: str) -> BarType:
    """Normalize a timeframe string into canonical BarType.

    Examples:
        "1m", "M1", "60" -> BarType.M1
        "1h", "H1" -> BarType.H1

    Raises:
        UnsupportedBarTypeError: If timeframe is not recognized.
    """
    if not isinstance(raw_timeframe, str):
        raise UnsupportedBarTypeError(f"Timeframe must be a string, got {type(raw_timeframe).__name__}")

    cleaned = raw_timeframe.strip().upper()
    if not cleaned:
        raise UnsupportedBarTypeError("Timeframe cannot be empty")

    if cleaned in _TIMEFRAME_MAP:
        return _TIMEFRAME_MAP[cleaned]

    # Fallback checking BarType enum values directly
    for bar_type in BarType:
        if cleaned == bar_type.value.upper():
            return bar_type

    raise UnsupportedBarTypeError(f"Unsupported timeframe: '{raw_timeframe}'")


def canonical_instruments() -> dict[str, Instrument]:
    """Return dictionary of all active canonical instruments."""
    return dict(_CANONICAL_INSTRUMENTS)
