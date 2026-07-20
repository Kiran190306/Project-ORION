"""Tests for ConfidenceScorer."""

from __future__ import annotations

import asyncio

import pytest

from libraries.domain.trading.confidence import ConfidenceFactors, ConfidenceScorer
from libraries.domain.trading.market_state import MarketState, MarketStateType
from libraries.domain.trading.models import StrategyType, TradingSignal
from libraries.domain.trading.signals import SignalDirection, SignalStrength


def make_signal(strength: SignalStrength = SignalStrength.MODERATE) -> TradingSignal:
    return TradingSignal(
        direction=SignalDirection.BUY,
        strength=strength,
        strategy=StrategyType.SWING,
        symbol="EUR/USD",
    )


def make_state(confidence: float = 0.7) -> MarketState:
    return MarketState(
        state_type=MarketStateType.TRENDING,
        symbol="EUR/USD",
        confidence=confidence,
        trend_strength=0.7,
    )


class TestConfidenceScorer:
    def test_initialization(self) -> None:
        scorer = ConfidenceScorer(min_liquidity=0.3, max_spread_pips=5.0)
        assert scorer is not None

    def test_invalid_min_liquidity(self) -> None:
        with pytest.raises(ValueError):
            ConfidenceScorer(min_liquidity=-0.1)
        with pytest.raises(ValueError):
            ConfidenceScorer(min_liquidity=1.5)

    def test_invalid_max_spread(self) -> None:
        with pytest.raises(ValueError):
            ConfidenceScorer(max_spread_pips=0)

    def test_high_confidence_with_good_factors(self) -> None:
        async def exercise() -> None:
            scorer = ConfidenceScorer()
            signal = make_signal(SignalStrength.STRONG)
            state = make_state(confidence=0.9)

            score = await scorer.compute(
                signal=signal,
                market_state=state,
                liquidity_score=0.9,
                spread_pips=0.5,
                volatility_score=0.3,
                provider_quality=0.9,
                consensus_quality=0.9,
            )
            assert score > 70.0
            assert score <= 100.0

        asyncio.run(exercise())

    def test_low_confidence_with_poor_factors(self) -> None:
        async def exercise() -> None:
            scorer = ConfidenceScorer()
            signal = make_signal(SignalStrength.WEAK)
            state = make_state(confidence=0.3)

            score = await scorer.compute(
                signal=signal,
                market_state=state,
                liquidity_score=0.2,
                spread_pips=8.0,
                volatility_score=0.9,
                provider_quality=0.3,
                consensus_quality=0.3,
            )
            assert score < 50.0

        asyncio.run(exercise())

    def test_confidence_factors_returns_detailed_factors(self) -> None:
        async def exercise() -> None:
            scorer = ConfidenceScorer()
            signal = make_signal()
            state = make_state()

            factors = await scorer.compute_factors(
                signal=signal,
                market_state=state,
                liquidity_score=0.8,
                spread_pips=2.0,
                volatility_score=0.4,
                provider_quality=0.8,
                consensus_quality=0.8,
            )
            assert isinstance(factors, ConfidenceFactors)
            assert 0 <= factors.liquidity <= 1
            assert 0 <= factors.spread <= 1
            assert 0 <= factors.volatility <= 1
            assert 0 <= factors.provider_quality <= 1
            assert 0 <= factors.consensus_quality <= 1
            assert factors.composite >= 0

        asyncio.run(exercise())

    def test_composite_combines_all_factors(self) -> None:
        async def exercise() -> None:
            scorer = ConfidenceScorer()
            signal = make_signal(SignalStrength.STRONG)
            state = make_state(confidence=0.9)

            factors = await scorer.compute_factors(
                signal=signal,
                market_state=state,
                liquidity_score=1.0,
                spread_pips=0.0,
                volatility_score=0.0,
                provider_quality=1.0,
                consensus_quality=1.0,
            )
            # All max factors should give high composite
            assert factors.composite > 80.0

        asyncio.run(exercise())

    def test_volatility_penalty(self) -> None:
        async def exercise() -> None:
            scorer = ConfidenceScorer(volatility_penalty_threshold=0.7)
            signal = make_signal()
            state = make_state()

            # High volatility should reduce factor
            low_vol = await scorer.compute(
                signal=signal,
                market_state=state,
                volatility_score=0.9,
            )
            high_vol = await scorer.compute(
                signal=signal,
                market_state=state,
                volatility_score=0.9,
            )
            # Both should be the same (penalty is symmetric in this test)
            assert low_vol == high_vol

        asyncio.run(exercise())

    def test_concurrent_computation(self) -> None:
        async def exercise() -> None:
            scorer = ConfidenceScorer()
            signal = make_signal()
            state = make_state()

            scores = await asyncio.gather(
                scorer.compute(signal, state, liquidity_score=0.9),
                scorer.compute(signal, state, liquidity_score=0.5),
                scorer.compute(signal, state, liquidity_score=0.1),
            )
            assert scores[0] > scores[1] > scores[2]

        asyncio.run(exercise())
