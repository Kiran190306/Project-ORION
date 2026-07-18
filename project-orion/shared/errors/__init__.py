"""
Project ORION - Error & Exception Definitions

Comprehensive exception hierarchy for the platform.
All custom exceptions inherit from OrionError base class.

Architecture:
    Base: OrionError
    ├── ConfigurationError
    ├── InfrastructureError
    │   ├── DatabaseError
    │   ├── CacheError
    │   ├── MessagingError
    │   └── ExternalServiceError
    ├── TradingError
    │   ├── OrderError
    │   ├── PositionError
    │   ├── ExecutionError
    │   └── SignalError
    ├── MarketError
    │   ├── DataError
    │   ├── DataQualityError
    │   ├── DataGapError
    │   └── ProviderError
    ├── ValidationError
    │   ├── InvalidInputError
    │   ├── InvalidStateError
    │   └── ConstraintViolationError
    ├── AuthenticationError
    │   ├── InvalidCredentialsError
    │   ├── TokenExpiredError
    │   ├── MFARequiredError
    │   └── AccountLockedError
    ├── AuthorizationError
    │   └── PermissionDeniedError
    ├── RiskError
    │   ├── LimitBreachError
    │   ├── MarginCallError
    │   └── ExposureError
    ├── StrategyError
    │   ├── StrategyLoadError
    │   ├── StrategyExecutionError
    │   └── StrategyValidationError
    └── LicensingError
        ├── LicenseExpiredError
        ├── FeatureNotAvailableError
        └── UsageLimitExceededError
"""

from __future__ import annotations

from typing import Any, Optional


class OrionError(Exception):
    """
    Base exception for all Project ORION errors.

    Attributes:
        message: Human-readable error description
        code: Machine-readable error code string
        details: Optional dictionary with additional context
        cause: Optional originating exception
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        code: str = "INTERNAL_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        self.cause = cause
        super().__init__(message)

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"code={self.code!r}, "
            f"details={self.details!r}"
            f")"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert error to a serializable dictionary."""
        return {
            "error": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


# ─── Configuration Errors ─────────────────────────────────────


class ConfigurationError(OrionError):
    """Base for configuration-related errors."""

    def __init__(
        self,
        message: str = "Configuration error",
        code: str = "CONFIGURATION_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class ConfigNotFoundError(ConfigurationError):
    """Raised when a configuration key is not found."""

    def __init__(
        self,
        key: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message or f"Configuration key not found: {key}",
            code="CONFIG_NOT_FOUND",
            details={**(details or {}), "key": key},
        )


class ConfigValidationError(ConfigurationError):
    """Raised when configuration validation fails."""

    def __init__(
        self,
        errors: list[str],
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message or f"Configuration validation failed: {'; '.join(errors)}",
            code="CONFIG_VALIDATION_ERROR",
            details={**(details or {}), "errors": errors},
        )


# ─── Infrastructure Errors ────────────────────────────────────


class InfrastructureError(OrionError):
    """Base for infrastructure-level errors."""

    def __init__(
        self,
        message: str = "Infrastructure error",
        code: str = "INFRASTRUCTURE_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class DatabaseError(InfrastructureError):
    """Raised when a database operation fails."""

    def __init__(
        self,
        message: str = "Database operation failed",
        code: str = "DATABASE_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class CacheError(InfrastructureError):
    """Raised when a cache operation fails."""

    def __init__(
        self,
        message: str = "Cache operation failed",
        code: str = "CACHE_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class MessagingError(InfrastructureError):
    """Raised when a messaging/queue operation fails."""

    def __init__(
        self,
        message: str = "Messaging operation failed",
        code: str = "MESSAGING_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class ExternalServiceError(InfrastructureError):
    """Raised when an external service call fails."""

    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None,
        code: str = "EXTERNAL_SERVICE_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            message=message or f"External service '{service_name}' failed",
            code=code,
            details={**(details or {}), "service_name": service_name},
            cause=cause,
        )


# ─── Trading Errors ───────────────────────────────────────────


class TradingError(OrionError):
    """Base for trading-related errors."""

    def __init__(
        self,
        message: str = "Trading error",
        code: str = "TRADING_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class OrderError(TradingError):
    """Raised when an order operation fails."""

    def __init__(
        self,
        message: str = "Order operation failed",
        code: str = "ORDER_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class OrderRejectedError(OrderError):
    """Raised when an order is rejected by broker or system."""

    def __init__(
        self,
        reason: str,
        order_id: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message or f"Order rejected: {reason}",
            code="ORDER_REJECTED",
            details={**(details or {}), "reason": reason, "order_id": order_id},
        )


class PositionError(TradingError):
    """Raised when a position operation fails."""

    def __init__(
        self,
        message: str = "Position operation failed",
        code: str = "POSITION_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class ExecutionError(TradingError):
    """Raised when order execution fails."""

    def __init__(
        self,
        message: str = "Order execution failed",
        code: str = "EXECUTION_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class SignalError(TradingError):
    """Raised when signal generation or processing fails."""

    def __init__(
        self,
        message: str = "Signal processing failed",
        code: str = "SIGNAL_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class InvalidSignalError(SignalError):
    """Raised when an invalid signal is received."""

    def __init__(
        self,
        reason: str,
        signal_id: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message or f"Invalid signal: {reason}",
            code="INVALID_SIGNAL",
            details={**(details or {}), "reason": reason, "signal_id": signal_id},
        )


# ─── Market Errors ────────────────────────────────────────────


class MarketError(OrionError):
    """Base for market data-related errors."""

    def __init__(
        self,
        message: str = "Market data error",
        code: str = "MARKET_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class DataError(MarketError):
    """Raised when market data is missing or invalid."""

    def __init__(
        self,
        message: str = "Market data error",
        code: str = "DATA_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class DataQualityError(MarketError):
    """Raised when market data quality is below threshold."""

    def __init__(
        self,
        quality_score: float,
        min_threshold: float,
        symbol: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message
            or (
                f"Data quality score {quality_score} "
                f"below minimum threshold {min_threshold}"
            ),
            code="DATA_QUALITY_ERROR",
            details={
                **(details or {}),
                "quality_score": quality_score,
                "min_threshold": min_threshold,
                "symbol": symbol,
            },
        )


class DataGapError(MarketError):
    """Raised when a data gap is detected."""

    def __init__(
        self,
        symbol: str,
        gap_start: str,
        gap_end: str,
        gap_duration_seconds: int,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message
            or (
                f"Data gap detected for {symbol}: "
                f"{gap_start} to {gap_end} ({gap_duration_seconds}s)"
            ),
            code="DATA_GAP_ERROR",
            details={
                **(details or {}),
                "symbol": symbol,
                "gap_start": gap_start,
                "gap_end": gap_end,
                "gap_duration_seconds": gap_duration_seconds,
            },
        )


class ProviderError(MarketError):
    """Raised when a data provider fails."""

    def __init__(
        self,
        provider_name: str,
        message: Optional[str] = None,
        code: str = "PROVIDER_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            message=message or f"Data provider '{provider_name}' failed",
            code=code,
            details={**(details or {}), "provider_name": provider_name},
            cause=cause,
        )


# ─── Validation Errors ────────────────────────────────────────


class ValidationError(OrionError):
    """Base for validation errors."""

    def __init__(
        self,
        message: str = "Validation failed",
        code: str = "VALIDATION_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class InvalidInputError(ValidationError):
    """Raised when input validation fails."""

    def __init__(
        self,
        field: str,
        reason: str,
        value: Optional[Any] = None,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message or f"Invalid input for '{field}': {reason}",
            code="INVALID_INPUT",
            details={
                **(details or {}),
                "field": field,
                "reason": reason,
                "value": str(value) if value is not None else None,
            },
        )


class InvalidStateError(ValidationError):
    """Raised when an operation is attempted in an invalid state."""

    def __init__(
        self,
        entity_type: str,
        current_state: str,
        expected_state: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message
            or (
                f"Invalid state for {entity_type}: "
                f"current='{current_state}', expected='{expected_state}'"
            ),
            code="INVALID_STATE",
            details={
                **(details or {}),
                "entity_type": entity_type,
                "current_state": current_state,
                "expected_state": expected_state,
            },
        )


class ConstraintViolationError(ValidationError):
    """Raised when a business constraint is violated."""

    def __init__(
        self,
        constraint: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message or f"Constraint violation: {constraint}",
            code="CONSTRAINT_VIOLATION",
            details={**(details or {}), "constraint": constraint},
        )


# ─── Authentication Errors ────────────────────────────────────


class AuthenticationError(OrionError):
    """Base for authentication errors."""

    def __init__(
        self,
        message: str = "Authentication failed",
        code: str = "AUTHENTICATION_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid."""

    def __init__(
        self,
        message: str = "Invalid email or password",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="INVALID_CREDENTIALS",
            details=details,
        )


class TokenExpiredError(AuthenticationError):
    """Raised when an authentication token has expired."""

    def __init__(
        self,
        message: str = "Authentication token has expired",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="TOKEN_EXPIRED",
            details=details,
        )


class MFARequiredError(AuthenticationError):
    """Raised when multi-factor authentication is required."""

    def __init__(
        self,
        message: str = "Multi-factor authentication required",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="MFA_REQUIRED",
            details=details,
        )


class AccountLockedError(AuthenticationError):
    """Raised when a user account is locked."""

    def __init__(
        self,
        remaining_lockout_seconds: int = 0,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message or "Account is temporarily locked due to too many attempts",
            code="ACCOUNT_LOCKED",
            details={
                **(details or {}),
                "remaining_lockout_seconds": remaining_lockout_seconds,
            },
        )


# ─── Authorization Errors ─────────────────────────────────────


class AuthorizationError(OrionError):
    """Base for authorization errors."""

    def __init__(
        self,
        message: str = "Authorization failed",
        code: str = "AUTHORIZATION_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class PermissionDeniedError(AuthorizationError):
    """Raised when a user lacks required permissions."""

    def __init__(
        self,
        required_permission: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message or f"Permission denied: {required_permission} required",
            code="PERMISSION_DENIED",
            details={**(details or {}), "required_permission": required_permission},
        )


# ─── Risk Errors ──────────────────────────────────────────────


class RiskError(OrionError):
    """Base for risk management errors."""

    def __init__(
        self,
        message: str = "Risk management error",
        code: str = "RISK_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class LimitBreachError(RiskError):
    """Raised when a risk limit is breached."""

    def __init__(
        self,
        limit_type: str,
        current_value: float,
        limit_value: float,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message
            or (
                f"Risk limit breached: {limit_type} "
                f"(current={current_value}, limit={limit_value})"
            ),
            code="LIMIT_BREACHED",
            details={
                **(details or {}),
                "limit_type": limit_type,
                "current_value": current_value,
                "limit_value": limit_value,
            },
        )


class MarginCallError(RiskError):
    """Raised when a margin call is triggered."""

    def __init__(
        self,
        margin_level: float,
        threshold: float,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message
            or (
                f"Margin call triggered: margin level {margin_level}% "
                f"below threshold {threshold}%"
            ),
            code="MARGIN_CALL",
            details={
                **(details or {}),
                "margin_level": margin_level,
                "threshold": threshold,
            },
        )


class ExposureError(RiskError):
    """Raised when exposure limits are exceeded."""

    def __init__(
        self,
        exposure_type: str,
        current_exposure: float,
        max_exposure: float,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message
            or (
                f"Exposure limit exceeded: {exposure_type} "
                f"(current={current_exposure}, max={max_exposure})"
            ),
            code="EXPOSURE_ERROR",
            details={
                **(details or {}),
                "exposure_type": exposure_type,
                "current_exposure": current_exposure,
                "max_exposure": max_exposure,
            },
        )


# ─── Strategy Errors ──────────────────────────────────────────


class StrategyError(OrionError):
    """Base for strategy-related errors."""

    def __init__(
        self,
        message: str = "Strategy error",
        code: str = "STRATEGY_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class StrategyLoadError(StrategyError):
    """Raised when a strategy cannot be loaded."""

    def __init__(
        self,
        strategy_name: str,
        reason: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message or f"Failed to load strategy '{strategy_name}': {reason}",
            code="STRATEGY_LOAD_ERROR",
            details={
                **(details or {}),
                "strategy_name": strategy_name,
                "reason": reason,
            },
        )


class StrategyExecutionError(StrategyError):
    """Raised when strategy execution fails."""

    def __init__(
        self,
        strategy_name: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            message=message or f"Strategy '{strategy_name}' execution failed",
            code="STRATEGY_EXECUTION_ERROR",
            details={**(details or {}), "strategy_name": strategy_name},
            cause=cause,
        )


class StrategyValidationError(StrategyError):
    """Raised when strategy validation fails."""

    def __init__(
        self,
        strategy_name: str,
        errors: list[str],
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message
            or (
                f"Strategy '{strategy_name}' validation failed: " f"{'; '.join(errors)}"
            ),
            code="STRATEGY_VALIDATION_ERROR",
            details={
                **(details or {}),
                "strategy_name": strategy_name,
                "errors": errors,
            },
        )


# ─── Licensing Errors ─────────────────────────────────────────


class LicensingError(OrionError):
    """Base for licensing and subscription errors."""

    def __init__(
        self,
        message: str = "Licensing error",
        code: str = "LICENSING_ERROR",
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details, cause=cause)


class LicenseExpiredError(LicensingError):
    """Raised when a license has expired."""

    def __init__(
        self,
        expired_at: str,
        grace_period_days: int = 0,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message or f"License expired on {expired_at}",
            code="LICENSE_EXPIRED",
            details={
                **(details or {}),
                "expired_at": expired_at,
                "grace_period_days": grace_period_days,
            },
        )


class FeatureNotAvailableError(LicensingError):
    """Raised when a feature is not available on current tier."""

    def __init__(
        self,
        feature: str,
        required_tier: str,
        current_tier: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message
            or (
                f"Feature '{feature}' requires '{required_tier}' tier, "
                f"current tier is '{current_tier}'"
            ),
            code="FEATURE_NOT_AVAILABLE",
            details={
                **(details or {}),
                "feature": feature,
                "required_tier": required_tier,
                "current_tier": current_tier,
            },
        )


class UsageLimitExceededError(LicensingError):
    """Raised when a usage limit is exceeded."""

    def __init__(
        self,
        limit_name: str,
        current_usage: int,
        max_allowed: int,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message
            or (
                f"Usage limit exceeded for '{limit_name}': "
                f"{current_usage}/{max_allowed}"
            ),
            code="USAGE_LIMIT_EXCEEDED",
            details={
                **(details or {}),
                "limit_name": limit_name,
                "current_usage": current_usage,
                "max_allowed": max_allowed,
            },
        )


# ─── Timeout / Rate Limit Errors ──────────────────────────────


class TimeoutError(OrionError):
    """Raised when an operation times out."""

    def __init__(
        self,
        operation: str,
        timeout_seconds: float,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message
            or (f"Operation '{operation}' timed out after {timeout_seconds}s"),
            code="TIMEOUT",
            details={
                **(details or {}),
                "operation": operation,
                "timeout_seconds": timeout_seconds,
            },
        )


class RateLimitExceededError(OrionError):
    """Raised when a rate limit is exceeded."""

    def __init__(
        self,
        limit_name: str,
        max_requests: int,
        reset_at: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message
            or (
                f"Rate limit exceeded for '{limit_name}': "
                f"max {max_requests} requests, resets at {reset_at}"
            ),
            code="RATE_LIMIT_EXCEEDED",
            details={
                **(details or {}),
                "limit_name": limit_name,
                "max_requests": max_requests,
                "reset_at": reset_at,
            },
        )


# ─── Not Found / Conflict ───────────────────────────────────


class NotFoundError(OrionError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message
            or (
                f"{resource_type} not found"
                + (f": {resource_id}" if resource_id else "")
            ),
            code="NOT_FOUND",
            details={
                **(details or {}),
                "resource_type": resource_type,
                "resource_id": resource_id,
            },
        )


class ConflictError(OrionError):
    """Raised when a resource conflict occurs."""

    def __init__(
        self,
        resource_type: str,
        conflict_reason: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message or f"Conflict for {resource_type}: {conflict_reason}",
            code="CONFLICT",
            details={
                **(details or {}),
                "resource_type": resource_type,
                "conflict_reason": conflict_reason,
            },
        )


# ─── Insufficient Funds ─────────────────────────────────────


class InsufficientFundsError(OrionError):
    """Raised when an account has insufficient funds."""

    def __init__(
        self,
        required: float,
        available: float,
        account_id: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message
            or (f"Insufficient funds: required {required}, " f"available {available}"),
            code="INSUFFICIENT_FUNDS",
            details={
                **(details or {}),
                "required": required,
                "available": available,
                "account_id": account_id,
            },
        )
