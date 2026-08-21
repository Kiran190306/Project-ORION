"""Portfolio Analytics — calculates performance and risk analytics.

Supports:
- Sharpe Ratio
- Sortino Ratio
- Calmar Ratio
- Win Rate
- Profit Factor
- Average Win/Loss
- Expected Value
- Recovery Factor
- Portfolio Heat
- Correlation Exposure (future-ready)
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class PortfolioAnalytics:
    """Immutable snapshot of portfolio analytics."""

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    expected_value: float = 0.0
    recovery_factor: float = 0.0
    portfolio_heat: float = 0.0  # 0-100
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PortfolioAnalyticsEngine:
    """Calculates portfolio analytics.

    Thread-safe via asyncio.Lock.
    Input data can be provided via trade records or snapshot data.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._pnl_history: list[float] = []
        self._equity_curve: list[float] = []
        self._trade_outcomes: list[float] = []  # +1 win, -1 loss, 0 breakeven
        self._peak_equity: float = 0.0
        self._current_dd: float = 0.0
        self._max_dd: float = 0.0

    # ─── Data Recording ──────────────────────────────────────

    async def record_trade(
        self,
        pnl: float,
        is_win: bool,
        is_loss: bool,
    ) -> None:
        """Record a trade outcome.

        Args:
            pnl: Profit/loss amount.
            is_win: True if winning trade.
            is_loss: True if losing trade.
        """
        async with self._lock:
            self._pnl_history.append(pnl)
            if is_win:
                self._trade_outcomes.append(1.0)
            elif is_loss:
                self._trade_outcomes.append(-1.0)
            else:
                self._trade_outcomes.append(0.0)

    async def record_equity(self, equity: float) -> None:
        """Record an equity value for drawdown calculations.

        Args:
            equity: Account equity value.
        """
        async with self._lock:
            self._equity_curve.append(equity)
            self._peak_equity = max(self._peak_equity, equity)
            self._current_dd = self._peak_equity - equity
            self._max_dd = max(self._max_dd, self._current_dd)

    # ─── Analytics Calculation ───────────────────────────────

    async def calculate(
        self,
        portfolio_heat: float = 0.0,
    ) -> PortfolioAnalytics:
        """Calculate comprehensive portfolio analytics.

        Args:
            portfolio_heat: Current portfolio heat (0-100).

        Returns:
            PortfolioAnalytics snapshot.
        """
        async with self._lock:
            total = len(self._trade_outcomes)
            if total == 0:
                return PortfolioAnalytics(portfolio_heat=portfolio_heat)

            wins = [
                pnl for pnl, outcome in zip(self._pnl_history, self._trade_outcomes) if outcome > 0
            ]
            losses = [
                pnl for pnl, outcome in zip(self._pnl_history, self._trade_outcomes) if outcome < 0
            ]
            [
                pnl for pnl, outcome in zip(self._pnl_history, self._trade_outcomes) if outcome == 0
            ]

            win_count = len(wins)
            loss_count = len(losses)

            win_rate = win_count / total if total > 0 else 0.0

            # Profit factor
            gross_profit = sum(wins)
            gross_loss = abs(sum(losses))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

            # Average win/loss
            avg_win = sum(wins) / win_count if win_count > 0 else 0.0
            avg_loss = sum(losses) / loss_count if loss_count > 0 else 0.0

            # Largest win/loss
            largest_win = max(wins) if wins else 0.0
            largest_loss = min(losses) if losses else 0.0

            # Expected value
            expected_value = (
                (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss)) if avg_loss != 0 else 0.0
            )

            # Sharpe ratio
            if len(self._pnl_history) > 1:
                mean_pnl = sum(self._pnl_history) / len(self._pnl_history)
                variance = sum((p - mean_pnl) ** 2 for p in self._pnl_history) / len(
                    self._pnl_history
                )
                std_pnl = math.sqrt(variance) if variance > 0 else 0.0
                sharpe_ratio = (mean_pnl / std_pnl) * math.sqrt(252) if std_pnl > 0 else 0.0
            else:
                sharpe_ratio = 0.0

            # Sortino ratio (downside deviation)
            if len(self._pnl_history) > 1:
                negative_returns = [p for p in self._pnl_history if p < 0]
                if negative_returns:
                    downside_var = sum(p**2 for p in negative_returns) / len(negative_returns)
                    downside_std = math.sqrt(downside_var) if downside_var > 0 else 0.0
                    sortino_ratio = (
                        (mean_pnl / downside_std) * math.sqrt(252) if downside_std > 0 else 0.0
                    )
                else:
                    sortino_ratio = 0.0
            else:
                sortino_ratio = 0.0

            # Calmar ratio
            calmar_ratio = (
                (sum(self._pnl_history) / len(self._pnl_history)) / self._max_dd
                if self._max_dd > 0
                else 0.0
            )

            # Recovery factor
            total_pnl = sum(self._pnl_history)
            recovery_factor = total_pnl / self._max_dd if self._max_dd > 0 else 0.0

            # Consecutive wins/losses
            max_consecutive_wins = 0
            max_consecutive_losses = 0
            current_win_streak = 0
            current_loss_streak = 0

            for outcome in self._trade_outcomes:
                if outcome > 0:
                    current_win_streak += 1
                    current_loss_streak = 0
                    max_consecutive_wins = max(max_consecutive_wins, current_win_streak)
                elif outcome < 0:
                    current_loss_streak += 1
                    current_win_streak = 0
                    max_consecutive_losses = max(max_consecutive_losses, current_loss_streak)
                else:
                    current_win_streak = 0
                    current_loss_streak = 0

            return PortfolioAnalytics(
                total_trades=total,
                winning_trades=win_count,
                losing_trades=loss_count,
                win_rate=round(win_rate, 4),
                profit_factor=(
                    round(profit_factor, 4) if profit_factor != float("inf") else float("inf")
                ),
                sharpe_ratio=round(sharpe_ratio, 4),
                sortino_ratio=round(sortino_ratio, 4),
                calmar_ratio=round(calmar_ratio, 4),
                average_win=round(avg_win, 2),
                average_loss=round(avg_loss, 2),
                largest_win=round(largest_win, 2),
                largest_loss=round(largest_loss, 2),
                expected_value=round(expected_value, 2),
                recovery_factor=round(recovery_factor, 4),
                portfolio_heat=portfolio_heat,
                max_consecutive_wins=max_consecutive_wins,
                max_consecutive_losses=max_consecutive_losses,
            )

    # ─── Update Methods ──────────────────────────────────────

    async def set_portfolio_heat(self, heat: float) -> None:
        """Set portfolio heat for analytics.

        Args:
            heat: Portfolio heat value (0-100).
        """
        async with self._lock:
            self._portfolio_heat = heat

    async def get_max_drawdown(self) -> float:
        """Get maximum drawdown observed.

        Returns:
            Max drawdown value.
        """
        async with self._lock:
            return self._max_dd

    async def get_current_drawdown(self) -> float:
        """Get current drawdown.

        Returns:
            Current drawdown value.
        """
        async with self._lock:
            return self._current_dd

    async def clear(self) -> None:
        """Clear all analytics data."""
        async with self._lock:
            self._pnl_history.clear()
            self._equity_curve.clear()
            self._trade_outcomes.clear()
            self._peak_equity = 0.0
            self._current_dd = 0.0
            self._max_dd = 0.0
