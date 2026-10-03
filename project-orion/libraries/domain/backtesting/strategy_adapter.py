"""Strategy Backtest Adapter.

Bridges BaseStrategy subclasses directly to the BacktestEngine, evaluating
strategy signals at each bar, simulating realistic execution with adverse
slippage, spread, and commission, maintaining position netting, and asserting
zero look-ahead bias with LeakageGuard.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.backtesting.leakage_guard import LeakageGuard
from libraries.domain.market_data.models import OHLCV
from libraries.domain.patterns.engine import CandlestickPatternEngine
from libraries.domain.patterns.models import CandlestickPattern
from libraries.domain.research.models import (
    EquityCurvePoint,
    ResearchPerformanceMetrics,
    TradeRecord,
)
from libraries.domain.strategy.base import BaseStrategy
from libraries.domain.strategy.exceptions import StopLossTakeProfitError
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
    """Orchestrates strategy evaluation and deterministic accounting during backtest replay.

    Execution Realism Model:
    - Intra-bar Stop-Loss Execution: YES (evaluated against bar OHLC extremes: low for BUY, high for SELL).
    - Intra-bar Take-Profit Execution: YES (evaluated against bar OHLC extremes: high for BUY, low for SELL).
    - Tick-level Execution / Path Reconstruction: NO (does not assume sub-candle price trajectories).
    - OHLC Ambiguity Resolution: Deterministic conservative risk-first convention. When both SL and TP
      thresholds are breached within the same candle and no intra-bar tick sequence is available,
      the engine triggers STOP_LOSS to prevent optimistic survivorship bias.
    - Financial Precision: 100% strict Decimal arithmetic; spread, adverse slippage, and commission modeled.
    """

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
        pattern_engine: CandlestickPatternEngine | None = None,
        candles: Sequence[Any] | None = None,
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
        self.pattern_engine = pattern_engine

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

        # Candlestick Pattern Mapping (timestamp -> immutable tuple of patterns)
        self._pattern_map: dict[datetime, tuple[CandlestickPattern, ...]] = {}
        if self.pattern_engine is not None and candles is not None:
            self.precompute_patterns(candles)

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

    @property
    def pattern_map(self) -> dict[datetime, tuple[CandlestickPattern, ...]]:
        """Return immutable view of the precomputed pattern map."""
        return dict(self._pattern_map)

    def precompute_patterns(self, candles: Sequence[Any]) -> None:
        """Precompute candlestick patterns across the historical series.

        Constructs an immutable mapping from candle timestamp to a tuple of
        patterns concluding at that exact candle. Strictly avoids cross-symbol
        and cross-timeframe contamination.
        """
        if self.pattern_engine is None or not candles:
            self._pattern_map = {}
            return

        from libraries.domain.market_data.normalization import normalize_symbol

        canonical_symbol = normalize_symbol(self.symbol)
        canonical_tf = str(self.timeframe).upper()

        # Filter candles for symbol and timeframe if those fields exist on candles
        filtered_candles: list[Any] = []
        for c in candles:
            c_sym = getattr(c, "symbol", None) or (c.get("symbol") if isinstance(c, dict) else None)
            if c_sym is not None and normalize_symbol(c_sym) != canonical_symbol:
                continue

            c_tf = getattr(c, "timeframe", None) or (c.get("timeframe") if isinstance(c, dict) else None)
            if c_tf is not None and str(c_tf).upper() != canonical_tf:
                continue

            filtered_candles.append(c)

        if not filtered_candles:
            self._pattern_map = {}
            return

        detected = self.pattern_engine.detect_patterns(filtered_candles)

        pattern_dict: dict[datetime, list[CandlestickPattern]] = {}
        for p in detected:
            ts = p.timestamp if p.timestamp.tzinfo is not None else p.timestamp.replace(tzinfo=timezone.utc)
            p_annotated = CandlestickPattern(
                pattern_id=p.pattern_id,
                name=p.name,
                direction=p.direction,
                strength=p.strength,
                candle_index=p.candle_index,
                timestamp=ts,
                description=p.description,
                confidence=p.confidence,
                metadata={
                    **p.metadata,
                    "symbol": self.symbol,
                    "timeframe": self.timeframe,
                },
            )
            pattern_dict.setdefault(ts, []).append(p_annotated)

        # Store as immutable tuples
        self._pattern_map = {
            ts: tuple(patterns_list)
            for ts, patterns_list in pattern_dict.items()
        }

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

        # ---------------------------------------------------------------------
        # 1. Deterministic Intra-Bar Stop-Loss and Take-Profit Evaluation
        # Timing: Evaluated at the start of on_candle across the current bar's
        # [effective_low, effective_high] range for existing positions entered
        # prior to this bar (entry_time < timestamp).
        #
        # Same-Bar Event Ordering:
        # If a bar triggers an active exit AND subsequently generates an
        # opposing strategy signal at bar close:
        # 1) STOP_LOSS / TAKE_PROFIT triggers first intra-bar, closing the carried position.
        # 2) Strategy evaluates at bar close with context.position = None.
        # 3) New signal opens a fresh position at Market-On-Close.
        #
        # Same-Bar SL/TP Conflict Resolution Convention:
        # If both stop-loss and take-profit trigger conditions are satisfied within the
        # same candle and no tick-level sequence is available from OHLC data, the engine
        # applies the conservative risk-first convention: STOP_LOSS is executed.
        # This prevents over-optimistic performance bias in backtesting.
        #
        # Execution-Price Convention:
        # Long Exit (Sell): fill_price = target_price - half_spread - adverse_slippage
        # Short Exit (Buy): fill_price = target_price + half_spread + adverse_slippage
        # ---------------------------------------------------------------------
        if (
            self._open_position is not None
            and self._open_position["entry_time"] < timestamp
            and (
                self._open_position.get("stop_loss") is not None
                or self._open_position.get("take_profit") is not None
            )
        ):
            sl = self._open_position.get("stop_loss")
            tp = self._open_position.get("take_profit")
            pos_side = self._open_position["side"]
            sl_triggered = False
            tp_triggered = False
            half_spread = self.spread / Decimal(2)

            if pos_side == "BUY":
                if sl is not None and effective_low <= sl:
                    sl_triggered = True
                if tp is not None and effective_high >= tp:
                    tp_triggered = True
            elif pos_side == "SELL":
                if sl is not None and effective_high >= sl:
                    sl_triggered = True
                if tp is not None and effective_low <= tp:
                    tp_triggered = True

            if sl_triggered or tp_triggered:
                # Deterministic conflict resolution: SL takes precedence over TP
                if sl_triggered:
                    exit_reason = (
                        "TRAILING_STOP"
                        if self._open_position.get("trailing_distance") is not None
                        else "STOP_LOSS"
                    )
                    target_price = sl
                else:
                    exit_reason = "TAKE_PROFIT"
                    target_price = tp

                assert target_price is not None

                if pos_side == "BUY":
                    exit_fill_price = target_price - half_spread - self.adverse_slippage
                else:
                    exit_fill_price = target_price + half_spread + self.adverse_slippage

                entry_p = self._open_position["entry_price"]
                pos_q = self._open_position["quantity"]
                commission_rate = self.commission_per_lot / Decimal(100000)
                exit_fee = (pos_q * commission_rate).quantize(Decimal("0.01"))
                total_fees = self._open_position["entry_fee"] + exit_fee

                if pos_side == "BUY":
                    gross_pnl = (exit_fill_price - entry_p) * pos_q
                else:
                    gross_pnl = (entry_p - exit_fill_price) * pos_q

                net_pnl = gross_pnl - total_fees
                self._balance += net_pnl

                duration = (timestamp - self._open_position["entry_time"]).total_seconds()
                exit_trade_metadata = dict(self._open_position.get("metadata", {}))
                if self._open_position.get("trailing_distance") is not None:
                    exit_trade_metadata["trailing_distance"] = str(self._open_position["trailing_distance"])
                self._trades.append(
                    TradeRecord(
                        trade_id=self._open_position["trade_id"],
                        symbol=symbol,
                        side=pos_side,
                        entry_time=self._open_position["entry_time"],
                        exit_time=timestamp,
                        entry_price=entry_p,
                        exit_price=exit_fill_price,
                        quantity=pos_q,
                        gross_pnl=gross_pnl.quantize(Decimal("0.01")),
                        fees=total_fees,
                        net_pnl=net_pnl.quantize(Decimal("0.01")),
                        duration_seconds=duration,
                        exit_reason=exit_reason,
                        metadata=exit_trade_metadata,
                    )
                )
                self._open_position = None

        # Dynamic Trailing-Stop Ratcheting
        # If position remains open and carries trailing_distance, update watermark and ratchet SL
        if (
            self._open_position is not None
            and self._open_position.get("trailing_distance") is not None
        ):
            active_trailing_dist = self._open_position["trailing_distance"]
            pos_side = self._open_position["side"]
            if pos_side == "BUY":
                hwm = self._open_position.get("high_water_mark")
                if hwm is None or effective_high > hwm:
                    self._open_position["high_water_mark"] = effective_high
                    ratcheted_sl = effective_high - active_trailing_dist
                    cur_sl = self._open_position.get("stop_loss")
                    if cur_sl is None or ratcheted_sl > cur_sl:
                        self._open_position["stop_loss"] = ratcheted_sl
            elif pos_side == "SELL":
                lwm = self._open_position.get("low_water_mark")
                if lwm is None or effective_low < lwm:
                    self._open_position["low_water_mark"] = effective_low
                    ratcheted_sl = effective_low + active_trailing_dist
                    cur_sl = self._open_position.get("stop_loss")
                    if cur_sl is None or ratcheted_sl < cur_sl:
                        self._open_position["stop_loss"] = ratcheted_sl

        # 2. Mark open position to market at bar close
        unrealized_pnl = Decimal("0.00")
        if self._open_position is not None:
            pos_side = self._open_position["side"]
            pos_entry = self._open_position["entry_price"]
            pos_qty = self._open_position["quantity"]
            if pos_side == "BUY":
                unrealized_pnl = (effective_close - pos_entry) * pos_qty
            else:
                unrealized_pnl = (pos_entry - effective_close) * pos_qty

        self._equity = self._balance + unrealized_pnl

        # 3. Update peak equity and drawdown
        self._peak_equity = max(self._peak_equity, self._equity)

        dd_abs = self._peak_equity - self._equity
        dd_pct = (
            float(dd_abs / self._peak_equity * 100)
            if self._peak_equity > Decimal(0)
            else 0.0
        )
        self._max_drawdown_pct = max(self._max_drawdown_pct, dd_pct)
        self._max_drawdown = max(self._max_drawdown, dd_abs)

        # 4. Record equity curve snapshot
        self._equity_curve.append(
            EquityCurvePoint(
                timestamp=timestamp,
                balance=self._balance,
                equity=self._equity,
                drawdown_pct=round(dd_pct, 4),
            )
        )

        # 5. Construct domain Position representation for strategy context
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
                current_price=effective_close,
                unrealized_pnl=unrealized_pnl,
                timestamp=timestamp,
            )

        # 6. Build StrategyContext with strictly historical candles [0..T]
        metadata: dict[str, Any] = {
            "timeframe": self.timeframe,
            "current_candle": candle,
            "historical_candles": list(self._candles_history),
            "free_margin": self._balance,
        }
        if self.pattern_engine is not None:
            norm_ts = timestamp if timestamp.tzinfo is not None else timestamp.replace(tzinfo=timezone.utc)
            metadata["patterns"] = self._pattern_map.get(norm_ts, ())

        context = StrategyContext(
            strategy_id=self.strategy.strategy_id,
            symbol=symbol,
            current_price=effective_close,
            position=current_pos_obj,
            account_equity=self._equity,
            account_balance=self._balance,
            timestamp=timestamp,
            metadata=metadata,
        )

        # 7. Quant Safety: Assert zero look-ahead bias
        LeakageGuard.validate_strategy_context(context, timestamp)

        # 8. Evaluate strategy
        result = await self.strategy.evaluate(context)

        # 9. Process Signal & Order Intent if generated
        if result.signal and result.signal.direction in (SignalDirection.BUY, SignalDirection.SELL):
            sig_side = "BUY" if result.signal.direction == SignalDirection.BUY else "SELL"
            qty = self.default_lot_size
            if result.order_intent and result.order_intent.quantity > Decimal(0):
                qty = result.order_intent.quantity

            # Execution pricing with bid/ask separation and adverse slippage
            half_spread = self.spread / Decimal(2)
            if sig_side == "BUY":
                # Buy against Ask + adverse slippage
                fill_price = effective_close + half_spread + self.adverse_slippage
            else:
                # Sell against Bid - adverse slippage
                fill_price = effective_close - half_spread - self.adverse_slippage

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
                            metadata=dict(self._open_position.get("metadata", {})),
                        )
                    )
                    self._open_position = None

            # Open new position if none active
            if self._open_position is None:
                # Pattern attribution lifecycle: extract attribution metadata from signal
                trade_metadata: dict[str, Any] = {}
                if result.signal and result.signal.metadata:
                    if "pattern_id" in result.signal.metadata:
                        trade_metadata["pattern_id"] = result.signal.metadata["pattern_id"]
                    if "pattern_confidence" in result.signal.metadata:
                        trade_metadata["pattern_confidence"] = result.signal.metadata["pattern_confidence"]
                    if "pattern_strength" in result.signal.metadata:
                        trade_metadata["pattern_strength"] = result.signal.metadata["pattern_strength"]

                # Active stop-loss extraction
                sl_val: Decimal | None = None
                if result.position_intent and result.position_intent.stop_loss is not None:
                    sl_val = result.position_intent.stop_loss
                elif result.signal and result.signal.metadata and "stop_loss" in result.signal.metadata:
                    sl_val = Decimal(str(result.signal.metadata["stop_loss"]))

                # Active take-profit extraction
                tp_val: Decimal | None = None
                if result.position_intent and result.position_intent.take_profit is not None:
                    tp_val = result.position_intent.take_profit
                elif result.signal and result.signal.metadata and "take_profit" in result.signal.metadata:
                    tp_val = Decimal(str(result.signal.metadata["take_profit"]))

                # Active trailing-distance extraction
                trailing_dist: Decimal | None = None
                if result.position_intent and getattr(result.position_intent, "trailing_distance", None) is not None:
                    trailing_dist = result.position_intent.trailing_distance
                elif result.position_intent and result.position_intent.metadata and "trailing_distance" in result.position_intent.metadata:
                    trailing_dist = Decimal(str(result.position_intent.metadata["trailing_distance"]))
                elif result.signal and result.signal.metadata and "trailing_distance" in result.signal.metadata:
                    trailing_dist = Decimal(str(result.signal.metadata["trailing_distance"]))

                # Trailing-distance validation & initial SL calculation if not explicitly set
                if trailing_dist is not None:
                    if trailing_dist <= Decimal(0):
                        raise ValueError(f"Trailing distance must be positive, got {trailing_dist}")
                    if sl_val is None:
                        if sig_side == "BUY":
                            sl_val = fill_price - trailing_dist
                        else:
                            sl_val = fill_price + trailing_dist

                # Stop-loss validation
                if sl_val is not None:
                    if sl_val <= Decimal(0):
                        raise ValueError(f"Stop loss price must be positive, got {sl_val}")
                    if sig_side == "BUY" and sl_val >= fill_price:
                        raise StopLossTakeProfitError(
                            f"For long positions, stop_loss ({sl_val}) must be below entry_price ({fill_price})"
                        )
                    elif sig_side == "SELL" and sl_val <= fill_price:
                        raise StopLossTakeProfitError(
                            f"For short positions, stop_loss ({sl_val}) must be above entry_price ({fill_price})"
                        )

                # Take-profit validation
                if tp_val is not None:
                    if tp_val <= Decimal(0):
                        raise ValueError(f"Take profit price must be positive, got {tp_val}")
                    if sig_side == "BUY" and tp_val <= fill_price:
                        raise StopLossTakeProfitError(
                            f"For long positions, take_profit ({tp_val}) must be above entry_price ({fill_price})"
                        )
                    elif sig_side == "SELL" and tp_val >= fill_price:
                        raise StopLossTakeProfitError(
                            f"For short positions, take_profit ({tp_val}) must be below entry_price ({fill_price})"
                        )

                self._open_position = {
                    "trade_id": str(uuid.uuid4())[:8],
                    "side": sig_side,
                    "quantity": qty,
                    "entry_price": fill_price,
                    "entry_time": timestamp,
                    "entry_fee": entry_fee,
                    "stop_loss": sl_val,
                    "take_profit": tp_val,
                    "trailing_distance": trailing_dist,
                    "high_water_mark": fill_price if sig_side == "BUY" else None,
                    "low_water_mark": fill_price if sig_side == "SELL" else None,
                    "metadata": trade_metadata,
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
                    metadata=dict(self._open_position.get("metadata", {})),
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
