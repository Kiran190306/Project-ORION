"""Tests for EPIC-014 Market Data validation layer."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.market_data.exceptions import (
    InvalidTickError,
    SymbolNotFoundError,
    UnsupportedBarTypeError,
)
from libraries.domain.market_data.validation import (
    validate_bar_type,
    validate_optional_price,
    validate_price,
    validate_symbol,
    validate_tick_fields,
    validate_timestamp,
    validate_volume,
)


class TestValidatePrice:
    """Test validate_price function."""

    def test_valid_price(self) -> None:
        result = validate_price(Decimal("1.12345"))
        assert result == Decimal("1.12345")

    def test_min_price(self) -> None:
        result = validate_price(Decimal("0.00000001"))
        assert result == Decimal("0.00000001")

    def test_max_price(self) -> None:
        result = validate_price(Decimal("999999999.99999999"))
        assert result == Decimal("999999999.99999999")

    def test_price_below_minimum_raises_error(self) -> None:
        with pytest.raises(InvalidTickError, match="below minimum"):
            validate_price(Decimal("0.000000001"))

    def test_price_above_maximum_raises_error(self) -> None:
        with pytest.raises(InvalidTickError, match="exceeds maximum"):
            validate_price(Decimal("1000000000"))

    def test_non_decimal_raises_error(self) -> None:
        with pytest.raises(InvalidTickError, match="must be a Decimal"):
            validate_price(1.50)  # type: ignore[arg-type]

    def test_custom_field_name(self) -> None:
        with pytest.raises(InvalidTickError, match="custom_price"):
            validate_price(Decimal("-1"), field_name="custom_price")


class TestValidateVolume:
    """Test validate_volume function."""

    def test_valid_volume(self) -> None:
        result = validate_volume(Decimal("1000000"))
        assert result == Decimal("1000000")

    def test_zero_volume(self) -> None:
        result = validate_volume(Decimal("0"))
        assert result == Decimal("0")

    def test_negative_volume_raises_error(self) -> None:
        with pytest.raises(InvalidTickError, match="negative"):
            validate_volume(Decimal("-1"))

    def test_max_volume(self) -> None:
        result = validate_volume(Decimal("9999999999999.99999999"))
        assert result == Decimal("9999999999999.99999999")

    def test_volume_exceeds_maximum_raises_error(self) -> None:
        with pytest.raises(InvalidTickError, match="exceeds maximum"):
            validate_volume(Decimal("10000000000000"))

    def test_non_decimal_raises_error(self) -> None:
        with pytest.raises(InvalidTickError, match="must be a Decimal"):
            validate_volume(1000)  # type: ignore[arg-type]


class TestValidateSymbol:
    """Test validate_symbol function."""

    def test_valid_symbol(self) -> None:
        result = validate_symbol("EURUSD")
        assert result == "EURUSD"

    def test_symbol_is_uppercased(self) -> None:
        result = validate_symbol("eurusd")
        assert result == "EURUSD"

    def test_symbol_is_stripped(self) -> None:
        result = validate_symbol("  EURUSD  ")
        assert result == "EURUSD"

    def test_empty_symbol_raises_error(self) -> None:
        with pytest.raises(SymbolNotFoundError, match="cannot be empty"):
            validate_symbol("")

    def test_whitespace_only_symbol_raises_error(self) -> None:
        with pytest.raises(SymbolNotFoundError, match="cannot be empty"):
            validate_symbol("   ")

    def test_symbol_too_long_raises_error(self) -> None:
        with pytest.raises(SymbolNotFoundError, match="exceeds maximum"):
            validate_symbol("A" * 51)

    def test_non_string_raises_error(self) -> None:
        with pytest.raises(SymbolNotFoundError, match="must be a string"):
            validate_symbol(123)  # type: ignore[arg-type]


class TestValidateTimestamp:
    """Test validate_timestamp function."""

    def test_valid_timestamp(self) -> None:
        ts = datetime.now(timezone.utc)
        result = validate_timestamp(ts)
        assert result == ts

    def test_none_timestamp_raises_error(self) -> None:
        with pytest.raises(InvalidTickError, match="must not be None"):
            validate_timestamp(None)

    def test_future_timestamp_raises_error(self) -> None:
        from datetime import timedelta

        future = datetime.now(timezone.utc) + timedelta(days=1)
        with pytest.raises(InvalidTickError, match="in the future"):
            validate_timestamp(future)

    def test_future_timestamp_allowed_when_flag_set(self) -> None:
        from datetime import timedelta

        future = datetime.now(timezone.utc) + timedelta(days=1)
        result = validate_timestamp(future, allow_future=True)
        assert result == future

    def test_non_datetime_raises_error(self) -> None:
        with pytest.raises(InvalidTickError, match="must be a datetime"):
            validate_timestamp("2024-01-01")  # type: ignore[arg-type]

    def test_custom_field_name(self) -> None:
        with pytest.raises(InvalidTickError, match="custom_ts"):
            validate_timestamp(None, field_name="custom_ts")


class TestValidateBarType:
    """Test validate_bar_type function."""

    def test_valid_bar_types(self) -> None:
        valid_types = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1mo"]
        for bt in valid_types:
            result = validate_bar_type(bt)
            assert result == bt

    def test_bar_type_is_normalized(self) -> None:
        result = validate_bar_type("  1H  ")
        assert result == "1h"

    def test_unsupported_bar_type_raises_error(self) -> None:
        with pytest.raises(UnsupportedBarTypeError, match="Unsupported"):
            validate_bar_type("2h")

    def test_invalid_format_raises_error(self) -> None:
        with pytest.raises(UnsupportedBarTypeError, match="Unsupported"):
            validate_bar_type("abc")

    def test_non_string_raises_error(self) -> None:
        with pytest.raises(UnsupportedBarTypeError, match="must be a string"):
            validate_bar_type(123)  # type: ignore[arg-type]


class TestValidateOptionalPrice:
    """Test validate_optional_price function."""

    def test_none_returns_none(self) -> None:
        result = validate_optional_price(None)
        assert result is None

    def test_valid_price(self) -> None:
        result = validate_optional_price(Decimal("1.12345"))
        assert result == Decimal("1.12345")

    def test_invalid_price_raises_error(self) -> None:
        with pytest.raises(InvalidTickError):
            validate_optional_price(Decimal("-1"))


class TestValidateTickFields:
    """Test validate_tick_fields convenience function."""

    def test_all_valid_fields(self) -> None:
        ts = datetime.now(timezone.utc)
        result = validate_tick_fields(
            symbol="EURUSD",
            price=Decimal("1.12345"),
            volume=Decimal("1000000"),
            timestamp=ts,
            extra_field="value",
        )
        assert result["symbol"] == "EURUSD"
        assert result["price"] == Decimal("1.12345")
        assert result["volume"] == Decimal("1000000")
        assert result["timestamp"] == ts
        assert result["extra_field"] == "value"

    def test_empty_symbol_raises_error(self) -> None:
        with pytest.raises(SymbolNotFoundError):
            validate_tick_fields(symbol="")

    def test_invalid_price_raises_error(self) -> None:
        with pytest.raises(InvalidTickError):
            validate_tick_fields(price=Decimal("-1"))

    def test_partial_fields(self) -> None:
        result = validate_tick_fields(symbol="EURUSD")
        assert result["symbol"] == "EURUSD"
        assert "price" not in result
        assert "volume" not in result
        assert "timestamp" not in result

    def test_empty_kwargs(self) -> None:
        result = validate_tick_fields()
        assert result == {}

