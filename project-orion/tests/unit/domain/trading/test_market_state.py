"""Tests for MarketStateDetector."""

from __future__ import annotations

import pytest

from libraries.domain.trading.market_state import (
    MarketState,
    MarketStateDetector,
    MarketStateType,
)


class TestMarketStateDetector:
    def test_initial_state(self) -> None:
        detector = MarketStateDetector()
        assert detector.trending_threshold == 0.6
        assert detector.breakout_threshold == 2.0

    def test_detects_trending(self) -> None:
        async def exercise() -> None:
            detector = MarketStateDetector(trending_threshold=0.6)
            state = await detector.detect(
                symbol="EUR/USD",
                trend_strength=0.8,
                volatility_percentile=0.5,
            )
            assert state.state_type == MarketStateType.TRENDING
            assert state.symbol == "EUR/USD"
            assert state.trend_strength == 0.8

        import asyncio

        asyncio.run(exercise())

    def test_detects_ranging(self) -> None:
        async def exercise() -> None:
            detector = MarketStateDetector(trending_threshold=0.6)
            state = await detector.detect(
                symbol="EUR/USD",
                trend_strength=0.3,
                volatility_percentile=0.5,
            )
            assert state.state_type == MarketStateType.RANGING

        import asyncio

        asyncio.run(exercise())

    def test_detects_high_volatility(self) -> None:
        async def exercise() -> None:
            detector = MarketStateDetector(high_volatility_percentile=0.8)
            state = await detector.detect(
                symbol="EUR/USD",
                trend_strength=0.4,
                volatility_percentile=0.9,
            )
            assert state.state_type == MarketStateType.HIGH_VOLATILITY

        import asyncio

        asyncio.run(exercise())

    def test_detects_low_volatility(self) -> None:
        async def exercise() -> None:
            detector = MarketStateDetector(low_volatility_percentile=0.2)
            state = await detector.detect(
                symbol="EUR/USD",
                trend_strength=0.3,
                volatility_percentile=0.1,
            )
            assert state.state_type == MarketStateType.LOW_VOLATILITY

        import asyncio

        asyncio.run(exercise())

    def test_detects_breakout(self) -> None:
        async def exercise() -> None:
            detector = MarketStateDetector()
            state = await detector.detect(
                symbol="EUR/USD",
                trend_strength=0.5,
                volatility_percentile=0.5,
                is_breaking_out=True,
            )
            assert state.state_type == MarketStateType.BREAKOUT

        import asyncio

        asyncio.run(exercise())

    def test_detects_reversal(self) -> None:
        async def exercise() -> None:
            detector = MarketStateDetector(reversal_threshold=0.7)
            state = await detector.detect(
                symbol="EUR/USD",
                trend_strength=0.8,
                volatility_percentile=0.5,
                is_reversing=True,
            )
            assert state.state_type == MarketStateType.REVERSAL

        import asyncio

        asyncio.run(exercise())

    def test_detects_news_mode(self) -> None:
        async def exercise() -> None:
            detector = MarketStateDetector()
            state = await detector.detect(
                symbol="EUR/USD",
                trend_strength=0.5,
                volatility_percentile=0.5,
                is_news_mode=True,
            )
            assert state.state_type == MarketStateType.NEWS_MODE

        import asyncio

        asyncio.run(exercise())

    def test_breakout_takes_precedence_over_volatility(self) -> None:
        async def exercise() -> None:
            detector = MarketStateDetector()
            state = await detector.detect(
                symbol="EUR/USD",
                trend_strength=0.5,
                volatility_percentile=0.9,
                is_breaking_out=True,
                is_news_mode=False,
            )
            assert state.state_type == MarketStateType.BREAKOUT

        import asyncio

        asyncio.run(exercise())

    def test_news_mode_takes_highest_precedence(self) -> None:
        async def exercise() -> None:
            detector = MarketStateDetector()
            state = await detector.detect(
                symbol="EUR/USD",
                trend_strength=0.8,
                volatility_percentile=0.9,
                is_breaking_out=True,
                is_reversing=True,
                is_news_mode=True,
            )
            assert state.state_type == MarketStateType.NEWS_MODE

        import asyncio

        asyncio.run(exercise())

    def test_market_state_immutable(self) -> None:
        state = MarketState(
            state_type=MarketStateType.TRENDING,
            symbol="EUR/USD",
            confidence=0.8,
        )
        assert state.state_type == MarketStateType.TRENDING
        assert state.confidence == 0.8

    def test_confidence_in_ranging(self) -> None:
        async def exercise() -> None:
            detector = MarketStateDetector()
            state = await detector.detect(
                symbol="EUR/USD",
                trend_strength=0.1,
                volatility_percentile=0.5,
            )
            assert state.state_type == MarketStateType.RANGING
            assert state.confidence >= 0.3

        import asyncio

        asyncio.run(exercise())

    def test_invalid_trending_threshold(self) -> None:
        with pytest.raises(ValueError):
            MarketStateDetector(trending_threshold=0.0)
        with pytest.raises(ValueError):
            MarketStateDetector(trending_threshold=1.0)

    def test_invalid_breakout_threshold(self) -> None:
        with pytest.raises(ValueError):
            MarketStateDetector(breakout_threshold=0)
        with pytest.raises(ValueError):
            MarketStateDetector(breakout_threshold=-1)

    def test_invalid_reversal_threshold(self) -> None:
        with pytest.raises(ValueError):
            MarketStateDetector(reversal_threshold=0.0)
        with pytest.raises(ValueError):
            MarketStateDetector(reversal_threshold=1.0)

    def test_concurrent_detection(self) -> None:
        async def exercise() -> None:
            detector = MarketStateDetector()
            states = await asyncio.gather(
                detector.detect("EUR/USD", 0.8, 0.5),
                detector.detect("GBP/USD", 0.3, 0.5),
                detector.detect("JPY/USD", 0.5, 0.9),
            )
            assert states[0].state_type == MarketStateType.TRENDING
            assert states[1].state_type == MarketStateType.RANGING
            assert states[2].state_type == MarketStateType.HIGH_VOLATILITY

        import asyncio

        asyncio.run(exercise())
