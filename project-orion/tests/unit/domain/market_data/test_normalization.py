"""Unit tests for market data symbol and timeframe normalization."""

from __future__ import annotations

from decimal import Decimal
import pytest

from libraries.domain.market_data.exceptions import (
    SymbolNotFoundError,
    UnsupportedBarTypeError,
)
from libraries.domain.market_data.models import BarType
from libraries.domain.market_data.normalization import (
    canonical_instruments,
    normalize_symbol,
    normalize_timeframe,
)


class TestSymbolNormalization:
    """Test canonical symbol normalization."""

    def test_already_canonical(self) -> None:
        assert normalize_symbol("EUR/USD") == "EUR/USD"
        assert normalize_symbol("GBP/USD") == "GBP/USD"
        assert normalize_symbol("USD/JPY") == "USD/JPY"

    def test_unseparated_six_char_symbol(self) -> None:
        assert normalize_symbol("EURUSD") == "EUR/USD"
        assert normalize_symbol("gbpusd") == "GBP/USD"
        assert normalize_symbol("usdjpy") == "USD/JPY"
        assert normalize_symbol("xauusd") == "XAU/USD"

    def test_underscore_and_hyphen_separators(self) -> None:
        assert normalize_symbol("EUR_USD") == "EUR/USD"
        assert normalize_symbol("GBP-USD") == "GBP/USD"
        assert normalize_symbol("usd_chf") == "USD/CHF"
        assert normalize_symbol("AUD-USD") == "AUD/USD"

    def test_whitespace_tolerance(self) -> None:
        assert normalize_symbol("  EUR/USD  ") == "EUR/USD"
        assert normalize_symbol("\tEURUSD\n") == "EUR/USD"

    def test_empty_symbol_raises_error(self) -> None:
        with pytest.raises(SymbolNotFoundError):
            normalize_symbol("")
        with pytest.raises(SymbolNotFoundError):
            normalize_symbol("   ")

    def test_invalid_type_raises_error(self) -> None:
        with pytest.raises(SymbolNotFoundError):
            normalize_symbol(123)  # type: ignore[arg-type]

    def test_unrecognized_symbol_raises_error(self) -> None:
        with pytest.raises(SymbolNotFoundError):
            normalize_symbol("UNKNOWN_COIN")
        with pytest.raises(SymbolNotFoundError):
            normalize_symbol("FAKE/SYM")


class TestTimeframeNormalization:
    """Test canonical timeframe normalization."""

    @pytest.mark.parametrize(
        ("input_tf", "expected"),
        [
            ("1m", BarType.M1),
            ("M1", BarType.M1),
            ("1min", BarType.M1),
            ("60", BarType.M1),
            ("5m", BarType.M5),
            ("M5", BarType.M5),
            ("5min", BarType.M5),
            ("15m", BarType.M15),
            ("M15", BarType.M15),
            ("30m", BarType.M30),
            ("M30", BarType.M30),
            ("1h", BarType.H1),
            ("H1", BarType.H1),
            ("60min", BarType.H1),
            ("4h", BarType.H4),
            ("H4", BarType.H4),
            ("1d", BarType.D1),
            ("D1", BarType.D1),
            ("daily", BarType.D1),
            ("1w", BarType.W1),
            ("W1", BarType.W1),
            ("1mo", BarType.MN1),
            ("MN1", BarType.MN1),
            ("monthly", BarType.MN1),
        ],
    )
    def test_valid_timeframes(self, input_tf: str, expected: BarType) -> None:
        assert normalize_timeframe(input_tf) == expected

    def test_invalid_timeframe_raises_error(self) -> None:
        with pytest.raises(UnsupportedBarTypeError):
            normalize_timeframe("2m")
        with pytest.raises(UnsupportedBarTypeError):
            normalize_timeframe("")
        with pytest.raises(UnsupportedBarTypeError):
            normalize_timeframe("invalid")


class TestCanonicalInstrumentsRegistry:
    """Test canonical instruments definitions."""

    def test_registry_contains_major_pairs(self) -> None:
        instruments = canonical_instruments()
        assert "EUR/USD" in instruments
        assert "GBP/USD" in instruments
        assert "USD/JPY" in instruments
        assert "XAU/USD" in instruments

        eurusd = instruments["EUR/USD"]
        assert eurusd.base_currency == "EUR"
        assert eurusd.quote_currency == "USD"
        assert eurusd.pip_size == Decimal("0.0001")
        assert eurusd.tick_size == Decimal("0.00001")
        assert eurusd.is_active is True
