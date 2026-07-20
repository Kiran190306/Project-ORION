"""Decision Engine - composition root for the Trading Decision Engine.

Combines Market Intelligence, Signal Engine, Risk Filter, Execution Filter,
and Position Sizing to produce a single decision per symbol.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.trading.confidence import ConfidenceScorer
from libraries.domain.trading.decision_context import DecisionContext
from libraries.domain.trading.decision_result import DecisionOutcome, TradeDecision
from libraries.domain.trading.execution_filter import ExecutionFilter
from libraries.domain.trading.market_state import MarketState, MarketStateDetector
from libraries.domain.trading.models import StrategyType, TradingSignal
from libraries.domain.trading.position_sizer import (
    ATRPositionSizer,
    FixedPositionSizer,
    KellyPositionSizer,
    PositionSizer,
    RiskPercentPositionSizer,
    VolatilityBasedPositionSizer,
)
from libraries.domain.trading.risk_filter import RiskFilter
from libraries.domain.trading.signal_generator import SignalGenerator
from libraries.domain.trading.signals import SignalDirection
from libraries.domain.trading.statistics import TradeStatistics
from libraries.domain.trading.strategy_router import StrategyRouter, StrategyRouterConfig
from libraries.domain.trading.trade_validator import TradeValidator


@dataclass(frozen=True, slots=True)
class EngineConfig:
    """Configuration for the Decision Engine."""

    min_confidence: float = 30.0
    max_spread_pips: float = 5.0
    min_liquidity: float = 0.3
    default_account_balance: Decimal = Decimal("10000")
    position_sizing_method: str = "risk_percent"
    risk_percent: float = 1.0
    max_position_size: float = 0.1
    max_daily_trades: int = 10
    max_drawdown: float = 0.2
    enable_news_block: bool = True
    generate_decision_id: bool = True


class DecisionEngine:
    """Composition root for the Trading Decision Engine.

    Wires together all components and produces a single trade decision
    per symbol. Thread-safe via asyncio.Lock.

    Supports dependency injection of all components for testing.
    """

    def __init__(
        self,
        config: EngineConfig | None = None,
        market_state_detector: MarketStateDetector | None = None,
        signal_generator: SignalGenerator | None = None,
        confidence_scorer: ConfidenceScorer | None = None,
        risk_filter: RiskFilter | None = None,
        execution_filter: ExecutionFilter | None = None,
        strategy_router: StrategyRouter | None = None,
        trade_validator: TradeValidator | None = None,
        position_sizer: PositionSizer | None = None,
        statistics: TradeStatistics | None = None,
    ) -> None:
        self._config = config or EngineConfig()

        # Core components (with defaults)
        self._market_state_detector = market_state_detector or MarketStateDetector()
        self._signal_generator = signal_generator or SignalGenerator(
            min_confidence_threshold=self._config.min_confidence,
        )
        self._confidence_scorer = confidence_scorer or ConfidenceScorer(
            min_liquidity=self._config.min_liquidity,
            max_spread_pips=self._config.max_spread_pips,
        )
        self._risk_filter = risk_filter or RiskFilter(
            max_position_size=self._config.max_position_size,
            max_risk_per_trade=self._config.risk_percent / 100.0,
            max_daily_trades=self._config.max_daily_trades,
            max_drawdown=self._config.max_drawdown,
            min_confidence=self._config.min_confidence,
        )
        self._execution_filter = execution_filter or ExecutionFilter(
            max_spread_pips=self._config.max_spread_pips,
            min_liquidity=self._config.min_liquidity,
        )
        self._strategy_router = strategy_router or StrategyRouter()
        self._trade_validator = trade_validator or TradeValidator(
            max_spread_pips=self._config.max_spread_pips,
            min_confidence=self._config.min_confidence,
            min_liquidity=self._config.min_liquidity,
        )
        self._position_sizer = position_sizer or self._create_default_sizer()
        self._statistics = statistics or TradeStatistics()

        self._lock = asyncio.Lock()
        self._decision_counter: int = 0

    @property
    def config(self) -> EngineConfig:
        return self._config

    @property
    def statistics(self) -> TradeStatistics:
        return self._statistics

    def _create_default_sizer(self) -> PositionSizer:
        """Create the default position sizer based on config."""
        method = self._config.position_sizing_method
        if method == "fixed":
            return FixedPositionSizer()
        elif method == "atr":
            return ATRPositionSizer(risk_percent=self._config.risk_percent)
        elif method == "kelly":
            return KellyPositionSizer()
        elif method == "volatility_based":
            return VolatilityBasedPositionSizer()
        else:
            return RiskPercentPositionSizer(risk_percent=self._config.risk_percent)

    async def make_decision(
        self,
        symbol: str,
        market_intelligence: MarketIntelligenceInput | None = None,
        account_balance: Decimal | None = None,
        current_positions: dict[str, float] | None = None,
        current_drawdown: float = 0.0,
        market_hours_active: bool = True,
    ) -> TradeDecision:
        """Make a trading decision for a symbol.

        This is the main entry point that runs the full decision pipeline:
        1. Detect market state
        2. Route to strategy
        3. Generate signal
        4. Compute confidence
        5. Apply risk filter
        6. Apply execution filter
        7. Calculate position size
        8. Validate trade
        9. Produce decision

        Args:
            symbol: Trading symbol.
            market_intelligence: Market intelligence data (optional).
            account_balance: Current account balance.
            current_positions: Current positions.
            current_drawdown: Current drawdown.
            market_hours_active: Whether market is open.

        Returns:
            TradeDecision with the final decision.
        """
        async with self._lock:
            mi = market_intelligence or MarketIntelligenceInput()
            balance = account_balance or self._config.default_account_balance

            # 1. Detect market state
            market_state = await self._market_state_detector.detect(
                symbol=symbol,
                trend_strength=mi.trend_strength,
                volatility_percentile=mi.volatility_percentile,
                is_breaking_out=mi.is_breaking_out,
                is_reversing=mi.is_reversing,
                is_news_mode=mi.is_news_mode,
            )

            # 2. Route to strategy
            strategy = await self._strategy_router.route(market_state)

            # 3. Generate signal
            signal = await self._signal_generator.generate(
                symbol=symbol,
                market_state=market_state,
                strategy=strategy,
                trend_strength=mi.trend_strength,
                rsi=mi.rsi,
                volume_ratio=mi.volume_ratio,
                price_position=mi.price_position,
            )

            if signal is None:
                return TradeDecision(
                    symbol=symbol,
                    outcome=DecisionOutcome.DEFER,
                    reason="No signal generated (HOLD)",
                    signal=None,
                    decision_id=self._next_decision_id(),
                )

            # 4. Compute confidence
            confidence = await self._confidence_scorer.compute(
                signal=signal,
                market_state=market_state,
                liquidity_score=mi.liquidity_score,
                spread_pips=mi.spread_pips,
                volatility_score=mi.volatility_score,
                provider_quality=mi.provider_quality,
                consensus_quality=mi.consensus_quality,
            )

            # 5. Apply risk filter
            risk_result = await self._risk_filter.check(
                signal=signal,
                confidence=confidence,
                current_positions=current_positions,
                current_drawdown=current_drawdown,
            )

            if not risk_result.is_allowed:
                return TradeDecision(
                    symbol=symbol,
                    outcome=DecisionOutcome.REJECT,
                    direction=signal.direction,
                    confidence=confidence,
                    strategy=strategy,
                    reason=risk_result.reason,
                    reject_reasons=[risk_result.reason],
                    signal=signal,
                    decision_id=self._next_decision_id(),
                )

            # 6. Apply execution filter
            exec_result = await self._execution_filter.check(
                signal=signal,
                market_state=market_state,
                spread_pips=mi.spread_pips,
                liquidity_score=mi.liquidity_score,
                volatility_score=mi.volatility_score,
                market_hours_active=market_hours_active,
            )

            if not exec_result.is_allowed:
                return TradeDecision(
                    symbol=symbol,
                    outcome=DecisionOutcome.REJECT,
                    direction=signal.direction,
                    confidence=confidence,
                    strategy=strategy,
                    reason=exec_result.reason,
                    reject_reasons=[exec_result.reason],
                    signal=signal,
                    decision_id=self._next_decision_id(),
                )

            # 7. Calculate position size
            sizing_result = await self._position_sizer.calculate(
                signal=signal,
                account_balance=balance,
                confidence=confidence,
                entry_price=mi.entry_price,
                stop_loss=mi.stop_loss,
                atr=mi.atr,
                volatility=mi.volatility_score,
            )

            # 8. Build decision
            decision = TradeDecision(
                symbol=symbol,
                outcome=DecisionOutcome.EXECUTE,
                direction=signal.direction,
                confidence=confidence,
                strategy=strategy,
                entry_price=mi.entry_price,
                stop_loss=mi.stop_loss,
                take_profit=mi.take_profit,
                position_size=sizing_result.units,
                risk_amount=sizing_result.risk_amount,
                account_risk_pct=sizing_result.account_risk_pct,
                reason="All checks passed - trade approved",
                signal=signal,
                decision_id=self._next_decision_id(),
                metadata={
                    "market_state": market_state.state_type.value,
                    "sizing_method": sizing_result.method.value,
                    "notional_value": str(sizing_result.notional_value),
                },
            )

            # 9. Final validation
            validation = await self._trade_validator.validate(
                signal=signal,
                decision=decision,
                spread_pips=mi.spread_pips,
                liquidity_score=mi.liquidity_score,
                market_quality=mi.consensus_quality,
                provider_health=mi.provider_quality,
            )

            if not validation.is_valid:
                return TradeDecision(
                    symbol=symbol,
                    outcome=DecisionOutcome.REJECT,
                    direction=signal.direction,
                    confidence=confidence,
                    strategy=strategy,
                    reason="; ".join(validation.errors),
                    reject_reasons=validation.errors,
                    signal=signal,
                    decision_id=self._next_decision_id(),
                )

            return decision

    def _next_decision_id(self) -> str:
        """Generate a unique decision ID."""
        self._decision_counter += 1
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"DEC-{ts}-{self._decision_counter:04d}"


@dataclass(frozen=True, slots=True)
class MarketIntelligenceInput:
    """Input data from market intelligence systems."""

    trend_strength: float = 0.0
    volatility_percentile: float = 0.5
    liquidity_score: float = 0.5
    spread_pips: float = 1.0
    volatility_score: float = 0.5
    provider_quality: float = 0.7
    consensus_quality: float = 0.7
    rsi: float = 50.0
    volume_ratio: float = 1.0
    price_position: float = 0.5
    entry_price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    atr: Decimal | None = None
    is_breaking_out: bool = False
    is_reversing: bool = False
    is_news_mode: bool = False
