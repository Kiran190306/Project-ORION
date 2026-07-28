"""Tests for EPIC-010 PerformanceEngine and metric calculators."""

from __future__ import annotations

import math
from decimal import Decimal

import pytest

from libraries.domain.backtesting.models import (
    PerformanceMetrics,
    PortfolioMetrics,
    RiskMetrics,
    StatisticalMetrics,
    TradeMetrics,
)
from libraries.domain.backtesting.performance import (
    ExecutionMetricsCalculator,
    PerformanceEngine,
    PortfolioMetricsCalculator,
    RiskMetricsCalculator,
    StatisticalMetricsCalculator,
    TradeMetricsCalculator,
)


class TestTradeMetricsCalculator:
    """Test trade-level performance metrics."""

    def test_empty_trades_returns_defaults(self):
        calc = TradeMetricsCalculator()
        result = calc.calculate_from_trades([])
        assert result.total_trades == 0
        assert result.win_rate == 0.0
        assert result.profit_factor == 0.0

    def test_single_winning_trade(self):
        calc = TradeMetricsCalculator()
        result = calc.calculate_from_trades([{"pnl": 100.0}])
        assert result.total_trades == 1
        assert result.winning_trades == 1
        assert result.win_rate == 1.0
        assert result.gross_profit == 100.0
        assert result.gross_loss == 0.0
        assert result.profit_factor == float("inf")

    def test_single_losing_trade(self):
        calc = TradeMetricsCalculator()
        result = calc.calculate_from_trades([{"pnl": -50.0}])
        assert result.total_trades == 1
        assert result.losing_trades == 1
        assert result.win_rate == 0.0
        assert result.gross_loss == 50.0

    def test_mixed_trades(self):
        calc = TradeMetricsCalculator()
        trades = [
            {"pnl": 200.0},
            {"pnl": -100.0},
            {"pnl": 50.0},
            {"pnl": -30.0},
            {"pnl": 80.0},
        ]
        result = calc.calculate_from_trades(trades)
        assert result.total_trades == 5
        assert result.winning_trades == 3
        assert result.losing_trades == 2
        assert result.win_rate == 0.6
        assert result.net_profit == 200.0

    def test_profit_factor_finite(self):
        calc = TradeMetricsCalculator()
        trades = [{"pnl": 100.0}, {"pnl": -25.0}]
        result = calc.calculate_from_trades(trades)
        assert result.profit_factor == 4.0

    def test_profit_factor_at_one(self):
        calc = TradeMetricsCalculator()
        trades = [{"pnl": 50.0}, {"pnl": -50.0}]
        result = calc.calculate_from_trades(trades)
        assert result.profit_factor == 1.0

    def test_largest_win_and_loss(self):
        calc = TradeMetricsCalculator()
        trades = [
            {"pnl": 100.0},
            {"pnl": 200.0},
            {"pnl": -50.0},
            {"pnl": -10.0},
        ]
        result = calc.calculate_from_trades(trades)
        assert result.largest_win == 200.0
        assert result.largest_loss == -50.0

    def test_average_win_and_loss(self):
        calc = TradeMetricsCalculator()
        trades = [
            {"pnl": 200.0},
            {"pnl": 100.0},
            {"pnl": -50.0},
            {"pnl": -150.0},
        ]
        result = calc.calculate_from_trades(trades)
        assert result.average_win == 150.0
        assert result.average_loss == 100.0

    def test_expectancy_positive(self):
        calc = TradeMetricsCalculator()
        trades = [
            {"pnl": 200.0},
            {"pnl": 100.0},
            {"pnl": -50.0},
        ]
        result = calc.calculate_from_trades(trades)
        assert result.expectancy > 0

    def test_expectancy_negative(self):
        calc = TradeMetricsCalculator()
        trades = [
            {"pnl": 50.0},
            {"pnl": -200.0},
            {"pnl": -100.0},
        ]
        result = calc.calculate_from_trades(trades)
        assert result.expectancy < 0

    def test_zero_pnl_trades_counted(self):
        calc = TradeMetricsCalculator()
        trades = [{"pnl": 0.0}, {"pnl": 0.0}]
        result = calc.calculate_from_trades(trades)
        assert result.total_trades == 2
        assert result.winning_trades == 0
        assert result.losing_trades == 0

    def test_decimal_rounding(self):
        calc = TradeMetricsCalculator()
        trades = [{"pnl": 100.567}, {"pnl": -50.123}]
        result = calc.calculate_from_trades(trades)
        assert result.net_profit == 50.44

    def test_large_number_of_trades(self):
        calc = TradeMetricsCalculator()
        trades = [{"pnl": 10.0 if i % 2 == 0 else -5.0} for i in range(1000)]
        result = calc.calculate_from_trades(trades)
        assert result.total_trades == 1000
        assert result.winning_trades == 500
        assert result.losing_trades == 500
        assert result.net_profit == 2500.0


class TestPortfolioMetricsCalculator:
    """Test portfolio-level metrics."""

    def test_empty_equity_curve(self):
        calc = PortfolioMetricsCalculator()
        result = calc.calculate_from_equity_curve([], 10000.0)
        assert result.total_return == 0.0
        assert result.total_return_pct == 0.0

    def test_single_point_equity_curve(self):
        calc = PortfolioMetricsCalculator()
        result = calc.calculate_from_equity_curve([10000.0], 10000.0)
        assert result.total_return == 0.0

    def test_positive_return(self):
        calc = PortfolioMetricsCalculator()
        curve = [10000.0, 10100.0, 10200.0, 10300.0]
        result = calc.calculate_from_equity_curve(curve, 10000.0)
        assert result.total_return == 300.0
        assert result.total_return_pct == 3.0

    def test_negative_return(self):
        calc = PortfolioMetricsCalculator()
        curve = [10000.0, 9900.0, 9800.0]
        result = calc.calculate_from_equity_curve(curve, 10000.0)
        assert result.total_return == -200.0
        assert result.total_return_pct == -2.0

    def test_zero_initial_balance(self):
        calc = PortfolioMetricsCalculator()
        curve = [0.0, 100.0]
        result = calc.calculate_from_equity_curve(curve, 0.0)
        assert result.total_return_pct == 0.0

    def test_peak_detection(self):
        calc = PortfolioMetricsCalculator()
        curve = [10000.0, 11000.0, 10500.0, 12000.0]
        result = calc.calculate_from_equity_curve(curve, 10000.0)
        assert result.total_return == 2000.0


class TestRiskMetricsCalculator:
    """Test risk-adjusted performance metrics."""

    def test_empty_returns(self):
        calc = RiskMetricsCalculator()
        result = calc.calculate([], [])
        assert result.sharpe_ratio == 0.0
        assert result.sortino_ratio == 0.0

    def test_single_return(self):
        calc = RiskMetricsCalculator()
        result = calc.calculate([0.01], [1000.0, 1010.0])
        assert result.sharpe_ratio == 0.0

    def test_sharpe_ratio_positive(self):
        calc = RiskMetricsCalculator()
        returns = [0.01, 0.02, 0.015, 0.01, 0.005]
        equity = [1000.0]
        for r in returns:
            equity.append(equity[-1] * (1 + r))
        result = calc.calculate(returns, equity)
        assert result.sharpe_ratio > 0

    def test_sharpe_ratio_negative(self):
        calc = RiskMetricsCalculator()
        returns = [-0.01, -0.02, -0.015, -0.01]
        equity = [1000.0]
        for r in returns:
            equity.append(equity[-1] * (1 + r))
        result = calc.calculate(returns, equity)
        assert result.sharpe_ratio < 0

    def test_sharpe_ratio_zero_std(self):
        calc = RiskMetricsCalculator()
        returns = [0.01, 0.01, 0.01, 0.01]
        equity = [1000.0, 1010.0, 1020.0, 1030.0, 1040.0]
        result = calc.calculate(returns, equity)
        assert result.sharpe_ratio == 0.0

    def test_sortino_ratio_no_negative(self):
        calc = RiskMetricsCalculator()
        returns = [0.01, 0.02, 0.015]
        equity = [1000.0, 1010.0, 1030.0, 1045.0]
        result = calc.calculate(returns, equity)
        assert result.sortino_ratio == 0.0

    def test_sortino_ratio_with_negatives(self):
        calc = RiskMetricsCalculator()
        returns = [0.01, -0.02, 0.015, -0.01, 0.005]
        equity = [1000.0]
        for r in returns:
            equity.append(equity[-1] * (1 + r))
        result = calc.calculate(returns, equity)
        assert result.sortino_ratio is not None

    def test_calmar_ratio(self):
        calc = RiskMetricsCalculator()
        # Equity: start 1000, peak 1100, drop to 1050 (drawdown), end 1080
        equity = [1000.0, 1100.0, 1050.0, 1080.0]
        returns = [0.1, -0.045, 0.029]
        result = calc.calculate(returns, equity, risk_free_rate=0.02)
        # total_return = (1080-1000)/1000*100 = 8%, max_dd = (1100-1050)/1100*100 = 4.55%
        # calmar = 8/4.55 = 1.76
        assert result.calmar_ratio > 0
        assert result.calmar_ratio != 0.0

    def test_calmar_ratio_zero_drawdown(self):
        result = RiskMetricsCalculator.calculate_calmar_ratio(10.0, 0.0)
        assert result == 0.0

    def test_max_drawdown_calculation(self):
        calc = RiskMetricsCalculator()
        equity = [10000.0, 11000.0, 10500.0, 9500.0, 10500.0, 10000.0]
        returns = [0.1, -0.045, -0.095, 0.105, -0.048]
        result = calc.calculate(returns, equity)
        assert result.max_drawdown_pct > 0
        assert result.max_drawdown > 0

    def test_max_drawdown_from_peak(self):
        calc = RiskMetricsCalculator()
        equity = [10000.0, 12000.0, 11000.0, 9000.0]
        returns = [0.2, -0.083, -0.182]
        result = calc.calculate(returns, equity)
        assert result.max_drawdown_pct >= 24.0

    def test_calculate_sharpe_static(self):
        returns = [0.01, 0.02, -0.01, 0.015, 0.005]
        result = RiskMetricsCalculator.calculate_sharpe_ratio(returns)
        assert isinstance(result, float)

    def test_calculate_sortino_static(self):
        returns = [0.01, -0.02, 0.015, -0.01, 0.005]
        result = RiskMetricsCalculator.calculate_sortino_ratio(returns)
        assert isinstance(result, float)

    def test_calculate_calmar_static(self):
        result = RiskMetricsCalculator.calculate_calmar_ratio(10.0, 5.0)
        assert result == 2.0

    def test_risk_free_rate_impact(self):
        calc = RiskMetricsCalculator()
        returns = [0.01, 0.02, 0.015]
        equity = [1000.0, 1010.0, 1030.0, 1045.0]
        result_no_rfr = calc.calculate(returns, equity, risk_free_rate=0.0)
        result_with_rfr = calc.calculate(returns, equity, risk_free_rate=0.05)
        assert result_no_rfr.sharpe_ratio >= result_with_rfr.sharpe_ratio


class TestExecutionMetricsCalculator:
    """Test execution quality metrics."""

    def test_no_orders(self):
        calc = ExecutionMetricsCalculator()
        result = calc.calculate(0, 0, 0.0, 0.0)
        assert result["fill_rate"] == 0.0
        assert result["total_orders"] == 0

    def test_perfect_fill_rate(self):
        calc = ExecutionMetricsCalculator()
        result = calc.calculate(10, 10, 1.0, 50.0)
        assert result["fill_rate"] == 1.0
        assert result["average_slippage_bps"] == 1.0

    def test_partial_fill_rate(self):
        calc = ExecutionMetricsCalculator()
        result = calc.calculate(10, 7, 2.5, 30.0)
        assert result["fill_rate"] == 0.7
        assert result["average_latency_ms"] == 30.0

    def test_zero_fills(self):
        calc = ExecutionMetricsCalculator()
        result = calc.calculate(5, 0, 0.0, 0.0)
        assert result["fill_rate"] == 0.0

    def test_rounding(self):
        calc = ExecutionMetricsCalculator()
        result = calc.calculate(3, 1, 1.2345, 12.3456)
        assert result["fill_rate"] == 0.3333
        assert result["average_slippage_bps"] == 1.23
        assert result["average_latency_ms"] == 12.3


class TestStatisticalMetricsCalculator:
    """Test advanced statistical metrics."""

    def test_empty_equity_curve(self):
        result = StatisticalMetricsCalculator.calculate_ulcer_index([])
        assert result == 0.0

    def test_no_drawdown(self):
        equity = [100.0, 101.0, 102.0, 103.0, 104.0]
        result = StatisticalMetricsCalculator.calculate_ulcer_index(equity)
        assert result == 0.0

    def test_with_drawdown(self):
        equity = [100.0, 110.0, 105.0, 95.0, 100.0]
        result = StatisticalMetricsCalculator.calculate_ulcer_index(equity)
        assert result > 0.0

    def test_monotonic_downtrend(self):
        equity = [100.0, 90.0, 80.0, 70.0]
        result = StatisticalMetricsCalculator.calculate_ulcer_index(equity)
        assert result > 0.0

    def test_single_point(self):
        result = StatisticalMetricsCalculator.calculate_ulcer_index([100.0])
        assert result == 0.0

    def test_ulcer_index_deep_drawdown(self):
        equity = [100.0, 200.0, 100.0]
        result = StatisticalMetricsCalculator.calculate_ulcer_index(equity)
        assert result > 0


class TestPerformanceEngine:
    """Test the composite performance engine."""

    @pytest.mark.asyncio
    async def test_empty_trades_and_curve(self):
        engine = PerformanceEngine()
        result = await engine.calculate([], [], Decimal("10000"))
        assert isinstance(result, PerformanceMetrics)
        assert result.trade_metrics.total_trades == 0
        assert result.portfolio_metrics.total_return == 0.0

    @pytest.mark.asyncio
    async def test_single_trade_and_curve(self):
        engine = PerformanceEngine()
        trades = [{"pnl": 100.0}]
        equity = [10000.0, 10100.0]
        result = await engine.calculate(trades, equity, Decimal("10000"))
        assert result.trade_metrics.net_profit == 100.0
        assert result.trade_metrics.winning_trades == 1

    @pytest.mark.asyncio
    async def test_multiple_trades(self):
        engine = PerformanceEngine()
        trades = [{"pnl": 100.0}, {"pnl": -50.0}, {"pnl": 75.0}]
        equity = [10000.0, 10100.0, 10050.0, 10125.0]
        result = await engine.calculate(trades, equity, Decimal("10000"))
        assert result.trade_metrics.total_trades == 3
        assert result.trade_metrics.net_profit == 125.0

    @pytest.mark.asyncio
    async def test_negative_initial_balance(self):
        engine = PerformanceEngine()
        result = await engine.calculate([], [100.0], Decimal("-1000"))
        assert isinstance(result, PerformanceMetrics)

    @pytest.mark.asyncio
    async def test_ulcer_index_in_performance(self):
        engine = PerformanceEngine()
        equity = [10000.0, 11000.0, 10500.0, 9500.0, 10000.0]
        returns = [0.1, -0.045, -0.095, 0.053]
        result = await engine.calculate([{"pnl": 0}], equity, Decimal("10000"))
        assert isinstance(result.statistical_metrics, StatisticalMetrics)

    @pytest.mark.asyncio
    async def test_risk_metrics_in_performance(self):
        engine = PerformanceEngine()
        trades = [{"pnl": 100.0}]
        equity = [10000.0, 10100.0]
        result = await engine.calculate(trades, equity, Decimal("10000"))
        assert isinstance(result.risk_metrics, RiskMetrics)
        assert isinstance(result.portfolio_metrics, PortfolioMetrics)
        assert isinstance(result.trade_metrics, TradeMetrics)

    @pytest.mark.asyncio
    async def test_large_dataset_performance(self):
        engine = PerformanceEngine()
        trades = [{"pnl": 10.0 if i % 2 == 0 else -5.0} for i in range(500)]
        equity = [10000.0]
        for i in range(1000):
            equity.append(equity[-1] * (1 + 0.001 * (1 if i % 2 == 0 else -0.5)))
        result = await engine.calculate(trades, equity, Decimal("10000"))
        assert result.trade_metrics.total_trades == 500

    @pytest.mark.asyncio
    async def test_calculate_twice_returns_same(self):
        engine = PerformanceEngine()
        trades = [{"pnl": 100.0}, {"pnl": -50.0}]
        equity = [10000.0, 10100.0, 10050.0]
        result1 = await engine.calculate(trades, equity, Decimal("10000"))
        result2 = await engine.calculate(trades, equity, Decimal("10000"))
        assert result1.trade_metrics.net_profit == result2.trade_metrics.net_profit
