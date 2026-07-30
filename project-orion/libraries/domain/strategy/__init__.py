"""Trading Strategy Abstraction Layer.

Defines broker-agnostic protocols and data models for implementing,
registering, and executing trading strategies. All strategy logic
remains pure domain — no I/O, no infrastructure concerns.
"""

from __future__ import annotations

from libraries.domain.strategy.models import (
    AssetAllocation,
    BacktestResult,
    OrderRequest,
    OrderType,
    Position,
    PositionSide,
    Signal,
    SignalDirection,
    SignalStrength,
    StrategyDefinition,
    StrategyMetadata,
    StrategyStatus,
    StrategyType,
    Trade,
    TradeStatus,
)

__all__ = [
    "AssetAllocation",
    "BacktestResult",
    "OrderRequest",
    "OrderType",
    "Position",
    "PositionSide",
    "Signal",
    "SignalDirection",
    "SignalStrength",
    "StrategyDefinition",
    "StrategyMetadata",
    "StrategyStatus",
    "StrategyType",
    "Trade",
    "TradeStatus",
]
