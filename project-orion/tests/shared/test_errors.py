"""
Unit tests for shared.errors module.

Tests error hierarchy, error properties, and error serialization.
"""

from shared.errors import (
    AccountLockedError,
    AuthenticationError,
    AuthorizationError,
    CacheError,
    ConfigNotFoundError,
    ConfigurationError,
    ConfigValidationError,
    ConflictError,
    ConstraintViolationError,
    DatabaseError,
    DataError,
    DataGapError,
    DataQualityError,
    ExecutionError,
    ExposureError,
    FeatureNotAvailableError,
    InfrastructureError,
    InsufficientFundsError,
    InvalidCredentialsError,
    InvalidInputError,
    InvalidSignalError,
    InvalidStateError,
    LicenseExpiredError,
    LicensingError,
    LimitBreachError,
    MarginCallError,
    MarketError,
    MFARequiredError,
    NotFoundError,
    OrderError,
    OrderRejectedError,
    OrionError,
    PermissionDeniedError,
    PositionError,
    ProviderError,
    RateLimitExceededError,
    RiskError,
    SignalError,
    StrategyError,
    StrategyExecutionError,
    StrategyLoadError,
    StrategyValidationError,
    TimeoutError,
    TokenExpiredError,
    TradingError,
    UsageLimitExceededError,
    ValidationError,
)


class TestOrionError:
    """Test base OrionError class."""

    def test_basic_error_creation(self):
        """Test creating a basic error."""
        error = OrionError("Test error", "TEST_ERROR")
        assert error.message == "Test error"
        assert error.code == "TEST_ERROR"
        assert error.details == {}
        assert error.cause is None

    def test_error_with_details(self):
        """Test error with details dictionary."""
        details = {"key": "value", "number": 42}
        error = OrionError("Test error", "TEST_ERROR", details=details)
        assert error.details == details

    def test_error_with_cause(self):
        """Test error with underlying cause."""
        cause = ValueError("Underlying error")
        error = OrionError("Test error", "TEST_ERROR", cause=cause)
        assert error.cause == cause

    def test_error_str_representation(self):
        """Test string representation of error."""
        error = OrionError("Test error", "TEST_ERROR")
        assert str(error) == "[TEST_ERROR] Test error"

    def test_error_repr(self):
        """Test repr representation of error."""
        error = OrionError("Test error", "TEST_ERROR")
        repr_str = repr(error)
        assert "OrionError" in repr_str
        assert "Test error" in repr_str
        assert "TEST_ERROR" in repr_str

    def test_error_to_dict(self):
        """Test error serialization to dictionary."""
        error = OrionError("Test error", "TEST_ERROR", details={"key": "value"})
        error_dict = error.to_dict()
        assert error_dict["error"] == "OrionError"
        assert error_dict["code"] == "TEST_ERROR"
        assert error_dict["message"] == "Test error"
        assert error_dict["details"] == {"key": "value"}


class TestConfigurationErrors:
    """Test configuration-related errors."""

    def test_config_not_found_error(self):
        """Test ConfigNotFoundError."""
        error = ConfigNotFoundError("missing_key")
        assert error.code == "CONFIG_NOT_FOUND"
        assert "missing_key" in error.message
        assert error.details["key"] == "missing_key"

    def test_config_validation_error(self):
        """Test ConfigValidationError."""
        errors = ["Invalid value", "Missing field"]
        error = ConfigValidationError(errors)
        assert error.code == "CONFIG_VALIDATION_ERROR"
        assert "Invalid value" in error.message
        assert error.details["errors"] == errors


class TestInfrastructureErrors:
    """Test infrastructure-related errors."""

    def test_database_error(self):
        """Test DatabaseError."""
        error = DatabaseError("Connection failed")
        assert error.code == "DATABASE_ERROR"
        assert error.message == "Connection failed"

    def test_cache_error(self):
        """Test CacheError."""
        error = CacheError("Cache miss")
        assert error.code == "CACHE_ERROR"

    def test_external_service_error(self):
        """Test ExternalServiceError."""
        from shared.errors import ExternalServiceError

        error = ExternalServiceError("external_api")

        assert error.code == "EXTERNAL_SERVICE_ERROR"
        assert error.details["service_name"] == "external_api"
        assert "external_api" in error.message


class TestTradingErrors:
    """Test trading-related errors."""

    def test_order_error(self):
        """Test OrderError."""
        error = OrderError("Order failed")
        assert error.code == "ORDER_ERROR"

    def test_order_rejected_error(self):
        """Test OrderRejectedError."""
        error = OrderRejectedError("Insufficient funds", order_id="ord_123")
        assert error.code == "ORDER_REJECTED"
        assert error.details["order_id"] == "ord_123"
        assert error.details["reason"] == "Insufficient funds"

    def test_position_error(self):
        """Test PositionError."""
        error = PositionError("Position not found")
        assert error.code == "POSITION_ERROR"

    def test_execution_error(self):
        """Test ExecutionError."""
        error = ExecutionError("Execution timeout")
        assert error.code == "EXECUTION_ERROR"

    def test_signal_error(self):
        """Test SignalError."""
        error = SignalError("Signal generation failed")
        assert error.code == "SIGNAL_ERROR"

    def test_invalid_signal_error(self):
        """Test InvalidSignalError."""
        error = InvalidSignalError("Invalid parameters", signal_id="sig_456")
        assert error.code == "INVALID_SIGNAL"
        assert error.details["signal_id"] == "sig_456"


class TestMarketErrors:
    """Test market data-related errors."""

    def test_data_error(self):
        """Test DataError."""
        error = DataError("Data missing")
        assert error.code == "DATA_ERROR"

    def test_data_quality_error(self):
        """Test DataQualityError."""
        error = DataQualityError(0.5, 0.8, symbol="EUR/USD")
        assert error.code == "DATA_QUALITY_ERROR"
        assert error.details["quality_score"] == 0.5
        assert error.details["min_threshold"] == 0.8
        assert error.details["symbol"] == "EUR/USD"

    def test_data_gap_error(self):
        """Test DataGapError."""
        error = DataGapError("EUR/USD", "2024-01-01T00:00:00", "2024-01-01T01:00:00", 3600)
        assert error.code == "DATA_GAP_ERROR"
        assert error.details["symbol"] == "EUR/USD"
        assert error.details["gap_duration_seconds"] == 3600

    def test_provider_error(self):
        """Test ProviderError."""
        error = ProviderError("broker_provider")
        assert error.code == "PROVIDER_ERROR"
        assert error.details["provider_name"] == "broker_provider"


class TestValidationErrors:
    """Test validation-related errors."""

    def test_invalid_input_error(self):
        """Test InvalidInputError."""
        error = InvalidInputError("price", "Must be positive", -1.0)
        assert error.code == "INVALID_INPUT"
        assert error.details["field"] == "price"
        assert error.details["reason"] == "Must be positive"

    def test_invalid_state_error(self):
        """Test InvalidStateError."""
        error = InvalidStateError("Order", "CANCELLED", "PENDING")
        assert error.code == "INVALID_STATE"
        assert error.details["entity_type"] == "Order"
        assert error.details["current_state"] == "CANCELLED"
        assert error.details["expected_state"] == "PENDING"

    def test_constraint_violation_error(self):
        """Test ConstraintViolationError."""
        error = ConstraintViolationError("Max positions exceeded")
        assert error.code == "CONSTRAINT_VIOLATION"
        assert error.details["constraint"] == "Max positions exceeded"


class TestAuthenticationErrors:
    """Test authentication-related errors."""

    def test_invalid_credentials_error(self):
        """Test InvalidCredentialsError."""
        error = InvalidCredentialsError()
        assert error.code == "INVALID_CREDENTIALS"
        assert "Invalid email or password" in error.message

    def test_token_expired_error(self):
        """Test TokenExpiredError."""
        error = TokenExpiredError()
        assert error.code == "TOKEN_EXPIRED"

    def test_mfa_required_error(self):
        """Test MFARequiredError."""
        error = MFARequiredError()
        assert error.code == "MFA_REQUIRED"

    def test_account_locked_error(self):
        """Test AccountLockedError."""
        error = AccountLockedError(remaining_lockout_seconds=300)
        assert error.code == "ACCOUNT_LOCKED"
        assert error.details["remaining_lockout_seconds"] == 300


class TestAuthorizationErrors:
    """Test authorization-related errors."""

    def test_permission_denied_error(self):
        """Test PermissionDeniedError."""
        error = PermissionDeniedError("admin:write")
        assert error.code == "PERMISSION_DENIED"
        assert error.details["required_permission"] == "admin:write"


class TestRiskErrors:
    """Test risk management errors."""

    def test_limit_breach_error(self):
        """Test LimitBreachError."""
        error = LimitBreachError("daily_loss", 0.06, 0.05)
        assert error.code == "LIMIT_BREACHED"
        assert error.details["limit_type"] == "daily_loss"
        assert error.details["current_value"] == 0.06
        assert error.details["limit_value"] == 0.05

    def test_margin_call_error(self):
        """Test MarginCallError."""
        error = MarginCallError(0.8, 1.0)
        assert error.code == "MARGIN_CALL"
        assert error.details["margin_level"] == 0.8
        assert error.details["threshold"] == 1.0

    def test_exposure_error(self):
        """Test ExposureError."""
        error = ExposureError("portfolio", 0.15, 0.10)
        assert error.code == "EXPOSURE_ERROR"
        assert error.details["exposure_type"] == "portfolio"
        assert error.details["current_exposure"] == 0.15
        assert error.details["max_exposure"] == 0.10


class TestStrategyErrors:
    """Test strategy-related errors."""

    def test_strategy_load_error(self):
        """Test StrategyLoadError."""
        error = StrategyLoadError("my_strategy", "File not found")
        assert error.code == "STRATEGY_LOAD_ERROR"
        assert error.details["strategy_name"] == "my_strategy"
        assert error.details["reason"] == "File not found"

    def test_strategy_execution_error(self):
        """Test StrategyExecutionError."""
        error = StrategyExecutionError("my_strategy")
        assert error.code == "STRATEGY_EXECUTION_ERROR"
        assert error.details["strategy_name"] == "my_strategy"

    def test_strategy_validation_error(self):
        """Test StrategyValidationError."""
        error = StrategyValidationError("my_strategy", ["Invalid parameter", "Missing field"])
        assert error.code == "STRATEGY_VALIDATION_ERROR"
        assert error.details["strategy_name"] == "my_strategy"
        assert error.details["errors"] == ["Invalid parameter", "Missing field"]


class TestLicensingErrors:
    """Test licensing-related errors."""

    def test_license_expired_error(self):
        """Test LicenseExpiredError."""
        error = LicenseExpiredError("2024-01-01", grace_period_days=7)
        assert error.code == "LICENSE_EXPIRED"
        assert error.details["expired_at"] == "2024-01-01"
        assert error.details["grace_period_days"] == 7

    def test_feature_not_available_error(self):
        """Test FeatureNotAvailableError."""
        error = FeatureNotAvailableError("advanced_analytics", "ENTERPRISE", "PROFESSIONAL")
        assert error.code == "FEATURE_NOT_AVAILABLE"
        assert error.details["feature"] == "advanced_analytics"
        assert error.details["required_tier"] == "ENTERPRISE"
        assert error.details["current_tier"] == "PROFESSIONAL"

    def test_usage_limit_exceeded_error(self):
        """Test UsageLimitExceededError."""
        error = UsageLimitExceededError("api_calls", 1001, 1000)
        assert error.code == "USAGE_LIMIT_EXCEEDED"
        assert error.details["limit_name"] == "api_calls"
        assert error.details["current_usage"] == 1001
        assert error.details["max_allowed"] == 1000


class TestTimeoutAndRateLimitErrors:
    """Test timeout and rate limit errors."""

    def test_timeout_error(self):
        """Test TimeoutError."""
        error = TimeoutError("api_call", 30.0)
        assert error.code == "TIMEOUT"
        assert error.details["operation"] == "api_call"
        assert error.details["timeout_seconds"] == 30.0

    def test_rate_limit_exceeded_error(self):
        """Test RateLimitExceededError."""
        error = RateLimitExceededError("api", 1000, "2024-01-01T01:00:00")
        assert error.code == "RATE_LIMIT_EXCEEDED"
        assert error.details["limit_name"] == "api"
        assert error.details["max_requests"] == 1000
        assert error.details["reset_at"] == "2024-01-01T01:00:00"


class TestNotFoundAndConflictErrors:
    """Test not found and conflict errors."""

    def test_not_found_error(self):
        """Test NotFoundError."""
        error = NotFoundError("Order", "ord_123")
        assert error.code == "NOT_FOUND"
        assert error.details["resource_type"] == "Order"
        assert error.details["resource_id"] == "ord_123"

    def test_conflict_error(self):
        """Test ConflictError."""
        error = ConflictError("Order", "Order already exists")
        assert error.code == "CONFLICT"
        assert error.details["resource_type"] == "Order"
        assert error.details["conflict_reason"] == "Order already exists"


class TestInsufficientFundsError:
    """Test insufficient funds error."""

    def test_insufficient_funds_error(self):
        """Test InsufficientFundsError."""
        error = InsufficientFundsError(1000.0, 500.0, account_id="acc_123")
        assert error.code == "INSUFFICIENT_FUNDS"
        assert error.details["required"] == 1000.0
        assert error.details["available"] == 500.0
        assert error.details["account_id"] == "acc_123"


class TestErrorInheritance:
    """Test error inheritance hierarchy."""

    def test_all_errors_inherit_from_orion_error(self):
        """Test all custom errors inherit from OrionError."""
        errors = [
            ConfigurationError(),
            InfrastructureError(),
            TradingError(),
            MarketError(),
            ValidationError(),
            AuthenticationError(),
            AuthorizationError(),
            RiskError(),
            StrategyError(),
            LicensingError(),
        ]
        for error in errors:
            assert isinstance(error, OrionError)

    def test_specific_error_inheritance(self):
        """Test specific error inheritance chains."""
        assert issubclass(ConfigNotFoundError, ConfigurationError)
        assert issubclass(DatabaseError, InfrastructureError)
        assert issubclass(OrderError, TradingError)
        assert issubclass(DataError, MarketError)
        assert issubclass(InvalidInputError, ValidationError)
        assert issubclass(InvalidCredentialsError, AuthenticationError)
        assert issubclass(PermissionDeniedError, AuthorizationError)
        assert issubclass(LimitBreachError, RiskError)
        assert issubclass(StrategyLoadError, StrategyError)
        assert issubclass(LicenseExpiredError, LicensingError)
