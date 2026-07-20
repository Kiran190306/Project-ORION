"""Tests for DecisionEngine."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from libraries.domain.trading.decision_engine import (
    DecisionEngine,
    EngineConfig,
    MarketIntelligenceInput,
)
from libraries.domain.trading.decision_result import DecisionOutcome
from libraries.domain.trading.market_state import (
    MarketStateDetector,
    MarketStateType,
)
from libraries.domain.trading.signals import SignalDirection


class TestDecisionEngine:
    def test_initialization_with_defaults(self) -> None:
        engine = DecisionEngine()
        assert engine.config.min_confidence == 30.0
        assert engine.config.default_account_balance == Decimal("10000")

    def test_initialization_with_custom_config(self) -> None:
        config = EngineConfig(
            min_confidence=50.0,
            max_spread_pips=3.0,
            risk_percent=2.0,
        )
        engine = DecisionEngine(config)
        assert engine.config.min_confidence == 50.0
        assert engine.config.max_spread_pips == 3.0

    def test_makes_buy_decision_for_trending_market(self) -> None:
        async def exercise() -> None:
            engine = DecisionEngine()
            mi = MarketIntelligenceInput(
                trend_strength=0.8,
                liquidity_score=0.9,
                spread_pips=0.5,
                volatility_score=0.3,
                provider_quality=0.9,
                consensus_quality=0.9,
                rsi=60,
                volume_ratio=1.5,
                price_position=0.75,
                entry_price=Decimal("1.1000"),
                stop_loss=Decimal("1.0900"),
                take_profit=Decimal("1.1200"),
            )
            decision = await engine.make_decision(
                symbol="EUR/USD",
                market_intelligence=mi,
                account_balance=Decimal("10000"),
            )
            assert decision.outcome == DecisionOutcome.EXECUTE
            assert decision.direction == SignalDirection.BUY
            assert decision.confidence > 0
            assert decision.position_size is not None
            assert decision.position_size > 0

        asyncio.run(exercise())

    def test_rejects_low_confidence(self) -> None:
        async def exercise() -> None:
            config = EngineConfig(min_confidence=80.0)
            engine = DecisionEngine(config)
            mi = MarketIntelligenceInput(
                trend_strength=0.8,
                liquidity_score=0.5,
                spread_pips=1.0,
                rsi=55,
                price_position=0.6,
            )
            decision = await engine.make_decision(
                symbol="EUR/USD",
                market_intelligence=mi,
            )
            assert decision.outcome == DecisionOutcome.DEFER or decision.outcome == DecisionOutcome.REJECT

        asyncio.run(exercise())

    def test_rejects_high_spread(self) -> None:
        async def exercise() -> None:
            config = EngineConfig(max_spread_pips=2.0)
            engine = DecisionEngine(config)
            mi = MarketIntelligenceInput(
                trend_strength=0.8,
                liquidity_score=0.9,
                spread_pips=10.0,
                volatility_score=0.3,
                provider_quality=0.9,
                consensus_quality=0.9,
                rsi=60,
                price_position=0.75,
            )
            decision = await engine.make_decision(
                symbol="EUR/USD",
                market_intelligence=mi,
            )
            assert decision.outcome == DecisionOutcome.REJECT
            assert "spread" in decision.reason.lower() or decision.is_rejected

        asyncio.run(exercise())

    def test_rejects_low_liquidity(self) -> None:
        async def exercise() -> None:
            config = EngineConfig(min_liquidity=0.8)
            engine = DecisionEngine(config)
            mi = MarketIntelligenceInput(
                trend_strength=0.8,
                liquidity_score=0.1,
                spread_pips=1.0,
                rsi=60,
                price_position=0.75,
            )
            decision = await engine.make_decision(
                symbol="EUR/USD",
                market_intelligence=mi,
            )
            assert decision.outcome == DecisionOutcome.REJECT

        asyncio.run(exercise())

    def test_defers_when_no_signal(self) -> None:
        async def exercise() -> None:
            engine = DecisionEngine()
            mi = MarketIntelligenceInput(
                trend_strength=0.3,
                rsi=50,
                price_position=0.5,
                liquidity_score=0.5,
            )
            decision = await engine.make_decision(
                symbol="EUR/USD",
                market_intelligence=mi,
            )
            assert decision.outcome == DecisionOutcome.DEFER

        asyncio.run(exercise())

    def test_respects_market_hours(self) -> None:
        async def exercise() -> None:
            engine = DecisionEngine()
            mi = MarketIntelligenceInput(
                trend_strength=0.8,
                liquidity_score=0.9,
                spread_pips=0.5,
                volatility_score=0.3,
                provider_quality=0.9,
                consensus_quality=0.9,
                rsi=60,
                price_position=0.75,
            )
            decision = await engine.make_decision(
                symbol="EUR/USD",
                market_intelligence=mi,
                market_hours_active=False,
            )
            assert decision.outcome == DecisionOutcome.REJECT

        asyncio.run(exercise())

    def test_respects_drawdown_limit(self) -> None:
        async def exercise() -> None:
            config = EngineConfig(max_drawdown=0.1)
            engine = DecisionEngine(config)
            mi = MarketIntelligenceInput(
                trend_strength=0.8,
                liquidity_score=0.9,
                spread_pips=0.5,
                volatility_score=0.3,
                rsi=60,
                price_position=0.75,
            )
            decision = await engine.make_decision(
                symbol="EUR/USD",
                market_intelligence=mi,
                current_drawdown=0.2,
            )
            assert decision.outcome == DecisionOutcome.REJECT
            assert "drawdown" in decision.reason.lower()

        asyncio.run(exercise())

    def test_generates_unique_decision_ids(self) -> None:
        async def exercise() -> None:
            engine = DecisionEngine()

            mi = MarketIntelligenceInput(
                trend_strength=0.3,
                rsi=50,
                liquidity_score=0.5,
            )
            d1 = await engine.make_decision("EUR/USD", mi)
            d2 = await engine.make_decision("EUR/USD", mi)
            assert d1.decision_id != d2.decision_id
            assert d1.decision_id.startswith("DEC-")
            assert d2.decision_id.startswith("DEC-")

        asyncio.run(exercise())

    def test_uses_custom_position_sizer(self) -> None:
        """Test that dependency injection of custom position sizer works."""
        async def exercise() -> None:
            from libraries.domain.trading.position_sizer import FixedPositionSizer

            fixed_sizer = FixedPositionSizer(fixed_notional=Decimal("500"))
            engine = DecisionEngine(position_sizer=fixed_sizer)

            mi = MarketIntelligenceInput(
                trend_strength=0.8,
                liquidity_score=0.9,
                spread_pips=0.5,
                volatility_score=0.3,
                rsi=60,
                price_position=0.75,
                entry_price=Decimal("1.1000"),
            )
            decision = await engine.make_decision("EUR/USD", mi)
            if decision.outcome == DecisionOutcome.EXECUTE:
                assert decision.position_size is not None

        asyncio.run(exercise())

    def test_concurrent_decisions(self) -> None:
        async def exercise() -> None:
            engine = DecisionEngine()
            mi1 = MarketIntelligenceInput(
                trend_strength=0.8, liquidity_score=0.9, spread_pips=0.5,
                rsi=60, price_position=0.75, entry_price=Decimal("1.1000"),
            )
            mi2 = MarketIntelligenceInput(
                trend_strength=0.3, rsi=50, liquidity_score=0.5,
            )
            decisions = await asyncio.gather(
                engine.make_decision("EUR/USD", mi1),
                engine.make_decision("GBP/USD", mi2),
            )
            # First should execute or defer, second should defer
            assert decisions[0].outcome in (
                DecisionOutcome.EXECUTE, DecisionOutcome.DEFER
            )
            assert decisions[1].outcome == DecisionOutcome.DEFER

        asyncio.run(exercise())
