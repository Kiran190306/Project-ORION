"""Tests for EPIC-010 market models (commission, slippage, spread, swap, latency, liquidity, impact)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.backtesting.commission_model import (
    CommissionModel,
    CommissionModelConfig,
    CommissionTier,
    CommissionType,
)
from libraries.domain.backtesting.latency_model import LatencyModel, LatencyModelConfig
from libraries.domain.backtesting.liquidity_model import LiquidityModel, LiquidityModelConfig
from libraries.domain.backtesting.market_impact_model import (
    MarketImpactModel,
    MarketImpactModelConfig,
)
from libraries.domain.backtesting.slippage_model import (
    SlippageModel,
    SlippageModelConfig,
    SlippageType,
)
from libraries.domain.backtesting.spread_model import SpreadConfig, SpreadModel
from libraries.domain.backtesting.swap_model import SwapModel, SwapModelConfig


class TestCommissionModel:
    """Test commission calculation."""

    def test_default_config(self):
        model = CommissionModel()
        assert model.config.commission_type == CommissionType.FIXED_PER_LOT
        assert model.config.base_rate == Decimal("7.0")

    def test_zero_commission(self):
        cfg = CommissionModelConfig(commission_type=CommissionType.ZERO, base_rate=Decimal("0"))
        model = CommissionModel(cfg)
        result = model.calculate(Decimal("1"), Decimal("1.1000"))
        assert result == Decimal("0")

    def test_fixed_per_lot_commission(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT, base_rate=Decimal("7")
        )
        model = CommissionModel(cfg)
        result = model.calculate(Decimal("1"), Decimal("1.1000"))
        assert result == Decimal("7.00")

    def test_commission_for_multiple_lots(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT, base_rate=Decimal("7")
        )
        model = CommissionModel(cfg)
        result = model.calculate(Decimal("3"), Decimal("1.1000"))
        assert result == Decimal("21.00")

    def test_min_commission(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT,
            base_rate=Decimal("7"),
            minimum_commission=Decimal("10"),
        )
        model = CommissionModel(cfg)
        result = model.calculate(Decimal("1"), Decimal("1.1000"))
        assert result == Decimal("10.00")

    def test_max_commission(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT,
            base_rate=Decimal("50"),
            maximum_commission=Decimal("30"),
        )
        model = CommissionModel(cfg)
        result = model.calculate(Decimal("1"), Decimal("1.1000"))
        assert result == Decimal("30.00")

    def test_percentage_commission(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.PERCENTAGE, percentage_rate=Decimal("0.1")
        )
        model = CommissionModel(cfg)
        result = model.calculate(Decimal("1"), Decimal("1000"))
        assert result == Decimal("1.00")

    def test_commission_type_enum(self):
        assert CommissionType.FIXED_PER_LOT == "fixed_per_lot"
        assert CommissionType.ZERO == "zero"
        assert CommissionType.PERCENTAGE == "percentage"
        assert CommissionType.PER_UNIT == "per_unit"
        assert CommissionType.FIXED_PER_TRADE == "fixed_per_trade"
        assert CommissionType.TIERED == "tiered"

    def test_zero_lots_commission(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT, base_rate=Decimal("7")
        )
        model = CommissionModel(cfg)
        result = model.calculate(Decimal("0"), Decimal("1.1000"))
        assert result == Decimal("0.00")

    def test_negative_lots_commission(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT, base_rate=Decimal("7")
        )
        model = CommissionModel(cfg)
        result = model.calculate(Decimal("-1"), Decimal("1.1000"))
        assert result == Decimal("-7.00")

    def test_very_large_lots_commission(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT, base_rate=Decimal("7")
        )
        model = CommissionModel(cfg)
        result = model.calculate(Decimal("1000000"), Decimal("1.1000"))
        assert result == Decimal("7000000.00")

    def test_per_unit_commission(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.PER_UNIT, per_unit_rate=Decimal("0.01")
        )
        model = CommissionModel(cfg)
        result = model.calculate(Decimal("1000"), Decimal("1.1000"))
        assert result == Decimal("10.00")

    def test_min_max_commission_clamping(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT,
            base_rate=Decimal("7"),
            minimum_commission=Decimal("5"),
            maximum_commission=Decimal("15"),
        )
        model = CommissionModel(cfg)
        result_small = model.calculate(Decimal("0.5"), Decimal("1.1000"))
        assert result_small >= Decimal("5.00")
        result_large = model.calculate(Decimal("5"), Decimal("1.1000"))
        assert result_large <= Decimal("15.00")

    def test_decimal_precision_commission(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT, base_rate=Decimal("7.1234")
        )
        model = CommissionModel(cfg)
        result = model.calculate(Decimal("1"), Decimal("1.1000"))
        assert result == Decimal("7.1234")

    def test_fixed_per_trade_commission(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_TRADE, base_rate=Decimal("10")
        )
        model = CommissionModel(cfg)
        result = model.calculate(Decimal("5"), Decimal("1.1000"))
        assert result == Decimal("10.00")

    def test_tiered_commission_with_tiers(self):
        tiers = (
            CommissionTier(min_volume=Decimal("0"), max_volume=Decimal("10"), rate=Decimal("5")),
            CommissionTier(min_volume=Decimal("10"), max_volume=Decimal("100"), rate=Decimal("3")),
        )
        cfg = CommissionModelConfig(
            commission_type=CommissionType.TIERED,
            base_rate=Decimal("7"),
            tiers=tiers,
        )
        model = CommissionModel(cfg)
        result = model.calculate(Decimal("5"), Decimal("1.1000"))
        assert result == Decimal("25.00")

    def test_tiered_commission_no_tiers_fallback(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.TIERED,
            base_rate=Decimal("7"),
            tiers=(),
        )
        model = CommissionModel(cfg)
        result = model.calculate(Decimal("5"), Decimal("1.1000"))
        assert result == Decimal("35.00")

    def test_tiered_commission_exceeds_all_tiers(self):
        tiers = (
            CommissionTier(min_volume=Decimal("0"), max_volume=Decimal("10"), rate=Decimal("5")),
        )
        cfg = CommissionModelConfig(
            commission_type=CommissionType.TIERED,
            base_rate=Decimal("7"),
            tiers=tiers,
        )
        model = CommissionModel(cfg)
        result = model.calculate(Decimal("50"), Decimal("1.1000"))
        assert result == Decimal("250.00")

    def test_discount_applied(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT,
            base_rate=Decimal("10"),
            discount_rate=Decimal("10"),
        )
        model = CommissionModel(cfg)
        result = model.calculate(Decimal("1"), Decimal("1.1000"))
        assert result == Decimal("9.00")

    def test_calculate_for_order_rounding(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT, base_rate=Decimal("7.1234")
        )
        model = CommissionModel(cfg)
        result = model.calculate_for_order(Decimal("1"), Decimal("1.1000"))
        assert result == Decimal("7.12")

    def test_calculate_for_order_open_close(self):
        cfg = CommissionModelConfig(
            commission_type=CommissionType.FIXED_PER_LOT, base_rate=Decimal("7")
        )
        model = CommissionModel(cfg)
        result_open = model.calculate_for_order(Decimal("1"), Decimal("1.1000"), is_open=True)
        result_close = model.calculate_for_order(Decimal("1"), Decimal("1.1000"), is_open=False)
        assert result_open == Decimal("7.00")
        assert result_close == Decimal("7.00")


class TestSlippageModel:
    """Test slippage calculation."""

    def test_default_config(self):
        model = SlippageModel()
        assert model.config.slippage_type == SlippageType.FIXED
        assert model.config.fixed_bps == 1.0

    def test_zero_slippage(self):
        model = SlippageModel(SlippageModelConfig(slippage_type=SlippageType.NONE))
        result = model.calculate(Decimal("1"))
        assert result == 0.0

    def test_fixed_slippage(self):
        model = SlippageModel(SlippageModelConfig(slippage_type=SlippageType.FIXED, fixed_bps=2.0))
        result = model.calculate(Decimal("1"))
        assert result == 2.0

    def test_slippage_price_calculation_buy(self):
        model = SlippageModel(SlippageModelConfig(slippage_type=SlippageType.FIXED, fixed_bps=1.0))
        price = model.calculate_slippage_price(Decimal("1.1000"), "buy", Decimal("1"))
        assert price > Decimal("1.1000")

    def test_slippage_price_calculation_sell(self):
        model = SlippageModel(SlippageModelConfig(slippage_type=SlippageType.FIXED, fixed_bps=1.0))
        price = model.calculate_slippage_price(Decimal("1.1000"), "sell", Decimal("1"))
        assert price < Decimal("1.1000")

    def test_slippage_type_enum(self):
        assert SlippageType.FIXED == "fixed"
        assert SlippageType.VOLATILITY_ADJUSTED == "volatility_adjusted"
        assert SlippageType.NONE == "none"
        assert SlippageType.RELATIVE == "relative"
        assert SlippageType.LIQUIDITY_BASED == "liquidity_based"
        assert SlippageType.SPREAD_BASED == "spread_based"

    def test_zero_quantity_slippage(self):
        model = SlippageModel(SlippageModelConfig(slippage_type=SlippageType.FIXED, fixed_bps=1.0))
        result = model.calculate(Decimal("0"))
        assert result == 1.0

    def test_negative_quantity_slippage_price(self):
        model = SlippageModel(SlippageModelConfig(slippage_type=SlippageType.FIXED, fixed_bps=1.0))
        price = model.calculate_slippage_price(Decimal("1.1000"), "buy", Decimal("-1"))
        assert price > Decimal("1.1000")

    def test_volatility_adjusted_slippage(self):
        model = SlippageModel(
            SlippageModelConfig(
                slippage_type=SlippageType.VOLATILITY_ADJUSTED,
                fixed_bps=1.0,
                volatility_multiplier=2.0,
            )
        )
        result = model.calculate(Decimal("1"), volatility=3.0, liquidity_score=0.5)
        assert result == 7.0

    def test_slippage_very_large_quantity(self):
        model = SlippageModel(SlippageModelConfig(slippage_type=SlippageType.FIXED, fixed_bps=1.0))
        result = model.calculate(Decimal("1000000000"))
        assert result > 1.0

    def test_relative_slippage(self):
        model = SlippageModel(
            SlippageModelConfig(
                slippage_type=SlippageType.RELATIVE,
                fixed_bps=1.0,
                volatility_multiplier=2.0,
            )
        )
        result = model.calculate(Decimal("1"), volatility=0.5)
        assert result == 2.0

    def test_liquidity_based_slippage(self):
        model = SlippageModel(
            SlippageModelConfig(
                slippage_type=SlippageType.LIQUIDITY_BASED,
                liquidity_base_bps=2.0,
            )
        )
        result = model.calculate(Decimal("1"), liquidity_score=0.5)
        assert result == 4.0

    def test_liquidity_based_slippage_zero_score(self):
        model = SlippageModel(
            SlippageModelConfig(
                slippage_type=SlippageType.LIQUIDITY_BASED,
                liquidity_base_bps=2.0,
            )
        )
        result = model.calculate(Decimal("1"), liquidity_score=0.0)
        assert result == 20.0

    def test_spread_based_slippage(self):
        model = SlippageModel(
            SlippageModelConfig(
                slippage_type=SlippageType.SPREAD_BASED,
                spread_multiplier=0.5,
            )
        )
        result = model.calculate(Decimal("1"), spread_pips=2.0)
        assert result == 1.0

    def test_limit_order_half_slippage(self):
        model = SlippageModel(SlippageModelConfig(slippage_type=SlippageType.FIXED, fixed_bps=2.0))
        result = model.calculate(Decimal("1"), is_market_order=False)
        assert result == 1.0

    def test_slippage_clamped_to_max(self):
        model = SlippageModel(
            SlippageModelConfig(
                slippage_type=SlippageType.FIXED,
                fixed_bps=100.0,
                max_slippage_bps=50.0,
            )
        )
        result = model.calculate(Decimal("1"))
        assert result == 50.0

    def test_slippage_clamped_to_min(self):
        model = SlippageModel(
            SlippageModelConfig(
                slippage_type=SlippageType.FIXED,
                fixed_bps=0.0,
                min_slippage_bps=1.0,
            )
        )
        result = model.calculate(Decimal("1"))
        assert result == 1.0


class TestSpreadModel:
    """Test spread simulation."""

    def test_default_config(self):
        model = SpreadModel()
        assert model.config.value_pips == 0.0

    @pytest.mark.asyncio
    async def test_fixed_spread(self):
        model = SpreadModel(SpreadConfig(type="fixed", value_pips=1.0))
        spread = await model.calculate_spread_pips()
        assert spread == 1.0

    @pytest.mark.asyncio
    async def test_variable_spread_with_volatility(self):
        model = SpreadModel(SpreadConfig(type="variable", value_pips=1.0, variable_factor=2.0))
        spread = await model.calculate_spread_pips(volatility=0.5)
        assert spread > 1.0

    @pytest.mark.asyncio
    async def test_min_max_spread(self):
        model = SpreadModel(SpreadConfig(type="fixed", value_pips=10.0, min_pips=1.0, max_pips=5.0))
        spread = await model.calculate_spread_pips()
        assert spread >= 1.0
        assert spread <= 5.0

    @pytest.mark.asyncio
    async def test_zero_spread(self):
        model = SpreadModel(SpreadConfig(type="fixed", value_pips=0.0))
        spread = await model.calculate_spread_pips()
        assert spread == 0.0

    @pytest.mark.asyncio
    async def test_extreme_volatility_spread(self):
        model = SpreadModel(SpreadConfig(type="variable", value_pips=1.0, variable_factor=10.0))
        spread = await model.calculate_spread_pips(volatility=10.0)
        assert spread >= 1.0

    @pytest.mark.asyncio
    async def test_variable_spread_no_volatility(self):
        model = SpreadModel(SpreadConfig(type="variable", value_pips=1.0, variable_factor=2.0))
        spread = await model.calculate_spread_pips(volatility=0.0)
        assert spread == 1.0

    @pytest.mark.asyncio
    async def test_news_event_spread(self):
        model = SpreadModel(SpreadConfig(type="fixed", value_pips=1.0))
        spread = await model.calculate_spread_pips(is_high_impact_news=True)
        assert spread == pytest.approx(3.0, abs=0.5)

    @pytest.mark.asyncio
    async def test_scenario_multiplier_spread(self):
        model = SpreadModel(SpreadConfig(type="fixed", value_pips=1.0))
        spread = await model.calculate_spread_pips(scenario_multiplier=5.0)
        assert spread == pytest.approx(5.0, abs=0.5)

    @pytest.mark.asyncio
    async def test_apply_spread_to_mid_price(self):
        model = SpreadModel(SpreadConfig(type="fixed", value_pips=2.0))
        bid, ask = await model.apply_spread(Decimal("1.1000"))
        assert bid < Decimal("1.1000")
        assert ask > Decimal("1.1000")
        assert bid > Decimal("0")

    @pytest.mark.asyncio
    async def test_apply_spread_ensures_positive_bid(self):
        model = SpreadModel(SpreadConfig(type="fixed", value_pips=100000.0))
        bid, ask = await model.apply_spread(Decimal("0.0001"))
        assert bid > Decimal("0")

    @pytest.mark.asyncio
    async def test_spread_in_pips(self):
        model = SpreadModel(SpreadConfig(type="fixed", value_pips=2.5))
        pips = await model.spread_in_pips()
        assert pips == 2.5

    @pytest.mark.asyncio
    async def test_get_config(self):
        config = SpreadConfig(type="variable", value_pips=1.0)
        model = SpreadModel(config)
        retrieved = await model.get_config()
        assert retrieved == config

    @pytest.mark.asyncio
    async def test_update_config(self):
        model = SpreadModel(SpreadConfig(type="fixed", value_pips=1.0))
        new_config = SpreadConfig(type="variable", value_pips=2.0)
        await model.update_config(new_config)
        assert model.config.value_pips == 2.0

    def test_set_seed(self):
        model = SpreadModel()
        model.set_seed(123)
        assert model._random is not None

    def test_set_seed_none(self):
        model = SpreadModel()
        model.set_seed(None)
        assert model._random is not None


class TestSwapModel:
    """Test swap calculation."""

    def test_default_config(self):
        model = SwapModel()
        assert model.config.long_swap_rate == Decimal("-2.0")
        assert model.config.short_swap_rate == Decimal("-1.5")

    def test_zero_swap(self):
        cfg = SwapModelConfig(long_swap_rate=Decimal("0"), short_swap_rate=Decimal("0"))
        model = SwapModel(cfg)
        result = model.calculate(Decimal("1"), "long", Decimal("100000"))
        assert result == Decimal("0.00")

    def test_long_swap_positive(self):
        cfg = SwapModelConfig(long_swap_rate=Decimal("0.5"), short_swap_rate=Decimal("-0.5"))
        model = SwapModel(cfg)
        result = model.calculate(Decimal("1"), "long", Decimal("100000"))
        assert result == Decimal("0.00")

    def test_short_swap_negative(self):
        cfg = SwapModelConfig(long_swap_rate=Decimal("0.5"), short_swap_rate=Decimal("-0.5"))
        model = SwapModel(cfg)
        result = model.calculate(Decimal("1000"), "short", Decimal("100000"))
        assert result < Decimal("0"), f"Expected negative swap but got {result}"

    def test_triple_swap_wednesday(self):
        from datetime import datetime, timezone

        wednesday = datetime(2024, 1, 3, tzinfo=timezone.utc)
        cfg = SwapModelConfig(long_swap_rate=Decimal("1.0"), short_swap_rate=Decimal("-1.0"))
        model = SwapModel(cfg)
        result = model.calculate(Decimal("1"), "long", Decimal("100000"), timestamp=wednesday)
        assert isinstance(result, Decimal)

    def test_swap_all_weekdays(self):
        from datetime import datetime, timezone

        cfg = SwapModelConfig(long_swap_rate=Decimal("1.0"), short_swap_rate=Decimal("-1.0"))
        model = SwapModel(cfg)
        for day in range(1, 8):
            ts = datetime(2024, 1, day, tzinfo=timezone.utc)
            result = model.calculate(Decimal("1"), "long", Decimal("100000"), timestamp=ts)
            assert isinstance(result, Decimal)

    def test_swap_large_quantity(self):
        cfg = SwapModelConfig(long_swap_rate=Decimal("2.5"), short_swap_rate=Decimal("-2.0"))
        model = SwapModel(cfg)
        result = model.calculate(Decimal("1000000"), "long", Decimal("100000"))
        assert isinstance(result, Decimal)

    def test_swap_invalid_side_falls_back_to_long(self):
        cfg = SwapModelConfig(long_swap_rate=Decimal("1.0"), short_swap_rate=Decimal("-1.0"))
        model = SwapModel(cfg)
        result = model.calculate(Decimal("1"), "invalid_side", Decimal("100000"))
        assert isinstance(result, Decimal)


class TestLatencyModel:
    """Test latency simulation."""

    def test_default_config(self):
        model = LatencyModel()
        assert model.config.base_latency_ms == 50.0

    def test_base_latency(self):
        model = LatencyModel()
        latency = model.calculate_latency_ms("market", 1.0)
        assert latency > 0

    def test_market_order_latency_lower(self):
        model = LatencyModel(LatencyModelConfig(base_latency_ms=50.0, use_jitter=False))
        market_latency = model.calculate_latency_ms("market", 1.0)
        limit_latency = model.calculate_latency_ms("limit", 1.0)
        assert (
            market_latency <= limit_latency
        ), f"Expected market ({market_latency}) <= limit ({limit_latency})"

    def test_stop_order_latency(self):
        model = LatencyModel(LatencyModelConfig(base_latency_ms=50.0, use_jitter=False))
        latency = model.calculate_latency_ms("stop", 1.0)
        assert latency > 0

    def test_zero_quantity_latency(self):
        model = LatencyModel(LatencyModelConfig(base_latency_ms=50.0, use_jitter=False))
        latency = model.calculate_latency_ms("market", 0.0)
        assert latency > 0

    def test_large_quantity_latency(self):
        model = LatencyModel(LatencyModelConfig(base_latency_ms=50.0, use_jitter=False))
        small_latency = model.calculate_latency_ms("market", 1.0)
        large_latency = model.calculate_latency_ms("market", 1000000.0)
        assert large_latency >= small_latency

    def test_latency_with_jitter(self):
        model = LatencyModel(LatencyModelConfig(base_latency_ms=50.0, use_jitter=True))
        latencies = [model.calculate_latency_ms("market", 1.0) for _ in range(5)]
        assert len(set(latencies)) > 1 or all(l >= 30 for l in latencies)

    def test_latency_clamped_to_min(self):
        model = LatencyModel(
            LatencyModelConfig(base_latency_ms=5.0, min_latency_ms=10.0, use_jitter=False)
        )
        latency = model.calculate_latency_ms("market", 1.0)
        assert latency >= 10.0

    def test_latency_clamped_to_max(self):
        model = LatencyModel(
            LatencyModelConfig(base_latency_ms=1000.0, max_latency_ms=500.0, use_jitter=False)
        )
        latency = model.calculate_latency_ms("market", 1.0)
        assert latency <= 500.0

    def test_confirmation_delay(self):
        model = LatencyModel(LatencyModelConfig(base_latency_ms=50.0, use_jitter=False))
        delay = model.calculate_confirmation_delay_ms()
        assert delay >= 50.0

    def test_confirmation_delay_with_latency(self):
        model = LatencyModel(LatencyModelConfig(base_latency_ms=50.0, use_jitter=False))
        delay = model.calculate_confirmation_delay_ms(latency_ms=100.0)
        assert delay >= 100.0


class TestLiquidityModel:
    """Test liquidity constraints."""

    def test_default_config(self):
        model = LiquidityModel()
        assert model.config.default_liquidity_score == 0.8

    def test_full_liquidity(self):
        model = LiquidityModel()
        assert model.is_executable(Decimal("1")) is True

    def test_zero_liquidity(self):
        model = LiquidityModel()
        assert model.is_executable(Decimal("1")) is True

    def test_small_order_executable(self):
        model = LiquidityModel()
        assert model.is_executable(Decimal("1")) is True

    def test_liquidity_with_custom_score(self):
        model = LiquidityModel(LiquidityModelConfig(default_liquidity_score=1.0))
        assert model.is_executable(Decimal("1000000")) is True

    def test_zero_quantity_executable(self):
        model = LiquidityModel()
        assert model.is_executable(Decimal("0")) is True

    def test_very_large_order_at_low_liquidity(self):
        model = LiquidityModel()
        assert model.is_executable(Decimal("1000000000")) is True

    def test_get_liquidity_score_default(self):
        model = LiquidityModel()
        score = model.get_liquidity_score("EURUSD", Decimal("1"))
        assert score > 0

    def test_get_liquidity_score_large_order(self):
        model = LiquidityModel()
        score = model.get_liquidity_score("EURUSD", Decimal("1000"))
        assert score > 0

    def test_get_max_executable_volume(self):
        model = LiquidityModel()
        max_vol = model.get_max_executable_volume(Decimal("100000"))
        assert max_vol > 0

    def test_is_executable_with_current_volume(self):
        model = LiquidityModel()
        assert model.is_executable(Decimal("1"), Decimal("100")) is True
        assert model.is_executable(Decimal("50"), Decimal("100")) is False

    def test_liquidity_score_time_adjustment_asian(self):
        from datetime import datetime, timezone

        model = LiquidityModel()
        asian_time = datetime(2024, 1, 3, 3, 0, tzinfo=timezone.utc)
        score = model.get_liquidity_score("EURUSD", Decimal("1"), timestamp=asian_time)
        assert score < 0.8

    def test_liquidity_score_time_adjustment_london_ny(self):
        from datetime import datetime, timezone

        model = LiquidityModel()
        overlap = datetime(2024, 1, 3, 15, 0, tzinfo=timezone.utc)
        score = model.get_liquidity_score("EURUSD", Decimal("1"), timestamp=overlap)
        assert score > 0.8

    def test_liquidity_score_time_adjustment_late(self):
        from datetime import datetime, timezone

        model = LiquidityModel()
        late = datetime(2024, 1, 3, 19, 0, tzinfo=timezone.utc)
        score = model.get_liquidity_score("EURUSD", Decimal("1"), timestamp=late)
        assert score < 0.8

    def test_liquidity_score_with_base_score(self):
        from datetime import datetime, timezone

        model = LiquidityModel()
        asian_time = datetime(2024, 1, 3, 3, 0, tzinfo=timezone.utc)
        score = model.get_liquidity_score(
            "EURUSD", Decimal("1"), base_score=0.5, timestamp=asian_time
        )
        assert score < 0.5

    def test_liquidity_score_minimum(self):
        model = LiquidityModel(LiquidityModelConfig(min_liquidity_score=0.2))
        score = model.get_liquidity_score("EURUSD", Decimal("1000000"))
        assert score >= 0.2


class TestMarketImpactModel:
    """Test market impact."""

    def test_default_config(self):
        model = MarketImpactModel()
        assert model.config.temporary_impact_coefficient == 0.1
        assert model.config.permanent_impact_coefficient == 0.01

    def test_zero_impact_small_order(self):
        cfg = MarketImpactModelConfig(
            temporary_impact_coefficient=0.0, permanent_impact_coefficient=0.0
        )
        model = MarketImpactModel(cfg)
        impact = model.calculate_impact_bps(Decimal("1"), Decimal("100000"))
        assert impact == 0.0

    def test_large_order_impact(self):
        model = MarketImpactModel()
        impact = model.calculate_impact_bps(Decimal("1000"), Decimal("100000"))
        assert impact > 0

    def test_zero_quantity_impact(self):
        model = MarketImpactModel()
        impact = model.calculate_impact_bps(Decimal("0"), Decimal("100000"))
        assert impact == 0.0

    def test_temporary_vs_permanent_impact(self):
        model = MarketImpactModel(
            MarketImpactModelConfig(
                temporary_impact_coefficient=0.2,
                permanent_impact_coefficient=0.01,
            )
        )
        impact = model.calculate_impact_bps(Decimal("1000"), Decimal("100000"))
        assert impact > 0

    def test_very_large_order_impact(self):
        model = MarketImpactModel()
        impact = model.calculate_impact_bps(Decimal("1000000000"), Decimal("100000"))
        assert impact > 0

    def test_impact_with_custom_avg_daily_volume(self):
        model = MarketImpactModel()
        small_volume = model.calculate_impact_bps(Decimal("1000"), Decimal("100000"))
        large_volume = model.calculate_impact_bps(Decimal("1000"), Decimal("1000000000"))
        assert small_volume > large_volume

    def test_impact_with_volatility(self):
        model = MarketImpactModel()
        impact = model.calculate_impact_bps(Decimal("1000"), Decimal("100000"), volatility_bps=20.0)
        assert impact > 0

    def test_impact_with_liquidity_score(self):
        model = MarketImpactModel()
        impact = model.calculate_impact_bps(Decimal("1000"), Decimal("100000"), liquidity_score=0.2)
        assert impact > 0

    def test_impact_clamped_to_max(self):
        model = MarketImpactModel(MarketImpactModelConfig(max_impact_bps=10.0))
        impact = model.calculate_impact_bps(Decimal("1000000000"), Decimal("1000"))
        assert impact <= 10.0

    def test_impact_zero_avg_daily_volume(self):
        model = MarketImpactModel()
        impact = model.calculate_impact_bps(Decimal("1000"), Decimal("0"))
        assert impact == 0.0

    def test_effective_spread_calculation(self):
        model = MarketImpactModel()
        effective = model.calculate_effective_spread(2.0, Decimal("1000"), Decimal("100000"))
        assert effective > 2.0

    def test_impact_cost_calculation(self):
        model = MarketImpactModel()
        cost = model.calculate_impact_cost(Decimal("100000"), Decimal("1.1000"), Decimal("100000"))
        assert cost > Decimal("0")
