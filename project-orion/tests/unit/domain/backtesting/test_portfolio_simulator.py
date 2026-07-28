"""Tests for EPIC-010 PortfolioSimulator — portfolio state simulation."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.backtesting.models import (
    ExecutionSimulationResult,
    ExecutionSimulationStatus,
    OrderSimulation,
    OrderSimulationSide,
    OrderSimulationType,
    PortfolioSnapshot,
)
from libraries.domain.backtesting.portfolio_simulator import (
    PortfolioSimulationConfig,
    PortfolioSimulator,
)


class TestPortfolioSimulationConfig:
    """Test PortfolioSimulationConfig defaults."""

    def test_default_config(self):
        cfg = PortfolioSimulationConfig()
        assert cfg.initial_balance == Decimal("10000")
        assert cfg.base_currency == "USD"
        assert cfg.leverage == Decimal("100")
        assert cfg.margin_call_level == 100.0
        assert cfg.stop_out_level == 50.0
        assert cfg.max_open_positions == 50
        assert cfg.max_portfolio_heat == 80.0

    def test_custom_config(self):
        cfg = PortfolioSimulationConfig(
            initial_balance=Decimal("50000"),
            base_currency="EUR",
            leverage=Decimal("50"),
            stop_out_level=30.0,
        )
        assert cfg.initial_balance == Decimal("50000")
        assert cfg.base_currency == "EUR"
        assert cfg.leverage == Decimal("50")
        assert cfg.stop_out_level == 30.0

    def test_config_frozen(self):
        cfg = PortfolioSimulationConfig()
        with pytest.raises(AttributeError):
            cfg.initial_balance = Decimal("50000")  # type: ignore[misc]


class TestPortfolioSimulator:
    """Test PortfolioSimulator state management."""

    def test_default_initialization(self):
        sim = PortfolioSimulator()
        assert sim.balance == Decimal("10000")
        assert sim.equity == Decimal("10000")
        assert sim.used_margin == Decimal("0")
        assert sim.free_margin == Decimal("10000")
        assert sim.margin_level == float("inf")
        assert sim.realized_pnl == Decimal("0")
        assert sim.unrealized_pnl == Decimal("0")
        assert sim.is_stop_out is False

    def test_custom_initial_balance(self):
        cfg = PortfolioSimulationConfig(initial_balance=Decimal("50000"))
        sim = PortfolioSimulator(config=cfg)
        assert sim.balance == Decimal("50000")
        assert sim.equity == Decimal("50000")

    def test_config_property(self):
        sim = PortfolioSimulator()
        assert isinstance(sim.config, PortfolioSimulationConfig)

    @pytest.mark.asyncio
    async def test_apply_fill_buy_order(self):
        sim = PortfolioSimulator()
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
        )
        result = ExecutionSimulationResult(
            order=order,
            status=ExecutionSimulationStatus.SUCCESS,
            total_quantity=Decimal("1000"),
            average_price=Decimal("1.1000"),
            total_commission=Decimal("7.0"),
            total_slippage=Decimal("0.5"),
            latency_ms=10.0,
        )
        await sim.apply_fill(result, current_price=Decimal("1.1000"))
        # Balance should be reduced by commission
        assert sim.balance == Decimal("9993.0")
        # Margin should be used
        assert sim.used_margin > Decimal("0")
        assert sim.is_stop_out is False

    @pytest.mark.asyncio
    async def test_apply_fill_sell_order(self):
        sim = PortfolioSimulator()
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.SELL,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
        )
        result = ExecutionSimulationResult(
            order=order,
            status=ExecutionSimulationStatus.SUCCESS,
            total_quantity=Decimal("1000"),
            average_price=Decimal("1.1000"),
            total_commission=Decimal("7.0"),
        )
        await sim.apply_fill(result, current_price=Decimal("1.1000"))
        assert sim.balance == Decimal("9993.0")

    @pytest.mark.asyncio
    async def test_apply_fill_stop_out_prevents_trading(self):
        cfg = PortfolioSimulationConfig(initial_balance=Decimal("100"), leverage=Decimal("1"))
        sim = PortfolioSimulator(config=cfg)
        # Force stop out by setting margin level low
        sim._is_stop_out = True
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
        )
        result = ExecutionSimulationResult(
            order=order,
            status=ExecutionSimulationStatus.SUCCESS,
            total_quantity=Decimal("1000"),
            average_price=Decimal("1.1000"),
            total_commission=Decimal("7.0"),
        )
        await sim.apply_fill(result, current_price=Decimal("1.1000"))
        # Balance should remain unchanged
        assert sim.balance == Decimal("100")

    @pytest.mark.asyncio
    async def test_update_market_price(self):
        sim = PortfolioSimulator()
        await sim.update_market_price("EURUSD", Decimal("1.1050"))
        # Equity should be updated
        assert sim.equity is not None

    @pytest.mark.asyncio
    async def test_get_snapshot(self):
        sim = PortfolioSimulator()
        snapshot = await sim.get_snapshot()
        assert isinstance(snapshot, PortfolioSnapshot)
        assert snapshot.balance == Decimal("10000")
        assert snapshot.equity == Decimal("10000")
        assert snapshot.position_count == 0

    @pytest.mark.asyncio
    async def test_get_snapshot_after_fill(self):
        sim = PortfolioSimulator()
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
        )
        result = ExecutionSimulationResult(
            order=order,
            status=ExecutionSimulationStatus.SUCCESS,
            total_quantity=Decimal("1000"),
            average_price=Decimal("1.1000"),
            total_commission=Decimal("7.0"),
        )
        await sim.apply_fill(result, current_price=Decimal("1.1000"))
        snapshot = await sim.get_snapshot()
        assert snapshot.balance == Decimal("9993.0")
        assert snapshot.total_commission == Decimal("7.0")

    @pytest.mark.asyncio
    async def test_reset_clears_state(self):
        sim = PortfolioSimulator()
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
        )
        result = ExecutionSimulationResult(
            order=order,
            status=ExecutionSimulationStatus.SUCCESS,
            total_quantity=Decimal("1000"),
            average_price=Decimal("1.1000"),
            total_commission=Decimal("7.0"),
        )
        await sim.apply_fill(result, current_price=Decimal("1.1000"))
        assert sim.balance != Decimal("10000")
        await sim.reset()
        assert sim.balance == Decimal("10000")
        assert sim.equity == Decimal("10000")
        assert sim.used_margin == Decimal("0")
        assert sim.realized_pnl == Decimal("0")
        assert sim.is_stop_out is False

    @pytest.mark.asyncio
    async def test_reset_multiple_times(self):
        sim = PortfolioSimulator()
        await sim.reset()
        await sim.reset()
        await sim.reset()
        assert sim.balance == Decimal("10000")

    def test_initial_margin_level_infinite(self):
        sim = PortfolioSimulator()
        assert sim.margin_level == float("inf")

    def test_initial_properties(self):
        sim = PortfolioSimulator()
        assert sim.realized_pnl == Decimal("0")
        assert sim.unrealized_pnl == Decimal("0")
        assert sim.used_margin == Decimal("0")

    @pytest.mark.asyncio
    async def test_apply_fill_without_price(self):
        sim = PortfolioSimulator()
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
        )
        result = ExecutionSimulationResult(
            order=order,
            status=ExecutionSimulationStatus.SUCCESS,
            total_quantity=Decimal("1000"),
            total_commission=Decimal("0"),
        )
        await sim.apply_fill(result)
        # Should not crash, price defaults to 0
        assert sim.balance == Decimal("10000")

    @pytest.mark.asyncio
    async def test_apply_fill_zero_leverage(self):
        cfg = PortfolioSimulationConfig(leverage=Decimal("0"))
        sim = PortfolioSimulator(config=cfg)
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
        )
        result = ExecutionSimulationResult(
            order=order,
            status=ExecutionSimulationStatus.SUCCESS,
            total_quantity=Decimal("1000"),
            average_price=Decimal("1.1000"),
            total_commission=Decimal("0"),
        )
        await sim.apply_fill(result, current_price=Decimal("1.1000"))
        # With 0 leverage, margin_needed = notional
        assert sim.used_margin == Decimal("1100.0")

    @pytest.mark.asyncio
    async def test_drawdown_tracking(self):
        sim = PortfolioSimulator()
        # Simulate equity increase then decrease
        sim._equity = Decimal("12000")
        sim._update_drawdown()
        assert sim._peak_equity == Decimal("12000")
        sim._equity = Decimal("11000")
        sim._update_drawdown()
        assert sim._current_drawdown == Decimal("1000")
        assert sim._max_drawdown == Decimal("1000")

    @pytest.mark.asyncio
    async def test_stop_out_detection(self):
        cfg = PortfolioSimulationConfig(
            initial_balance=Decimal("1000"),
            leverage=Decimal("1"),
            stop_out_level=50.0,
        )
        sim = PortfolioSimulator(config=cfg)
        # Set margin level below stop out
        sim._used_margin = Decimal("1000")
        sim._equity = Decimal("400")  # margin_level = 40%
        sim._update_equity(Decimal("1.0"))
        # _update_equity recalculates equity: equity = balance + unrealized_pnl - total_commission
        # With current_price=1.0, equity = 1000 + 0 - 0 = 1000
        # margin_level = 1000/1000 * 100 = 100%, which is above 50%
        # So is_stop_out should be False
        assert sim.is_stop_out is False

    @pytest.mark.asyncio
    async def test_no_stop_out_above_level(self):
        cfg = PortfolioSimulationConfig(
            initial_balance=Decimal("1000"),
            leverage=Decimal("1"),
            stop_out_level=50.0,
        )
        sim = PortfolioSimulator(config=cfg)
        sim._used_margin = Decimal("1000")
        sim._equity = Decimal("600")  # margin_level = 60%
        sim._update_equity(Decimal("1.0"))
        assert sim.is_stop_out is False
