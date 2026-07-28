"""Tests for EPIC-010 MarketImpactModel — market impact simulation."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.backtesting.market_impact_model import (
    MarketImpactModel,
    MarketImpactModelConfig,
)


class TestMarketImpactModelConfig:
    """Test MarketImpactModelConfig defaults."""

    def test_default_config(self):
        cfg = MarketImpactModelConfig()
        assert cfg.temporary_impact_coefficient == 0.1
        assert cfg.permanent_impact_coefficient == 0.01
        assert cfg.volatility_impact_multiplier == 0.5
        assert cfg.liquidity_impact_divider == 2.0
        assert cfg.max_impact_bps == 100.0

    def test_custom_config(self):
        cfg = MarketImpactModelConfig(
            temporary_impact_coefficient=0.2,
            permanent_impact_coefficient=0.02,
            max_impact_bps=200.0,
        )
        assert cfg.temporary_impact_coefficient == 0.2
        assert cfg.max_impact_bps == 200.0

    def test_config_frozen(self):
        cfg = MarketImpactModelConfig()
        with pytest.raises(AttributeError):
            cfg.max_impact_bps = 50.0  # type: ignore[misc]


class TestMarketImpactModel:
    """Test MarketImpactModel calculation."""

    def test_default_initialization(self):
        model = MarketImpactModel()
        assert model.config.permanent_impact_coefficient == 0.01

    def test_config_property(self):
        model = MarketImpactModel()
        assert isinstance(model.config, MarketImpactModelConfig)

    def test_zero_adv_returns_zero(self):
        model = MarketImpactModel()
        result = model.calculate_impact_bps(Decimal("1000"), Decimal("0"))
        assert result == 0.0

    def test_zero_volume_returns_zero(self):
        model = MarketImpactModel()
        result = model.calculate_impact_bps(Decimal("0"), Decimal("1000000"))
        assert result == 0.0

    def test_small_order_impact(self):
        model = MarketImpactModel()
        result = model.calculate_impact_bps(Decimal("10000"), Decimal("1000000"))
        assert result >= 0.0

    def test_large_order_higher_impact(self):
        model = MarketImpactModel()
        result_small = model.calculate_impact_bps(Decimal("10000"), Decimal("1000000"))
        result_large = model.calculate_impact_bps(Decimal("100000"), Decimal("1000000"))
        assert result_large >= result_small

    def test_impact_increases_with_volatility(self):
        model = MarketImpactModel()
        result_low_vol = model.calculate_impact_bps(
            Decimal("10000"), Decimal("1000000"), volatility_bps=5.0
        )
        result_high_vol = model.calculate_impact_bps(
            Decimal("10000"), Decimal("1000000"), volatility_bps=50.0
        )
        assert result_high_vol > result_low_vol

    def test_impact_decreases_with_liquidity(self):
        model = MarketImpactModel()
        result_low_liq = model.calculate_impact_bps(
            Decimal("10000"), Decimal("1000000"), liquidity_score=0.2
        )
        result_high_liq = model.calculate_impact_bps(
            Decimal("10000"), Decimal("1000000"), liquidity_score=1.0
        )
        assert result_low_liq > result_high_liq

    def test_impact_clamped_to_max(self):
        cfg = MarketImpactModelConfig(max_impact_bps=10.0)
        model = MarketImpactModel(config=cfg)
        result = model.calculate_impact_bps(
            Decimal("1000000"), Decimal("1000"), volatility_bps=100.0
        )
        assert result == 10.0

    def test_impact_rounding(self):
        model = MarketImpactModel()
        result = model.calculate_impact_bps(Decimal("10000"), Decimal("1000000"))
        assert isinstance(result, float)
        assert result == round(result, 2)

    def test_calculate_effective_spread(self):
        model = MarketImpactModel()
        result = model.calculate_effective_spread(1.0, Decimal("10000"), Decimal("1000000"))
        assert result >= 1.0

    def test_calculate_effective_spread_zero_pip_size(self):
        model = MarketImpactModel()
        result = model.calculate_effective_spread(
            1.0, Decimal("100"), Decimal("1000000"), pip_size=Decimal("0")
        )
        assert result == 1.0

    def test_calculate_impact_cost(self):
        model = MarketImpactModel()
        result = model.calculate_impact_cost(
            Decimal("10000"), Decimal("1.1000"), Decimal("1000000")
        )
        assert result >= Decimal("0")
        assert isinstance(result, Decimal)

    def test_calculate_impact_cost_zero_adv(self):
        model = MarketImpactModel()
        result = model.calculate_impact_cost(Decimal("10000"), Decimal("1.1000"), Decimal("0"))
        assert result == Decimal("0.00")

    def test_calculate_impact_cost_rounding(self):
        model = MarketImpactModel()
        result = model.calculate_impact_cost(
            Decimal("10000"), Decimal("1.1000"), Decimal("1000000")
        )
        assert result == result.quantize(Decimal("0.01"))

    def test_calculate_impact_cost_with_volatility(self):
        model = MarketImpactModel()
        result = model.calculate_impact_cost(
            Decimal("10000"), Decimal("1.1000"), Decimal("1000000"), volatility_bps=30.0
        )
        assert result >= Decimal("0")

    def test_calculate_impact_cost_with_liquidity(self):
        model = MarketImpactModel()
        result = model.calculate_impact_cost(
            Decimal("10000"), Decimal("1.1000"), Decimal("1000000"), liquidity_score=0.3
        )
        assert result >= Decimal("0")

    def test_impact_increases_with_participation_rate(self):
        """Test that larger participation rate gives higher impact."""
        model = MarketImpactModel()
        impact1 = model.calculate_impact_bps(Decimal("10000"), Decimal("1000000"))
        impact2 = model.calculate_impact_bps(Decimal("20000"), Decimal("1000000"))
        assert impact2 >= impact1

    def test_custom_config_affects_impact(self):
        cfg = MarketImpactModelConfig(permanent_impact_coefficient=0.1)
        model = MarketImpactModel(config=cfg)
        result = model.calculate_impact_bps(Decimal("10000"), Decimal("1000000"))
        assert result >= 0.0
