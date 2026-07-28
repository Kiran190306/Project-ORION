"""Tests for EPIC-010 statistics calculators."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.backtesting.models import (
    EquitySnapshot,
    ExecutionSimulationResult,
    ExecutionSimulationStatus,
    FillSimulation,
    OrderSimulation,
    OrderSimulationSide,
    OrderSimulationType,
    PortfolioSnapshot,
)
from libraries.domain.backtesting.statistics import (
    ExecutionStatistics,
    ExecutionStatisticsResult,
    PortfolioStatistics,
    PortfolioStatisticsResult,
    RiskStatisticsCalculator,
    RiskStatisticsResult,
    ScenarioStatistics,
    ScenarioStatisticsResult,
    TradeStatistics,
    TradeStatisticsResult,
)


class TestTradeStatistics:
    """Test trade-level statistics."""

    @pytest.mark.asyncio
    async def test_empty_trades(self):
        stats = TradeStatistics()
        result = await stats.calculate()
        assert isinstance(result, TradeStatisticsResult)
        assert result.total_trades == 0

    @pytest.mark.asyncio
    async def test_single_trade(self):
        stats = TradeStatistics()
        stats.add_trade(
            {"pnl": 100.0, "symbol": "EURUSD", "entry_price": 1.1000, "exit_price": 1.1100}
        )
        result = await stats.calculate()
        assert result.total_trades == 1
        assert result.winning_trades == 1
        assert result.win_rate == 1.0

    @pytest.mark.asyncio
    async def test_multiple_trades(self):
        stats = TradeStatistics()
        stats.add_trade({"pnl": 100.0})
        stats.add_trade({"pnl": -50.0})
        stats.add_trade({"pnl": 75.0})
        result = await stats.calculate()
        assert result.total_trades == 3
        assert result.winning_trades == 2
        assert result.losing_trades == 1
        assert abs(result.win_rate - 2 / 3) < 0.001

    @pytest.mark.asyncio
    async def test_profit_factor_infinite(self):
        stats = TradeStatistics()
        stats.add_trade({"pnl": 100.0})
        result = await stats.calculate()
        assert result.profit_factor == float("inf")

    @pytest.mark.asyncio
    async def test_profit_factor_finite(self):
        stats = TradeStatistics()
        stats.add_trade({"pnl": 200.0})
        stats.add_trade({"pnl": -50.0})
        result = await stats.calculate()
        assert result.profit_factor == 4.0  # 200/50

    @pytest.mark.asyncio
    async def test_single_trade_large_pnl(self):
        stats = TradeStatistics()
        stats.add_trade({"pnl": 1000000.0})
        result = await stats.calculate()
        assert result.total_trades == 1
        assert result.winning_trades == 1
        assert result.largest_win == 1000000.0

    @pytest.mark.asyncio
    async def test_all_losing_trades(self):
        stats = TradeStatistics()
        stats.add_trade({"pnl": -10.0})
        stats.add_trade({"pnl": -20.0})
        result = await stats.calculate()
        assert result.total_trades == 2
        assert result.winning_trades == 0
        assert result.losing_trades == 2
        assert result.win_rate == 0.0
        assert result.profit_factor == 0.0

    @pytest.mark.asyncio
    async def test_trade_largest_values(self):
        stats = TradeStatistics()
        stats.add_trade({"pnl": 10.0})
        stats.add_trade({"pnl": -5.0})
        stats.add_trade({"pnl": 8.0})
        stats.add_trade({"pnl": -3.0})
        stats.add_trade({"pnl": 6.0})
        stats.add_trade({"pnl": -1.0})
        result = await stats.calculate()
        assert result.largest_win == 10.0
        assert result.largest_loss == -5.0


class TestPortfolioStatistics:
    """Test portfolio-level statistics."""

    @pytest.mark.asyncio
    async def test_empty(self):
        stats = PortfolioStatistics()
        result = await stats.calculate()
        assert isinstance(result, PortfolioStatisticsResult)

    @pytest.mark.asyncio
    async def test_with_snapshots(self):
        from datetime import datetime, timezone

        stats = PortfolioStatistics()
        snap1 = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc), balance=Decimal("10000"), equity=Decimal("10000")
        )
        snap2 = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc), balance=Decimal("11000"), equity=Decimal("11000")
        )
        stats.add_snapshot(snap1)
        stats.add_snapshot(snap2)
        result = await stats.calculate()
        assert result.final_balance == 11000.0
        assert result.net_profit == 1000.0

    @pytest.mark.asyncio
    async def test_single_snapshot(self):
        from datetime import datetime, timezone

        stats = PortfolioStatistics()
        snap = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc), balance=Decimal("50000"), equity=Decimal("50000")
        )
        stats.add_snapshot(snap)
        result = await stats.calculate()
        assert result.final_balance == 50000.0
        assert result.net_profit == 0.0


class TestExecutionStatistics:
    """Test execution-level statistics."""

    @pytest.mark.asyncio
    async def test_empty(self):
        stats = ExecutionStatistics()
        result = await stats.calculate()
        assert isinstance(result, ExecutionStatisticsResult)

    @pytest.mark.asyncio
    async def test_with_results(self):
        stats = ExecutionStatistics()
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
            total_commission=Decimal("5"),
            total_slippage=Decimal("0.5"),
            latency_ms=10.0,
        )
        stats.add_result(result)
        calc = await stats.calculate()
        assert calc.total_orders == 1
        assert calc.filled_orders == 1


class TestRiskStatisticsCalculator:
    """Test risk statistics."""

    @pytest.mark.asyncio
    async def test_empty(self):
        calc = RiskStatisticsCalculator()
        result = await calc.calculate()
        assert isinstance(result, RiskStatisticsResult)

    @pytest.mark.asyncio
    async def test_with_equity_curve(self):
        calc = RiskStatisticsCalculator()
        calc.add_equity(10000.0)
        calc.add_equity(11000.0)
        calc.add_equity(10500.0)
        calc.add_equity(12000.0)
        result = await calc.calculate()
        assert result.max_drawdown > 0
        assert result.max_drawdown_pct > 0

    @pytest.mark.asyncio
    async def test_flat_equity_curve(self):
        calc = RiskStatisticsCalculator()
        calc.add_equity(10000.0)
        calc.add_equity(10000.0)
        result = await calc.calculate()
        assert result.max_drawdown == 0.0

    @pytest.mark.asyncio
    async def test_single_equity_point(self):
        calc = RiskStatisticsCalculator()
        calc.add_equity(10000.0)
        result = await calc.calculate()
        assert result.max_drawdown == 0.0


class TestScenarioStatistics:
    """Test scenario tracking."""

    @pytest.mark.asyncio
    async def test_empty(self):
        stats = ScenarioStatistics()
        result = await stats.calculate()
        assert isinstance(result, ScenarioStatisticsResult)

    @pytest.mark.asyncio
    async def test_with_results(self):
        stats = ScenarioStatistics()
        stats.add_result("flash_crash", True)
        stats.add_result("high_volatility", False)
        result = await stats.calculate()
        assert result.scenario_count == 2
        assert result.passed_scenarios == 1
        assert result.pass_rate == 0.5

    @pytest.mark.asyncio
    async def test_all_passed(self):
        stats = ScenarioStatistics()
        stats.add_result("test1", True)
        stats.add_result("test2", True)
        result = await stats.calculate()
        assert result.pass_rate == 1.0

    @pytest.mark.asyncio
    async def test_all_failed(self):
        stats = ScenarioStatistics()
        stats.add_result("test1", False)
        stats.add_result("test2", False)
        result = await stats.calculate()
        assert result.pass_rate == 0.0
