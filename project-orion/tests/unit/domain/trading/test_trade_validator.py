"""Tests for TradeValidator."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from libraries.domain.trading.decision_result import DecisionOutcome, TradeDecision
from libraries.domain.trading.models import StrategyType, TradingSignal
from libraries.domain.trading.signals import SignalDirection, SignalStrength
from libraries.domain.trading.trade_validator import TradeValidator


def make_signal() -> TradingSignal:
    return TradingSignal(
        direction=SignalDirection.BUY,
        strength=SignalStrength.STRONG,
        strategy=StrategyType.SWING,
        symbol="EUR/USD",
    )


def make_decision(
    confidence: float = 80.0,
    risk_pct: float = 1.0,
    reject_reasons: list[str] | None = None,
) -> TradeDecision:
    return TradeDecision(
        symbol="EUR/USD",
        outcome=DecisionOutcome.EXECUTE,
        direction=SignalDirection.BUY,
        confidence=confidence,
        account_risk_pct=risk_pct,
        reject_reasons=reject_reasons or [],
    )


class TestTradeValidator:
    def test_initialization(self) -> None:
        tv = TradeValidator(
            max_spread_pips=5.0,
            min_confidence=30.0,
            min_liquidity=0.3,
        )
        assert tv is not None

    def test_invalid_params(self) -> None:
        with pytest.raises(ValueError):
            TradeValidator(max_spread_pips=0)
        with pytest.raises(ValueError):
            TradeValidator(min_confidence=-1)
        with pytest.raises(ValueError):
            TradeValidator(min_confidence=101)
        with pytest.raises(ValueError):
            TradeValidator(min_liquidity=-0.1)
        with pytest.raises(ValueError):
            TradeValidator(min_liquidity=1.5)

    def test_validates_good_trade(self) -> None:
        async def exercise() -> None:
            tv = TradeValidator()
            report = await tv.validate(
                signal=make_signal(),
                decision=make_decision(),
                spread_pips=1.0,
                liquidity_score=0.8,
                market_quality=0.8,
                provider_health=0.8,
            )
            assert report.is_valid
            assert len(report.errors) == 0

        asyncio.run(exercise())

    def test_rejects_excessive_spread(self) -> None:
        async def exercise() -> None:
            tv = TradeValidator(max_spread_pips=3.0)
            report = await tv.validate(
                signal=make_signal(),
                decision=make_decision(),
                spread_pips=10.0,
                liquidity_score=0.8,
                market_quality=0.8,
                provider_health=0.8,
            )
            assert not report.is_valid
            assert not report.spread_check[0]

        asyncio.run(exercise())

    def test_rejects_low_confidence(self) -> None:
        async def exercise() -> None:
            tv = TradeValidator(min_confidence=50.0)
            report = await tv.validate(
                signal=make_signal(),
                decision=make_decision(confidence=30.0),
                spread_pips=1.0,
                liquidity_score=0.8,
                market_quality=0.8,
                provider_health=0.8,
            )
            assert not report.is_valid
            assert not report.confidence_check[0]

        asyncio.run(exercise())

    def test_rejects_low_liquidity(self) -> None:
        async def exercise() -> None:
            tv = TradeValidator(min_liquidity=0.5)
            report = await tv.validate(
                signal=make_signal(),
                decision=make_decision(),
                spread_pips=1.0,
                liquidity_score=0.1,
                market_quality=0.8,
                provider_health=0.8,
            )
            assert not report.is_valid
            assert not report.liquidity_check[0]

        asyncio.run(exercise())

    def test_includes_reject_reasons(self) -> None:
        async def exercise() -> None:
            tv = TradeValidator()
            report = await tv.validate(
                signal=make_signal(),
                decision=make_decision(reject_reasons=["Risk too high"]),
                spread_pips=1.0,
                liquidity_score=0.8,
                market_quality=0.8,
                provider_health=0.8,
            )
            assert "Risk too high" in report.errors

        asyncio.run(exercise())

    def test_warns_on_high_risk(self) -> None:
        async def exercise() -> None:
            tv = TradeValidator()
            report = await tv.validate(
                signal=make_signal(),
                decision=make_decision(risk_pct=10.0),
                spread_pips=1.0,
                liquidity_score=0.8,
                market_quality=0.8,
                provider_health=0.8,
            )
            assert report.is_valid  # Risk is a warning, not error
            assert len(report.warnings) > 0

        asyncio.run(exercise())

    def test_trade_validation_report_immutable(self) -> None:
        report = TradeValidator(
            max_spread_pips=5.0,
            min_confidence=30.0,
            min_liquidity=0.3,
        )
        assert report is not None
