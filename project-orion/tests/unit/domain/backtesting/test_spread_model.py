"""Tests for EPIC-010 SpreadModel — bid/ask spread simulation."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.backtesting.models import SpreadConfig
from libraries.domain.backtesting.spread_model import SpreadModel


class TestSpreadConfig:
    """Test SpreadConfig defaults."""

    def test_default_config(self):
        cfg = SpreadConfig()
        assert cfg.type == "fixed"
        assert cfg.value_pips == 0.0  # Default is 0.0
        assert cfg.min_pips == 0.0  # Default is 0.0
        assert cfg.max_pips == 100.0
        assert cfg.variable_factor == 0.0

    def test_custom_config(self):
        cfg = SpreadConfig(
            type="variable",
            value_pips=2.0,
            min_pips=0.5,
            max_pips=50.0,
            variable_factor=1.0,
        )
        assert cfg.type == "variable"
        assert cfg.value_pips == 2.0
        assert cfg.variable_factor == 1.0

    def test_spread_config_default_enum_values(self):
        cfg1 = SpreadConfig(type="fixed")
        cfg2 = SpreadConfig(type="variable")
        assert cfg1.type == "fixed"
        assert cfg2.type == "variable"


class TestSpreadModel:
    """Test SpreadModel calculation."""

    @pytest.mark.asyncio
    async def test_fixed_spread_base(self):
        cfg = SpreadConfig(type="fixed", value_pips=2.0)
        model = SpreadModel(config=cfg)
        spread = await model.calculate_spread_pips()
        # Fixed spread with some noise, but should be close to 2.0
        assert 1.8 <= spread <= 2.2

    @pytest.mark.asyncio
    async def test_variable_spread_with_volatility(self):
        cfg = SpreadConfig(type="variable", value_pips=1.0, variable_factor=2.0)
        model = SpreadModel(config=cfg)
        spread = await model.calculate_spread_pips(volatility=0.5)
        # base = 1.0, variable = 2.0 * 0.5 = 1.0, total = 2.0 + noise
        assert 1.8 <= spread <= 2.2

    @pytest.mark.asyncio
    async def test_variable_spread_no_volatility(self):
        cfg = SpreadConfig(type="variable", value_pips=1.0, variable_factor=2.0)
        model = SpreadModel(config=cfg)
        spread = await model.calculate_spread_pips(volatility=0.0)
        # base = 1.0, variable = 2.0 * 0.0 = 0.0, total = 1.0 + noise
        assert 0.9 <= spread <= 1.1

    @pytest.mark.asyncio
    async def test_news_multiplier(self):
        cfg = SpreadConfig(type="fixed", value_pips=1.0)
        model = SpreadModel(config=cfg)
        spread = await model.calculate_spread_pips(is_high_impact_news=True)
        # 1.0 * 3.0 = 3.0 + noise
        assert 2.7 <= spread <= 3.3

    @pytest.mark.asyncio
    async def test_scenario_multiplier(self):
        cfg = SpreadConfig(type="fixed", value_pips=1.0)
        model = SpreadModel(config=cfg)
        spread = await model.calculate_spread_pips(scenario_multiplier=5.0)
        # 1.0 * 5.0 = 5.0 + noise
        assert 4.5 <= spread <= 5.5

    @pytest.mark.asyncio
    async def test_news_and_scenario_combined(self):
        cfg = SpreadConfig(type="fixed", value_pips=1.0)
        model = SpreadModel(config=cfg)
        spread = await model.calculate_spread_pips(
            is_high_impact_news=True, scenario_multiplier=2.0
        )
        # 1.0 * 3.0 * 2.0 = 6.0 + noise
        assert 5.4 <= spread <= 6.6

    @pytest.mark.asyncio
    async def test_spread_clamped_to_min(self):
        cfg = SpreadConfig(type="fixed", value_pips=0.05, min_pips=0.5)
        model = SpreadModel(config=cfg)
        spread = await model.calculate_spread_pips()
        assert spread >= 0.5

    @pytest.mark.asyncio
    async def test_spread_clamped_to_max(self):
        cfg = SpreadConfig(type="fixed", value_pips=200.0, max_pips=100.0)
        model = SpreadModel(config=cfg)
        spread = await model.calculate_spread_pips()
        assert spread <= 100.0

    @pytest.mark.asyncio
    async def test_spread_rounding(self):
        cfg = SpreadConfig(type="fixed", value_pips=1.234)
        model = SpreadModel(config=cfg)
        spread = await model.calculate_spread_pips()
        # Should be rounded to 1 decimal
        assert spread == round(spread, 1)

    @pytest.mark.asyncio
    async def test_apply_spread_creates_bid_ask(self):
        cfg = SpreadConfig(type="fixed", value_pips=2.0)
        model = SpreadModel(config=cfg)
        bid, ask = await model.apply_spread(Decimal("1.1000"))
        assert bid < ask
        assert bid > Decimal("0")
        # With 2 pip spread, bid should be ~1.0999, ask ~1.1001
        spread_price = ask - bid
        assert spread_price > Decimal("0")

    @pytest.mark.asyncio
    async def test_apply_spread_midpoint(self):
        cfg = SpreadConfig(type="fixed", value_pips=0.0)
        model = SpreadModel(config=cfg)
        bid, ask = await model.apply_spread(Decimal("1.1000"))
        spread_price = ask - bid
        assert spread_price >= Decimal("0")

    @pytest.mark.asyncio
    async def test_apply_spread_bid_not_zero(self):
        cfg = SpreadConfig(type="fixed", value_pips=100.0)
        model = SpreadModel(config=cfg)
        bid, ask = await model.apply_spread(Decimal("0.0001"))
        assert bid > Decimal("0")

    @pytest.mark.asyncio
    async def test_apply_spread_with_volatility(self):
        cfg = SpreadConfig(type="variable", value_pips=1.0, variable_factor=1.0)
        model = SpreadModel(config=cfg)
        bid, ask = await model.apply_spread(Decimal("1.1000"), volatility=0.3)
        assert bid < ask
        assert bid > Decimal("0")

    @pytest.mark.asyncio
    async def test_apply_spread_with_news(self):
        cfg = SpreadConfig(type="fixed", value_pips=1.0)
        model = SpreadModel(config=cfg)
        bid, ask = await model.apply_spread(Decimal("1.1000"), is_high_impact_news=True)
        spread_price = ask - bid
        normal_bid, normal_ask = await model.apply_spread(Decimal("1.1000"))
        # News spread should be wider
        assert spread_price > (normal_ask - normal_bid)

    @pytest.mark.asyncio
    async def test_spread_in_pips(self):
        cfg = SpreadConfig(type="fixed", value_pips=3.5)
        model = SpreadModel(config=cfg)
        result = await model.spread_in_pips()
        assert result == 3.5

    @pytest.mark.asyncio
    async def test_get_config(self):
        cfg = SpreadConfig(type="variable", value_pips=2.0)
        model = SpreadModel(config=cfg)
        retrieved = await model.get_config()
        assert retrieved.type == "variable"
        assert retrieved.value_pips == 2.0

    @pytest.mark.asyncio
    async def test_update_config(self):
        model = SpreadModel()
        new_cfg = SpreadConfig(type="variable", value_pips=5.0)
        await model.update_config(new_cfg)
        retrieved = await model.get_config()
        assert retrieved.type == "variable"
        assert retrieved.value_pips == 5.0

    @pytest.mark.asyncio
    async def test_set_seed_determinism(self):
        cfg = SpreadConfig(type="fixed", value_pips=1.0)
        model1 = SpreadModel(config=cfg)
        model2 = SpreadModel(config=cfg)
        model1.set_seed(12345)
        model2.set_seed(12345)
        spread1 = await model1.calculate_spread_pips()
        spread2 = await model2.calculate_spread_pips()
        assert spread1 == spread2

    @pytest.mark.asyncio
    async def test_set_seed_none_random(self):
        cfg = SpreadConfig(type="fixed", value_pips=1.0)
        model = SpreadModel(config=cfg)
        model.set_seed(None)
        spread = await model.calculate_spread_pips()
        assert 0.9 <= spread <= 1.1

    @pytest.mark.asyncio
    async def test_unknown_type_with_value_pips(self):
        cfg = SpreadConfig(type="unknown_type", value_pips=5.0)
        model = SpreadModel(config=cfg)
        spread = await model.calculate_spread_pips()
        # Falls to else branch which uses value_pips = 5.0
        assert 4.5 <= spread <= 5.5

    @pytest.mark.asyncio
    async def test_unknown_config_type_other(self):
        cfg = SpreadConfig(type="other", value_pips=5.0)
        model = SpreadModel(config=cfg)
        spread = await model.calculate_spread_pips()
        assert 4.5 <= spread <= 5.5
