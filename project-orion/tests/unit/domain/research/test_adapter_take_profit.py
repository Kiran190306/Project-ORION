"""Tests for StrategyBacktestAdapter Intra-Bar Take-Profit Execution.

Covers TD-002 requirements:
A. LONG TP trigger
B. SHORT TP trigger
C. TP fill price
D. spread impact
E. adverse slippage impact
F. commission
G. TP exit reason
H. SL/TP both touched same candle (conservative risk-first resolution)
I. newly opened position cannot incorrectly self-exit
J. pattern attribution survives TP exit
K. legacy strategy without TP unchanged
L. deterministic repeated execution
M. TP wrong-side validation
N. invalid/zero-distance TP handling according to existing validation conventions
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.backtesting.strategy_adapter import StrategyBacktestAdapter
from libraries.domain.strategy.base import BaseStrategy
from libraries.domain.strategy.exceptions import StopLossTakeProfitError
from libraries.domain.strategy.models import (
    PositionIntent,
    PositionSide,
    Signal,
    SignalDirection,
    StrategyContext,
    StrategyMetadata,
)


class MockTPStrategy(BaseStrategy):
    """Controllable mock strategy that yields prescribed signals and intents."""

    def __init__(
        self,
        metadata: StrategyMetadata,
        plan: dict[datetime, tuple[Signal, PositionIntent]] | None = None,
    ) -> None:
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
# A & G: LONG Take-Profit Trigger & Exit Reason
# =============================================================================


@pytest.mark.asyncio
async def test_long_tp_hit_by_candle_high() -> None:
    """A. LONG TP is triggered when effective_high >= take_profit."""
    t0 = _dt(0)
    t1 = _dt(1)

    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0, price=Decimal("1.08500"))
    pos_intent = PositionIntent(
        strategy_id="mock",
        symbol="EUR/USD",
        side=PositionSide.LONG,
        target_quantity=Decimal(10000),
        take_profit=Decimal("1.09000"),
        timestamp=t0,
    )
    strat = MockTPStrategy(_meta(), {t0: (sig, pos_intent)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD", initial_capital=Decimal("10000.00"))

    # Bar 0: Enter LONG at close 1.08500
    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08450"), high=Decimal("1.08550"), low=Decimal("1.08400"), close=Decimal("1.08500"))
    assert adapter._open_position is not None
    assert adapter._open_position["take_profit"] == Decimal("1.09000")

    # Bar 1: High reaches 1.09050 >= 1.09000 -> Triggers TAKE_PROFIT
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08500"), high=Decimal("1.09050"), low=Decimal("1.08480"), close=Decimal("1.08900"))

    assert adapter._open_position is None
    assert len(adapter.trades) == 1
    trade = adapter.trades[0]
    assert trade.exit_reason == "TAKE_PROFIT"
    assert trade.side == "BUY"
    assert trade.exit_time == t1


# =============================================================================
# B: SHORT Take-Profit Trigger
# =============================================================================


@pytest.mark.asyncio
async def test_short_tp_hit_by_candle_low() -> None:
    """B. SHORT TP is triggered when effective_low <= take_profit."""
    t0 = _dt(0)
    t1 = _dt(1)

    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.SELL, timestamp=t0, price=Decimal("1.08500"))
    pos_intent = PositionIntent(
        strategy_id="mock",
        symbol="EUR/USD",
        side=PositionSide.SHORT,
        target_quantity=Decimal(10000),
        take_profit=Decimal("1.08000"),
        timestamp=t0,
    )
    strat = MockTPStrategy(_meta(), {t0: (sig, pos_intent)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD", initial_capital=Decimal("10000.00"))

    # Bar 0: Enter SHORT at close 1.08500
    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08550"), high=Decimal("1.08600"), low=Decimal("1.08450"), close=Decimal("1.08500"))
    assert adapter._open_position is not None
    assert adapter._open_position["take_profit"] == Decimal("1.08000")

    # Bar 1: Low dips to 1.07950 <= 1.08000 -> Triggers TAKE_PROFIT
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08500"), high=Decimal("1.08520"), low=Decimal("1.07950"), close=Decimal("1.08100"))

    assert adapter._open_position is None
    assert len(adapter.trades) == 1
    trade = adapter.trades[0]
    assert trade.exit_reason == "TAKE_PROFIT"
    assert trade.side == "SELL"
    assert trade.exit_time == t1


# =============================================================================
# C, D, E, F: TP Fill Price, Spread, Slippage, and Commission Accounting
# =============================================================================


@pytest.mark.asyncio
async def test_long_tp_fill_price_spread_slippage_and_commission() -> None:
    """C, D, E, F. LONG TP execution pricing, spread deduction, slippage, and commission."""
    t0 = _dt(0)
    t1 = _dt(1)

    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
    pos_intent = PositionIntent(
        strategy_id="mock",
        symbol="EUR/USD",
        side=PositionSide.LONG,
        target_quantity=Decimal(10000),
        take_profit=Decimal("1.09000"),
    )
    strat = MockTPStrategy(_meta(), {t0: (sig, pos_intent)})

    # Spread = 2.0 pips (0.00020), half_spread = 0.00010
    # Adverse slippage = 1.0 pips (0.00010)
    # Commission = $10.00 / 100k -> 0.00010/unit -> $1.00 for 10k units
    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        initial_capital=Decimal("10000.00"),
        spread_pips=Decimal("2.0"),
        adverse_slippage_pips=Decimal("1.0"),
        commission_per_lot=Decimal("10.00"),
        default_lot_size=Decimal(10000),
    )

    # Entry at 1.08500:
    # Buy fill = 1.08500 + half_spread (0.00010) + slippage (0.00010) = 1.08520
    # Entry fee = 10000 * 10 / 100000 = 1.00
    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08450"), close=Decimal("1.08500"))
    assert adapter._open_position["entry_price"] == Decimal("1.08520")
    assert adapter._open_position["entry_fee"] == Decimal("1.00")

    # Bar 1 touches TP (1.09000)
    # Long exit is a Sell order:
    # Exit fill = 1.09000 - half_spread (0.00010) - slippage (0.00010) = 1.08980
    # Exit fee = 1.00 -> total fees = 2.00
    # Gross PnL = (1.08980 - 1.08520) * 10000 = +46.00
    # Net PnL = 46.00 - 2.00 = +44.00
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08600"), high=Decimal("1.09100"), low=Decimal("1.08550"), close=Decimal("1.08950"))

    trade = adapter.trades[0]
    assert trade.exit_price == Decimal("1.08980")
    assert trade.fees == Decimal("2.00")
    assert trade.gross_pnl == Decimal("46.00")
    assert trade.net_pnl == Decimal("44.00")
    assert trade.exit_reason == "TAKE_PROFIT"
    assert adapter.balance == Decimal("10044.00")
    assert adapter.equity == Decimal("10044.00")


@pytest.mark.asyncio
async def test_short_tp_fill_price_spread_slippage_and_commission() -> None:
    """C, D, E, F. SHORT TP execution pricing, spread addition, slippage, and commission."""
    t0 = _dt(0)
    t1 = _dt(1)

    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.SELL, timestamp=t0)
    pos_intent = PositionIntent(
        strategy_id="mock",
        symbol="EUR/USD",
        side=PositionSide.SHORT,
        target_quantity=Decimal(10000),
        take_profit=Decimal("1.08000"),
    )
    strat = MockTPStrategy(_meta(), {t0: (sig, pos_intent)})

    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        initial_capital=Decimal("10000.00"),
        spread_pips=Decimal("2.0"),
        adverse_slippage_pips=Decimal("1.0"),
        commission_per_lot=Decimal("10.00"),
        default_lot_size=Decimal(10000),
    )

    # Entry at 1.08500:
    # Sell fill = 1.08500 - half_spread (0.00010) - slippage (0.00010) = 1.08480
    # Entry fee = 1.00
    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08550"), close=Decimal("1.08500"))
    assert adapter._open_position["entry_price"] == Decimal("1.08480")

    # Bar 1 touches TP (1.08000)
    # Short exit is a Buy order:
    # Exit fill = 1.08000 + half_spread (0.00010) + slippage (0.00010) = 1.08020
    # Exit fee = 1.00 -> total fees = 2.00
    # Gross PnL = (1.08480 - 1.08020) * 10000 = +46.00
    # Net PnL = 46.00 - 2.00 = +44.00
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08400"), high=Decimal("1.08450"), low=Decimal("1.07900"), close=Decimal("1.08100"))

    trade = adapter.trades[0]
    assert trade.exit_price == Decimal("1.08020")
    assert trade.fees == Decimal("2.00")
    assert trade.gross_pnl == Decimal("46.00")
    assert trade.net_pnl == Decimal("44.00")
    assert trade.exit_reason == "TAKE_PROFIT"
    assert adapter.balance == Decimal("10044.00")


# =============================================================================
# H: Same-Bar SL and TP Conflict Resolution (Conservative Risk-First)
# =============================================================================


@pytest.mark.asyncio
async def test_same_bar_sl_tp_both_touched_long_triggers_stop_loss() -> None:
    """H. Long position where both SL and TP are touched in the same candle: STOP_LOSS executed."""
    t0 = _dt(0)
    t1 = _dt(1)

    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
    pos_intent = PositionIntent(
        strategy_id="mock",
        symbol="EUR/USD",
        side=PositionSide.LONG,
        target_quantity=Decimal(10000),
        stop_loss=Decimal("1.08000"),
        take_profit=Decimal("1.09000"),
    )
    strat = MockTPStrategy(_meta(), {t0: (sig, pos_intent)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD", initial_capital=Decimal("10000.00"))

    # Enter Long at 1.08500
    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08450"), close=Decimal("1.08500"))

    # Bar 1: Extreme volatility: High hits 1.09200 (touches TP) AND Low dips to 1.07800 (touches SL)
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08500"), high=Decimal("1.09200"), low=Decimal("1.07800"), close=Decimal("1.08600"))

    assert len(adapter.trades) == 1
    trade = adapter.trades[0]
    # Conservative risk-first rule requires STOP_LOSS to precede TAKE_PROFIT
    assert trade.exit_reason == "STOP_LOSS"
    # Exit price should reflect SL level (1.08000 - spread/slippage), not TP level
    half_spread = adapter.spread / Decimal(2)
    expected_exit = Decimal("1.08000") - half_spread - adapter.adverse_slippage
    assert trade.exit_price == expected_exit


@pytest.mark.asyncio
async def test_same_bar_sl_tp_both_touched_short_triggers_stop_loss() -> None:
    """H. Short position where both SL and TP are touched in the same candle: STOP_LOSS executed."""
    t0 = _dt(0)
    t1 = _dt(1)

    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.SELL, timestamp=t0)
    pos_intent = PositionIntent(
        strategy_id="mock",
        symbol="EUR/USD",
        side=PositionSide.SHORT,
        target_quantity=Decimal(10000),
        stop_loss=Decimal("1.09000"),
        take_profit=Decimal("1.08000"),
    )
    strat = MockTPStrategy(_meta(), {t0: (sig, pos_intent)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD", initial_capital=Decimal("10000.00"))

    # Enter Short at 1.08500
    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08550"), close=Decimal("1.08500"))

    # Bar 1: Extreme volatility: High hits 1.09200 (touches SL) AND Low dips to 1.07800 (touches TP)
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08500"), high=Decimal("1.09200"), low=Decimal("1.07800"), close=Decimal("1.08400"))

    assert len(adapter.trades) == 1
    trade = adapter.trades[0]
    assert trade.exit_reason == "STOP_LOSS"
    half_spread = adapter.spread / Decimal(2)
    expected_exit = Decimal("1.09000") + half_spread + adapter.adverse_slippage
    assert trade.exit_price == expected_exit


# =============================================================================
# I: Position Eligibility (No immediate self-exit on same candle)
# =============================================================================


@pytest.mark.asyncio
async def test_newly_opened_position_cannot_self_exit_on_same_candle() -> None:
    """I. Position opened on bar T cannot self-exit intra-bar on bar T."""
    t0 = _dt(0)

    # Bar 0 has high=1.09500, but strategy produces signal at bar close (t0) with TP=1.09000
    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
    pos_intent = PositionIntent(
        strategy_id="mock",
        symbol="EUR/USD",
        side=PositionSide.LONG,
        target_quantity=Decimal(10000),
        take_profit=Decimal("1.09000"),
    )
    strat = MockTPStrategy(_meta(), {t0: (sig, pos_intent)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD")

    # Bar 0 high was 1.09500 >= 1.09000, but position is entered at bar close
    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08400"), high=Decimal("1.09500"), low=Decimal("1.08300"), close=Decimal("1.08500"))

    # Position must remain open, zero exits on bar 0
    assert adapter._open_position is not None
    assert adapter._open_position["side"] == "BUY"
    assert len(adapter.trades) == 0


# =============================================================================
# J: Pattern Attribution Survives TP Exit
# =============================================================================


@pytest.mark.asyncio
async def test_pattern_attribution_survives_tp_exit() -> None:
    """J. Pattern attribution metadata is preserved intact on TP exit."""
    t0 = _dt(0)
    t1 = _dt(1)

    sig = Signal(
        strategy_id="mock",
        symbol="EUR/USD",
        direction=SignalDirection.BUY,
        timestamp=t0,
        metadata={
            "pattern_id": "bullish_engulfing",
            "pattern_confidence": 0.92,
            "pattern_strength": "strong",
        },
    )
    pos_intent = PositionIntent(
        strategy_id="mock",
        symbol="EUR/USD",
        side=PositionSide.LONG,
        target_quantity=Decimal(10000),
        take_profit=Decimal("1.09000"),
    )
    strat = MockTPStrategy(_meta(), {t0: (sig, pos_intent)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD")

    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08450"), close=Decimal("1.08500"))
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08500"), high=Decimal("1.09050"), low=Decimal("1.08490"), close=Decimal("1.08800"))

    assert len(adapter.trades) == 1
    trade = adapter.trades[0]
    assert trade.exit_reason == "TAKE_PROFIT"
    assert trade.metadata["pattern_id"] == "bullish_engulfing"
    assert trade.metadata["pattern_confidence"] == 0.92
    assert trade.metadata["pattern_strength"] == "strong"


# =============================================================================
# Canonical Source & Fallback (Signal.metadata["take_profit"])
# =============================================================================


@pytest.mark.asyncio
async def test_tp_via_signal_metadata_fallback() -> None:
    """1. Take-profit carried in Signal.metadata is respected when PositionIntent has no TP."""
    t0 = _dt(0)
    t1 = _dt(1)

    sig = Signal(
        strategy_id="mock",
        symbol="EUR/USD",
        direction=SignalDirection.BUY,
        timestamp=t0,
        metadata={"take_profit": "1.09000"},
    )
    # PositionIntent has no take_profit
    pos_intent = PositionIntent(
        strategy_id="mock",
        symbol="EUR/USD",
        side=PositionSide.LONG,
        target_quantity=Decimal(10000),
    )
    strat = MockTPStrategy(_meta(), {t0: (sig, pos_intent)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD")

    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08450"), close=Decimal("1.08500"))
    assert adapter._open_position is not None
    assert adapter._open_position["take_profit"] == Decimal("1.09000")

    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08500"), high=Decimal("1.09050"), low=Decimal("1.08490"), close=Decimal("1.08800"))
    assert len(adapter.trades) == 1
    assert adapter.trades[0].exit_reason == "TAKE_PROFIT"


# =============================================================================
# K: Legacy Strategy Without TP Unchanged
# =============================================================================


@pytest.mark.asyncio
async def test_legacy_strategy_without_tp_unchanged() -> None:
    """K. Strategies without TP behave identically to existing baseline."""
    t0 = _dt(0)
    t1 = _dt(1)
    t2 = _dt(2)

    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
    pos_intent = PositionIntent(strategy_id="mock", symbol="EUR/USD", side=PositionSide.LONG, target_quantity=Decimal(10000))
    strat = MockTPStrategy(_meta(), {t0: (sig, pos_intent)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD")

    await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08450"), close=Decimal("1.08500"))
    await adapter.on_candle("EUR/USD", t1, open_price=Decimal("1.08500"), high=Decimal("1.09500"), low=Decimal("1.07500"), close=Decimal("1.08600"))

    # No TP or SL set -> position stays open through extreme bar
    assert adapter._open_position is not None
    assert len(adapter.trades) == 0

    await adapter.finalize(t2, Decimal("1.08700"))
    assert len(adapter.trades) == 1
    assert adapter.trades[0].exit_reason == "END_OF_DATA"


# =============================================================================
# L: Deterministic Repeated Execution
# =============================================================================


@pytest.mark.asyncio
async def test_deterministic_repeated_execution() -> None:
    """L. Same inputs produce byte-for-byte identical trade results across runs."""
    t0 = _dt(0)
    t1 = _dt(1)
    t2 = _dt(2)

    def _create_run() -> StrategyBacktestAdapter:
        sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
        pos = PositionIntent(strategy_id="mock", symbol="EUR/USD", side=PositionSide.LONG, target_quantity=Decimal(10000), take_profit=Decimal("1.09000"))
        strat = MockTPStrategy(_meta(), {t0: (sig, pos)})
        return StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD", initial_capital=Decimal("10000.00"))

    adapter1 = _create_run()
    adapter2 = _create_run()

    for ad in (adapter1, adapter2):
        await ad.on_candle("EUR/USD", t0, open_price=Decimal("1.08450"), high=Decimal("1.08550"), low=Decimal("1.08400"), close=Decimal("1.08500"))
        await ad.on_candle("EUR/USD", t1, open_price=Decimal("1.08500"), high=Decimal("1.09050"), low=Decimal("1.08490"), close=Decimal("1.08800"))
        await ad.finalize(t2, Decimal("1.08800"))

    assert len(adapter1.trades) == len(adapter2.trades) == 1
    t1_rec, t2_rec = adapter1.trades[0], adapter2.trades[0]
    assert t1_rec.exit_price == t2_rec.exit_price
    assert t1_rec.gross_pnl == t2_rec.gross_pnl
    assert t1_rec.net_pnl == t2_rec.net_pnl
    assert t1_rec.fees == t2_rec.fees
    assert t1_rec.exit_reason == t2_rec.exit_reason == "TAKE_PROFIT"
    assert adapter1.balance == adapter2.balance


# =============================================================================
# M: TP Wrong-Side Validation
# =============================================================================


@pytest.mark.asyncio
async def test_long_tp_wrong_side_validation_raises() -> None:
    """M. LONG TP below entry price raises StopLossTakeProfitError."""
    t0 = _dt(0)

    # Entry close is 1.08500, fill price is ~1.08510. TP at 1.08000 is below entry!
    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
    pos_intent = PositionIntent(
        strategy_id="mock",
        symbol="EUR/USD",
        side=PositionSide.LONG,
        target_quantity=Decimal(10000),
        take_profit=Decimal("1.08000"),
    )
    strat = MockTPStrategy(_meta(), {t0: (sig, pos_intent)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD")

    with pytest.raises(StopLossTakeProfitError, match="must be above entry_price"):
        await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08450"), close=Decimal("1.08500"))


@pytest.mark.asyncio
async def test_short_tp_wrong_side_validation_raises() -> None:
    """M. SHORT TP above entry price raises StopLossTakeProfitError."""
    t0 = _dt(0)

    # Entry close is 1.08500, fill price is ~1.08490. TP at 1.09000 is above entry!
    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.SELL, timestamp=t0)
    pos_intent = PositionIntent(
        strategy_id="mock",
        symbol="EUR/USD",
        side=PositionSide.SHORT,
        target_quantity=Decimal(10000),
        take_profit=Decimal("1.09000"),
    )
    strat = MockTPStrategy(_meta(), {t0: (sig, pos_intent)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD")

    with pytest.raises(StopLossTakeProfitError, match="must be below entry_price"):
        await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08550"), close=Decimal("1.08500"))


# =============================================================================
# N: Invalid / Zero-Distance TP Validation
# =============================================================================


@pytest.mark.asyncio
async def test_zero_or_negative_tp_raises_value_error() -> None:
    """N. Zero or negative TP raises ValueError."""
    t0 = _dt(0)

    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
    pos_intent = PositionIntent(
        strategy_id="mock",
        symbol="EUR/USD",
        side=PositionSide.LONG,
        target_quantity=Decimal(10000),
        take_profit=Decimal("0.00000"),
    )
    strat = MockTPStrategy(_meta(), {t0: (sig, pos_intent)})
    adapter = StrategyBacktestAdapter(strategy=strat, symbol="EUR/USD")

    with pytest.raises(ValueError, match="Take profit price must be positive"):
        await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08450"), close=Decimal("1.08500"))


@pytest.mark.asyncio
async def test_zero_distance_tp_raises_stop_loss_take_profit_error() -> None:
    """N. Zero-distance TP (equal to fill price) raises StopLossTakeProfitError."""
    t0 = _dt(0)

    # With spread_pips=0, adverse_slippage_pips=0, fill_price = 1.08500 exactly
    sig = Signal(strategy_id="mock", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
    pos_intent = PositionIntent(
        strategy_id="mock",
        symbol="EUR/USD",
        side=PositionSide.LONG,
        target_quantity=Decimal(10000),
        take_profit=Decimal("1.08500"),
    )
    strat = MockTPStrategy(_meta(), {t0: (sig, pos_intent)})
    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        spread_pips=Decimal(0),
        adverse_slippage_pips=Decimal(0),
    )

    with pytest.raises(StopLossTakeProfitError, match="must be above entry_price"):
        await adapter.on_candle("EUR/USD", t0, open_price=Decimal("1.08450"), close=Decimal("1.08500"))
