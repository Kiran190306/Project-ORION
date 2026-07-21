"""Base strategy implementation and built-in sample strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.strategies.context import StrategyContext
from libraries.domain.strategies.interfaces import (
    StrategyCapabilities,
    StrategyMetadata,
)
from libraries.domain.strategies.models import StrategyConfig, StrategyStatus
from libraries.domain.trading.signals import SignalDirection, SignalStrength


@dataclass(frozen=True, slots=True)
class StrategyResult:
    """Result produced by a strategy evaluation."""

    strategy_id: str
    symbol: str
    direction: SignalDirection
    confidence: float
    strength: SignalStrength
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
    price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None


class BaseStrategy:
    """Base class for strategy implementations.

    Provides common lifecycle management and property defaults.
    Subclasses override evaluate() with their specific logic.
    """

    def __init__(
        self,
        metadata: StrategyMetadata,
        capabilities: StrategyCapabilities,
        config: StrategyConfig | None = None,
    ) -> None:
        self._metadata = metadata
        self._capabilities = capabilities
        self._config = config or StrategyConfig()
        self._status: StrategyStatus = StrategyStatus.DRAFT
        self._initialized = False

    @property
    def id(self) -> str:
        return self._metadata.id

    @property
    def name(self) -> str:
        return self._metadata.name

    @property
    def metadata(self) -> StrategyMetadata:
        return self._metadata

    @property
    def capabilities(self) -> StrategyCapabilities:
        return self._capabilities

    @property
    def config(self) -> StrategyConfig:
        return self._config

    @property
    def status(self) -> StrategyStatus:
        return self._status

    @status.setter
    def status(self, value: StrategyStatus) -> None:
        self._status = value

    async def initialize(self) -> None:
        """Initialize the strategy. Called once before first use."""
        self._initialized = True
        self._status = StrategyStatus.ACTIVE

    async def evaluate(
        self,
        symbol: str,
        context: StrategyContext,
    ) -> StrategyResult | None:
        """Evaluate market conditions. Must be overridden by subclasses.

        Returns:
            StrategyResult if a signal is generated, None for HOLD.
        """
        raise NotImplementedError

    async def dispose(self) -> None:
        """Clean up resources."""
        self._status = StrategyStatus.STOPPED
        self._initialized = False

    def get_param(self, key: str, default: Any = None) -> Any:
        """Get a configuration parameter."""
        return self._config.params.get(key, default)


class EmaCrossStrategy(BaseStrategy):
    """Simple EMA crossover strategy.

    Generates BUY when fast EMA crosses above slow EMA,
    SELL when fast EMA crosses below slow EMA.
    """

    def __init__(self, config: StrategyConfig | None = None) -> None:
        super().__init__(
            metadata=StrategyMetadata(
                id="ema_cross",
                name="EMA Cross",
                version="1.0.0",
                description="EMA crossover strategy - BUY on fast>slow, SELL on fast<slow",
            ),
            capabilities=StrategyCapabilities(
                supported_markets=frozenset({"forex"}),
                supported_timeframes=frozenset({"M1", "M5", "M15", "H1", "H4", "D1"}),
                required_indicators=frozenset({"ema_fast", "ema_slow"}),
                required_market_state=frozenset({"trending"}),
            ),
            config=config,
        )

    async def evaluate(
        self,
        symbol: str,
        context: StrategyContext,
    ) -> StrategyResult | None:
        if context.ema_fast is None or context.ema_slow is None:
            return None

        fast = float(context.ema_fast)
        slow = float(context.ema_slow)

        if fast <= 0 or slow <= 0:
            return None

        ratio = fast / slow
        if ratio > 1.001:
            confidence = min(100.0, (ratio - 1.0) * 5000)
            strength = SignalStrength.STRONG if confidence > 70 else SignalStrength.MODERATE
            return StrategyResult(
                strategy_id=self.id,
                symbol=symbol,
                direction=SignalDirection.BUY,
                confidence=round(confidence, 2),
                strength=strength,
                price=context.bid,
            )
        elif ratio < 0.999:
            confidence = min(100.0, (1.0 - ratio) * 5000)
            strength = SignalStrength.STRONG if confidence > 70 else SignalStrength.MODERATE
            return StrategyResult(
                strategy_id=self.id,
                symbol=symbol,
                direction=SignalDirection.SELL,
                confidence=round(confidence, 2),
                strength=strength,
                price=context.ask,
            )

        return None


class RsiStrategy(BaseStrategy):
    """Simple RSI mean-reversion strategy.

    BUY when RSI is oversold (< 30).
    SELL when RSI is overbought (> 70).
    """

    def __init__(
        self,
        oversold_threshold: float = 30.0,
        overbought_threshold: float = 70.0,
        config: StrategyConfig | None = None,
    ) -> None:
        super().__init__(
            metadata=StrategyMetadata(
                id="rsi_strategy",
                name="RSI Mean Reversion",
                version="1.0.0",
                description="RSI-based mean reversion - BUY oversold, SELL overbought",
            ),
            capabilities=StrategyCapabilities(
                supported_markets=frozenset({"forex"}),
                supported_timeframes=frozenset({"M1", "M5", "M15", "H1", "H4", "D1"}),
                required_indicators=frozenset({"rsi"}),
                required_market_state=frozenset({"ranging", "low_volatility"}),
            ),
            config=config,
        )
        self._oversold = oversold_threshold
        self._overbought = overbought_threshold

    async def evaluate(
        self,
        symbol: str,
        context: StrategyContext,
    ) -> StrategyResult | None:
        if context.rsi is None:
            return None

        if context.rsi <= self._oversold:
            distance = (self._oversold - context.rsi) / self._oversold
            confidence = min(100.0, 50.0 + distance * 100)
            strength = SignalStrength.STRONG if confidence > 70 else SignalStrength.MODERATE
            return StrategyResult(
                strategy_id=self.id,
                symbol=symbol,
                direction=SignalDirection.BUY,
                confidence=round(confidence, 2),
                strength=strength,
                price=context.ask,
            )
        elif context.rsi >= self._overbought:
            distance = (context.rsi - self._overbought) / (100.0 - self._overbought)
            confidence = min(100.0, 50.0 + distance * 100)
            strength = SignalStrength.STRONG if confidence > 70 else SignalStrength.MODERATE
            return StrategyResult(
                strategy_id=self.id,
                symbol=symbol,
                direction=SignalDirection.SELL,
                confidence=round(confidence, 2),
                strength=strength,
                price=context.bid,
            )

        return None


class BreakoutStrategy(BaseStrategy):
    """Simple breakout strategy.

    BUY when price breaks above high-water mark (price_position > 0.8)
    with above-average volume.
    """

    def __init__(
        self,
        breakout_threshold: float = 0.8,
        volume_threshold: float = 1.5,
        config: StrategyConfig | None = None,
    ) -> None:
        super().__init__(
            metadata=StrategyMetadata(
                id="breakout_strategy",
                name="Breakout Strategy",
                version="1.0.0",
                description="Breakout strategy - BUY on price/volume breakout above threshold",
            ),
            capabilities=StrategyCapabilities(
                supported_markets=frozenset({"forex"}),
                supported_timeframes=frozenset({"M1", "M5", "M15", "H1"}),
                required_indicators=frozenset(),
                required_market_state=frozenset({"breakout", "trending"}),
            ),
            config=config,
        )
        self._breakout_threshold = breakout_threshold
        self._volume_threshold = volume_threshold

    async def evaluate(
        self,
        symbol: str,
        context: StrategyContext,
    ) -> StrategyResult | None:
        if (
            context.price_position >= self._breakout_threshold
            and context.volume_ratio >= self._volume_threshold
        ):
            confidence = min(
                100.0,
                50.0
                + (context.price_position - self._breakout_threshold) * 100
                + (context.volume_ratio - self._volume_threshold) * 20,
            )
            strength = SignalStrength.STRONG if confidence > 75 else SignalStrength.MODERATE
            return StrategyResult(
                strategy_id=self.id,
                symbol=symbol,
                direction=SignalDirection.BUY,
                confidence=round(confidence, 2),
                strength=strength,
                price=context.ask,
                metadata={
                    "breakout_level": context.price_position,
                    "volume_ratio": context.volume_ratio,
                },
            )

        return None
