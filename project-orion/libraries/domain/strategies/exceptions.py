"""Strategy framework exception hierarchy."""

from __future__ import annotations


class StrategyError(Exception):
    """Base exception for all strategy framework errors."""


class StrategyRegistrationError(StrategyError):
    """Raised when strategy registration fails."""


class StrategyNotFoundError(StrategyError):
    """Raised when a strategy is not found in the registry."""


class StrategyValidationError(StrategyError):
    """Raised when strategy validation fails."""


class StrategyExecutionError(StrategyError):
    """Raised when strategy execution fails."""
