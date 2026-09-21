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
