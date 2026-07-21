"""Tests for BaseStrategy and built-in sample strategies."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from libraries.domain.strategies.context import StrategyContext
from libraries.domain.strategies.interfaces import (
    StrategyCapabilities,
    StrategyMetadata,
)
from libraries.domain.strategies.models import StrategyConfig, StrategyPriority, StrategyStatus
from libraries.domain.strategies.strategy import (
    BaseStrategy,
    BreakoutStrategy,
    EmaCrossStrategy,
    RsiStrategy,
    StrategyResult,
)
from libraries.domain.trading.signals import SignalDirection, SignalStrength


class TestBaseStrategy:
    def test_initialization(self) -> None:
        meta = StrategyMetadata(id="test", name="Test", version="1.0.0")
        caps = StrategyCapabilities()
        strategy = BaseStrategy(metadata=meta, capabilities=caps)
        assert strategy.id == "test"
        assert strategy.name == "Test"
        assert strategy.status == StrategyStatus.DRAFT

    def test_initialize_sets_active(self) -> None:
        async def exercise() -> None:
            meta = StrategyMetadata(id="test", name="Test", version="1.0.0")
            caps = StrategyCapabilities()
            strategy = BaseStrategy(metadata=meta, capabilities=caps)
            await strategy.initialize()
            assert strategy.status == StrategyStatus.ACTIVE

        asyncio.run(exercise())

    def test_dispose_sets_stopped(self) -> None:
        async def exercise() -> None:
            meta = StrategyMetadata(id="test", name="Test", version="1.0.0")
            caps = StrategyCapabilities()
            strategy = BaseStrategy(metadata=meta, capabilities=caps)
            await strategy.initialize()
            await strategy.dispose()
            assert strategy.status == StrategyStatus.STOPPED

        asyncio.run(exercise())

    def test_get_param(self) -> None:
        config = StrategyConfig(params={"fast": 10, "slow": 30})
        meta = StrategyMetadata(id="test", name="Test", version="1.0.0")
        caps = StrategyCapabilities()
        strategy = BaseStrategy(metadata=meta, capabilities=caps, config=config)
        assert strategy.get_param("fast") == 10
        assert strategy.get_param("nonexistent") is None
        assert strategy.get_param("nonexistent", "default") == "default"

    def test_evaluate_raises_not_implemented(self) -> None:
        async def exercise() -> None:
            meta = StrategyMetadata(id="test", name="Test", version="1.0.0")
            caps = StrategyCapabilities()
            strategy = BaseStrategy(metadata=meta, capabilities=caps)
            ctx = StrategyContext(symbol="EUR/USD")
            with pytest.raises(NotImplementedError):
                await strategy.evaluate("EUR/USD", ctx)

        asyncio.run(exercise())


class TestEmaCrossStrategy:
    def test_buy_when_fast_above_slow(self) -> None:
        async def exercise() -> None:
            strategy = EmaCrossStrategy()
            ctx = StrategyContext(
                symbol="EUR/USD",
                ema_fast=Decimal("1.1050"),
                ema_slow=Decimal("1.1000"),
            )
            result = await strategy.evaluate("EUR/USD", ctx)
            assert result is not None
            assert result.direction == SignalDirection.BUY
            assert result.confidence > 0

        asyncio.run(exercise())

    def test_sell_when_fast_below_slow(self) -> None:
        async def exercise() -> None:
            strategy = EmaCrossStrategy()
            ctx = StrategyContext(
                symbol="EUR/USD",
                ema_fast=Decimal("1.1000"),
                ema_slow=Decimal("1.1050"),
            )
            result = await strategy.evaluate("EUR/USD", ctx)
            assert result is not None
            assert result.direction == SignalDirection.SELL
            assert result.confidence > 0

        asyncio.run(exercise())

    def test_hold_when_no_cross(self) -> None:
        async def exercise() -> None:
            strategy = EmaCrossStrategy()
            ctx = StrategyContext(
                symbol="EUR/USD",
                ema_fast=Decimal("1.1020"),
                ema_slow=Decimal("1.1020"),
            )
            result = await strategy.evaluate("EUR/USD", ctx)
            assert result is None  # HOLD

        asyncio.run(exercise())

    def test_none_when_indicators_missing(self) -> None:
        async def exercise() -> None:
            strategy = EmaCrossStrategy()
            ctx = StrategyContext(symbol="EUR/USD")
            result = await strategy.evaluate("EUR/USD", ctx)
            assert result is None

        asyncio.run(exercise())

    def test_strength_based_on_confidence(self) -> None:
        async def exercise() -> None:
            strategy = EmaCrossStrategy()
            # Wide crossover = high confidence
            ctx = StrategyContext(
                symbol="EUR/USD",
                ema_fast=Decimal("1.2000"),
                ema_slow=Decimal("1.1000"),
            )
            result = await strategy.evaluate("EUR/USD", ctx)
            assert result is not None
            assert result.strength == SignalStrength.STRONG

        asyncio.run(exercise())


class TestRsiStrategy:
    def test_buy_when_oversold(self) -> None:
        async def exercise() -> None:
            strategy = RsiStrategy(oversold_threshold=30.0)
            ctx = StrategyContext(symbol="EUR/USD", rsi=25.0)
            result = await strategy.evaluate("EUR/USD", ctx)
            assert result is not None
            assert result.direction == SignalDirection.BUY
            assert result.confidence > 0

        asyncio.run(exercise())

    def test_sell_when_overbought(self) -> None:
        async def exercise() -> None:
            strategy = RsiStrategy(overbought_threshold=70.0)
            ctx = StrategyContext(symbol="EUR/USD", rsi=75.0)
            result = await strategy.evaluate("EUR/USD", ctx)
            assert result is not None
            assert result.direction == SignalDirection.SELL
            assert result.confidence > 0

        asyncio.run(exercise())

    def test_hold_in_normal_range(self) -> None:
        async def exercise() -> None:
            strategy = RsiStrategy()
            ctx = StrategyContext(symbol="EUR/USD", rsi=50.0)
            result = await strategy.evaluate("EUR/USD", ctx)
            assert result is None

        asyncio.run(exercise())

    def test_none_when_rsi_missing(self) -> None:
        async def exercise() -> None:
            strategy = RsiStrategy()
            ctx = StrategyContext(symbol="EUR/USD")
            result = await strategy.evaluate("EUR/USD", ctx)
            assert result is None

        asyncio.run(exercise())

    def test_deep_oversold_high_confidence(self) -> None:
        async def exercise() -> None:
            strategy = RsiStrategy()
            ctx = StrategyContext(symbol="EUR/USD", rsi=10.0)
            result = await strategy.evaluate("EUR/USD", ctx)
            assert result is not None
            assert result.strength == SignalStrength.STRONG

        asyncio.run(exercise())


class TestBreakoutStrategy:
    def test_buy_on_breakout_with_volume(self) -> None:
        async def exercise() -> None:
            strategy = BreakoutStrategy()
            ctx = StrategyContext(
                symbol="EUR/USD",
                price_position=0.9,
                volume_ratio=2.0,
            )
            result = await strategy.evaluate("EUR/USD", ctx)
            assert result is not None
            assert result.direction == SignalDirection.BUY
            assert result.confidence > 0

        asyncio.run(exercise())

    def test_hold_without_volume(self) -> None:
        async def exercise() -> None:
            strategy = BreakoutStrategy(volume_threshold=2.0)
            ctx = StrategyContext(
                symbol="EUR/USD",
                price_position=0.9,
                volume_ratio=1.0,
            )
            result = await strategy.evaluate("EUR/USD", ctx)
            assert result is None

        asyncio.run(exercise())

    def test_hold_without_breakout(self) -> None:
        async def exercise() -> None:
            strategy = BreakoutStrategy(breakout_threshold=0.8)
            ctx = StrategyContext(
                symbol="EUR/USD",
                price_position=0.5,
                volume_ratio=2.0,
            )
            result = await strategy.evaluate("EUR/USD", ctx)
            assert result is None

        asyncio.run(exercise())

    def test_metadata_in_result(self) -> None:
        async def exercise() -> None:
            strategy = BreakoutStrategy()
            ctx = StrategyContext(
                symbol="EUR/USD",
                price_position=0.95,
                volume_ratio=2.5,
            )
            result = await strategy.evaluate("EUR/USD", ctx)
            assert result is not None
            assert "breakout_level" in result.metadata
            assert "volume_ratio" in result.metadata

        asyncio.run(exercise())
