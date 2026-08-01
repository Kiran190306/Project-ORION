"""Validation utilities for the Risk Analytics sub-package.

Pure functions that validate inputs used across all analytics engines.
No business logic, no I/O, no infrastructure concerns.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


class RiskAnalyticsError(Exception):
    """Base exception for all risk analytics errors."""


class InvalidReturnsError(RiskAnalyticsError):
    """Raised when a returns series is invalid."""


class InsufficientDataError(RiskAnalyticsError):
    """Raised when there is not enough data for a calculation."""


class InvalidConfidenceLevelError(RiskAnalyticsError):
    """Raised when a confidence level is outside (0, 1)."""


class InvalidProbabilityError(RiskAnalyticsError):
    """Raised when a probability is outside [0, 1]."""


class InvalidHorizonError(RiskAnalyticsError):
    """Raised when a horizon is not a positive integer."""


class InvalidWindowError(RiskAnalyticsError):
    """Raised when a rolling window is invalid."""


class InvalidValueError(RiskAnalyticsError):
    """Raised when a numeric value is invalid."""


def validate_returns(
    returns: Sequence[float],
    min_length: int = 2,
) -> list[float]:
    """Validate a sequence of period returns.

    Args:
        returns: Sequence of returns (e.g. daily returns).
        min_length: Minimum number of observations required.

    Returns:
        A list of validated float returns.

    Raises:
        InvalidReturnsError: If the series is empty or non-finite.
        InsufficientDataError: If fewer than ``min_length`` observations.
    """
    if isinstance(returns, (str, bytes)) or not isinstance(returns, Sequence):
        raise InvalidReturnsError("returns must be a sequence of floats")

    validated = [float(r) for r in returns]
    if not validated:
        raise InvalidReturnsError("returns must not be empty")

    if any(math.isnan(r) or r in (float("inf"), float("-inf")) for r in validated):
        raise InvalidReturnsError("returns must contain only finite numbers")

    if len(validated) < min_length:
        raise InsufficientDataError(
            f"at least {min_length} observations required, got {len(validated)}"
        )

    return validated


def validate_confidence_level(confidence_level: float) -> float:
    """Validate a confidence level in the open interval (0, 1).

    Args:
        confidence_level: Confidence level such as 0.95.

    Returns:
        The validated confidence level.

    Raises:
        InvalidConfidenceLevelError: If the value is outside (0, 1).
    """
    try:
        level = float(confidence_level)
    except (TypeError, ValueError) as exc:
        raise InvalidConfidenceLevelError(
            f"confidence_level must be a number, got {confidence_level!r}"
        ) from exc

    if not 0.0 < level < 1.0:
        raise InvalidConfidenceLevelError(
            f"confidence_level must be in (0, 1), got {level}"
        )
    return level


def validate_probability(probability: float) -> float:
    """Validate a probability in the inclusive range [0, 1].

    Args:
        probability: Probability of a winning trade.

    Returns:
        The validated probability.

    Raises:
        InvalidProbabilityError: If the value is outside [0, 1].
    """
    try:
        p = float(probability)
    except (TypeError, ValueError) as exc:
        raise InvalidProbabilityError(
            f"probability must be a number, got {probability!r}"
        ) from exc

    if not 0.0 <= p <= 1.0:
        raise InvalidProbabilityError(f"probability must be in [0, 1], got {p}")
    return p


def validate_horizon(horizon_days: int) -> int:
    """Validate a positive integer holding period.

    Args:
        horizon_days: Holding period in days.

    Returns:
        The validated horizon.

    Raises:
        InvalidHorizonError: If the value is not a positive integer.
    """
    if not isinstance(horizon_days, int) or horizon_days < 1:
        raise InvalidHorizonError(
            f"horizon_days must be a positive integer, got {horizon_days!r}"
        )
    return horizon_days


def validate_window(window: int, data_length: int) -> int:
    """Validate a rolling window size.

    Args:
        window: Rolling window length.
        data_length: Length of the underlying data series.

    Returns:
        The validated window.

    Raises:
        InvalidWindowError: If the window is invalid or exceeds data length.
    """
    if not isinstance(window, int) or window < 1:
        raise InvalidWindowError(f"window must be a positive integer, got {window!r}")
    if window > data_length:
        raise InvalidWindowError(
            f"window ({window}) exceeds data length ({data_length})"
        )
    return window


def validate_positive_float(value: float, field_name: str) -> float:
    """Validate a strictly positive float.

    Args:
        value: Numeric value to validate.
        field_name: Name used in error messages.

    Returns:
        The validated value.

    Raises:
        InvalidValueError: If the value is not a positive number.
    """
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidValueError(
            f"{field_name} must be a number, got {value!r}"
        ) from exc
    if v <= 0.0:
        raise InvalidValueError(f"{field_name} must be positive, got {v}")
    return v
