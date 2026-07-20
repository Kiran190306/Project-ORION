"""Tests for StrategyRouter."""

from __future__ import annotations

import asyncio

import pytest

from libraries.domain.trading.market_state import MarketState, MarketStateType
from libraries.domain.trading.models import StrategyType
from libraries.domain.trading.strategy_router import StrategyRouter, StrategyRouterConfig


def make_state(state_type: MarketStateType) -> MarketState:
    return MarketState(
        state_type=state_type,
        symbol="EUR/USD",
        confidence=0.7,
    )


class TestStrategyRouter:
    def test_default_config(self) -> None:
        router = StrategyRouter()
        assert router.config.trending_strategy == StrategyType.TREND_FOLLOWING
        assert router.config.ranging_strategy == StrategyType.MEAN_REVERSION
        assert router.config.breakout_strategy == StrategyType.BREAKOUT
        assert router.config.default_strategy == StrategyType.SWING

    def test_custom_config(self) -> None:
        config = StrategyRouterConfig(
            trending_strategy=StrategyType.SCALPING,
            ranging_strategy=StrategyType.SWING,
        )
        router = StrategyRouter(config)
        assert router.config.trending_strategy == StrategyType.SCALPING
        assert router.config.ranging_strategy == StrategyType.SWING

    def test_routes_trending_to_trend_following(self) -> None:
        async def exercise() -> None:
            router = StrategyRouter()
            strategy = await router.route(make_state(MarketStateType.TRENDING))
            assert strategy == StrategyType.TREND_FOLLOWING

        asyncio.run(exercise())

    def test_routes_ranging_to_mean_reversion(self) -> None:
        async def exercise() -> None:
            router = StrategyRouter()
            strategy = await router.route(make_state(MarketStateType.RANGING))
            assert strategy == StrategyType.MEAN_REVERSION

        asyncio.run(exercise())

    def test_routes_breakout_to_breakout(self) -> None:
        async def exercise() -> None:
            router = StrategyRouter()
            strategy = await router.route(make_state(MarketStateType.BREAKOUT))
            assert strategy == StrategyType.BREAKOUT

        asyncio.run(exercise())

    def test_routes_reversal_to_trend_following(self) -> None:
        async def exercise() -> None:
            router = StrategyRouter()
            strategy = await router.route(make_state(MarketStateType.REVERSAL))
            assert strategy == StrategyType.TREND_FOLLOWING

        asyncio.run(exercise())

    def test_routes_high_volatility_to_scalping(self) -> None:
        async def exercise() -> None:
            router = StrategyRouter()
            strategy = await router.route(make_state(MarketStateType.HIGH_VOLATILITY))
            assert strategy == StrategyType.SCALPING

        asyncio.run(exercise())

    def test_routes_low_volatility_to_swing(self) -> None:
        async def exercise() -> None:
            router = StrategyRouter()
            strategy = await router.route(make_state(MarketStateType.LOW_VOLATILITY))
            assert strategy == StrategyType.SWING

        asyncio.run(exercise())

    def test_routes_news_to_news(self) -> None:
        async def exercise() -> None:
            router = StrategyRouter()
            strategy = await router.route(make_state(MarketStateType.NEWS_MODE))
            assert strategy == StrategyType.NEWS

        asyncio.run(exercise())

    def test_plugin_strategy_registration(self) -> None:
        async def exercise() -> None:
            router = StrategyRouter()
            await router.register_plugin_strategy(
                "custom_momentum", StrategyType.TREND_FOLLOWING, MarketStateType.TRENDING
            )
            plugins = await router.get_plugin_strategies()
            assert "custom_momentum" in plugins
            assert plugins["custom_momentum"] == StrategyType.TREND_FOLLOWING

        asyncio.run(exercise())

    def test_concurrent_routing(self) -> None:
        async def exercise() -> None:
            router = StrategyRouter()
            states = [
                make_state(MarketStateType.TRENDING),
                make_state(MarketStateType.RANGING),
                make_state(MarketStateType.BREAKOUT),
                make_state(MarketStateType.NEWS_MODE),
            ]
            strategies = await asyncio.gather(*[router.route(s) for s in states])
            assert strategies[0] == StrategyType.TREND_FOLLOWING
            assert strategies[1] == StrategyType.MEAN_REVERSION
            assert strategies[2] == StrategyType.BREAKOUT
            assert strategies[3] == StrategyType.NEWS

        asyncio.run(exercise())
