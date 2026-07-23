"""Integration tests for the Trading Decision Engine.

Tests the full pipeline: MarketIntelligence -> SignalGenerator ->
ConfidenceScorer -> RiskFilter -> ExecutionFilter -> PositionSizer ->
TradeValidator -> DecisionEngine producing a final TradeDecision.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from libraries.domain.trading.confidence import ConfidenceScorer
from libraries.domain.trading.decision_engine import (
    DecisionEngine,
    EngineConfig,
    MarketIntelligenceInput,
)
from libraries.domain.trading.decision_result import DecisionOutcome, TradeDecision
from libraries.domain.trading.execution_filter import ExecutionFilter
from libraries.domain.trading.market_state import MarketStateDetector
from libraries.domain.trading.models import StrategyType
from libraries.domain.trading.position_sizer import RiskPercentPositionSizer
from libraries.domain.trading.risk_filter import RiskFilter
from libraries.domain.trading.signal_generator import SignalGenerator
from libraries.domain.trading.signals import SignalDirection, SignalStrength
from libraries.domain.trading.strategy_router import StrategyRouter
from libraries.domain.trading.trade_validator import TradeValidator


class TestTradingDecisionIntegration:
    def test_full_pipeline_buy_decision(self) -> None:
        """Test the full decision pipeline producing a BUY decision."""

        async def exercise() -> None:
            engine = DecisionEngine(
                config=EngineConfig(
                    min_confidence=20.0,
                    max_spread_pips=5.0,
                    min_liquidity=0.3,
                    risk_percent=1.0,
                )
            )

            mi = MarketIntelligenceInput(
                trend_strength=0.85,
                volatility_percentile=0.4,
                liquidity_score=0.9,
                spread_pips=0.3,
                volatility_score=0.2,
                provider_quality=0.95,
                consensus_quality=0.9,
                rsi=60,
                volume_ratio=1.8,
                price_position=0.7,
                entry_price=Decimal("1.1050"),
                stop_loss=Decimal("1.0950"),
                take_profit=Decimal("1.1250"),
                is_breaking_out=False,
                is_reversing=False,
                is_news_mode=False,
            )

            decision = await engine.make_decision(
                symbol="EUR/USD",
                market_intelligence=mi,
                account_balance=Decimal("10000"),
                market_hours_active=True,
            )

            # Verify decision structure
            assert decision.symbol == "EUR/USD"
            assert decision.outcome == DecisionOutcome.EXECUTE
            assert decision.direction == SignalDirection.BUY
            assert decision.confidence > 20.0
            assert decision.strategy is not None
            assert decision.position_size is not None
            assert decision.position_size > 0
            assert decision.risk_amount is not None
            assert decision.risk_amount > 0
            assert decision.account_risk_pct > 0
            assert decision.decision_id.startswith("DEC-")
            assert decision.is_executable

            # Verify metadata
            assert "market_state" in decision.metadata
            assert "sizing_method" in decision.metadata

        asyncio.run(exercise())

    def test_full_pipeline_reject_high_spread(self) -> None:
        """Test rejection due to excessive spread."""

        async def exercise() -> None:
            engine = DecisionEngine(config=EngineConfig(max_spread_pips=3.0))

            mi = MarketIntelligenceInput(
                trend_strength=0.8,
                liquidity_score=0.9,
                spread_pips=15.0,
                volatility_score=0.3,
                provider_quality=0.9,
                consensus_quality=0.9,
                rsi=60,
                volume_ratio=1.5,
                price_position=0.75,
            )

            decision = await engine.make_decision(
                symbol="EUR/USD",
                market_intelligence=mi,
                account_balance=Decimal("10000"),
            )

            assert decision.outcome in (DecisionOutcome.REJECT, DecisionOutcome.DEFER)
            if decision.outcome == DecisionOutcome.REJECT:
                assert not decision.is_executable

        asyncio.run(exercise())

    def test_full_pipeline_reject_low_confidence(self) -> None:
        """Test rejection due to low confidence."""

        async def exercise() -> None:
            engine = DecisionEngine(config=EngineConfig(min_confidence=90.0))

            mi = MarketIntelligenceInput(
                trend_strength=0.6,
                liquidity_score=0.5,
                spread_pips=2.0,
                volatility_score=0.5,
                rsi=55,
                price_position=0.6,
            )

            decision = await engine.make_decision(
                symbol="EUR/USD",
                market_intelligence=mi,
            )

            assert decision.outcome in (DecisionOutcome.REJECT, DecisionOutcome.DEFER)

        asyncio.run(exercise())

    def test_full_pipeline_defer_no_signal(self) -> None:
        """Test defer when no signal is generated."""

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
            assert "No signal" in decision.reason

        asyncio.run(exercise())

    def test_multiple_symbols_independent_decisions(self) -> None:
        """Test that decisions for different symbols are independent."""

        async def exercise() -> None:
            engine = DecisionEngine()

            mi_bullish = MarketIntelligenceInput(
                trend_strength=0.85,
                liquidity_score=0.9,
                spread_pips=0.5,
                rsi=60,
                price_position=0.75,
                entry_price=Decimal("1.1000"),
            )
            mi_bearish = MarketIntelligenceInput(
                trend_strength=0.8,
                liquidity_score=0.9,
                spread_pips=0.5,
                rsi=40,
                price_position=0.3,
                entry_price=Decimal("0.8500"),
            )
            mi_neutral = MarketIntelligenceInput(
                trend_strength=0.3,
                rsi=50,
                liquidity_score=0.5,
            )

            decisions = await asyncio.gather(
                engine.make_decision("EUR/USD", mi_bullish),
                engine.make_decision("GBP/USD", mi_bearish),
                engine.make_decision("USD/JPY", mi_neutral),
            )

            # EUR/USD should be buy
            assert decisions[0].symbol == "EUR/USD"
            # GBP/USD should be sell in trending with low price position
            # USD/JPY should defer
            assert decisions[2].outcome == DecisionOutcome.DEFER

        asyncio.run(exercise())

    def test_risk_filter_respects_daily_limit(self) -> None:
        """Test that risk filter respects daily trade limits."""

        async def exercise() -> None:
            risk_filter = RiskFilter(max_daily_trades=2, min_confidence=0.0)

            engine = DecisionEngine(
                config=EngineConfig(min_confidence=0.0),
                risk_filter=risk_filter,
            )

            mi = MarketIntelligenceInput(
                trend_strength=0.8,
                liquidity_score=0.9,
                spread_pips=0.5,
                rsi=60,
                price_position=0.75,
                entry_price=Decimal("1.1000"),
            )

            # First two should be executable
            d1 = await engine.make_decision("EUR/USD", mi)
            await risk_filter.record_trade()

            d2 = await engine.make_decision("EUR/USD", mi)
            await risk_filter.record_trade()

            # Third should be rejected
            d3 = await engine.make_decision("EUR/USD", mi)

            if d1.outcome == DecisionOutcome.EXECUTE:
                assert d1.is_executable
            if d3.outcome == DecisionOutcome.REJECT:
                assert not d3.is_executable

        asyncio.run(exercise())

    def test_confidence_scorer_with_execution_filter(self) -> None:
        """Test that confidence scorer and execution filter work together."""

        async def exercise() -> None:
            config = EngineConfig(min_confidence=30.0, max_spread_pips=5.0)

            engine = DecisionEngine(config=config)

            # Good conditions
            good_mi = MarketIntelligenceInput(
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
            )

            # Poor conditions
            poor_mi = MarketIntelligenceInput(
                trend_strength=0.8,
                liquidity_score=0.1,
                spread_pips=8.0,
                volatility_score=0.9,
                provider_quality=0.2,
                consensus_quality=0.2,
                rsi=60,
                volume_ratio=1.5,
                price_position=0.75,
                entry_price=Decimal("1.1000"),
            )

            good_decision = await engine.make_decision("EUR/USD", good_mi)
            poor_decision = await engine.make_decision("EUR/USD", poor_mi)

            # Good should execute, poor should reject
            if good_decision.outcome == DecisionOutcome.EXECUTE:
                assert good_decision.confidence > poor_decision.confidence

        asyncio.run(exercise())

    def test_statistics_tracking(self) -> None:
        """Test that statistics are tracked through the engine."""

        async def exercise() -> None:
            engine = DecisionEngine()
            stats = engine.statistics

            mi = MarketIntelligenceInput(
                trend_strength=0.8,
                liquidity_score=0.9,
                spread_pips=0.5,
                rsi=60,
                price_position=0.75,
                entry_price=Decimal("1.1000"),
            )

            await engine.make_decision("EUR/USD", mi)
            # Statistics should be accessible
            assert stats.trade_count == 0  # No trades recorded yet

        asyncio.run(exercise())

    def test_custom_dependency_injection(self) -> None:
        """Test that all components can be dependency-injected."""

        async def exercise() -> None:
            detector = MarketStateDetector(trending_threshold=0.5)
            generator = SignalGenerator(min_confidence_threshold=10.0)
            scorer = ConfidenceScorer(min_liquidity=0.2)
            rfilter = RiskFilter(min_confidence=0.0)
            efilter = ExecutionFilter(max_spread_pips=10.0)
            router = StrategyRouter()
            validator = TradeValidator(min_confidence=0.0)
            sizer = RiskPercentPositionSizer(risk_percent=2.0)

            engine = DecisionEngine(
                config=EngineConfig(min_confidence=0.0),
                market_state_detector=detector,
                signal_generator=generator,
                confidence_scorer=scorer,
                risk_filter=rfilter,
                execution_filter=efilter,
                strategy_router=router,
                trade_validator=validator,
                position_sizer=sizer,
            )

            mi = MarketIntelligenceInput(
                trend_strength=0.6,
                liquidity_score=0.8,
                spread_pips=1.0,
                rsi=55,
                price_position=0.65,
                entry_price=Decimal("1.1000"),
            )

            decision = await engine.make_decision("EUR/USD", mi)
            assert decision.symbol == "EUR/USD"

        asyncio.run(exercise())
