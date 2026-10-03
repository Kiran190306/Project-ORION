"""Tests for StrategyBacktestAdapter Dynamic Trailing Stop Simulation.

Verifies:
1. Long position trailing stop ratchets upward on new candle highs.
2. Long position exits deterministically when subsequent candle low breaches ratcheted SL.
3. Short position trailing stop ratchets downward on new candle lows.
4. Short position exits deterministically when subsequent candle high breaches ratcheted SL.
5. Exit reason is explicitly 'TRAILING_STOP'.
6. Metadata on TradeRecord contains 'trailing_distance'.
7. Trailing distance carried via PositionIntent.trailing_distance.
8. Trailing distance carried via PositionIntent.metadata['trailing_distance'].
9. Trailing distance carried via Signal.metadata['trailing_distance'].
10. Explicit initial stop loss preserved and ratchets upward when watermark improves.
11. Zero or negative trailing distance raises ValueError.
12. Backward compatibility: trades without trailing distance remain 'STOP_LOSS'.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from libraries.domain.backtesting.models import Timeframe
from libraries.domain.backtesting.strategy_adapter import StrategyBacktestAdapter
from libraries.domain.strategy.base import BaseStrategy
from libraries.domain.strategy.models import (
    PositionIntent,
    PositionSide,
    Signal,
    SignalDirection,
    StrategyContext,
    StrategyMetadata,
)


class MockTrailingStrategy(BaseStrategy):
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


def _meta(name: str = "mock_trailing") -> StrategyMetadata:
    return StrategyMetadata(strategy_id=name, name=name, version="1.0.0")


@pytest.mark.asyncio
async def test_long_trailing_stop_ratchets_and_exits() -> None:
    t0 = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=5)
    t2 = t0 + timedelta(minutes=10)

    sig = Signal(strategy_id="mock_trailing", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
    intent = PositionIntent(
        strategy_id="mock_trailing",
        symbol="EUR/USD",
        side=PositionSide.LONG,
        target_quantity=Decimal(1000),
        trailing_distance=Decimal("0.0050"),
    )

    strat = MockTrailingStrategy(_meta(), plan={t0: (sig, intent)})
    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        timeframe=Timeframe.M5,
        initial_capital=Decimal("10000.00"),
        spread_pips=Decimal("2.0"),
        adverse_slippage_pips=Decimal("1.0"),
        commission_per_lot=Decimal("7.00"),
    )

    # Bar 0: Enter LONG at 1.1000
    # Fill price: 1.1000 + 0.0001 (half spread) + 0.0001 (slippage) = 1.1002
    # Initial SL: 1.1002 - 0.0050 = 1.0952
    await adapter.on_candle(
        symbol="EUR/USD",
        timestamp=t0,
        open_price=Decimal("1.1000"),
        high=Decimal("1.1005"),
        low=Decimal("1.0995"),
        close=Decimal("1.1000"),
    )
    assert adapter._open_position is not None
    assert adapter._open_position["stop_loss"] == Decimal("1.0952")
    assert adapter._open_position["trailing_distance"] == Decimal("0.0050")

    # Bar 1: Price rallies. High reaches 1.1100, low is 1.0990 (above carried SL 1.0952).
    # Watermark updates to 1.1100, new ratcheted SL = 1.1100 - 0.0050 = 1.1050.
    await adapter.on_candle(
        symbol="EUR/USD",
        timestamp=t1,
        open_price=Decimal("1.1000"),
        high=Decimal("1.1100"),
        low=Decimal("1.0990"),
        close=Decimal("1.1080"),
    )
    assert adapter._open_position is not None
    assert adapter._open_position["stop_loss"] == Decimal("1.1050")
    assert adapter._open_position["high_water_mark"] == Decimal("1.1100")
    assert len(adapter.trades) == 0

    # Bar 2: Price dips. Low reaches 1.1040, which is <= ratcheted SL (1.1050).
    # Intra-bar check triggers trailing stop!
    # Exit target price = 1.1050
    # Fill price: 1.1050 - 0.0001 (half spread) - 0.0001 (slippage) = 1.1048
    await adapter.on_candle(
        symbol="EUR/USD",
        timestamp=t2,
        open_price=Decimal("1.1080"),
        high=Decimal("1.1085"),
        low=Decimal("1.1040"),
        close=Decimal("1.1045"),
    )

    assert adapter._open_position is None
    assert len(adapter.trades) == 1
    trade = adapter.trades[0]
    assert trade.exit_reason == "TRAILING_STOP"
    assert trade.exit_price == Decimal("1.1048")
    assert trade.net_pnl > Decimal(0)
    assert trade.metadata.get("trailing_distance") == "0.0050"


@pytest.mark.asyncio
async def test_short_trailing_stop_ratchets_and_exits() -> None:
    t0 = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=5)
    t2 = t0 + timedelta(minutes=10)

    sig = Signal(strategy_id="mock_trailing", symbol="EUR/USD", direction=SignalDirection.SELL, timestamp=t0)
    intent = PositionIntent(
        strategy_id="mock_trailing",
        symbol="EUR/USD",
        side=PositionSide.SHORT,
        target_quantity=Decimal(1000),
        trailing_distance=Decimal("0.0050"),
    )

    strat = MockTrailingStrategy(_meta(), plan={t0: (sig, intent)})
    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        timeframe=Timeframe.M5,
        initial_capital=Decimal("10000.00"),
        spread_pips=Decimal("2.0"),
        adverse_slippage_pips=Decimal("1.0"),
        commission_per_lot=Decimal("7.00"),
    )

    # Bar 0: Enter SHORT at 1.2000
    # Fill price: 1.2000 - 0.0001 (half spread) - 0.0001 (slippage) = 1.1998
    # Initial SL: 1.1998 + 0.0050 = 1.2048
    await adapter.on_candle(
        symbol="EUR/USD",
        timestamp=t0,
        open_price=Decimal("1.2000"),
        high=Decimal("1.2005"),
        low=Decimal("1.1995"),
        close=Decimal("1.2000"),
    )
    assert adapter._open_position is not None
    assert adapter._open_position["stop_loss"] == Decimal("1.2048")

    # Bar 1: Price drops favorably. Low reaches 1.1900, high is 1.2010 (below carried SL 1.2048).
    # Watermark updates to 1.1900, ratcheted SL = 1.1900 + 0.0050 = 1.1950.
    await adapter.on_candle(
        symbol="EUR/USD",
        timestamp=t1,
        open_price=Decimal("1.2000"),
        high=Decimal("1.2010"),
        low=Decimal("1.1900"),
        close=Decimal("1.1910"),
    )
    assert adapter._open_position is not None
    assert adapter._open_position["stop_loss"] == Decimal("1.1950")
    assert adapter._open_position["low_water_mark"] == Decimal("1.1900")
    assert len(adapter.trades) == 0

    # Bar 2: Price retraces upward. High reaches 1.1960, which is >= ratcheted SL (1.1950).
    # Exit target price = 1.1950
    # Fill price: 1.1950 + 0.0001 (half spread) + 0.0001 (slippage) = 1.1952
    await adapter.on_candle(
        symbol="EUR/USD",
        timestamp=t2,
        open_price=Decimal("1.1910"),
        high=Decimal("1.1960"),
        low=Decimal("1.1905"),
        close=Decimal("1.1955"),
    )

    assert adapter._open_position is None
    assert len(adapter.trades) == 1
    trade = adapter.trades[0]
    assert trade.exit_reason == "TRAILING_STOP"
    assert trade.exit_price == Decimal("1.1952")
    assert trade.net_pnl > Decimal(0)
    assert trade.metadata.get("trailing_distance") == "0.0050"


@pytest.mark.asyncio
async def test_trailing_stop_via_signal_metadata() -> None:
    t0 = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=5)
    t2 = t0 + timedelta(minutes=10)

    sig = Signal(
        strategy_id="mock_trailing",
        symbol="EUR/USD",
        direction=SignalDirection.BUY,
        timestamp=t0,
        metadata={"trailing_distance": Decimal("0.0040")},
    )
    intent = PositionIntent(
        strategy_id="mock_trailing",
        symbol="EUR/USD",
        side=PositionSide.LONG,
        target_quantity=Decimal(1000),
    )

    strat = MockTrailingStrategy(_meta(), plan={t0: (sig, intent)})
    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        timeframe=Timeframe.M5,
        initial_capital=Decimal("10000.00"),
        spread_pips=Decimal("2.0"),
        adverse_slippage_pips=Decimal("1.0"),
        commission_per_lot=Decimal("7.00"),
    )

    await adapter.on_candle(
        symbol="EUR/USD",
        timestamp=t0,
        open_price=Decimal("1.1000"),
        high=Decimal("1.1005"),
        low=Decimal("1.0995"),
        close=Decimal("1.1000"),
    )
    assert adapter._open_position is not None
    assert adapter._open_position["trailing_distance"] == Decimal("0.0040")

    # Bar 1: High reaches 1.1080 -> SL ratchets to 1.1080 - 0.0040 = 1.1040
    await adapter.on_candle(
        symbol="EUR/USD",
        timestamp=t1,
        open_price=Decimal("1.1000"),
        high=Decimal("1.1080"),
        low=Decimal("1.0980"),
        close=Decimal("1.1070"),
    )
    assert adapter._open_position["stop_loss"] == Decimal("1.1040")

    # Bar 2: Low reaches 1.1030 <= 1.1040 -> Triggers exit
    await adapter.on_candle(
        symbol="EUR/USD",
        timestamp=t2,
        open_price=Decimal("1.1070"),
        high=Decimal("1.1075"),
        low=Decimal("1.1030"),
        close=Decimal("1.1035"),
    )
    assert adapter._open_position is None
    assert adapter.trades[0].exit_reason == "TRAILING_STOP"


@pytest.mark.asyncio
async def test_trailing_stop_with_explicit_initial_stop_loss() -> None:
    t0 = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=5)

    sig = Signal(strategy_id="mock_trailing", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
    # Explicit initial SL at 1.0900 (wide initial risk), trailing_distance = 0.0050
    intent = PositionIntent(
        strategy_id="mock_trailing",
        symbol="EUR/USD",
        side=PositionSide.LONG,
        target_quantity=Decimal(1000),
        stop_loss=Decimal("1.0900"),
        trailing_distance=Decimal("0.0050"),
    )

    strat = MockTrailingStrategy(_meta(), plan={t0: (sig, intent)})
    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        timeframe=Timeframe.M5,
        initial_capital=Decimal("10000.00"),
        spread_pips=Decimal("2.0"),
        adverse_slippage_pips=Decimal("1.0"),
        commission_per_lot=Decimal("7.00"),
    )

    await adapter.on_candle(
        symbol="EUR/USD",
        timestamp=t0,
        open_price=Decimal("1.1000"),
        high=Decimal("1.1005"),
        low=Decimal("1.0995"),
        close=Decimal("1.1000"),
    )
    assert adapter._open_position is not None
    # Explicit stop_loss is kept initially
    assert adapter._open_position["stop_loss"] == Decimal("1.0900")

    # Bar 1: High reaches 1.1100 -> new trailing SL = 1.1100 - 0.0050 = 1.1050 > 1.0900
    # Stop loss ratchets up to 1.1050!
    await adapter.on_candle(
        symbol="EUR/USD",
        timestamp=t1,
        open_price=Decimal("1.1000"),
        high=Decimal("1.1100"),
        low=Decimal("1.0990"),
        close=Decimal("1.1080"),
    )
    assert adapter._open_position["stop_loss"] == Decimal("1.1050")


@pytest.mark.asyncio
async def test_zero_or_negative_trailing_distance_raises() -> None:
    t0 = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)

    sig = Signal(strategy_id="mock_trailing", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
    intent = PositionIntent(
        strategy_id="mock_trailing",
        symbol="EUR/USD",
        side=PositionSide.LONG,
        target_quantity=Decimal(1000),
        trailing_distance=Decimal("-0.0010"),
    )

    strat = MockTrailingStrategy(_meta(), plan={t0: (sig, intent)})
    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        timeframe=Timeframe.M5,
        initial_capital=Decimal("10000.00"),
    )

    with pytest.raises(ValueError, match="Trailing distance must be positive"):
        await adapter.on_candle(
            symbol="EUR/USD",
            timestamp=t0,
            open_price=Decimal("1.1000"),
            high=Decimal("1.1005"),
            low=Decimal("1.0995"),
            close=Decimal("1.1000"),
        )


@pytest.mark.asyncio
async def test_strategy_without_trailing_stop_retains_stop_loss_exit_reason() -> None:
    t0 = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=5)

    sig = Signal(strategy_id="mock_trailing", symbol="EUR/USD", direction=SignalDirection.BUY, timestamp=t0)
    intent = PositionIntent(
        strategy_id="mock_trailing",
        symbol="EUR/USD",
        side=PositionSide.LONG,
        target_quantity=Decimal(1000),
        stop_loss=Decimal("1.0950"),
    )

    strat = MockTrailingStrategy(_meta(), plan={t0: (sig, intent)})
    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        timeframe=Timeframe.M5,
        initial_capital=Decimal("10000.00"),
    )

    await adapter.on_candle(
        symbol="EUR/USD",
        timestamp=t0,
        open_price=Decimal("1.1000"),
        high=Decimal("1.1005"),
        low=Decimal("1.0995"),
        close=Decimal("1.1000"),
    )

    # Bar 1 dips below 1.0950
    await adapter.on_candle(
        symbol="EUR/USD",
        timestamp=t1,
        open_price=Decimal("1.1000"),
        high=Decimal("1.1005"),
        low=Decimal("1.0940"),
        close=Decimal("1.0945"),
    )

    assert adapter._open_position is None
    assert len(adapter.trades) == 1
    assert adapter.trades[0].exit_reason == "STOP_LOSS"
