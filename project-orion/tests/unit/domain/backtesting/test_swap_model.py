"""Tests for EPIC-010 SwapModel — overnight financing calculation."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.backtesting.swap_model import SwapModel, SwapModelConfig


class TestSwapModelConfig:
    """Test SwapModelConfig defaults."""

    def test_default_config(self):
        cfg = SwapModelConfig()
        assert cfg.long_swap_rate == Decimal("-2.0")
        assert cfg.short_swap_rate == Decimal("-1.5")
        assert cfg.triple_swap_day == 3  # Wednesday
        assert cfg.pip_size == Decimal("0.0001")
        assert cfg.currency == "USD"

    def test_custom_config(self):
        cfg = SwapModelConfig(
            long_swap_rate=Decimal("-1.0"),
            short_swap_rate=Decimal("0.5"),
            triple_swap_day=5,
            pip_size=Decimal("0.01"),
            currency="EUR",
        )
        assert cfg.long_swap_rate == Decimal("-1.0")
        assert cfg.short_swap_rate == Decimal("0.5")
        assert cfg.triple_swap_day == 5
        assert cfg.pip_size == Decimal("0.01")
        assert cfg.currency == "EUR"

    def test_config_frozen(self):
        cfg = SwapModelConfig()
        with pytest.raises(AttributeError):
            cfg.long_swap_rate = Decimal("-1.0")  # type: ignore[misc]


class TestSwapModel:
    """Test SwapModel calculation."""

    def test_default_initialization(self):
        model = SwapModel()
        assert model.config.long_swap_rate == Decimal("-2.0")

    def test_config_property(self):
        model = SwapModel()
        assert isinstance(model.config, SwapModelConfig)

    def test_long_swap_negative(self):
        model = SwapModel()
        result = model.calculate(Decimal("1"), "long", Decimal("100000"))
        # rate = -2.0, volume = 1, days = 1
        # swap_pips = -2.0 * 1 * 1 = -2.0
        # swap_amount = -2.0 * 0.0001 = -0.0002, rounded to -0.00
        assert result <= Decimal("0")

    def test_short_swap_negative(self):
        model = SwapModel()
        result = model.calculate(Decimal("1"), "short", Decimal("100000"))
        # rate = -1.5, volume = 1, days = 1
        assert result <= Decimal("0")

    def test_long_swap_positive_rate(self):
        cfg = SwapModelConfig(long_swap_rate=Decimal("1.0"))
        model = SwapModel(config=cfg)
        result = model.calculate(Decimal("1"), "long", Decimal("100000"))
        # swap_pips = 1.0 * 1 * 1 = 1.0
        # swap_amount = 1.0 * 0.0001 = 0.0001, rounded to 0.00
        assert result == Decimal("0.00")

    def test_long_swap_large_volume(self):
        cfg = SwapModelConfig(long_swap_rate=Decimal("2.0"))
        model = SwapModel(config=cfg)
        result = model.calculate(Decimal("10"), "long", Decimal("100000"))
        # swap_pips = 2.0 * 10 * 1 = 20.0
        # swap_amount = 20.0 * 0.0001 = 0.002, rounded to 0.00
        assert result == Decimal("0.00")

    def test_long_swap_multiple_days(self):
        cfg = SwapModelConfig(long_swap_rate=Decimal("100.0"))
        model = SwapModel(config=cfg)
        result = model.calculate(Decimal("1"), "long", Decimal("100000"), holding_days=5)
        # swap_pips = 100.0 * 1 * 5 = 500.0
        # swap_amount = 500.0 * 0.0001 = 0.05
        assert result == Decimal("0.05")

    def test_triple_swap_wednesday(self):
        """Wednesday is day 3 (ISO weekday)."""
        cfg = SwapModelConfig(long_swap_rate=Decimal("100.0"), triple_swap_day=3)
        model = SwapModel(config=cfg)
        # A Wednesday
        ts = datetime(2023, 1, 4, tzinfo=timezone.utc)
        assert ts.isoweekday() == 3
        result = model.calculate(Decimal("1"), "long", Decimal("100000"), timestamp=ts)
        # swap_pips = 100.0 * 1 * 3 (triple) = 300.0
        # swap_amount = 300.0 * 0.0001 = 0.03
        assert result == Decimal("0.03")

    def test_triple_swap_non_wednesday(self):
        cfg = SwapModelConfig(long_swap_rate=Decimal("100.0"), triple_swap_day=3)
        model = SwapModel(config=cfg)
        # A Monday
        ts = datetime(2023, 1, 2, tzinfo=timezone.utc)
        assert ts.isoweekday() == 1
        result = model.calculate(Decimal("1"), "long", Decimal("100000"), timestamp=ts)
        # swap_pips = 100.0 * 1 * 1 = 100.0
        # swap_amount = 100.0 * 0.0001 = 0.01
        assert result == Decimal("0.01")

    def test_triple_swap_custom_day(self):
        cfg = SwapModelConfig(long_swap_rate=Decimal("100.0"), triple_swap_day=5)  # Friday
        model = SwapModel(config=cfg)
        # A Friday
        ts = datetime(2023, 1, 6, tzinfo=timezone.utc)
        assert ts.isoweekday() == 5
        result = model.calculate(Decimal("1"), "long", Decimal("100000"), timestamp=ts)
        assert result == Decimal("0.03")

    def test_calculate_long_swap_method(self):
        model = SwapModel()
        result = model.calculate_long_swap(Decimal("1"), Decimal("100000"))
        assert isinstance(result, Decimal)

    def test_calculate_short_swap_method(self):
        model = SwapModel()
        result = model.calculate_short_swap(Decimal("1"), Decimal("100000"))
        assert isinstance(result, Decimal)

    def test_long_short_different_rates(self):
        model = SwapModel()
        long_result = model.calculate_long_swap(Decimal("1"), Decimal("100000"))
        short_result = model.calculate_short_swap(Decimal("1"), Decimal("100000"))
        # Long uses -2.0, short uses -1.5
        assert long_result <= short_result  # More negative for long

    def test_positive_short_rate(self):
        cfg = SwapModelConfig(short_swap_rate=Decimal("5.0"))
        model = SwapModel(config=cfg)
        result = model.calculate(Decimal("10"), "short", Decimal("100000"), holding_days=1)
        # swap_pips = 5.0 * 10 * 1 = 50.0
        # swap_amount = 50.0 * 0.0001 = 0.005, rounded to 0.00 (banker's rounding)
        assert result == Decimal("0.00")

    def test_positive_short_rate_larger_volume(self):
        cfg = SwapModelConfig(short_swap_rate=Decimal("5.0"))
        model = SwapModel(config=cfg)
        result = model.calculate(Decimal("100"), "short", Decimal("100000"), holding_days=1)
        # swap_pips = 5.0 * 100 * 1 = 500.0
        # swap_amount = 500.0 * 0.0001 = 0.05
        assert result == Decimal("0.05")

    def test_zero_volume_swap(self):
        model = SwapModel()
        result = model.calculate(Decimal("0"), "long", Decimal("100000"))
        assert result == Decimal("0.00")

    def test_decimal_precision_rounding(self):
        cfg = SwapModelConfig(long_swap_rate=Decimal("1.234"))
        model = SwapModel(config=cfg)
        result = model.calculate(Decimal("1"), "long", Decimal("100000"))
        # Should be rounded to 2 decimal places
        assert result == result.quantize(Decimal("0.01"))

    def test_position_value_not_used_in_current_calculation(self):
        """Position value is accepted but current impl doesn't use it."""
        model = SwapModel()
        result1 = model.calculate(Decimal("1"), "long", Decimal("100000"))
        result2 = model.calculate(Decimal("1"), "long", Decimal("1"))
        assert result1 == result2  # Position value not used in current impl

    def test_case_insensitive_side(self):
        model = SwapModel()
        result1 = model.calculate(Decimal("1"), "LONG", Decimal("100000"))
        result2 = model.calculate(Decimal("1"), "Long", Decimal("100000"))
        result3 = model.calculate(Decimal("1"), "long", Decimal("100000"))
        assert result1 == result2 == result3

    def test_triple_swap_with_holding_days(self):
        """Triple swap and holding_days should compound."""
        cfg = SwapModelConfig(long_swap_rate=Decimal("100.0"), triple_swap_day=3)
        model = SwapModel(config=cfg)
        ts = datetime(2023, 1, 4, tzinfo=timezone.utc)  # Wednesday
        result = model.calculate(
            Decimal("1"), "long", Decimal("100000"), holding_days=2, timestamp=ts
        )
        # swap_pips = 100.0 * 1 * (2 * 3) = 600.0
        # swap_amount = 600.0 * 0.0001 = 0.06
        assert result == Decimal("0.06")
