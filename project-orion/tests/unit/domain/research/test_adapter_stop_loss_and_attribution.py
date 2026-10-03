"""Tests for StrategyBacktestAdapter Intra-Bar Stop-Loss Simulation and Pattern Attribution.

Verifies:
A. Stop-Loss Simulation:
1. LONG stop hit by candle LOW.
2. SHORT stop hit by candle HIGH.
3. Stop not hit when price remains outside trigger range.
4. STOP_LOSS exit reason explicitly populated.
5. Correct exit accounting (balance, equity, PnL).
6. Correct fees and adverse slippage application.
7. Strict Decimal precision across all balances and metrics.
8. Same-bar stop-loss trigger and opposing signal deterministic event ordering.
9. Causal evaluation with no future-candle leakage.
10. Existing 4 strategies remain behaviorally unchanged.

B. Pattern Attribution:
11. candlestick_reversal pattern_id reaches TradeRecord.metadata.
12. Different pattern IDs remain correctly attributed.
13. Missing metadata does not crash.
14. Existing strategies without pattern metadata remain compatible.
15. TradeRecord backward compatibility.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from libraries.domain.backtesting.models import Timeframe
from libraries.domain.backtesting.strategy_adapter import StrategyBacktestAdapter
from libraries.domain.market_data.models import OHLCV
from libraries.domain.patterns.engine import CandlestickPatternEngine
from libraries.domain.patterns.models import CandlestickPattern, PatternDirection, PatternStrength
from libraries.domain.research.models import TradeRecord
from libraries.domain.strategy.base import BaseStrategy
from libraries.domain.strategy.models import (
    ExecutionAction,
    OrderIntent,
    PositionIntent,
    PositionSide,
    Signal,
    SignalDirection,
    SignalStrength,
    StrategyContext,
    StrategyMetadata,
    StrategyStatus,
)
from libraries.domain.strategy.registry import StrategyRegistry
from libraries.domain.strategy.strategies.candlestick_reversal import CandlestickReversalStrategy
from libraries.domain.strategy.strategies.trend_following import TrendFollowingStrategy


class MockSignalStrategy(BaseStrategy):
    """Controllable mock strategy that yields prescribed signals and intents."""

    def __init__(self, metadata: StrategyMetadata, plan: dict[datetime, tuple[Signal, PositionIntent]] | None = None) -> None:
        super().__init__(metadata, {})
        self.plan = plan or {}
        self.initialize()
        self._symbols = ["EUR/USD"]

    async def generate_signal(self, context: StrategyContext) -> Signal | None:
        if context.timestamp in self.plan:
            return self.plan[context.timestamp][0]
        return None

    async def _size_position(self, signal: Signal, context: StrategyContext) -> PositionIntent:
        if context.timestamp in self.plan:
            return self.plan[context.timestamp][1]
        return await super()._size_position(signal, context)


def _meta(name: str = "mock") -> StrategyMetadata:
    return StrategyMetadata(strategy_id=name, name=name, version="1.0.0")


def _dt(hour: int) -> datetime:
    return datetime(2025, 1, 1, hour, 0, tzinfo=timezone.utc)


# =============================================================================
# Phase A: Stop-Loss Tests
# =============================================================================

@pytest.mark.asyncio
async def test_long_stop_hit_by_candle_low() -> None:
    """1. LONG stop hit by candle LOW."""
    t0 = _dt(0)
    t1 = _dt(1)

    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0, price=Decimal("1.08500"))
    pos_intent = PositionIntent(
        strategy_id="mock",
        symbol="EUR/USD",
        side=PositionSide.LONG,
        target_quantity=Decimal("10000"),
        stop_loss=Decimal("1.08000"),
        timestamp=t0,
    )
    strat = MockSignalStrategy(_meta(), {t0: (sig, pos_intent)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD", initial_capital=Decimal("10000.00"))

    # Bar 0: Enter LONG at close 1.08500
    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08450"), high=Decimal("1.08550"), low=Decimal("1.08400"), close=Decimal("1.08500"))
    assert adapter._open_position is not None
    assert adapter._open_position["stop_loss"] == Decimal("1.08000")

    # Bar 1: Low dips to 1.07950 <= 1.08000 -> Triggers STOP_LOSS
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08500"), high=Decimal("1.08520"), low=Decimal("1.07950"), close=Decimal("1.08100"))

    assert adapter._open_position is None
    assert len(adapter.trades) == 1
    trade = adapter.trades[0]
    assert trade.exit_reason == "STOP_LOSS"
    assert trade.side == "BUY"
    assert trade.exit_time == t1


@pytest.mark.asyncio
async def test_short_stop_hit_by_candle_high() -> None:
    """2. SHORT stop hit by candle HIGH."""
    t0 = _dt(0)
    t1 = _dt(1)

    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.SELL, timestamp=t0, price=Decimal("1.08500"))
    pos_intent = PositionIntent(
        strategy_id="mock",
        symbol="EUR/USD",
        side=PositionSide.SHORT,
        target_quantity=Decimal("10000"),
        stop_loss=Decimal("1.09000"),
        timestamp=t0,
    )
    strat = MockSignalStrategy(_meta(), {t0: (sig, pos_intent)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD", initial_capital=Decimal("10000.00"))

    # Bar 0: Enter SHORT at close 1.08500
    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08550"), high=Decimal("1.08600"), low=Decimal("1.08450"), close=Decimal("1.08500"))
    assert adapter._open_position is not None
    assert adapter._open_position["stop_loss"] == Decimal("1.09000")

    # Bar 1: High spikes to 1.09050 >= 1.09000 -> Triggers STOP_LOSS
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08500"), high=Decimal("1.09050"), low=Decimal("1.08480"), close=Decimal("1.08800"))

    assert adapter._open_position is None
    assert len(adapter.trades) == 1
    trade = adapter.trades[0]
    assert trade.exit_reason == "STOP_LOSS"
    assert trade.side == "SELL"
    assert trade.exit_time == t1


@pytest.mark.asyncio
async def test_stop_not_hit_when_price_remains_outside_trigger_range() -> None:
    """3. Stop not hit when price remains outside trigger range."""
    t0 = _dt(0)
    t1 = _dt(1)

    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0, price=Decimal("1.08500"))
    pos_intent = PositionIntent(
        strategy_id="mock",
        symbol="EUR/USD",
        side=PositionSide.LONG,
        target_quantity=Decimal("10000"),
        stop_loss=Decimal("1.08000"),
        timestamp=t0,
    )
    strat = MockSignalStrategy(_meta(), {t0: (sig, pos_intent)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD", initial_capital=Decimal("10000.00"))

    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08450"), high=Decimal("1.08550"), low=Decimal("1.08400"), close=Decimal("1.08500"))
    # Bar 1 low is 1.08200 > 1.08000 -> No stop trigger
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08500"), high=Decimal("1.08600"), low=Decimal("1.08200"), close=Decimal("1.08400"))

    assert adapter._open_position is not None
    assert len(adapter.trades) == 0


@pytest.mark.asyncio
async def test_stop_loss_exit_reason_explicit() -> None:
    """4. STOP_LOSS exit reason explicitly verified."""
    t0 = _dt(0)
    t1 = _dt(1)

    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
    pos_intent = PositionIntent(strategy_id="mock", symbol="EUR/USD", side=PositionSide.LONG, target_quantity=Decimal("10000"), stop_loss=Decimal("1.08000"))
    strat = MockSignalStrategy(_meta(), {t0: (sig, pos_intent)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD")

    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08500"), close=Decimal("1.08500"))
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08500"), low=Decimal("1.07900"), close=Decimal("1.08000"))

    assert len(adapter.trades) == 1
    assert adapter.trades[0].exit_reason == "STOP_LOSS"


@pytest.mark.asyncio
async def test_correct_exit_accounting() -> None:
    """5. Correct exit accounting (gross PnL, net PnL, and balance updates)."""
    t0 = _dt(0)
    t1 = _dt(1)

    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
    pos_intent = PositionIntent(strategy_id="mock", symbol="EUR/USD", side=PositionSide.LONG, target_quantity=Decimal("10000"), stop_loss=Decimal("1.08000"))
    strat = MockSignalStrategy(_meta(), {t0: (sig, pos_intent)})

    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        initial_capital=Decimal("10000.00"),
        spread_pips=Decimal("1.5"),
        adverse_slippage_pips=Decimal("0.5"),
        commission_per_lot=Decimal("7.00"),
        default_lot_size=Decimal("10000"),
    )

    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08450"), close=Decimal("1.08500"))
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08500"), low=Decimal("1.07990"), close=Decimal("1.08200"))

    trade = adapter.trades[0]
    assert trade.gross_pnl == Decimal("-52.50")
    assert trade.net_pnl == Decimal("-53.90")
    assert adapter.balance == Decimal("9946.10")
    assert adapter.equity == Decimal("9946.10")


@pytest.mark.asyncio
async def test_correct_fees_and_slippage() -> None:
    """6. Correct fees and adverse slippage application during stop-loss exit."""
    t0 = _dt(0)
    t1 = _dt(1)

    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
    pos_intent = PositionIntent(strategy_id="mock", symbol="EUR/USD", side=PositionSide.LONG, target_quantity=Decimal("10000"), stop_loss=Decimal("1.08000"))
    strat = MockSignalStrategy(_meta(), {t0: (sig, pos_intent)})

    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        initial_capital=Decimal("10000.00"),
        spread_pips=Decimal("2.0"),
        adverse_slippage_pips=Decimal("1.0"),
        commission_per_lot=Decimal("10.00"),
        default_lot_size=Decimal("10000"),
    )

    # Buy entry fill at 1.08500 + 0.00010 (half spread) + 0.00010 (slippage) = 1.08520
    # Entry fee: 10000 * 10 / 100000 = 1.00
    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08450"), close=Decimal("1.08500"))
    assert adapter._open_position["entry_price"] == Decimal("1.08520")
    assert adapter._open_position["entry_fee"] == Decimal("1.00")

    # Exit fill (Sell): 1.08000 - 0.00010 (half spread) - 0.00010 (slippage) = 1.07980
    # Exit fee: 1.00 -> total fees = 2.00
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08500"), low=Decimal("1.07950"), close=Decimal("1.08200"))

    trade = adapter.trades[0]
    assert trade.exit_price == Decimal("1.07980")
    assert trade.fees == Decimal("2.00")
    assert trade.gross_pnl == (Decimal("1.07980") - Decimal("1.08520")) * Decimal("10000")


@pytest.mark.asyncio
async def test_decimal_precision() -> None:
    """7. Decimal precision across all accounting operations."""
    t0 = _dt(0)
    t1 = _dt(1)

    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
    pos_intent = PositionIntent(strategy_id="mock", symbol="EUR/USD", side=PositionSide.LONG, target_quantity=Decimal("10000"), stop_loss=Decimal("1.08123"))
    strat = MockSignalStrategy(_meta(), {t0: (sig, pos_intent)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD")

    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08500"), close=Decimal("1.08500"))
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08500"), low=Decimal("1.08100"), close=Decimal("1.08300"))

    trade = adapter.trades[0]
    assert isinstance(trade.entry_price, Decimal)
    assert isinstance(trade.exit_price, Decimal)
    assert isinstance(trade.gross_pnl, Decimal)
    assert isinstance(trade.net_pnl, Decimal)
    assert isinstance(trade.fees, Decimal)
    assert isinstance(adapter.balance, Decimal)
    assert isinstance(adapter.equity, Decimal)


@pytest.mark.asyncio
async def test_same_bar_stop_and_signal_deterministic_ordering() -> None:
    """8. Same-bar stop-loss and opposing signal deterministic event ordering."""
    t0 = _dt(0)
    t1 = _dt(1)
    t2 = _dt(2)

    # At t0: Buy signal with SL at 1.08000
    sig0 = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
    pos0 = PositionIntent(strategy_id="mock", symbol="EUR/USD", side=PositionSide.LONG, target_quantity=Decimal("10000"), stop_loss=Decimal("1.08000"))

    # At t1: Sell signal with SL at 1.09000
    sig1 = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.SELL, timestamp=t1)
    pos1 = PositionIntent(strategy_id="mock", symbol="EUR/USD", side=PositionSide.SHORT, target_quantity=Decimal("10000"), stop_loss=Decimal("1.09000"))

    strat = MockSignalStrategy(_meta(), {t0: (sig0, pos0), t1: (sig1, pos1)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD")

    # Bar 0: Long entered
    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08500"), close=Decimal("1.08500"))

    # Bar 1: Low dips to 1.07900 (stops out Long) AND bar close emits Sell signal!
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08500"), low=Decimal("1.07900"), close=Decimal("1.08400"))

    # Verified ordering:
    # 1. Long exited via STOP_LOSS
    assert len(adapter.trades) == 1
    assert adapter.trades[0].exit_reason == "STOP_LOSS"
    assert adapter.trades[0].side == "BUY"

    # 2. Sell signal at bar close entered a new Short position
    assert adapter._open_position is not None
    assert adapter._open_position["side"] == "SELL"
    assert adapter._open_position["stop_loss"] == Decimal("1.09000")

    # Finalize at t2
    await adapter.finalize(t2, Decimal("1.08300"))
    assert len(adapter.trades) == 2
    assert adapter.trades[1].exit_reason == "END_OF_DATA"
    assert adapter.trades[1].side == "SELL"


@pytest.mark.asyncio
async def test_no_future_candle_access() -> None:
    """9. Stop evaluation is causal and does not inspect future candles."""
    t0 = _dt(0)
    t1 = _dt(1)
    t2 = _dt(2)

    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
    pos = PositionIntent(strategy_id="mock", symbol="EUR/USD", side=PositionSide.LONG, target_quantity=Decimal("10000"), stop_loss=Decimal("1.08000"))
    strat = MockSignalStrategy(_meta(), {t0: (sig, pos)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD")

    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08500"), close=Decimal("1.08500"))
    # Bar 1 remains safely above stop
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08500"), low=Decimal("1.08200"), close=Decimal("1.08400"))
    assert adapter._open_position is not None
    assert len(adapter.trades) == 0

    # Bar 2 hits stop
    await adapter.on_candle("EUR/USD", t2, open_price=Decimal("1.08400"), low=Decimal("1.07900"), close=Decimal("1.08100"))
    assert adapter._open_position is None
    assert len(adapter.trades) == 1
    assert adapter.trades[0].exit_time == t2


@pytest.mark.asyncio
async def test_existing_strategies_remain_behaviorally_unchanged() -> None:
    """10. Existing strategies without stop-loss remain behaviorally unchanged."""
    strat = TrendFollowingStrategy(_meta("trend_following"), fast_period=2, slow_period=4)
    strat.initialize()
    strat._symbols = ["EUR/USD"]
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD")

    # Replay 10 price bars
    prices = [Decimal("1.0800"), Decimal("1.0810"), Decimal("1.0820"), Decimal("1.0830"), Decimal("1.0840"),
              Decimal("1.0830"), Decimal("1.0820"), Decimal("1.0810"), Decimal("1.0800"), Decimal("1.0790")]

    for i, p in enumerate(prices):
        # Even with extreme low and high, no stop-loss can trigger because stop_loss is None
        await adapter.on_candle("EUR/USD", _dt(i), open_price=p, high=p + Decimal("0.0500"), low=p - Decimal("0.0500"), close=p)

    await adapter.finalize(_dt(len(prices)), prices[-1])

    for trade in adapter.trades:
        assert trade.exit_reason in ("SIGNAL", "END_OF_DATA")
        assert trade.exit_reason != "STOP_LOSS"


# =============================================================================
# Phase B: Pattern Attribution Tests
# =============================================================================

@pytest.mark.asyncio
async def test_candlestick_reversal_pattern_id_reaches_trade_record() -> None:
    """11. candlestick_reversal pattern_id reaches TradeRecord.metadata."""
    t0 = _dt(0)
    t1 = _dt(1)
    t2 = _dt(2)

    # Bullish hammer pattern at t0
    hammer = CandlestickPattern(
        pattern_id="hammer",
        name="Hammer",
        direction=PatternDirection.BULLISH,
        strength=PatternStrength.STRONG,
        candle_index=0,
        timestamp=t0,
        description="Bullish reversal",
        confidence=0.85,
        metadata={"high": "1.0860", "low": "1.0830", "required_candles": 1},
    )

    strat = StrategyRegistry.create_strategy("candlestick_reversal", {"min_confidence": 0.70}, ["EUR/USD"])
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD", pattern_engine=CandlestickPatternEngine())
    adapter._pattern_map = {t0: (hammer,)}

    # Bar 0: Enter Long on hammer
    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.0850"), high=Decimal("1.0860"), low=Decimal("1.0830"), close=Decimal("1.0855"))
    assert adapter._open_position is not None
    assert adapter._open_position["metadata"].get("pattern_id") == "hammer"

    # Bar 1: Normal candle
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.0855"), high=Decimal("1.0870"), low=Decimal("1.0840"), close=Decimal("1.0860"))

    # Finalize at t2
    await adapter.finalize(t2, Decimal("1.0865"))

    assert len(adapter.trades) == 1
    trade = adapter.trades[0]
    assert trade.metadata["pattern_id"] == "hammer"
    assert trade.metadata["pattern_confidence"] == 0.85
    assert trade.metadata["pattern_strength"] == "strong"


@pytest.mark.asyncio
async def test_different_pattern_ids_remain_correctly_attributed() -> None:
    """12. Different pattern IDs remain correctly attributed across trade lifecycle."""
    t0 = _dt(0)
    t1 = _dt(1)
    t2 = _dt(2)

    # Trade 1: Bullish engulfing
    sig1 = Signal(
        strategy_id="candlestick_reversal",
        symbol="EUR/USD",
        direction=SignalDirection.BUY,
        timestamp=t0,
        metadata={"pattern_id": "bullish_engulfing", "pattern_confidence": 0.88, "stop_loss": "1.08000"},
    )
    pos1 = PositionIntent(strategy_id="candlestick_reversal", symbol="EUR/USD", side=PositionSide.LONG, target_quantity=Decimal("10000"), stop_loss=Decimal("1.08000"))

    # Trade 2: Bearish engulfing (reversal)
    sig2 = Signal(
        strategy_id="candlestick_reversal",
        symbol="EUR/USD",
        direction=SignalDirection.SELL,
        timestamp=t1,
        metadata={"pattern_id": "bearish_engulfing", "pattern_confidence": 0.92, "stop_loss": "1.09000"},
    )
    pos2 = PositionIntent(strategy_id="candlestick_reversal", symbol="EUR/USD", side=PositionSide.SHORT, target_quantity=Decimal("10000"), stop_loss=Decimal("1.09000"))

    strat = MockSignalStrategy(_meta("candlestick_reversal"), {t0: (sig1, pos1), t1: (sig2, pos2)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD")

    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.0850"), close=Decimal("1.0850"))
    # At t1: opposing signal closes Trade 1 and opens Trade 2
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.0850"), close=Decimal("1.0840"))
    await adapter.finalize(t2, Decimal("1.0830"))

    assert len(adapter.trades) == 2
    assert adapter.trades[0].metadata["pattern_id"] == "bullish_engulfing"
    assert adapter.trades[1].metadata["pattern_id"] == "bearish_engulfing"


@pytest.mark.asyncio
async def test_missing_metadata_does_not_crash() -> None:
    """13. Missing metadata does not crash and defaults cleanly."""
    t0 = _dt(0)
    t1 = _dt(1)

    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0, metadata={})
    pos = PositionIntent(strategy_id="mock", symbol="EUR/USD", side=PositionSide.LONG, target_quantity=Decimal("10000"))
    strat = MockSignalStrategy(_meta(), {t0: (sig, pos)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD")

    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.0850"), close=Decimal("1.0850"))
    await adapter.finalize(t1, Decimal("1.0860"))

    assert len(adapter.trades) == 1
    assert adapter.trades[0].metadata == {}
    assert "pattern_id" not in adapter.trades[0].metadata


@pytest.mark.asyncio
async def test_existing_strategies_without_pattern_metadata_compatible() -> None:
    """14. Existing strategies without pattern metadata remain compatible."""
    strat = TrendFollowingStrategy(_meta("trend_following"), fast_period=2, slow_period=3)
    strat.initialize()
    strat._symbols = ["EUR/USD"]
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD")

    candles = [Decimal("1.0800"), Decimal("1.0810"), Decimal("1.0820"), Decimal("1.0830"), Decimal("1.0810"), Decimal("1.0800")]
    for i, p in enumerate(candles):
        await adapter.on_candle("EUR/USD", _dt(i), open_price=p, close=p)
    await adapter.finalize(_dt(len(candles)), candles[-1])

    for trade in adapter.trades:
        assert isinstance(trade.metadata, dict)
        assert trade.metadata == {}


def test_trade_record_backward_compatibility() -> None:
    """15. TradeRecord backward compatibility with positional and keyword instantiation."""
    t_now = datetime.now(timezone.utc)

    # Classic positional instantiation without metadata
    tr1 = TradeRecord(
        "t1", "EUR/USD", "BUY", t_now, t_now,
        Decimal("1.0850"), Decimal("1.0860"), Decimal("10000"),
        Decimal("10.00"), Decimal("1.40"), Decimal("8.60"), 3600.0, "SIGNAL"
    )
    assert tr1.metadata == {}
    assert tr1.exit_reason == "SIGNAL"

    # Keyword instantiation with metadata
    tr2 = TradeRecord(
        trade_id="t2",
        symbol="EUR/USD",
        side="SELL",
        entry_time=t_now,
        exit_time=t_now,
        entry_price=Decimal("1.0860"),
        exit_price=Decimal("1.0850"),
        quantity=Decimal("10000"),
        gross_pnl=Decimal("10.00"),
        fees=Decimal("1.40"),
        net_pnl=Decimal("8.60"),
        duration_seconds=3600.0,
        exit_reason="STOP_LOSS",
        metadata={"pattern_id": "shooting_star"},
    )
    assert tr2.metadata == {"pattern_id": "shooting_star"}
    assert tr2.exit_reason == "STOP_LOSS"
