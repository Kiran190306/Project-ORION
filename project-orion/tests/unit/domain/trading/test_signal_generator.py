"""Tests for SignalGenerator."""

from __future__ import annotations

import asyncio

import pytest

from libraries.domain.trading.market_state import (
    MarketState,
    MarketStateDetector,
    MarketStateType,
)
from libraries.domain.trading.models import StrategyType
from libraries.domain.trading.signal_generator import SignalGenerator
from libraries.domain.trading.signals import SignalDirection, SignalStrength


class TestSignalGenerator:
    def test_initialization(self) -> None:
        gen = SignalGenerator(min_confidence_threshold=30.0)
        assert gen.min_confidence_threshold == 30.0

    def test_invalid_threshold(self) -> None:
        with pytest.raises(ValueError):
            SignalGenerator(min_confidence_threshold=-1)
        with pytest.raises(ValueError):
            SignalGenerator(min_confidence_threshold=101)

    def test_generates_buy_in_trending(self) -> None:
        async def exercise() -> None:
            gen = SignalGenerator(min_confidence_threshold=10.0)
            detector = MarketStateDetector()
            state = await detector.detect("EUR/USD", trend_strength=0.8, volatility_percentile=0.5)

            signal = await gen.generate(
                symbol="EUR/USD",
                market_state=state,
                strategy=StrategyType.TREND_FOLLOWING,
                trend_strength=0.8,
                rsi=60,
                price_position=0.7,
            )
            assert signal is not None
            assert signal.direction == SignalDirection.BUY
            assert signal.symbol == "EUR/USD"

        asyncio.run(exercise())

    def test_generates_sell_in_trending(self) -> None:
        async def exercise() -> None:
            gen = SignalGenerator(min_confidence_threshold=10.0)
            detector = MarketStateDetector()
            state = await detector.detect("EUR/USD", trend_strength=0.8, volatility_percentile=0.5)

            signal = await gen.generate(
                symbol="EUR/USD",
                market_state=state,
                strategy=StrategyType.TREND_FOLLOWING,
                trend_strength=0.8,
                rsi=40,
                price_position=0.3,
            )
            assert signal is not None
            assert signal.direction == SignalDirection.SELL

        asyncio.run(exercise())

    def test_hold_in_news_mode(self) -> None:
        async def exercise() -> None:
            gen = SignalGenerator(min_confidence_threshold=10.0)
            detector = MarketStateDetector()
            state = await detector.detect(
                "EUR/USD", trend_strength=0.8, volatility_percentile=0.5, is_news_mode=True
            )

            signal = await gen.generate(
                symbol="EUR/USD",
                market_state=state,
                strategy=StrategyType.NEWS,
                trend_strength=0.8,
            )
            assert signal is None  # HOLD returns None

        asyncio.run(exercise())

    def test_mean_reversion_in_ranging(self) -> None:
        async def exercise() -> None:
            gen = SignalGenerator(min_confidence_threshold=10.0)
            detector = MarketStateDetector()
            state = await detector.detect("EUR/USD", trend_strength=0.3, volatility_percentile=0.5)

            # Oversold in range -> BUY
            signal = await gen.generate(
                symbol="EUR/USD",
                market_state=state,
                strategy=StrategyType.MEAN_REVERSION,
                trend_strength=0.3,
                rsi=25,
                price_position=0.2,
            )
            assert signal is not None
            assert signal.direction == SignalDirection.BUY

        asyncio.run(exercise())

    def test_no_signal_low_confidence(self) -> None:
        async def exercise() -> None:
            gen = SignalGenerator(min_confidence_threshold=90.0)
            detector = MarketStateDetector()
            state = await detector.detect("EUR/USD", trend_strength=0.8, volatility_percentile=0.5)

            signal = await gen.generate(
                symbol="EUR/USD",
                market_state=state,
                strategy=StrategyType.TREND_FOLLOWING,
                trend_strength=0.8,
                rsi=55,
                price_position=0.6,
            )
            # Should be HOLD because confidence is below threshold
            assert signal is None

        asyncio.run(exercise())

    def test_breakout_signal_with_volume(self) -> None:
        async def exercise() -> None:
            gen = SignalGenerator(min_confidence_threshold=10.0)
            detector = MarketStateDetector()
            state = await detector.detect(
                "EUR/USD", trend_strength=0.6, volatility_percentile=0.7, is_breaking_out=True
            )

            signal = await gen.generate(
                symbol="EUR/USD",
                market_state=state,
                strategy=StrategyType.BREAKOUT,
                trend_strength=0.6,
                volume_ratio=2.0,
                price_position=0.9,
            )
            assert signal is not None
            assert signal.direction == SignalDirection.BUY

        asyncio.run(exercise())

    def test_low_volatility_scale_in(self) -> None:
        async def exercise() -> None:
            gen = SignalGenerator(min_confidence_threshold=10.0)
            detector = MarketStateDetector(low_volatility_percentile=0.2)
            state = await detector.detect("EUR/USD", trend_strength=0.3, volatility_percentile=0.1)

            signal = await gen.generate(
                symbol="EUR/USD",
                market_state=state,
                strategy=StrategyType.SWING,
                trend_strength=0.3,
                volume_ratio=1.5,
                price_position=0.9,
            )
            assert signal is not None
            assert signal.direction == SignalDirection.SCALE_IN

        asyncio.run(exercise())

    def test_high_volatility_cautious_buy(self) -> None:
        async def exercise() -> None:
            gen = SignalGenerator(min_confidence_threshold=10.0)
            detector = MarketStateDetector(high_volatility_percentile=0.8)
            state = await detector.detect("EUR/USD", trend_strength=0.4, volatility_percentile=0.9)

            signal = await gen.generate(
                symbol="EUR/USD",
                market_state=state,
                strategy=StrategyType.SCALPING,
                trend_strength=0.4,
                rsi=20,
                price_position=0.1,
            )
            assert signal is not None
            assert signal.direction == SignalDirection.BUY

        asyncio.run(exercise())

    def test_concurrent_signal_generation(self) -> None:
        async def exercise() -> None:
            gen = SignalGenerator(min_confidence_threshold=10.0)
            detector = MarketStateDetector()

            state1 = await detector.detect("EUR/USD", 0.8, 0.5)
            state2 = await detector.detect("GBP/USD", 0.3, 0.5)

            signals = await asyncio.gather(
                gen.generate("EUR/USD", state1, StrategyType.TREND_FOLLOWING, trend_strength=0.8, price_position=0.7),
                gen.generate("GBP/USD", state2, StrategyType.MEAN_REVERSION, trend_strength=0.3, rsi=25, price_position=0.2),
            )

            assert signals[0] is not None
            assert signals[0].direction == SignalDirection.BUY
            assert signals[1] is not None
            assert signals[1].direction == SignalDirection.BUY

        asyncio.run(exercise())

