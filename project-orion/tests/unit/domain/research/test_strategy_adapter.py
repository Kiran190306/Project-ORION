"""Unit tests for StrategyBacktestAdapter and accounting invariants (EPIC-023 Phases 6-11, 35)."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from libraries.domain.backtesting.historical_data import (
    MarketDataServiceHistoricalProvider,
)
from libraries.domain.backtesting.models import Timeframe
from libraries.domain.backtesting.strategy_adapter import (
    StrategyBacktestAdapter,
    downsample_equity_curve,
)
from libraries.domain.research.models import EquityCurvePoint
from libraries.domain.strategy.registry import StrategyRegistry


@pytest.mark.asyncio
async def test_strategy_adapter_execution_and_metrics() -> None:
    """StrategyBacktestAdapter simulates signals with slippage, commission, and returns metrics."""
    strategy = StrategyRegistry.create_strategy(
        strategy_id="trend_following",
        parameters={"fast_period": 5, "slow_period": 15},
        symbols=["EUR/USD"],
    )

    adapter = StrategyBacktestAdapter(
        strategy=strategy,
        symbol="EUR/USD",
        timeframe="H1",
        initial_capital=Decimal("10000.00"),
        spread_pips=Decimal("1.5"),
        adverse_slippage_pips=Decimal("0.5"),
        commission_per_lot=Decimal("7.00"),
    )

    # Generate test candles
    provider = MarketDataServiceHistoricalProvider()
    candles = await provider.load_candles(
        symbol="EUR/USD",
        timeframe=Timeframe.H1,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 15),
    )
    assert len(candles) > 50

    for c in candles:
        await adapter.on_candle(
            symbol="EUR/USD",
            timestamp=c["timestamp"],
            open_price=c["open"],
            high_price=c["high"],
            low_price=c["low"],
            close_price=c["close"],
            volume=c["volume"],
        )

    await adapter.finalize(
        final_timestamp=candles[-1]["timestamp"],
        final_close=candles[-1]["close"],
    )

    metrics = adapter.calculate_performance_metrics()
    assert metrics.initial_capital == Decimal("10000.00")
    assert metrics.final_balance > Decimal(0)
    assert isinstance(metrics.sharpe_ratio, float)
    assert not math.isnan(metrics.sharpe_ratio)
    assert metrics.max_drawdown_pct >= 0.0
    assert len(adapter.equity_curve) == len(candles)


@pytest.mark.asyncio
async def test_backtest_determinism_invariant() -> None:
    """INVARIANT: Replaying identical candles with identical config must produce identical results."""
    provider = MarketDataServiceHistoricalProvider()
    candles = await provider.load_candles(
        symbol="EUR/USD",
        timeframe=Timeframe.H1,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 10),
    )

    # Run 1
    strat1 = StrategyRegistry.create_strategy(
        strategy_id="trend_following",
        parameters={"fast_period": 5, "slow_period": 15},
        symbols=["EUR/USD"],
    )
    adapter1 = StrategyBacktestAdapter(
        strategy=strat1,
        symbol="EUR/USD",
        timeframe="H1",
        initial_capital=Decimal("10000.00"),
    )
    for c in candles:
        await adapter1.on_candle("EUR/USD", c["timestamp"], c["open"], c["high"], c["low"], c["close"], c["volume"])
    await adapter1.finalize(candles[-1]["timestamp"], candles[-1]["close"])
    m1 = adapter1.calculate_performance_metrics()

    # Run 2
    strat2 = StrategyRegistry.create_strategy(
        strategy_id="trend_following",
        parameters={"fast_period": 5, "slow_period": 15},
        symbols=["EUR/USD"],
    )
    adapter2 = StrategyBacktestAdapter(
        strategy=strat2,
        symbol="EUR/USD",
        timeframe="H1",
        initial_capital=Decimal("10000.00"),
    )
    for c in candles:
        await adapter2.on_candle("EUR/USD", c["timestamp"], c["open"], c["high"], c["low"], c["close"], c["volume"])
    await adapter2.finalize(candles[-1]["timestamp"], candles[-1]["close"])
    m2 = adapter2.calculate_performance_metrics()

    # Assert exact equality
    assert m1.final_balance == m2.final_balance
    assert m1.net_profit == m2.net_profit
    assert m1.total_trades == m2.total_trades
    assert m1.sharpe_ratio == m2.sharpe_ratio
    assert m1.max_drawdown_pct == m2.max_drawdown_pct
    assert len(adapter1.trades) == len(adapter2.trades)


def test_downsample_equity_curve_limits_points() -> None:
    """Downsampling must reduce large curves to max_points while preserving start and end."""
    base_t = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    points = [
        EquityCurvePoint(
            timestamp=base_t + timedelta(hours=i),
            balance=Decimal(10000 + i),
            equity=Decimal(10000 + i),
            drawdown_pct=0.0,
        )
        for i in range(1000)
    ]

    downsampled = downsample_equity_curve(points, max_points=200)
    assert len(downsampled) <= 200
    assert downsampled[0].timestamp == points[0].timestamp
    assert downsampled[-1].timestamp == points[-1].timestamp


def test_downsample_small_curve_unchanged() -> None:
    """Curves smaller than max_points should remain intact."""
    base_t = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    points = [
        EquityCurvePoint(
            timestamp=base_t + timedelta(hours=i),
            balance=Decimal(10000 + i),
            equity=Decimal(10000 + i),
            drawdown_pct=0.0,
        )
        for i in range(50)
    ]
    downsampled = downsample_equity_curve(points, max_points=100)
    assert len(downsampled) == 50


from libraries.domain.strategy.base import BaseStrategy
from libraries.domain.strategy.models import Signal, StrategyContext, StrategyMetadata


class _PriceCapturingStrategy(BaseStrategy):
    def __init__(self, metadata: StrategyMetadata, **kwargs: object) -> None:
        super().__init__(metadata, kwargs)
        self.captured_prices: list[Decimal | None] = []

    async def generate_signal(self, context: StrategyContext) -> Signal | None:
        self.captured_prices.append(context.current_price)
        return None


@pytest.mark.asyncio
async def test_on_candle_close_price_populates_context_current_price() -> None:
    """REGRESSION: on_candle(close_price=DECIMAL) must produce context.current_price == close_price and not None."""
    meta = StrategyMetadata(
        strategy_id="price_capturing",
        name="Price Capturing",
        version="1.0.0",
        tags=["EUR/USD"],
    )
    strat = _PriceCapturingStrategy(meta)
    strat.initialize()

    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        timeframe="H1",
    )

    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    expected_close = Decimal("1.0850")
    await adapter.on_candle(
        symbol="EUR/USD",
        timestamp=t0,
        open_price=Decimal("1.0800"),
        high_price=Decimal("1.0900"),
        low_price=Decimal("1.0750"),
        close_price=expected_close,
        volume=Decimal("100"),
    )

    assert len(strat.captured_prices) == 1
    assert strat.captured_prices[0] is not None
    assert strat.captured_prices[0] == expected_close


@pytest.mark.asyncio
async def test_on_candle_close_backward_compatibility() -> None:
    """REGRESSION: on_candle(close=DECIMAL) remains fully backward compatible."""
    meta = StrategyMetadata(
        strategy_id="price_capturing",
        name="Price Capturing",
        version="1.0.0",
        tags=["EUR/USD"],
    )
    strat = _PriceCapturingStrategy(meta)
    strat.initialize()

    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        timeframe="H1",
    )

    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    expected_close = Decimal("1.0850")
    await adapter.on_candle(
        symbol="EUR/USD",
        timestamp=t0,
        open_price=Decimal("1.0800"),
        high=Decimal("1.0900"),
        low=Decimal("1.0750"),
        close=expected_close,
        volume=Decimal("100"),
    )

    assert len(strat.captured_prices) == 1
    assert strat.captured_prices[0] is not None
    assert strat.captured_prices[0] == expected_close
