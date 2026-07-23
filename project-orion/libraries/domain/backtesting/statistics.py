"""Statistics calculators for backtesting.

Provides comprehensive trade, portfolio, execution, risk, and scenario
statistics used for performance evaluation and reporting.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.backtesting.models import (
    ExecutionSimulationResult,
    ExecutionSimulationStatus,
    PortfolioSnapshot,
)


@dataclass(frozen=True, slots=True)
class TradeStatisticsResult:
    """Aggregated trade statistics."""

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    average_holding_period_hours: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0


class TradeStatistics:
    """Calculates trade-level statistics from execution results."""

    def __init__(self) -> None:
        self._trades: list[dict[str, Any]] = []

    def add_trade(self, trade: dict[str, Any]) -> None:
        self._trades.append(trade)

    async def calculate(self) -> TradeStatisticsResult:
        trades = self._trades
        if not trades:
            return TradeStatisticsResult()

        total = len(trades)
        winning = [t for t in trades if t.get("pnl", 0) > 0]
        losing = [t for t in trades if t.get("pnl", 0) < 0]

        win_count = len(winning)
        loss_count = len(losing)

        win_rate = win_count / total if total > 0 else 0.0

        gross_profit = sum(t.get("pnl", 0) for t in winning) or 0.0
        gross_loss = abs(sum(t.get("pnl", 0) for t in losing)) or 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        avg_win = gross_profit / win_count if win_count > 0 else 0.0
        avg_loss = gross_loss / loss_count if loss_count > 0 else 0.0

        largest_win = max((t.get("pnl", 0) for t in winning), default=0.0)
        largest_loss = min((t.get("pnl", 0) for t in losing), default=0.0)

        return TradeStatisticsResult(
            total_trades=total,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate=round(win_rate, 4),
            profit_factor=round(profit_factor, 4),
            average_win=round(avg_win, 2),
            average_loss=round(avg_loss, 2),
            largest_win=round(largest_win, 2),
            largest_loss=round(largest_loss, 2),
        )


@dataclass(frozen=True, slots=True)
class PortfolioStatisticsResult:
    """Aggregated portfolio statistics."""

    net_profit: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    total_commission: float = 0.0
    total_swap: float = 0.0
    total_trades: int = 0
    final_balance: float = 0.0
    final_equity: float = 0.0
    peak_balance: float = 0.0
    peak_equity: float = 0.0


class PortfolioStatistics:
    """Calculates portfolio-level statistics."""

    def __init__(self) -> None:
        self._snapshots: list[PortfolioSnapshot] = []

    def add_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        self._snapshots.append(snapshot)

    async def calculate(self) -> PortfolioStatisticsResult:
        if not self._snapshots:
            return PortfolioStatisticsResult()

        first = self._snapshots[0]
        last = self._snapshots[-1]

        peak_balance = max(s.balance for s in self._snapshots)
        peak_equity = max(s.equity for s in self._snapshots)

        return PortfolioStatisticsResult(
            net_profit=float(last.balance - first.balance),
            total_commission=float(last.total_commission),
            total_swap=float(last.total_swap),
            total_trades=last.position_count,
            final_balance=float(last.balance),
            final_equity=float(last.equity),
            peak_balance=float(peak_balance),
            peak_equity=float(peak_equity),
        )


@dataclass(frozen=True, slots=True)
class ExecutionStatisticsResult:
    """Aggregated execution statistics."""

    total_orders: int = 0
    filled_orders: int = 0
    partial_fills: int = 0
    rejected_orders: int = 0
    average_slippage_bps: float = 0.0
    average_latency_ms: float = 0.0
    average_commission: float = 0.0


class ExecutionStatistics:
    """Calculates execution-level statistics."""

    def __init__(self) -> None:
        self._results: list[ExecutionSimulationResult] = []

    def add_result(self, result: ExecutionSimulationResult) -> None:
        self._results.append(result)

    async def calculate(self) -> ExecutionStatisticsResult:
        results = self._results
        if not results:
            return ExecutionStatisticsResult()

        filled = [r for r in results if r.is_success]
        rejected = [r for r in results if r.status == ExecutionSimulationStatus.REJECTED]
        partial_fills = [r for r in results if r.is_partial]

        avg_slippage = sum(float(r.total_slippage) for r in filled) / len(filled) if filled else 0.0
        avg_latency = sum(r.latency_ms for r in results) / len(results) if results else 0.0
        avg_commission = (
            sum(float(r.total_commission) for r in filled) / len(filled) if filled else 0.0
        )

        return ExecutionStatisticsResult(
            total_orders=len(results),
            filled_orders=len(filled),
            partial_fills=len(partial_fills),
            rejected_orders=len(rejected),
            average_slippage_bps=round(avg_slippage, 2),
            average_latency_ms=round(avg_latency, 1),
            average_commission=round(avg_commission, 2),
        )


@dataclass(frozen=True, slots=True)
class RiskStatisticsResult:
    """Risk statistics result."""

    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    recovery_factor: float = 0.0
    ulcer_index: float = 0.0


class RiskStatisticsCalculator:
    """Calculates risk-related statistics."""

    def __init__(self) -> None:
        self._equity_curve: list[float] = []

    def add_equity(self, equity: float) -> None:
        self._equity_curve.append(equity)

    async def calculate(self) -> RiskStatisticsResult:
        curve = self._equity_curve
        if not curve:
            return RiskStatisticsResult()

        peak = curve[0]
        max_dd = 0.0
        max_dd_pct = 0.0

        for val in curve:
            if val > peak:
                peak = val
            dd = peak - val
            dd_pct = dd / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct

        total_return = curve[-1] - curve[0]
        recovery_factor = total_return / max_dd if max_dd > 0 else 0.0

        return RiskStatisticsResult(
            max_drawdown=round(max_dd, 2),
            max_drawdown_pct=round(max_dd_pct, 2),
            recovery_factor=round(recovery_factor, 4),
        )


@dataclass(frozen=True, slots=True)
class ScenarioStatisticsResult:
    """Scenario statistics result."""

    scenario_count: int = 0
    passed_scenarios: int = 0
    failed_scenarios: int = 0
    pass_rate: float = 0.0


class ScenarioStatistics:
    """Tracks statistics for scenario testing."""

    def __init__(self) -> None:
        self._results: list[dict[str, Any]] = []

    def add_result(self, name: str, passed: bool, details: dict[str, Any] | None = None) -> None:
        self._results.append({"name": name, "passed": passed, "details": details or {}})

    async def calculate(self) -> ScenarioStatisticsResult:
        if not self._results:
            return ScenarioStatisticsResult()

        passed = sum(1 for r in self._results if r["passed"])
        return ScenarioStatisticsResult(
            scenario_count=len(self._results),
            passed_scenarios=passed,
            failed_scenarios=len(self._results) - passed,
            pass_rate=round(passed / len(self._results), 4),
        )
