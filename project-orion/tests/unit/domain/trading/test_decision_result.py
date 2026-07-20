"""Tests for TradeDecision and DecisionOutcome."""

from __future__ import annotations

from decimal import Decimal

from libraries.domain.trading.decision_result import DecisionOutcome, TradeDecision
from libraries.domain.trading.models import StrategyType, TradingSignal
from libraries.domain.trading.signals import SignalDirection, SignalStrength


class TestDecisionOutcome:
    def test_enum_values(self) -> None:
        assert DecisionOutcome.EXECUTE == "execute"
        assert DecisionOutcome.REJECT == "reject"
        assert DecisionOutcome.DEFER == "defer"

    def test_all_outcomes_covered(self) -> None:
        assert len(DecisionOutcome) == 3


class TestTradeDecision:
    def test_creates_execute_decision(self) -> None:
        signal = TradingSignal(
            direction=SignalDirection.BUY,
            strength=SignalStrength.STRONG,
            strategy=StrategyType.SWING,
            symbol="EUR/USD",
        )
        decision = TradeDecision(
            symbol="EUR/USD",
            outcome=DecisionOutcome.EXECUTE,
            direction=SignalDirection.BUY,
            confidence=80.0,
            strategy=StrategyType.SWING,
            entry_price=Decimal("1.1000"),
            stop_loss=Decimal("1.0900"),
            take_profit=Decimal("1.1200"),
            position_size=Decimal("10000"),
            risk_amount=Decimal("100"),
            account_risk_pct=1.0,
            reason="All checks passed",
            signal=signal,
            decision_id="DEC-001",
        )
        assert decision.is_executable
        assert not decision.is_rejected
        assert not decision.is_deferred
        assert decision.symbol == "EUR/USD"
        assert decision.direction == SignalDirection.BUY
        assert decision.entry_price == Decimal("1.1000")
        assert decision.position_size == Decimal("10000")

    def test_creates_reject_decision(self) -> None:
        decision = TradeDecision(
            symbol="EUR/USD",
            outcome=DecisionOutcome.REJECT,
            reason="Confidence too low",
            reject_reasons=["Confidence 20 below minimum 30"],
        )
        assert not decision.is_executable
        assert decision.is_rejected
        assert not decision.is_deferred
        assert len(decision.reject_reasons) == 1

    def test_creates_defer_decision(self) -> None:
        decision = TradeDecision(
            symbol="EUR/USD",
            outcome=DecisionOutcome.DEFER,
            reason="No signal generated",
        )
        assert not decision.is_executable
        assert not decision.is_rejected
        assert decision.is_deferred

    def test_decision_immutable(self) -> None:
        decision = TradeDecision(
            symbol="EUR/USD",
            outcome=DecisionOutcome.EXECUTE,
            direction=SignalDirection.BUY,
        )
        assert decision.symbol == "EUR/USD"
        assert decision.outcome == DecisionOutcome.EXECUTE
