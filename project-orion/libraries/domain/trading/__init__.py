"""
Project ORION - Trading Decision Engine (EPIC-006 Sprint-1).

Central decision-making brain that combines market intelligence, signal generation,
confidence scoring, risk filtering, execution validation, and position sizing
to produce a single trade decision per symbol.

Consumes MarketIntelligence from EPIC-005 Sprint-4 and produces
actionable TradeDecision outputs for downstream execution systems.
"""

from __future__ import annotations

from libraries.domain.trading.confidence import (
    ConfidenceFactors,
    ConfidenceScorer,
)
from libraries.domain.trading.decision_context import DecisionContext
from libraries.domain.trading.decision_engine import DecisionEngine, EngineConfig
from libraries.domain.trading.decision_result import (
    DecisionOutcome,
    TradeDecision,
)
from libraries.domain.trading.execution_filter import (
    ExecutionFilter,
    ExecutionFilterResult,
)
from libraries.domain.trading.interfaces import (
    ConfidencePort,
    DecisionEnginePort,
    ExecutionFilterPort,
    MarketIntelligencePort,
    MarketStatePort,
    PositionSizerPort,
    RiskFilterPort,
    SignalGeneratorPort,
    StrategyRouterPort,
    TradeValidatorPort,
    TradingDecisionSink,
)
from libraries.domain.trading.market_state import (
    MarketState,
    MarketStateDetector,
    MarketStateType,
)
from libraries.domain.trading.models import (
    PositionSizingMethod,
    SizingResult,
    StrategyType,
    TradeSignal,
    TradingSignal,
)
from libraries.domain.trading.position_sizer import (
    ATRPositionSizer,
    FixedPositionSizer,
    KellyPositionSizer,
    PositionSizer,
    RiskPercentPositionSizer,
    VolatilityBasedPositionSizer,
)
from libraries.domain.trading.risk_filter import RiskFilter, RiskFilterResult
from libraries.domain.trading.signal_generator import SignalGenerator
from libraries.domain.trading.signals import SignalDirection, SignalStrength
from libraries.domain.trading.statistics import (
    TradeOutcome,
    TradeStatistics,
    TradeStats,
)
from libraries.domain.trading.strategy_router import (
    StrategyRouter,
    StrategyRouterConfig,
)
from libraries.domain.trading.trade_validator import (
    TradeValidationReport,
    TradeValidator,
)

__all__ = [
    "ATRPositionSizer",
    "ConfidenceFactors",
    "ConfidencePort",
    "ConfidenceScorer",
    "DecisionContext",
    "DecisionEngine",
    "DecisionEnginePort",
    "DecisionOutcome",
    "EngineConfig",
    "ExecutionFilter",
    "ExecutionFilterPort",
    "ExecutionFilterResult",
    "FixedPositionSizer",
    "KellyPositionSizer",
    "MarketIntelligencePort",
    "MarketState",
    "MarketStateDetector",
    "MarketStatePort",
    "MarketStateType",
    "PositionSizer",
    "PositionSizerPort",
    "PositionSizingMethod",
    "RiskFilter",
    "RiskFilterPort",
    "RiskFilterResult",
    "RiskPercentPositionSizer",
    "SignalDirection",
    "SignalGenerator",
    "SignalGeneratorPort",
    "SignalStrength",
    "SizingResult",
    "StrategyRouter",
    "StrategyRouterConfig",
    "StrategyRouterPort",
    "StrategyType",
    "TradeDecision",
    "TradeOutcome",
    "TradeSignal",
    "TradeStatistics",
    "TradeStats",
    "TradeValidationReport",
    "TradeValidator",
    "TradeValidatorPort",
    "TradingDecisionSink",
    "TradingSignal",
    "VolatilityBasedPositionSizer",
]
