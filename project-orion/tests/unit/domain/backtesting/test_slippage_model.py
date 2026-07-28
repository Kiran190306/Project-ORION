"""Tests for EPIC-010 SlippageModel — slippage calculation."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.backtesting.slippage_model import (
    SlippageModel,
    SlippageModelConfig,
    SlippageType,
)


class TestSlippageType:
    """Test SlippageType enum."""

    def test_enum_values(self):
        assert SlippageType.FIXED.value == "fixed"
        assert SlippageType.RELATIVE.value == "relative"
        assert SlippageType.VOLATILITY_ADJUSTED.value == "volatility_adjusted"
        assert SlippageType.LIQUIDITY_BASED.value == "liquidity_based"
        assert SlippageType.SPREAD_BASED.value == "spread_based"
        assert SlippageType.NONE.value == "none"


class TestSlippageModelConfig:
    """Test SlippageModelConfig defaults."""

    def test_default_config(self):
        cfg = SlippageModelConfig()
        assert cfg.slippage_type == SlippageType.FIXED
        assert cfg.fixed_bps == 1.0
        assert cfg.volatility_multiplier == 1.5
        assert cfg.liquidity_base_bps == 0.5
        assert cfg.spread_multiplier == 0.25
        assert cfg.max_slippage_bps == 50.0
        assert cfg.min_slippage_bps == 0.0

    def test_custom_config(self):
        cfg = SlippageModelConfig(
            slippage_type=SlippageType.LIQUIDITY_BASED,
            fixed_bps=2.0,
            max_slippage_bps=100.0,
        )
        assert cfg.slippage_type == SlippageType.LIQUIDITY_BASED
        assert cfg.fixed_bps == 2.0
        assert cfg.max_slippage_bps == 100.0

    def test_config_frozen(self):
        cfg = SlippageModelConfig()
        with pytest.raises(AttributeError):
            cfg.fixed_bps = 2.0  # type: ignore[misc]


class TestSlippageModel:
    """Test SlippageModel calculation."""

    def test_default_initialization(self):
        model = SlippageModel()
        assert model.config.slippage_type == SlippageType.FIXED

    def test_config_property(self):
        model = SlippageModel()
        assert isinstance(model.config, SlippageModelConfig)

    def test_none_slippage(self):
        cfg = SlippageModelConfig(slippage_type=SlippageType.NONE)
        model = SlippageModel(config=cfg)
        result = model.calculate(Decimal("1"))
        assert result == 0.0

    def test_fixed_slippage(self):
        cfg = SlippageModelConfig(slippage_type=SlippageType.FIXED, fixed_bps=2.5)
        model = SlippageModel(config=cfg)
        result = model.calculate(Decimal("1"))
        assert result == 2.5

    def test_relative_slippage(self):
        cfg = SlippageModelConfig(
            slippage_type=SlippageType.RELATIVE, fixed_bps=1.0, volatility_multiplier=2.0
        )
        model = SlippageModel(config=cfg)
        result = model.calculate(Decimal("1"), volatility=0.5)
        assert result == 2.0  # 1.0 * (1 + 0.5 * 2.0)

    def test_volatility_adjusted_slippage(self):
        cfg = SlippageModelConfig(
            slippage_type=SlippageType.VOLATILITY_ADJUSTED, fixed_bps=1.0, volatility_multiplier=1.5
        )
        model = SlippageModel(config=cfg)
        result = model.calculate(Decimal("1"), volatility=0.2)
        assert result == 1.3  # 1.0 * (1 + 0.2 * 1.5)

    def test_liquidity_based_slippage(self):
        cfg = SlippageModelConfig(
            slippage_type=SlippageType.LIQUIDITY_BASED, liquidity_base_bps=1.0
        )
        model = SlippageModel(config=cfg)
        result = model.calculate(Decimal("1"), liquidity_score=0.5)
        assert result == 2.0  # 1.0 / 0.5

    def test_liquidity_based_zero_score(self):
        cfg = SlippageModelConfig(
            slippage_type=SlippageType.LIQUIDITY_BASED, liquidity_base_bps=1.0
        )
        model = SlippageModel(config=cfg)
        result = model.calculate(Decimal("1"), liquidity_score=0.0)
        assert result == 10.0  # 1.0 * 10.0

    def test_spread_based_slippage(self):
        cfg = SlippageModelConfig(slippage_type=SlippageType.SPREAD_BASED, spread_multiplier=0.5)
        model = SlippageModel(config=cfg)
        result = model.calculate(Decimal("1"), spread_pips=2.0)
        assert result == 1.0  # 2.0 * 0.5

    def test_limit_order_half_slippage(self):
        cfg = SlippageModelConfig(slippage_type=SlippageType.FIXED, fixed_bps=2.0)
        model = SlippageModel(config=cfg)
        result = model.calculate(Decimal("1"), is_market_order=False)
        assert result == 1.0  # 2.0 * 0.5

    def test_large_volume_increases_slippage(self):
        cfg = SlippageModelConfig(slippage_type=SlippageType.FIXED, fixed_bps=1.0)
        model = SlippageModel(config=cfg)
        result = model.calculate(Decimal("20"))
        # 1.0 * (1 + (20-10) * 0.05) = 1.0 * 1.5 = 1.5
        assert result == 1.5

    def test_small_volume_no_increase(self):
        cfg = SlippageModelConfig(slippage_type=SlippageType.FIXED, fixed_bps=1.0)
        model = SlippageModel(config=cfg)
        result = model.calculate(Decimal("5"))
        assert result == 1.0

    def test_slippage_clamped_to_min(self):
        cfg = SlippageModelConfig(
            slippage_type=SlippageType.FIXED, fixed_bps=0.5, min_slippage_bps=1.0
        )
        model = SlippageModel(config=cfg)
        result = model.calculate(Decimal("1"))
        assert result == 1.0

    def test_slippage_clamped_to_max(self):
        cfg = SlippageModelConfig(
            slippage_type=SlippageType.FIXED, fixed_bps=100.0, max_slippage_bps=50.0
        )
        model = SlippageModel(config=cfg)
        result = model.calculate(Decimal("1"))
        assert result == 50.0

    def test_slippage_rounding(self):
        cfg = SlippageModelConfig(slippage_type=SlippageType.FIXED, fixed_bps=1.234)
        model = SlippageModel(config=cfg)
        result = model.calculate(Decimal("1"))
        assert result == 1.23

    def test_calculate_slippage_price_buy(self):
        cfg = SlippageModelConfig(slippage_type=SlippageType.FIXED, fixed_bps=10.0)
        model = SlippageModel(config=cfg)
        result = model.calculate_slippage_price(Decimal("1.1000"), "buy", Decimal("1"))
        # 10 bps = 0.001, price = 1.1000 * 1.001 = 1.1011
        assert result == Decimal("1.1011")

    def test_calculate_slippage_price_sell(self):
        cfg = SlippageModelConfig(slippage_type=SlippageType.FIXED, fixed_bps=10.0)
        model = SlippageModel(config=cfg)
        result = model.calculate_slippage_price(Decimal("1.1000"), "sell", Decimal("1"))
        # 10 bps = 0.001, price = 1.1000 * 0.999 = 1.0989
        assert result == Decimal("1.0989")

    def test_calculate_slippage_price_with_volatility(self):
        cfg = SlippageModelConfig(
            slippage_type=SlippageType.VOLATILITY_ADJUSTED, fixed_bps=5.0, volatility_multiplier=2.0
        )
        model = SlippageModel(config=cfg)
        result = model.calculate_slippage_price(
            Decimal("1.1000"), "buy", Decimal("1"), volatility=0.5
        )
        # slippage = 5.0 * (1 + 0.5 * 2.0) = 10 bps = 0.001
        # price = 1.1000 * 1.001 = 1.1011
        assert result == Decimal("1.1011")

    def test_calculate_slippage_price_with_liquidity(self):
        cfg = SlippageModelConfig(
            slippage_type=SlippageType.LIQUIDITY_BASED, liquidity_base_bps=2.0
        )
        model = SlippageModel(config=cfg)
        result = model.calculate_slippage_price(
            Decimal("1.1000"), "buy", Decimal("1"), liquidity_score=0.25
        )
        # slippage = 2.0 / 0.25 = 8 bps = 0.0008
        # price = 1.1000 * 1.0008 = 1.10088
        assert result == Decimal("1.10088")

    def test_calculate_with_metadata(self):
        model = SlippageModel()
        result = model.calculate(Decimal("1"), metadata={"order_type": "iceberg"})
        assert result is not None

    def test_unknown_type_defaults_to_fixed(self):
        cfg = SlippageModelConfig(
            slippage_type="unknown",  # type: ignore[arg-type]
            fixed_bps=3.0,
        )
        model = SlippageModel(config=cfg)
        result = model.calculate(Decimal("1"))
        assert result == 3.0

    def test_volume_and_limit_combined(self):
        cfg = SlippageModelConfig(slippage_type=SlippageType.FIXED, fixed_bps=2.0)
        model = SlippageModel(config=cfg)
        result = model.calculate(Decimal("20"), is_market_order=False)
        # 2.0 * 0.5 (limit) * 1.5 (volume) = 1.5
        assert result == 1.5
