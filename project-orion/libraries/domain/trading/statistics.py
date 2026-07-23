"""Trading statistics for the Trading Decision Engine.

Tracks win/loss records, performance metrics, and trade outcomes
for strategy evaluation and improvement.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from libraries.domain.trading.signals import SignalDirection


class TradeOutcome(StrEnum):
    """Outcome of an executed trade."""

    WIN = "win"
    LOSS = "loss"
    BREAK_EVEN = "break_even"
    OPEN = "open"


@dataclass(frozen=True, slots=True)
class TradeStats:
    """Comprehensive trading statistics snapshot."""

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    break_even_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    current_streak: int = 0
    best_streak: int = 0
    worst_streak: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TradeStatistics:
    """Tracks and computes trading performance statistics.

    Thread-safe via asyncio.Lock.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._trades: list[dict[str, Any]] = []
        self._pnl_history: list[float] = []
        self._max_trades: int = 10000

    @property
    def trade_count(self) -> int:
        return len(self._trades)

    async def record_trade(
        self,
        direction: SignalDirection,
        pnl: float,
        outcome: TradeOutcome,
        symbol: str = "",
        strategy: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a completed trade.

        Args:
            direction: Trade direction.
            pnl: Profit/loss amount.
            outcome: Trade outcome.
            symbol: Trading symbol.
            strategy: Strategy used.
            metadata: Optional additional data.
        """
        async with self._lock:
            record = {
                "direction": direction.value,
                "pnl": pnl,
                "outcome": outcome.value,
                "symbol": symbol,
                "strategy": strategy,
                "timestamp": datetime.now(timezone.utc),
                "metadata": metadata or {},
            }
            self._trades.append(record)
            self._pnl_history.append(pnl)

            if len(self._trades) > self._max_trades:
                self._trades.pop(0)
                self._pnl_history.pop(0)

    async def get_stats(self) -> TradeStats:
        """Compute current trading statistics."""
        async with self._lock:
            total = len(self._trades)
            if total == 0:
                return TradeStats()

            wins = [t for t in self._trades if t["outcome"] == TradeOutcome.WIN.value]
            losses = [t for t in self._trades if t["outcome"] == TradeOutcome.LOSS.value]
            breakeven = [t for t in self._trades if t["outcome"] == TradeOutcome.BREAK_EVEN.value]

            win_count = len(wins)
            loss_count = len(losses)
            be_count = len(breakeven)
            win_rate = win_count / total if total > 0 else 0.0

            total_pnl = sum(self._pnl_history)
            avg_win = sum(t["pnl"] for t in wins) / win_count if win_count > 0 else 0.0
            avg_loss = sum(t["pnl"] for t in losses) / loss_count if loss_count > 0 else 0.0
            largest_win = max((t["pnl"] for t in wins), default=0.0)
            largest_loss = min((t["pnl"] for t in losses), default=0.0)

            # Profit factor
            gross_profit = sum(t["pnl"] for t in wins)
            gross_loss = abs(sum(t["pnl"] for t in losses))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

            # Sharpe ratio (simplified, assuming risk-free rate = 0)
            if len(self._pnl_history) > 1:
                mean_pnl = sum(self._pnl_history) / len(self._pnl_history)
                variance = sum((p - mean_pnl) ** 2 for p in self._pnl_history) / len(
                    self._pnl_history
                )
                std_pnl = math.sqrt(variance) if variance > 0 else 0.0
                sharpe_ratio = (mean_pnl / std_pnl) * math.sqrt(252) if std_pnl > 0 else 0.0
            else:
                sharpe_ratio = 0.0

            # Max drawdown
            peak = float("-inf")
            max_dd = 0.0
            cumulative = 0.0
            for pnl in self._pnl_history:
                cumulative += pnl
                if cumulative > peak:
                    peak = cumulative
                dd = peak - cumulative
                if dd > max_dd:
                    max_dd = dd

            # Streaks
            current_streak = 0
            best_streak = 0
            worst_streak = 0
            if self._trades:
                last_outcome = self._trades[-1]["outcome"]
                for t in reversed(self._trades):
                    if t["outcome"] == last_outcome:
                        current_streak += 1 if last_outcome == TradeOutcome.WIN.value else -1
                    else:
                        break
                # Best/worst streaks
                streak = 0
                for t in self._trades:
                    if t["outcome"] == TradeOutcome.WIN.value:
                        streak = streak + 1 if streak >= 0 else 1
                    elif t["outcome"] == TradeOutcome.LOSS.value:
                        streak = streak - 1 if streak <= 0 else -1
                    else:
                        streak = 0
                    best_streak = max(best_streak, streak)
                    worst_streak = min(worst_streak, streak)

            return TradeStats(
                total_trades=total,
                winning_trades=win_count,
                losing_trades=loss_count,
                break_even_trades=be_count,
                win_rate=round(win_rate, 4),
                total_pnl=round(total_pnl, 2),
                average_win=round(avg_win, 2),
                average_loss=round(avg_loss, 2),
                largest_win=round(largest_win, 2),
                largest_loss=round(largest_loss, 2),
                profit_factor=(
                    round(profit_factor, 4) if profit_factor != float("inf") else float("inf")
                ),
                sharpe_ratio=round(sharpe_ratio, 4),
                max_drawdown=round(max_dd, 2),
                current_streak=current_streak,
                best_streak=best_streak,
                worst_streak=worst_streak,
            )

    async def clear(self) -> None:
        """Clear all trade records."""
        async with self._lock:
            self._trades.clear()
            self._pnl_history.clear()
