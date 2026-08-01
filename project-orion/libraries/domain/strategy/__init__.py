"""Trading Strategy Abstraction Layer.

Defines broker-agnostic protocols and data models for implementing,
registering, and executing trading strategies. All strategy logic
remains pure domain — no I/O, no infrastructure concerns.
"""

from __future__ import annotations

from libraries.domain.strategy.base import BaseStrategy
from libraries.domain.strategy.exceptions import (
    InsufficientCapitalError,
    InvalidPositionSizeError,
    InvalidRiskRewardError,
    InvalidSignalError,
    RiskLimitExceededError,
    StopLossTakeProfitError,
    StrategyError,
    StrategyExecutionError,
    UnsupportedSymbolError,
)
from libraries.domain.strategy.interfaces import (
    PortfolioAllocator,
    PositionSizer,
    RiskController,
    SignalGenerator,
    Strategy,
)
from libraries.domain.strategy.models import (
    AssetAllocation,
    BacktestResult,
    ExecutionAction,
    ExecutionDecision,
    OrderIntent,
    OrderRequest,
    OrderType,
    Position,
    PositionIntent,
    PositionSide,
    Signal,
    SignalDirection,
    SignalStrength,
    StrategyContext,
    StrategyDefinition,
    StrategyMetadata,
    StrategyResult,
    StrategyStatus,
    StrategyType,
    Trade,
    TradeStatus,
)
from libraries.domain.strategy.strategies import (
    BreakoutStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    TrendFollowingStrategy,
)
from libraries.domain.strategy.validation import (
    validate_position_intent,
    validate_position_size,
    validate_risk_reward_ratio,
    validate_signal,
    validate_stop_loss_take_profit,
)

__all__ = [
    "AssetAllocation",
    "BacktestResult",
    "BaseStrategy",
    "BreakoutStrategy",
    "ExecutionAction",
    "ExecutionDecision",
    "InsufficientCapitalError",
    "InvalidPositionSizeError",
    "InvalidRiskRewardError",
    "InvalidSignalError",
    "MeanReversionStrategy",
    "MomentumStrategy",
    "OrderIntent",
    "OrderRequest",
    "OrderType",
    "PortfolioAllocator",
    "Position",
    "PositionIntent",
    "PositionSide",
    "PositionSizer",
    "RiskController",
    "RiskLimitExceededError",
    "Signal",
    "SignalDirection",
    "SignalGenerator",
    "SignalStrength",
    "StopLossTakeProfitError",
    "Strategy",
    "StrategyContext",
    "StrategyDefinition",
    "StrategyError",
    "StrategyExecutionError",
    "StrategyMetadata",
    "StrategyResult",
    "StrategyStatus",
    "StrategyType",
    "Trade",
    "TradeStatus",
    "TrendFollowingStrategy",
    "UnsupportedSymbolError",
    "validate_position_intent",
    "validate_position_size",
    "validate_risk_reward_ratio",
    "validate_signal",
    "validate_stop_loss_take_profit",
]
