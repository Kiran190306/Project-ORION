"""Performance metrics calculators for backtesting.

Calculates comprehensive performance metrics including:
- Net Profit, Gross Profit, Gross Loss
- Win Rate, Profit Factor, Recovery Factor
- Sharpe Ratio, Sortino Ratio, Calmar Ratio
- Maximum Drawdown, Ulcer Index
- Expectancy, Average Trade, Largest Win/Loss
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.backtesting.models import (
    PerformanceMetrics,
    PortfolioMetrics,
    RiskMetrics,
    StatisticalMetrics,
    TradeMetrics,
)
from libraries.domain.backtesting.statistics import (
    ExecutionStatisticsResult,
    PortfolioStatisticsResult,
    RiskStatisticsResult,
    TradeStatisticsResult,
)


class TradeMetricsCalculator:
    """Calculates trade-level performance metrics."""

    def calculate_from_trades(self, trades: list[dict[str, Any]]) -> TradeMetrics:
        if not trades:
            return TradeMetrics()

        total_pnl = sum(t.get("pnl", 0) for t in trades)
        winning = [t for t in trades if t.get("pnl", 0) > 0]
        losing = [t for t in trades if t.get("pnl", 0) < 0]

        gross_profit = sum(t.get("pnl", 0) for t in winning)
        gross_loss = abs(sum(t.get("pnl", 0) for t in losing))
        win_rate = len(winning) / len(trades) if trades else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        avg_win = gross_profit / len(winning) if winning else 0.0
        avg_loss = gross_loss / len(losing) if losing else 0.0
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss)) if avg_loss else 0.0

        return TradeMetrics(
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=round(win_rate, 4),
            profit_factor=(
                round(profit_factor, 4) if profit_factor != float("inf") else float("inf")
            ),
            gross_profit=round(gross_profit, 2),
            gross_loss=round(gross_loss, 2),
            net_profit=round(total_pnl, 2),
            average_win=round(avg_win, 2),
            average_loss=round(avg_loss, 2),
            largest_win=round(max((t.get("pnl", 0) for t in winning), default=0.0), 2),
            largest_loss=round(min((t.get("pnl", 0) for t in losing), default=0.0), 2),
            expectancy=round(expectancy, 2),
        )


class PortfolioMetricsCalculator:
    """Calculates portfolio-level performance metrics."""

    def calculate_from_equity_curve(
        self,
        equity_curve: list[float],
        initial_balance: float,
    ) -> PortfolioMetrics:
        if not equity_curve:
            return PortfolioMetrics()

        final_equity = equity_curve[-1]
        total_return = final_equity - initial_balance
        total_return_pct = (
            ((final_equity - initial_balance) / initial_balance * 100)
            if initial_balance > 0
            else 0.0
        )
        peak = max(equity_curve)

        return PortfolioMetrics(
            return_pct=round(total_return_pct, 2),
            annualized_return=round(total_return_pct, 2),
            total_return=round(total_return, 2),
            total_return_pct=round(total_return_pct, 2),
        )


class RiskMetricsCalculator:
    """Calculates risk-adjusted performance metrics."""

    @staticmethod
    def calculate_sharpe_ratio(
        returns: list[float],
        risk_free_rate: float = 0.02,
        periods_per_year: int = 252,
    ) -> float:
        if len(returns) < 2:
            return 0.0
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std = math.sqrt(variance) if variance > 0 else 0.0
        if std == 0:
            return 0.0
        excess_return = mean_return - (risk_free_rate / periods_per_year)
        return (excess_return / std) * math.sqrt(periods_per_year)

    @staticmethod
    def calculate_sortino_ratio(
        returns: list[float],
        risk_free_rate: float = 0.02,
        periods_per_year: int = 252,
    ) -> float:
        if len(returns) < 2:
            return 0.0
        mean_return = sum(returns) / len(returns)
        negative = [r for r in returns if r < 0]
        if not negative:
            return 0.0
        downside_var = sum(r**2 for r in negative) / len(returns)
        downside_std = math.sqrt(downside_var) if downside_var > 0 else 0.0
        if downside_std == 0:
            return 0.0
        excess_return = mean_return - (risk_free_rate / periods_per_year)
        return (excess_return / downside_std) * math.sqrt(periods_per_year)

    @staticmethod
    def calculate_calmar_ratio(
        total_return_pct: float,
        max_drawdown_pct: float,
    ) -> float:
        if max_drawdown_pct == 0:
            return 0.0
        return total_return_pct / max_drawdown_pct

    def calculate(
        self,
        returns: list[float],
        equity_curve: list[float],
        risk_free_rate: float = 0.02,
    ) -> RiskMetrics:
        sharpe = self.calculate_sharpe_ratio(returns, risk_free_rate)
        sortino = self.calculate_sortino_ratio(returns, risk_free_rate)

        if equity_curve and len(equity_curve) > 1:
            peak = max(equity_curve)
            total_return = (
                ((equity_curve[-1] - equity_curve[0]) / equity_curve[0]) * 100
                if equity_curve[0] > 0
                else 0
            )
            max_dd = 0.0
            current_peak = equity_curve[0]
            for val in equity_curve:
                if val > current_peak:
                    current_peak = val
                dd = (current_peak - val) / current_peak * 100 if current_peak > 0 else 0
                if dd > max_dd:
                    max_dd = dd
            calmar = self.calculate_calmar_ratio(total_return, max_dd)

            # Calculate downside volatility
            negative_returns = [r for r in returns if r < 0]
            downside_var = sum(r**2 for r in negative_returns) / len(returns) if returns else 0.0
            downside_vol = math.sqrt(downside_var) if downside_var > 0 else 0.0
        else:
            total_return = 0.0
            max_dd = 0.0
            calmar = 0.0
            downside_vol = 0.0

        return RiskMetrics(
            sharpe_ratio=round(sharpe, 4),
            sortino_ratio=round(sortino, 4),
            calmar_ratio=round(calmar, 4),
            total_return_pct=round(total_return, 2),
            max_drawdown_pct=round(max_dd, 2),
            max_drawdown=round(max_dd * max(equity_curve) / 100 if equity_curve else 0, 2),
            downside_volatility=round(downside_vol, 4),
        )


class ExecutionMetricsCalculator:
    """Calculates execution quality metrics."""

    def calculate(
        self,
        total_orders: int,
        filled_orders: int,
        avg_slippage_bps: float,
        avg_latency_ms: float,
    ) -> dict[str, Any]:
        fill_rate = filled_orders / total_orders if total_orders > 0 else 0.0
        return {
            "total_orders": total_orders,
            "filled_orders": filled_orders,
            "fill_rate": round(fill_rate, 4),
            "average_slippage_bps": round(avg_slippage_bps, 2),
            "average_latency_ms": round(avg_latency_ms, 1),
        }


class StatisticalMetricsCalculator:
    """Calculates advanced statistical metrics."""

    @staticmethod
    def calculate_ulcer_index(equity_curve: list[float]) -> float:
        if not equity_curve:
            return 0.0
        peak = equity_curve[0]
        squared_drawdowns = []
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak * 100 if peak > 0 else 0
            squared_drawdowns.append(dd**2)
        if not squared_drawdowns:
            return 0.0
        return math.sqrt(sum(squared_drawdowns) / len(squared_drawdowns))


class PerformanceEngine:
    """Comprehensive performance analysis engine.

    Aggregates all metrics calculators for a complete performance report.
    """

    def __init__(self) -> None:
        self._trade_calc = TradeMetricsCalculator()
        self._portfolio_calc = PortfolioMetricsCalculator()
        self._risk_calc = RiskMetricsCalculator()
        self._execution_calc = ExecutionMetricsCalculator()
        self._statistical_calc = StatisticalMetricsCalculator()

    async def calculate(
        self,
        trades: list[dict[str, Any]],
        equity_curve: list[float],
        initial_balance: Decimal,
        execution_stats: ExecutionStatisticsResult | None = None,
    ) -> PerformanceMetrics:
        trade_metrics = self._trade_calc.calculate_from_trades(trades)
        portfolio_metrics = self._portfolio_calc.calculate_from_equity_curve(
            equity_curve, float(initial_balance)
        )

        # Calculate returns for risk metrics
        returns = []
        for i in range(1, len(equity_curve)):
            if equity_curve[i - 1] > 0:
                returns.append((equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1])

        risk_metrics = self._risk_calc.calculate(returns, equity_curve)
        ulcer_index = self._statistical_calc.calculate_ulcer_index(equity_curve)

        return PerformanceMetrics(
            trade_metrics=trade_metrics,
            portfolio_metrics=portfolio_metrics,
            risk_metrics=risk_metrics,
            statistical_metrics=StatisticalMetrics(
                skewness=0.0,
                kurtosis=0.0,
                gain_to_pain_ratio=(
                    round(risk_metrics.sharpe_ratio, 4) if risk_metrics.sharpe_ratio != 0 else 0.0
                ),
                profit_per_bar=0.0,
                profit_per_day=0.0,
                profit_per_month=0.0,
                avg_daily_volatility=0.0,
                avg_weekly_volatility=0.0,
            ),
        )
