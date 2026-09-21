"""Strategy Backtest Adapter.

Bridges BaseStrategy subclasses directly to the BacktestEngine, evaluating
strategy signals at each bar, simulating realistic execution with adverse
slippage, spread, and commission, maintaining position netting, and asserting
zero look-ahead bias with LeakageGuard.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from libraries.domain.backtesting.leakage_guard import LeakageGuard
from libraries.domain.market_data.models import OHLCV
from libraries.domain.research.models import (
    EquityCurvePoint,
    ResearchPerformanceMetrics,
    TradeRecord,
)
from libraries.domain.strategy.base import BaseStrategy
from libraries.domain.strategy.models import (
    Position,
    PositionSide,
    SignalDirection,
    StrategyContext,
)


def downsample_equity_curve(
    points: list[EquityCurvePoint],
    max_points: int = 500,
) -> list[EquityCurvePoint]:
    """Downsample equity curve points preserving initial, final, and local extrema."""
    if len(points) <= max_points:
        return points

    target_buckets = max(1, (max_points - 2) // 2)
    step = max(1, len(points) // target_buckets)
    sampled: list[EquityCurvePoint] = [points[0]]

    for i in range(1, len(points) - 1, step):
        bucket = points[i : min(i + step, len(points) - 1)]
        if bucket:
            # Pick min and max equity in bucket to preserve drawdown peaks and troughs
            min_pt = min(bucket, key=lambda p: p.equity)
            max_pt = max(bucket, key=lambda p: p.equity)
            if min_pt.timestamp < max_pt.timestamp:
                sampled.extend([min_pt, max_pt])
            elif min_pt.timestamp > max_pt.timestamp:
                sampled.extend([max_pt, min_pt])
            else:
                sampled.append(min_pt)

    if points[-1] not in sampled:
        sampled.append(points[-1])

    if len(sampled) > max_points:
        sampled = sampled[: max_points - 1] + [points[-1]]

    return sampled


class StrategyBacktestAdapter:
    """Orchestrates strategy evaluation and deterministic accounting during backtest replay."""

    def __init__(
        self,
        strategy: BaseStrategy,
        symbol: str,
        timeframe: str = "H1",
        initial_capital: Decimal = Decimal("10000.00"),
        spread_pips: Decimal = Decimal("1.5"),
        pip_size: Decimal = Decimal("0.0001"),
        adverse_slippage_pips: Decimal = Decimal("0.5"),
        commission_per_lot: Decimal = Decimal("7.00"),  # $7 per 100k units ($0.00007 / unit)
        default_lot_size: Decimal = Decimal(10000),  # 0.1 standard lot
    ) -> None:
        self.strategy = strategy
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_capital = initial_capital
        self.pip_size = Decimal("0.01") if "JPY" in symbol else Decimal("0.0001")
        self.spread = spread_pips * self.pip_size
        self.adverse_slippage = adverse_slippage_pips * self.pip_size
        self.commission_per_lot = commission_per_lot
        self.default_lot_size = default_lot_size

        # Financial Accounting State (Strictly Decimal)
        self._balance: Decimal = initial_capital
        self._equity: Decimal = initial_capital
        self._peak_equity: Decimal = initial_capital
        self._max_drawdown: Decimal = Decimal("0.00")
        self._max_drawdown_pct: float = 0.0

        # Position and Ledger State
        self._open_position: dict[str, Any] | None = None
        self._trades: list[TradeRecord] = []
        self._equity_curve: list[EquityCurvePoint] = []
        self._candles_history: list[OHLCV] = []

    @property
    def balance(self) -> Decimal:
        return self._balance

    @property
    def equity(self) -> Decimal:
        return self._equity

    @property
    def trades(self) -> list[TradeRecord]:
        return list(self._trades)

    @property
    def equity_curve(self) -> list[EquityCurvePoint]:
        return list(self._equity_curve)

    async def on_candle(
        self,
        symbol: str,
        timestamp: datetime,
        open_price: Decimal,
        high: Decimal | None = None,
        low: Decimal | None = None,
        close: Decimal | None = None,
        volume: Decimal = Decimal(0),
        high_price: Decimal | None = None,
        low_price: Decimal | None = None,
        close_price: Decimal | None = None,
    ) -> None:
        """Process a single historical bar through the strategy and accounting engine."""
        effective_high = high if high is not None else (high_price if high_price is not None else open_price)
        effective_low = low if low is not None else (low_price if low_price is not None else open_price)
        effective_close = close if close is not None else (close_price if close_price is not None else open_price)

        candle = OHLCV(
            symbol=symbol,
            timestamp=timestamp,
            open=open_price,
            high=effective_high,
            low=effective_low,
            close=effective_close,
            volume=volume,
        )
        self._candles_history.append(candle)

        # 1. Mark open position to market at bar close
        unrealized_pnl = Decimal("0.00")
        if self._open_position is not None:
            pos_side = self._open_position["side"]
            pos_entry = self._open_position["entry_price"]
            pos_qty = self._open_position["quantity"]
            if pos_side == "BUY":
                unrealized_pnl = (close - pos_entry) * pos_qty
            else:
                unrealized_pnl = (pos_entry - close) * pos_qty

        self._equity = self._balance + unrealized_pnl

        # 2. Update peak equity and drawdown
        self._peak_equity = max(self._peak_equity, self._equity)

        dd_abs = self._peak_equity - self._equity
        dd_pct = (
            float(dd_abs / self._peak_equity * 100)
            if self._peak_equity > Decimal(0)
            else 0.0
        )
        self._max_drawdown_pct = max(self._max_drawdown_pct, dd_pct)
        self._max_drawdown = max(self._max_drawdown, dd_abs)

        # 3. Record equity curve snapshot
        self._equity_curve.append(
            EquityCurvePoint(
                timestamp=timestamp,
                balance=self._balance,
                equity=self._equity,
                drawdown_pct=round(dd_pct, 4),
            )
        )

        # 4. Construct domain Position representation for strategy context
        current_pos_obj: Position | None = None
        if self._open_position is not None:
            side_enum = (
                PositionSide.LONG
                if self._open_position["side"] == "BUY"
                else PositionSide.SHORT
            )
            current_pos_obj = Position(
                position_id=self._open_position["trade_id"],
                strategy_id=self.strategy.strategy_id,
                symbol=symbol,
                side=side_enum,
                quantity=self._open_position["quantity"],
                entry_price=self._open_position["entry_price"],
                current_price=close,
                unrealized_pnl=unrealized_pnl,
                timestamp=timestamp,
            )

        # 5. Build StrategyContext with strictly historical candles [0..T]
        context = StrategyContext(
            strategy_id=self.strategy.strategy_id,
            symbol=symbol,
            current_price=close,
            position=current_pos_obj,
            account_equity=self._equity,
            account_balance=self._balance,
            timestamp=timestamp,
            metadata={
                "timeframe": self.timeframe,
                "current_candle": candle,
                "historical_candles": list(self._candles_history),
                "free_margin": self._balance,
            },
        )

        # 6. Quant Safety: Assert zero look-ahead bias
        LeakageGuard.validate_strategy_context(context, timestamp)

        # 7. Evaluate strategy
        result = await self.strategy.evaluate(context)

        # 8. Process Signal & Order Intent if generated
        if result.signal and result.signal.direction in (SignalDirection.BUY, SignalDirection.SELL):
            sig_side = "BUY" if result.signal.direction == SignalDirection.BUY else "SELL"
            qty = self.default_lot_size
            if result.order_intent and result.order_intent.quantity > Decimal(0):
                qty = result.order_intent.quantity

            # Execution pricing with bid/ask separation and adverse slippage
            half_spread = self.spread / Decimal(2)
            if sig_side == "BUY":
                # Buy against Ask + adverse slippage
                fill_price = close + half_spread + self.adverse_slippage
            else:
                # Sell against Bid - adverse slippage
                fill_price = close - half_spread - self.adverse_slippage

            # Commission fee ($7 per 100,000 units)
            commission_rate = self.commission_per_lot / Decimal(100000)
            entry_fee = (qty * commission_rate).quantize(Decimal("0.01"))

            # Position Netting Logic
            if self._open_position is not None:
                existing_side = self._open_position["side"]
                if existing_side != sig_side:
                    # Closing existing position
                    entry_p = self._open_position["entry_price"]
                    pos_q = self._open_position["quantity"]
                    exit_fee = (pos_q * commission_rate).quantize(Decimal("0.01"))
                    total_fees = self._open_position["entry_fee"] + exit_fee

                    if existing_side == "BUY":
                        gross_pnl = (fill_price - entry_p) * pos_q
                    else:
                        gross_pnl = (entry_p - fill_price) * pos_q

                    net_pnl = gross_pnl - total_fees
                    self._balance += net_pnl

                    duration = (timestamp - self._open_position["entry_time"]).total_seconds()
                    self._trades.append(
                        TradeRecord(
                            trade_id=self._open_position["trade_id"],
                            symbol=symbol,
                            side=existing_side,
                            entry_time=self._open_position["entry_time"],
                            exit_time=timestamp,
                            entry_price=entry_p,
                            exit_price=fill_price,
                            quantity=pos_q,
                            gross_pnl=gross_pnl.quantize(Decimal("0.01")),
                            fees=total_fees,
                            net_pnl=net_pnl.quantize(Decimal("0.01")),
                            duration_seconds=duration,
                            exit_reason="SIGNAL",
                        )
                    )
                    self._open_position = None

            # Open new position if none active
            if self._open_position is None:
                self._open_position = {
                    "trade_id": str(uuid.uuid4())[:8],
                    "side": sig_side,
                    "quantity": qty,
                    "entry_price": fill_price,
                    "entry_time": timestamp,
                    "entry_fee": entry_fee,
                }

    async def finalize(self, final_timestamp: datetime, final_close: Decimal) -> None:
        """Close any remaining open position at end of backtest simulation."""
        if self._open_position is not None:
            existing_side = self._open_position["side"]
            entry_p = self._open_position["entry_price"]
            pos_q = self._open_position["quantity"]
            commission_rate = self.commission_per_lot / Decimal(100000)
            exit_fee = (pos_q * commission_rate).quantize(Decimal("0.01"))
            total_fees = self._open_position["entry_fee"] + exit_fee

            if existing_side == "BUY":
                gross_pnl = (final_close - entry_p) * pos_q
            else:
                gross_pnl = (entry_p - final_close) * pos_q

            net_pnl = gross_pnl - total_fees
            self._balance += net_pnl

            duration = (final_timestamp - self._open_position["entry_time"]).total_seconds()
            self._trades.append(
                TradeRecord(
                    trade_id=self._open_position["trade_id"],
                    symbol=self.symbol,
                    side=existing_side,
                    entry_time=self._open_position["entry_time"],
                    exit_time=final_timestamp,
                    entry_price=entry_p,
                    exit_price=final_close,
                    quantity=pos_q,
                    gross_pnl=gross_pnl.quantize(Decimal("0.01")),
                    fees=total_fees,
                    net_pnl=net_pnl.quantize(Decimal("0.01")),
                    duration_seconds=duration,
                    exit_reason="END_OF_DATA",
                )
            )
            self._open_position = None
            self._equity = self._balance

    def calculate_performance_metrics(self) -> ResearchPerformanceMetrics:
        """Compute institutional research performance metrics."""
        total_trades = len(self._trades)
        winning_trades = [t for t in self._trades if t.net_pnl > Decimal("0.00")]
        losing_trades = [t for t in self._trades if t.net_pnl < Decimal("0.00")]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0
        loss_rate = (loss_count / total_trades * 100) if total_trades > 0 else 0.0

        gross_profit = sum((t.gross_pnl for t in winning_trades), Decimal("0.00"))
        gross_loss = abs(sum((t.gross_pnl for t in losing_trades), Decimal("0.00")))
        net_profit = self._balance - self.initial_capital
        total_return_pct = (
            float(net_profit / self.initial_capital * 100)
            if self.initial_capital > Decimal("0.00")
            else 0.0
        )

        profit_factor = (
            float(gross_profit / gross_loss)
            if gross_loss > Decimal("0.00")
            else (float("inf") if gross_profit > Decimal("0.00") else 1.0)
        )
        if math.isinf(profit_factor):
            profit_factor = 999.99

        avg_win = (gross_profit / Decimal(str(win_count))) if win_count > 0 else Decimal("0.00")
        avg_loss = (gross_loss / Decimal(str(loss_count))) if loss_count > 0 else Decimal("0.00")

        # Expectancy = (Win% * AvgWin) - (Loss% * AvgLoss)
        win_prob = Decimal(str(win_count / total_trades)) if total_trades > 0 else Decimal("0.00")
        loss_prob = Decimal(str(loss_count / total_trades)) if total_trades > 0 else Decimal("0.00")
        expectancy = (win_prob * avg_win) - (loss_prob * avg_loss)

        largest_win = max((t.net_pnl for t in winning_trades), default=Decimal("0.00"))
        largest_loss = min((t.net_pnl for t in losing_trades), default=Decimal("0.00"))

        avg_trade_pnl = (
            (net_profit / Decimal(str(total_trades))).quantize(Decimal("0.01"))
            if total_trades > 0
            else Decimal("0.00")
        )

        # Sharpe and Sortino computation from bar-to-bar returns
        if len(self._equity_curve) > 1:
            returns = []
            for i in range(1, len(self._equity_curve)):
                prev = float(self._equity_curve[i - 1].equity)
                curr = float(self._equity_curve[i].equity)
                if prev > 0:
                    returns.append((curr - prev) / prev)

            if len(returns) >= 2:
                mean_ret = sum(returns) / len(returns)
                variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
                std_dev = math.sqrt(variance) if variance > 0 else 0.0

                # Annualized (assuming ~252 * 24 periods for H1)
                annual_factor = math.sqrt(252 * 24)
                sharpe_ratio = (mean_ret / std_dev * annual_factor) if std_dev > 0 else 0.0

                downside = [r for r in returns if r < 0]
                downside_var = sum(r**2 for r in downside) / len(returns) if downside else 0.0
                downside_std = math.sqrt(downside_var) if downside_var > 0 else 0.0
                sortino_ratio = (mean_ret / downside_std * annual_factor) if downside_std > 0 else 0.0
            else:
                sharpe_ratio = 0.0
                sortino_ratio = 0.0
        else:
            sharpe_ratio = 0.0
            sortino_ratio = 0.0

        recovery_factor = (
            float(net_profit / self._max_drawdown)
            if self._max_drawdown > Decimal("0.00")
            else 0.0
        )

        return ResearchPerformanceMetrics(
            initial_capital=self.initial_capital,
            final_balance=self._balance.quantize(Decimal("0.01")),
            net_profit=net_profit.quantize(Decimal("0.01")),
            total_return_pct=round(total_return_pct, 2),
            gross_profit=gross_profit.quantize(Decimal("0.01")),
            gross_loss=gross_loss.quantize(Decimal("0.01")),
            profit_factor=round(profit_factor, 2),
            win_rate_pct=round(win_rate, 2),
            loss_rate_pct=round(loss_rate, 2),
            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            avg_trade_pnl=avg_trade_pnl,
            largest_win=largest_win,
            largest_loss=largest_loss,
            sharpe_ratio=round(sharpe_ratio, 2),
            sortino_ratio=round(sortino_ratio, 2),
            max_drawdown_pct=round(self._max_drawdown_pct, 2),
            max_drawdown_duration_seconds=0.0,
            recovery_factor=round(recovery_factor, 2),
            expectancy=expectancy.quantize(Decimal("0.01")),
        )
