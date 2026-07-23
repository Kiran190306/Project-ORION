"""Tests for ExecutionFilter."""

from __future__ import annotations

import asyncio

import pytest

from libraries.domain.trading.execution_filter import ExecutionFilter, ExecutionFilterResult
from libraries.domain.trading.market_state import MarketState, MarketStateType
from libraries.domain.trading.models import StrategyType, TradingSignal
from libraries.domain.trading.signals import SignalDirection, SignalStrength


def make_signal() -> TradingSignal:
    return TradingSignal(
        direction=SignalDirection.BUY,
        strength=SignalStrength.STRONG,
        strategy=StrategyType.SWING,
        symbol="EUR/USD",
    )


def make_state(state_type: MarketStateType = MarketStateType.TRENDING) -> MarketState:
    return MarketState(
        state_type=state_type,
        symbol="EUR/USD",
        confidence=0.7,
    )


class TestExecutionFilter:
    def test_initialization(self) -> None:
        ef = ExecutionFilter(max_spread_pips=5.0, min_liquidity=0.2, max_volatility=0.9)
        assert ef.max_spread_pips == 5.0
        assert ef.min_liquidity == 0.2
        assert ef.max_volatility == 0.9

    def test_invalid_params(self) -> None:
        with pytest.raises(ValueError):
            ExecutionFilter(max_spread_pips=0)
        with pytest.raises(ValueError):
            ExecutionFilter(min_liquidity=-0.1)
        with pytest.raises(ValueError):
            ExecutionFilter(min_liquidity=1.5)
        with pytest.raises(ValueError):
            ExecutionFilter(max_volatility=-0.1)
        with pytest.raises(ValueError):
            ExecutionFilter(max_volatility=1.5)

    def test_allows_execution_when_all_checks_pass(self) -> None:
        async def exercise() -> None:
            ef = ExecutionFilter(max_spread_pips=5.0)
            result = await ef.check(
                signal=make_signal(),
                market_state=make_state(),
                spread_pips=1.0,
                liquidity_score=0.8,
                volatility_score=0.3,
                market_hours_active=True,
            )
            assert result.is_allowed
            assert result.spread_ok
            assert result.liquidity_ok
            assert result.volatility_ok
            assert result.market_hours_ok

        asyncio.run(exercise())

    def test_rejects_excessive_spread(self) -> None:
        async def exercise() -> None:
            ef = ExecutionFilter(max_spread_pips=3.0)
            result = await ef.check(
                signal=make_signal(),
                market_state=make_state(),
                spread_pips=10.0,
                liquidity_score=0.8,
                volatility_score=0.3,
            )
            assert not result.is_allowed
            assert not result.spread_ok
            assert "spread" in result.reason.lower()

        asyncio.run(exercise())

    def test_rejects_low_liquidity(self) -> None:
        async def exercise() -> None:
            ef = ExecutionFilter(min_liquidity=0.5)
            result = await ef.check(
                signal=make_signal(),
                market_state=make_state(),
                spread_pips=1.0,
                liquidity_score=0.1,
                volatility_score=0.3,
            )
            assert not result.is_allowed
            assert not result.liquidity_ok
            assert "liquidity" in result.reason.lower()

        asyncio.run(exercise())

    def test_rejects_high_volatility(self) -> None:
        async def exercise() -> None:
            ef = ExecutionFilter(max_volatility=0.5)
            result = await ef.check(
                signal=make_signal(),
                market_state=make_state(),
                spread_pips=1.0,
                liquidity_score=0.8,
                volatility_score=0.9,
            )
            assert not result.is_allowed
            assert not result.volatility_ok
            assert "volatility" in result.reason.lower()

        asyncio.run(exercise())

    def test_rejects_closed_market(self) -> None:
        async def exercise() -> None:
            ef = ExecutionFilter(check_market_hours=True)
            result = await ef.check(
                signal=make_signal(),
                market_state=make_state(),
                spread_pips=1.0,
                liquidity_score=0.8,
                volatility_score=0.3,
                market_hours_active=False,
            )
            assert not result.is_allowed
            assert not result.market_hours_ok

        asyncio.run(exercise())

    def test_blocks_news_mode(self) -> None:
        async def exercise() -> None:
            ef = ExecutionFilter()
            result = await ef.check(
                signal=make_signal(),
                market_state=make_state(MarketStateType.NEWS_MODE),
                spread_pips=1.0,
                liquidity_score=0.8,
                volatility_score=0.3,
            )
            assert not result.is_allowed
            assert "news" in result.reason.lower()

        asyncio.run(exercise())

    def test_execution_filter_result_immutable(self) -> None:
        result = ExecutionFilterResult(
            allowed=True,
            reason="All good",
            spread_ok=True,
            liquidity_ok=True,
            volatility_ok=True,
            market_hours_ok=True,
        )
        assert result.is_allowed
        assert result.spread_ok
        assert result.liquidity_ok

    def test_concurrent_checks(self) -> None:
        async def exercise() -> None:
            ef = ExecutionFilter()
            state = make_state()
            signal = make_signal()

            results = await asyncio.gather(
                ef.check(signal, state, spread_pips=1.0, liquidity_score=0.8, volatility_score=0.3),
                ef.check(
                    signal, state, spread_pips=10.0, liquidity_score=0.8, volatility_score=0.3
                ),
                ef.check(signal, state, spread_pips=1.0, liquidity_score=0.1, volatility_score=0.3),
            )
            assert results[0].is_allowed
            assert not results[1].is_allowed
            assert not results[2].is_allowed

        asyncio.run(exercise())
