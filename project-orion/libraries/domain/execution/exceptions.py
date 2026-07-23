"""Exception hierarchy for the Smart Order Execution Engine."""

from __future__ import annotations


class ExecutionError(Exception):
    """Base exception for all execution engine errors."""


class ExecutionEngineError(ExecutionError):
    """Raised when the execution engine encounters a general error."""


class ExecutionEngineNotReadyError(ExecutionEngineError):
    """Raised when the engine is called before being initialized."""


class ExecutionEngineShutdownError(ExecutionEngineError):
    """Raised when the engine is called after shutdown."""


class OrderValidationError(ExecutionError):
    """Raised when order validation fails."""


class OrderBuildError(ExecutionError):
    """Raised when order construction fails."""


class RoutingError(ExecutionError):
    """Raised when order routing fails."""


class DuplicateOrderError(ExecutionError):
    """Raised when a duplicate order submission is detected."""


class OrderNotFoundError(ExecutionError):
    """Raised when an order is not found in the tracker."""


class OrderRejectedByBrokerError(ExecutionError):
    """Raised when a broker rejects an order."""


class InvalidOrderStateError(ExecutionError):
    """Raised when an operation is attempted in an invalid order state."""


class InvalidTransitionError(ExecutionError):
    """Raised when an invalid state transition is attempted."""


class FillValidationError(ExecutionError):
    """Raised when a fill cannot be validated."""


class RetryExhaustedError(ExecutionError):
    """Raised when all retry attempts are exhausted."""


class TimeoutError(ExecutionError):
    """Raised when an order submission times out."""


class RecoveryError(ExecutionError):
    """Raised when order recovery fails."""
