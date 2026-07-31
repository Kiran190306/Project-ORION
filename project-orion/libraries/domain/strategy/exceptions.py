"""Domain exceptions for the Strategy Abstraction Layer."""

from __future__ import annotations


class StrategyError(Exception):
    """Base exception for all strategy errors."""


class InvalidSignalError(StrategyError):
    """Raised when a signal fails validation."""


class InvalidPositionSizeError(StrategyError):
    """Raised when a position size is invalid."""


class RiskLimitExceededError(StrategyError):
    """Raised when a risk limit is exceeded."""


class InvalidRiskRewardError(StrategyError):
    """Raised when risk/reward ratio is invalid."""


class StopLossTakeProfitError(StrategyError):
    """Raised when stop-loss/take-profit are inconsistent."""


class StrategyExecutionError(StrategyError):
    """Raised when strategy execution fails."""


class InsufficientCapitalError(StrategyError):
    """Raised when there is insufficient capital for a trade."""


class UnsupportedSymbolError(StrategyError):
    """Raised when a symbol is not supported by the strategy."""