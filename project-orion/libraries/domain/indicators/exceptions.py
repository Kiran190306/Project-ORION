"""Exception hierarchy for the Indicator Engine."""

from __future__ import annotations


class IndicatorError(Exception):
    """Base exception for all indicator errors."""


class IndicatorInitializationError(IndicatorError):
    """Raised when an indicator fails to initialize."""


class IndicatorCalculationError(IndicatorError):
    """Raised when an indicator calculation fails."""


class IndicatorValidationError(IndicatorError):
    """Raised when indicator input validation fails."""


class WarmupError(IndicatorError):
    """Raised when warmup has not been completed."""


class IndicatorNotFoundError(IndicatorError):
    """Raised when an indicator is not found."""


class IndicatorRegistrationError(IndicatorError):
    """Raised when indicator registration fails."""
