"""Strategy router for the Trading Decision Engine.

Routes trading signals to the appropriate strategy based on market state.
Supports: Scalping, Swing, Trend Following, Mean Reversion, Breakout, News,
and future plug-in strategies.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from libraries.domain.trading.market_state import MarketState, MarketStateType
from libraries.domain.trading.models import StrategyType


@dataclass(frozen=True, slots=True)
class StrategyRouterConfig:
    """Configuration for strategy routing."""

    trending_strategy: StrategyType = StrategyType.TREND_FOLLOWING
    ranging_strategy: StrategyType = StrategyType.MEAN_REVERSION
    breakout_strategy: StrategyType = StrategyType.BREAKOUT
    reversal_strategy: StrategyType = StrategyType.TREND_FOLLOWING
    high_volatility_strategy: StrategyType = StrategyType.SCALPING
    low_volatility_strategy: StrategyType = StrategyType.SWING
    news_strategy: StrategyType = StrategyType.NEWS
    default_strategy: StrategyType = StrategyType.SWING


class StrategyRouter:
    """Routes signals to strategies based on market state.

    Thread-safe via asyncio.Lock. Supports plug-in strategies via
    custom strategy registry (future Sprint-2).
    """

    def __init__(self, config: StrategyRouterConfig | None = None) -> None:
        self._config = config or StrategyRouterConfig()
        self._lock = asyncio.Lock()
        self._plugin_strategies: dict[str, StrategyType] = {}

    @property
    def config(self) -> StrategyRouterConfig:
        return self._config

    async def route(self, market_state: MarketState) -> StrategyType:
        """Route to the appropriate strategy based on market state.

        Args:
            market_state: Current detected market state.

        Returns:
            StrategyType to use for this market condition.
        """
        async with self._lock:
            state_type = market_state.state_type

            mapping = {
                MarketStateType.TRENDING: self._config.trending_strategy,
                MarketStateType.RANGING: self._config.ranging_strategy,
                MarketStateType.BREAKOUT: self._config.breakout_strategy,
                MarketStateType.REVERSAL: self._config.reversal_strategy,
                MarketStateType.HIGH_VOLATILITY: self._config.high_volatility_strategy,
                MarketStateType.LOW_VOLATILITY: self._config.low_volatility_strategy,
                MarketStateType.NEWS_MODE: self._config.news_strategy,
            }

            return mapping.get(state_type, self._config.default_strategy)

    async def register_plugin_strategy(
        self, name: str, strategy: StrategyType, market_state: MarketStateType
    ) -> None:
        """Register a custom plugin strategy for a market state.

        This enables future extensibility without modifying core routing.
        """
        async with self._lock:
            self._plugin_strategies[name] = strategy

    async def get_plugin_strategies(self) -> dict[str, StrategyType]:
        """Return registered plugin strategies."""
        async with self._lock:
            return dict(self._plugin_strategies)
