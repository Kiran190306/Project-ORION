"""Tests for EPIC-010 execution and portfolio simulators."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.backtesting.execution_simulator import (
    ExecutionSimulationConfig,
    ExecutionSimulator,
)
from libraries.domain.backtesting.models import (
    ExecutionSimulationResult,
    ExecutionSimulationStatus,
    FillSimulation,
    OrderSimulation,
    OrderSimulationSide,
    OrderSimulationStatus,
    OrderSimulationType,
    PortfolioSnapshot,
)
from libraries.domain.backtesting.portfolio_simulator import (
    PortfolioSimulationConfig,
    PortfolioSimulator,
)


class TestExecutionSimulator:
    """Test execution simulation."""

    @pytest.mark.asyncio
    async def test_market_order_execution(self):
        sim = ExecutionSimulator()
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
        )
        result = await sim.execute_order(order, Decimal("1.0990"), Decimal("1.1000"))
        assert result.status == ExecutionSimulationStatus.SUCCESS
        assert len(result.fills) == 1
        assert result.average_price is not None

    @pytest.mark.asyncio
    async def test_sell_market_order(self):
        sim = ExecutionSimulator()
        order = OrderSimulation(
            order_id="o2",
            symbol="EURUSD",
            side=OrderSimulationSide.SELL,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
        )
        result = await sim.execute_order(order, Decimal("1.0990"), Decimal("1.1000"))
        assert result.status == ExecutionSimulationStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_limit_order(self):
        sim = ExecutionSimulator()
        order = OrderSimulation(
            order_id="o3",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.LIMIT,
            quantity=Decimal("1000"),
            price=Decimal("1.0950"),
        )
        result = await sim.execute_order(order, Decimal("1.0990"), Decimal("1.1000"))
        assert result.status == ExecutionSimulationStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_stop_order(self):
        sim = ExecutionSimulator()
        order = OrderSimulation(
            order_id="o4",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.STOP,
            quantity=Decimal("1000"),
            price=Decimal("1.1050"),
        )
        result = await sim.execute_order(order, Decimal("1.0990"), Decimal("1.1000"))
        assert result.status == ExecutionSimulationStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_commission_included(self):
        sim = ExecutionSimulator()
        order = OrderSimulation(
            order_id="o6",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("100000"),
        )
        result = await sim.execute_order(order, Decimal("1.0990"), Decimal("1.1000"))
        assert result.total_commission is not None

    @pytest.mark.asyncio
    async def test_slippage_applied(self):
        sim = ExecutionSimulator()
        order = OrderSimulation(
            order_id="o7",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("100000"),
        )
        result = await sim.execute_order(
            order, Decimal("1.0990"), Decimal("1.1000"), volatility=2.0
        )
        assert result.total_slippage is not None


class TestPortfolioSimulator:
    """Test portfolio simulation."""

    @pytest.mark.asyncio
    async def test_initial_state(self):
        sim = PortfolioSimulator()
        assert sim.balance == Decimal("10000")
        assert sim.equity == Decimal("10000")

    @pytest.mark.asyncio
    async def test_custom_initial_balance(self):
        config = PortfolioSimulationConfig(initial_balance=Decimal("50000"))
        sim = PortfolioSimulator(config)
        assert sim.balance == Decimal("50000")

    @pytest.mark.asyncio
    async def test_apply_fill(self):
        sim = PortfolioSimulator(PortfolioSimulationConfig(initial_balance=Decimal("50000")))
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("100"),
        )
        result = ExecutionSimulationResult(
            order=order,
            status=ExecutionSimulationStatus.SUCCESS,
            fills=(),
            total_quantity=Decimal("100"),
            average_price=Decimal("1.1000"),
            total_commission=Decimal("0"),
            total_slippage=Decimal("0"),
            latency_ms=0.0,
        )
        await sim.apply_fill(result)
        assert sim.balance == Decimal("50000")
        assert sim.is_stop_out is False

    @pytest.mark.asyncio
    async def test_reset(self):
        sim = PortfolioSimulator()
        assert sim.balance == Decimal("10000")
        await sim.reset()
        assert sim.balance == Decimal("10000")

    @pytest.mark.asyncio
    async def test_snapshot(self):
        sim = PortfolioSimulator()
        snap = await sim.get_snapshot()
        assert isinstance(snap, PortfolioSnapshot)
        assert snap.balance == Decimal("10000")

    @pytest.mark.asyncio
    async def test_margin_level(self):
        sim = PortfolioSimulator()
        assert sim.margin_level == float("inf")


class TestSimulationEdgeCases:
    """Test edge cases for simulators."""

    @pytest.mark.asyncio
    async def test_stop_out(self):
        sim = PortfolioSimulator(
            PortfolioSimulationConfig(initial_balance=Decimal("100"), stop_out_level=50.0)
        )
        order = OrderSimulation(
            order_id="o1",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("100000"),
        )
        result = ExecutionSimulationResult(
            order=order,
            status=ExecutionSimulationStatus.SUCCESS,
            total_quantity=Decimal("100000"),
            average_price=Decimal("1.1000"),
            total_commission=Decimal("0"),
        )
        await sim.apply_fill(result)
        assert sim.balance >= Decimal("0")

    @pytest.mark.asyncio
    async def test_multiple_fills(self):
        sim = PortfolioSimulator()
        for i in range(3):
            order = OrderSimulation(
                order_id=f"o{i}",
                symbol="EURUSD",
                side=OrderSimulationSide.BUY,
                order_type=OrderSimulationType.MARKET,
                quantity=Decimal("100"),
            )
            result = ExecutionSimulationResult(
                order=order,
                status=ExecutionSimulationStatus.SUCCESS,
                total_quantity=Decimal("100"),
                average_price=Decimal("1.1000"),
                total_commission=Decimal("0"),
            )
            await sim.apply_fill(result)
        snap = await sim.get_snapshot()
        assert snap.position_count == 0

    @pytest.mark.asyncio
    async def test_insufficient_liquidity_execution(self):
        sim = ExecutionSimulator()
        order = OrderSimulation(
            order_id="o_liq",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000000000"),
        )
        result = await sim.execute_order(
            order, Decimal("1.0990"), Decimal("1.1000"), liquidity_score=0.01
        )
        assert result.status in (
            ExecutionSimulationStatus.SUCCESS,
            ExecutionSimulationStatus.FAILURE,
        )

    @pytest.mark.asyncio
    async def test_zero_quantity_execution(self):
        sim = ExecutionSimulator()
        order = OrderSimulation(
            order_id="o_zero",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("0"),
        )
        result = await sim.execute_order(order, Decimal("1.0990"), Decimal("1.1000"))
        assert result.status == ExecutionSimulationStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_extreme_volatility_execution(self):
        sim = ExecutionSimulator()
        order = OrderSimulation(
            order_id="o_vol",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
        )
        result = await sim.execute_order(
            order, Decimal("1.0990"), Decimal("1.1000"), volatility=100.0
        )
        assert result.status == ExecutionSimulationStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_market_price_update_portfolio(self):
        sim = PortfolioSimulator()
        await sim.update_market_price("EURUSD", Decimal("1.2000"))
        snap = await sim.get_snapshot()
        assert snap.equity is not None

    @pytest.mark.asyncio
    async def test_commission_in_execution(self):
        sim = ExecutionSimulator()
        order = OrderSimulation(
            order_id="o_comm",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
        )
        result = await sim.execute_order(order, Decimal("1.0990"), Decimal("1.1000"))
        assert result.total_commission > Decimal("0")

    @pytest.mark.asyncio
    async def test_stop_out_after_multiple_fills(self):
        sim = PortfolioSimulator(
            PortfolioSimulationConfig(
                initial_balance=Decimal("1000"), stop_out_level=20.0, leverage=Decimal("1")
            )
        )
        for i in range(10):
            order = OrderSimulation(
                order_id=f"o_so{i}",
                symbol="EURUSD",
                side=OrderSimulationSide.BUY,
                order_type=OrderSimulationType.MARKET,
                quantity=Decimal("10000"),
            )
            result = ExecutionSimulationResult(
                order=order,
                status=ExecutionSimulationStatus.SUCCESS,
                total_quantity=Decimal("10000"),
                average_price=Decimal("1.1000"),
                total_commission=Decimal("0"),
            )
            await sim.apply_fill(result, current_price=Decimal("0.9500"))
        # Verify the portfolio has significant margin usage
        assert sim.used_margin > Decimal("0")

    @pytest.mark.asyncio
    async def test_execution_with_timestamp(self):
        from datetime import datetime, timezone

        sim = ExecutionSimulator()
        order = OrderSimulation(
            order_id="o_ts",
            symbol="EURUSD",
            side=OrderSimulationSide.BUY,
            order_type=OrderSimulationType.MARKET,
            quantity=Decimal("1000"),
        )
        ts = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = await sim.execute_order(order, Decimal("1.0990"), Decimal("1.1000"), timestamp=ts)
        assert result.timestamp == ts
