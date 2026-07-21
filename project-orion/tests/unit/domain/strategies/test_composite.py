"""Tests for CompositeStrategy."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from libraries.domain.strategies.composite import CompositeStrategy
from libraries.domain.strategies.context import StrategyContext
from libraries.domain.strategies.strategy import (
    BreakoutStrategy,
    EmaCrossStrategy,
    RsiStrategy,
)
from libraries.domain.trading.signals import SignalDirection


class TestCompositeStrategy:
    def test_empty_composite(self) -> None:
        async def exercise() -> None:
            composite = CompositeStrategy()
            ctx = StrategyContext(symbol="EUR/USD")
            result = await composite.evaluate("EUR/USD", ctx)
            assert result.total_strategies == 0
            assert result.voting_result.direction is None

        asyncio.run(exercise())

    def test_single_strategy(self) -> None:
        async def exercise() -> None:
            composite = CompositeStrategy()
            composite.add_strategy(EmaCrossStrategy())
            ctx = StrategyContext(
                symbol="EUR/USD",
                ema_fast=Decimal("1.1050"),
                ema_slow=Decimal("1.1000"),
            )
            result = await composite.evaluate("EUR/USD", ctx)
            assert result.total_strategies == 1
            assert result.executed_strategies >= 1
            assert result.voting_result.direction == SignalDirection.BUY

        asyncio.run(exercise())

    def test_multiple_strategies_same_direction(self) -> None:
        async def exercise() -> None:
            composite = CompositeStrategy()
            composite.add_strategy(EmaCrossStrategy())
            composite.add_strategy(RsiStrategy())

            # RSI oversold + EMA bullish
            ctx = StrategyContext(
                symbol="EUR/USD",
                ema_fast=Decimal("1.1050"),
                ema_slow=Decimal("1.1000"),
                rsi=25.0,
                bid=Decimal("1.1050"),
                ask=Decimal("1.1052"),
            )
            result = await composite.evaluate("EUR/USD", ctx)
            assert result.total_strategies == 2
            assert result.executed_strategies >= 1
            assert result.voting_result.direction is not None

        asyncio.run(exercise())

    def test_remove_strategy(self) -> None:
        async def exercise() -> None:
            composite = CompositeStrategy()
            composite.add_strategy(EmaCrossStrategy())
            composite.remove_strategy("ema_cross")
            assert composite.strategy_count == 0

        asyncio.run(exercise())

    def test_get_strategy(self) -> None:
        async def exercise() -> None:
            composite = CompositeStrategy()
            strategy = EmaCrossStrategy()
            composite.add_strategy(strategy)
            retrieved = composite.get_strategy("ema_cross")
            assert retrieved is strategy
            assert composite.get_strategy("nonexistent") is None

        asyncio.run(exercise())

    def test_add_strategy_increments_count(self) -> None:
        async def exercise() -> None:
            composite = CompositeStrategy()
            assert composite.strategy_count == 0
            composite.add_strategy(EmaCrossStrategy())
            assert composite.strategy_count == 1
            composite.add_strategy(RsiStrategy())
            assert composite.strategy_count == 2

        asyncio.run(exercise())

    def test_breakout_with_ema_composite(self) -> None:
        async def exercise() -> None:
            composite = CompositeStrategy()
            composite.add_strategy(BreakoutStrategy())
            composite.add_strategy(EmaCrossStrategy())

            # Breakout conditions met
            ctx = StrategyContext(
                symbol="EUR/USD",
                price_position=0.95,
                volume_ratio=2.5,
                ema_fast=Decimal("1.1050"),
                ema_slow=Decimal("1.1000"),
                bid=Decimal("1.1050"),
                ask=Decimal("1.1052"),
            )
            result = await composite.evaluate("EUR/USD", ctx)
            assert result.total_strategies == 2
            assert result.executed_strategies >= 1

        asyncio.run(exercise())
