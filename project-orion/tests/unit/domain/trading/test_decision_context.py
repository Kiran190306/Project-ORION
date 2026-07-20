"""Tests for DecisionContext."""

from __future__ import annotations

from decimal import Decimal

from libraries.domain.trading.decision_context import DecisionContext
from libraries.domain.trading.market_state import MarketState, MarketStateType
from libraries.domain.trading.models import StrategyType, TradingSignal
from libraries.domain.trading.signals import SignalDirection, SignalStrength


class TestDecisionContext:
    def test_creates_with_defaults(self) -> None:
        ctx = DecisionContext(symbol="EUR/USD")
        assert ctx.symbol == "EUR/USD"
        assert ctx.confidence_score == 0.0
        assert not ctx.is_ready

    def test_is_ready_when_all_inputs_present(self) -> None:
        signal = TradingSignal(
            direction=SignalDirection.BUY,
            strength=SignalStrength.STRONG,
            strategy=StrategyType.SWING,
            symbol="EUR/USD",
            confidence_score=80.0,
        )
        state = MarketState(
            state_type=MarketStateType.TRENDING,
            symbol="EUR/USD",
            confidence=0.8,
        )
        ctx = DecisionContext(
            symbol="EUR/USD",
            signal=signal,
            market_state=state,
            confidence_score=80.0,
            risk_allowed=True,
            execution_allowed=True,
        )
        assert ctx.is_ready

    def test_not_ready_without_signal(self) -> None:
        ctx = DecisionContext(symbol="EUR/USD", confidence_score=80.0)
        assert not ctx.is_ready

    def test_not_ready_with_risk_blocked(self) -> None:
        signal = TradingSignal(
            direction=SignalDirection.BUY,
            strength=SignalStrength.STRONG,
            strategy=StrategyType.SWING,
            symbol="EUR/USD",
        )
        state = MarketState(
            state_type=MarketStateType.TRENDING, symbol="EUR/USD", confidence=0.8
        )
        ctx = DecisionContext(
            symbol="EUR/USD",
            signal=signal,
            market_state=state,
            confidence_score=80.0,
            risk_allowed=False,
            risk_reason="Max drawdown exceeded",
        )
        assert not ctx.is_ready

    def test_not_ready_with_validation_errors(self) -> None:
        signal = TradingSignal(
            direction=SignalDirection.BUY,
            strength=SignalStrength.STRONG,
            strategy=StrategyType.SWING,
            symbol="EUR/USD",
        )
        ctx = DecisionContext(
            symbol="EUR/USD",
            signal=signal,
            confidence_score=80.0,
            risk_allowed=True,
            execution_allowed=True,
            validation_errors=["Spread too wide"],
        )
        assert not ctx.is_ready

    def test_signal_direction(self) -> None:
        signal = TradingSignal(
            direction=SignalDirection.SELL,
            strength=SignalStrength.MODERATE,
            strategy=StrategyType.SWING,
            symbol="EUR/USD",
        )
        ctx = DecisionContext(symbol="EUR/USD", signal=signal)
        assert ctx.signal_direction == SignalDirection.SELL

    def test_signal_direction_none(self) -> None:
        ctx = DecisionContext(symbol="EUR/USD")
        assert ctx.signal_direction is None

    def test_composite_quality(self) -> None:
        ctx = DecisionContext(
            symbol="EUR/USD",
            liquidity_score=0.8,
            spread_pips=2.0,
            consensus_quality=0.7,
            provider_health=0.9,
            confidence_score=80.0,
        )
        quality = ctx.composite_quality
        assert 0 <= quality <= 1

    def test_composite_quality_with_market_state(self) -> None:
        state = MarketState(
            state_type=MarketStateType.TRENDING, symbol="EUR/USD", confidence=0.9
        )
        ctx = DecisionContext(
            symbol="EUR/USD",
            market_state=state,
            liquidity_score=0.8,
            spread_pips=2.0,
            consensus_quality=0.7,
            provider_health=0.9,
            confidence_score=80.0,
        )
        quality = ctx.composite_quality
        assert quality > 0.5
