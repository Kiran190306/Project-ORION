"""
Unit tests for shared.enums module.

Tests enum definitions, enum values, and enum properties.
"""

from enum import auto

from shared.enums import (
    AccountStatus,
    AccountType,
    AlertChannel,
    AlertSeverity,
    ApiVersion,
    AssetClass,
    BacktestStatus,
    BrokerStatus,
    CacheStrategy,
    CircuitBreakerState,
    CurrencyPair,
    DataProvider,
    DataQuality,
    ErrorCategory,
    ErrorCode,
    EventPriority,
    EventType,
    ExecutionStrategy,
    HttpMethod,
    LicenseStatus,
    MarketRegime,
    MarketSession,
    MetricType,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionDirection,
    PositionSizingMethod,
    PositionStatus,
    RegimeDetectionMethod,
    ResponseStatus,
    RiskRuleType,
    RiskSeverity,
    ServiceStatus,
    SignalConfidence,
    SignalSource,
    SignalType,
    StrategyExecutionMode,
    StrategyStatus,
    StrategyType,
    StrEnum,
    SubscriptionTier,
    Timeframe,
    TradeStatus,
    UserRole,
    UserStatus,
    WalkForwardType,
)


class TestStrEnum:
    """Test base StrEnum class."""

    def test_str_enum_value(self):
        """Test StrEnum returns lowercase string value."""

        class TestEnum(StrEnum):
            TEST_VALUE = auto()

        assert str(TestEnum.TEST_VALUE) == "test_value"
        assert TestEnum.TEST_VALUE.value == "test_value"


class TestTradingEnums:
    """Test trading-related enums."""

    def test_order_side(self):
        """Test OrderSide enum."""
        assert OrderSide.BUY.value == "buy"
        assert OrderSide.SELL.value == "sell"
        assert str(OrderSide.BUY) == "buy"

    def test_order_type(self):
        """Test OrderType enum."""
        assert OrderType.MARKET.value == "market"
        assert OrderType.LIMIT.value == "limit"
        assert OrderType.STOP.value == "stop"
        assert OrderType.STOP_LIMIT.value == "stop_limit"
        assert OrderType.TRAILING_STOP.value == "trailing_stop"
        assert OrderType.OCO.value == "one_cancels_other"

    def test_order_status(self):
        """Test OrderStatus enum."""
        assert OrderStatus.PENDING.value == "pending"
        assert OrderStatus.SUBMITTED.value == "submitted"
        assert OrderStatus.PARTIAL.value == "partial"
        assert OrderStatus.FILLED.value == "filled"
        assert OrderStatus.CANCELLED.value == "cancelled"
        assert OrderStatus.REJECTED.value == "rejected"
        assert OrderStatus.EXPIRED.value == "expired"

    def test_position_direction(self):
        """Test PositionDirection enum."""
        assert PositionDirection.LONG.value == "long"
        assert PositionDirection.SHORT.value == "short"

    def test_position_status(self):
        """Test PositionStatus enum."""
        assert PositionStatus.PENDING.value == "pending"
        assert PositionStatus.OPEN.value == "open"
        assert PositionStatus.MODIFIED.value == "modified"
        assert PositionStatus.CLOSING.value == "closing"
        assert PositionStatus.CLOSED.value == "closed"
        assert PositionStatus.REJECTED.value == "rejected"

    def test_trade_status(self):
        """Test TradeStatus enum."""
        assert TradeStatus.OPENED.value == "opened"
        assert TradeStatus.CLOSED.value == "closed"
        assert TradeStatus.PARTIALLY_CLOSED.value == "partially_closed"


class TestSignalEnums:
    """Test signal-related enums."""

    def test_signal_type(self):
        """Test SignalType enum."""
        assert SignalType.ENTRY.value == "entry"
        assert SignalType.EXIT.value == "exit"
        assert SignalType.MODIFY.value == "modify"
        assert SignalType.CANCEL.value == "cancel"

    def test_signal_confidence(self):
        """Test SignalConfidence enum (IntEnum)."""
        assert SignalConfidence.VERY_LOW.value == 1
        assert SignalConfidence.LOW.value == 2
        assert SignalConfidence.MEDIUM.value == 3
        assert SignalConfidence.HIGH.value == 4
        assert SignalConfidence.VERY_HIGH.value == 5

    def test_signal_source(self):
        """Test SignalSource enum."""
        assert SignalSource.STRATEGY.value == "strategy"
        assert SignalSource.MANUAL.value == "manual"
        assert SignalSource.AI_ASSIST.value == "ai_assist"
        assert SignalSource.SYSTEM.value == "system"


class TestMarketDataEnums:
    """Test market data-related enums."""

    def test_timeframe(self):
        """Test Timeframe enum."""
        assert Timeframe.TICK.value == "tick"
        assert Timeframe.M1.value == "M1"
        assert Timeframe.M5.value == "M5"
        assert Timeframe.M15.value == "M15"
        assert Timeframe.M30.value == "M30"
        assert Timeframe.H1.value == "H1"
        assert Timeframe.H4.value == "H4"
        assert Timeframe.D1.value == "D1"
        assert Timeframe.W1.value == "W1"
        assert Timeframe.MN.value == "MN"

    def test_data_provider(self):
        """Test DataProvider enum."""
        assert DataProvider.BROKER.value == "broker"
        assert DataProvider.DUKASCOPY.value == "dukascopy"
        assert DataProvider.OANDA.value == "oanda"
        assert DataProvider.FXCM.value == "fxcm"
        assert DataProvider.FOREX_COM.value == "forex_com"
        assert DataProvider.HISTORICAL_FILE.value == "historical_file"

    def test_data_quality(self):
        """Test DataQuality enum."""
        assert DataQuality.GOOD.value == "good"
        assert DataQuality.SUSPECT.value == "suspect"
        assert DataQuality.BAD.value == "bad"
        assert DataQuality.MISSING.value == "missing"
        assert DataQuality.RECOVERED.value == "recovered"

    def test_market_session(self):
        """Test MarketSession enum."""
        assert MarketSession.ASIAN.value == "asian"
        assert MarketSession.EUROPEAN.value == "european"
        assert MarketSession.LONDON.value == "london"
        assert MarketSession.NEW_YORK.value == "new_york"
        assert MarketSession.OVERLAP.value == "overlap"
        assert MarketSession.CLOSED.value == "closed"


class TestInstrumentEnums:
    """Test instrument-related enums."""

    def test_asset_class(self):
        """Test AssetClass enum."""
        assert AssetClass.FOREX.value == "forex"
        assert AssetClass.CRYPTO.value == "crypto"
        assert AssetClass.COMMODITY.value == "commodity"
        assert AssetClass.INDEX.value == "index"
        assert AssetClass.STOCK.value == "stock"
        assert AssetClass.CFD.value == "cfd"

    def test_currency_pair(self):
        """Test CurrencyPair enum."""
        assert CurrencyPair.EUR_USD.value == "EUR/USD"
        assert CurrencyPair.GBP_USD.value == "GBP/USD"
        assert CurrencyPair.USD_JPY.value == "USD/JPY"
        assert CurrencyPair.USD_CHF.value == "USD/CHF"
        assert CurrencyPair.AUD_USD.value == "AUD/USD"
        assert CurrencyPair.NZD_USD.value == "NZD/USD"
        assert CurrencyPair.USD_CAD.value == "USD/CAD"
        assert CurrencyPair.EUR_GBP.value == "EUR/GBP"
        assert CurrencyPair.EUR_JPY.value == "EUR/JPY"
        assert CurrencyPair.GBP_JPY.value == "GBP/JPY"


class TestRiskEnums:
    """Test risk management enums."""

    def test_risk_rule_type(self):
        """Test RiskRuleType enum."""
        assert RiskRuleType.POSITION_SIZING.value == "position_sizing"
        assert RiskRuleType.PORTFOLIO_EXPOSURE.value == "portfolio_exposure"
        assert RiskRuleType.DAILY_LOSS_LIMIT.value == "daily_loss_limit"
        assert RiskRuleType.WEEKLY_LOSS_LIMIT.value == "weekly_loss_limit"
        assert RiskRuleType.MONTHLY_LOSS_LIMIT.value == "monthly_loss_limit"
        assert RiskRuleType.MAX_DRAWDOWN.value == "max_drawdown"
        assert RiskRuleType.CORRELATION_LIMIT.value == "correlation_limit"
        assert RiskRuleType.STOP_LOSS.value == "stop_loss"
        assert RiskRuleType.TAKE_PROFIT.value == "take_profit"

    def test_risk_severity(self):
        """Test RiskSeverity enum."""
        assert RiskSeverity.LOW.value == "low"
        assert RiskSeverity.MEDIUM.value == "medium"
        assert RiskSeverity.HIGH.value == "high"
        assert RiskSeverity.CRITICAL.value == "critical"

    def test_position_sizing_method(self):
        """Test PositionSizingMethod enum."""
        assert PositionSizingMethod.FIXED.value == "fixed"
        assert PositionSizingMethod.PERCENTAGE_EQUITY.value == "percentage_equity"
        assert PositionSizingMethod.VOLATILITY_BASED.value == "volatility_based"
        assert PositionSizingMethod.KELLY_CAPPED.value == "kelly_capped"
        assert PositionSizingMethod.RISK_PARITY.value == "risk_parity"


class TestExecutionEnums:
    """Test execution-related enums."""

    def test_execution_strategy(self):
        """Test ExecutionStrategy enum."""
        assert ExecutionStrategy.MARKET.value == "market"
        assert ExecutionStrategy.LIMIT.value == "limit"
        assert ExecutionStrategy.ICEBERG.value == "iceberg"
        assert ExecutionStrategy.TWAP.value == "twap"
        assert ExecutionStrategy.VWAP.value == "vwap"
        assert ExecutionStrategy.SMART.value == "smart"

    def test_broker_status(self):
        """Test BrokerStatus enum."""
        assert BrokerStatus.ONLINE.value == "online"
        assert BrokerStatus.OFFLINE.value == "offline"
        assert BrokerStatus.DEGRADED.value == "degraded"
        assert BrokerStatus.RATE_LIMITED.value == "rate_limited"
        assert BrokerStatus.MAINTENANCE.value == "maintenance"


class TestMarketRegimeEnums:
    """Test market regime enums."""

    def test_market_regime(self):
        """Test MarketRegime enum."""
        assert MarketRegime.TRENDING_BULLISH.value == "trending_bullish"
        assert MarketRegime.TRENDING_BEARISH.value == "trending_bearish"
        assert MarketRegime.RANGING.value == "ranging"
        assert MarketRegime.VOLATILE.value == "volatile"
        assert MarketRegime.QUIET.value == "quiet"
        assert MarketRegime.UNKNOWN.value == "unknown"
        assert MarketRegime.TRANSITIONING.value == "transitioning"

    def test_regime_detection_method(self):
        """Test RegimeDetectionMethod enum."""
        assert RegimeDetectionMethod.ADF_TEST.value == "adf_test"
        assert RegimeDetectionMethod.HURST_EXPONENT.value == "hurst_exponent"
        assert RegimeDetectionMethod.HIDDEN_MARKOV.value == "hidden_markov"
        assert RegimeDetectionMethod.GAUSSIAN_MIXTURE.value == "gaussian_mixture"
        assert RegimeDetectionMethod.BOLLINGER_BANDS.value == "bollinger_bands"
        assert RegimeDetectionMethod.ATR_VOLATILITY.value == "atr_volatility"
        assert RegimeDetectionMethod.RANDOM_FOREST.value == "random_forest"


class TestAccountEnums:
    """Test account-related enums."""

    def test_account_type(self):
        """Test AccountType enum."""
        assert AccountType.LIVE.value == "live"
        assert AccountType.PAPER.value == "paper"
        assert AccountType.BACKTEST.value == "backtest"
        assert AccountType.DEMO.value == "demo"

    def test_account_status(self):
        """Test AccountStatus enum."""
        assert AccountStatus.ACTIVE.value == "active"
        assert AccountStatus.INACTIVE.value == "inactive"
        assert AccountStatus.SUSPENDED.value == "suspended"
        assert AccountStatus.CLOSED.value == "closed"


class TestUserEnums:
    """Test user-related enums."""

    def test_user_role(self):
        """Test UserRole enum."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.TRADER.value == "trader"
        assert UserRole.ANALYST.value == "analyst"
        assert UserRole.VIEWER.value == "viewer"
        assert UserRole.API_ONLY.value == "api_only"

    def test_user_status(self):
        """Test UserStatus enum."""
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.INACTIVE.value == "inactive"
        assert UserStatus.SUSPENDED.value == "suspended"
        assert UserStatus.BANNED.value == "banned"
        assert UserStatus.PENDING_VERIFICATION.value == "pending_verification"


class TestStrategyEnums:
    """Test strategy-related enums."""

    def test_strategy_status(self):
        """Test StrategyStatus enum."""
        assert StrategyStatus.ACTIVE.value == "active"
        assert StrategyStatus.INACTIVE.value == "inactive"
        assert StrategyStatus.ERROR.value == "error"
        assert StrategyStatus.PAUSED.value == "paused"
        assert StrategyStatus.STOPPED.value == "stopped"
        assert StrategyStatus.INITIALIZING.value == "initializing"

    def test_strategy_type(self):
        """Test StrategyType enum."""
        assert StrategyType.TREND_FOLLOWING.value == "trend_following"
        assert StrategyType.MEAN_REVERSION.value == "mean_reversion"
        assert StrategyType.BREAKOUT.value == "breakout"
        assert StrategyType.MOMENTUM.value == "momentum"
        assert StrategyType.GRID.value == "grid"
        assert StrategyType.MARTINGALE.value == "martingale"
        assert StrategyType.ARBITRAGE.value == "arbitrage"
        assert StrategyType.CUSTOM.value == "custom"

    def test_strategy_execution_mode(self):
        """Test StrategyExecutionMode enum."""
        assert StrategyExecutionMode.REAL_TIME.value == "real_time"
        assert StrategyExecutionMode.BACKTEST.value == "backtest"
        assert StrategyExecutionMode.PAPER.value == "paper"
        assert StrategyExecutionMode.OPTIMIZATION.value == "optimization"
        assert StrategyExecutionMode.WALK_FORWARD.value == "walk_forward"


class TestSystemEnums:
    """Test system-related enums."""

    def test_service_status(self):
        """Test ServiceStatus enum."""
        assert ServiceStatus.HEALTHY.value == "healthy"
        assert ServiceStatus.DEGRADED.value == "degraded"
        assert ServiceStatus.DOWN.value == "down"
        assert ServiceStatus.STARTING.value == "starting"
        assert ServiceStatus.MAINTENANCE.value == "maintenance"

    def test_cache_strategy(self):
        """Test CacheStrategy enum."""
        assert CacheStrategy.CACHE_ASIDE.value == "cache_aside"
        assert CacheStrategy.WRITE_THROUGH.value == "write_through"
        assert CacheStrategy.WRITE_BACK.value == "write_back"
        assert CacheStrategy.TTL_ONLY.value == "ttl_only"

    def test_circuit_breaker_state(self):
        """Test CircuitBreakerState enum."""
        assert CircuitBreakerState.CLOSED.value == "closed"
        assert CircuitBreakerState.OPEN.value == "open"
        assert CircuitBreakerState.HALF_OPEN.value == "half_open"

    def test_event_priority(self):
        """Test EventPriority enum (IntEnum)."""
        assert EventPriority.LOW.value == 0
        assert EventPriority.NORMAL.value == 1
        assert EventPriority.HIGH.value == 2
        assert EventPriority.CRITICAL.value == 3


class TestSubscriptionEnums:
    """Test subscription/license enums."""

    def test_subscription_tier(self):
        """Test SubscriptionTier enum."""
        assert SubscriptionTier.FREE.value == "free"
        assert SubscriptionTier.BASIC.value == "basic"
        assert SubscriptionTier.PROFESSIONAL.value == "professional"
        assert SubscriptionTier.ENTERPRISE.value == "enterprise"

    def test_license_status(self):
        """Test LicenseStatus enum."""
        assert LicenseStatus.ACTIVE.value == "active"
        assert LicenseStatus.EXPIRED.value == "expired"
        assert LicenseStatus.GRACE.value == "grace"
        assert LicenseStatus.SUSPENDED.value == "suspended"
        assert LicenseStatus.REVOKED.value == "revoked"


class TestBacktestEnums:
    """Test backtest-related enums."""

    def test_backtest_status(self):
        """Test BacktestStatus enum."""
        assert BacktestStatus.PENDING.value == "pending"
        assert BacktestStatus.RUNNING.value == "running"
        assert BacktestStatus.COMPLETED.value == "completed"
        assert BacktestStatus.FAILED.value == "failed"
        assert BacktestStatus.CANCELLED.value == "cancelled"

    def test_walk_forward_type(self):
        """Test WalkForwardType enum."""
        assert WalkForwardType.ROLLING.value == "rolling"
        assert WalkForwardType.ANCHORED.value == "anchored"
        assert WalkForwardType.CUSTOM.value == "custom"


class TestMonitoringEnums:
    """Test monitoring-related enums."""

    def test_alert_severity(self):
        """Test AlertSeverity enum."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"

    def test_alert_channel(self):
        """Test AlertChannel enum."""
        assert AlertChannel.EMAIL.value == "email"
        assert AlertChannel.SMS.value == "sms"
        assert AlertChannel.WEBHOOK.value == "webhook"
        assert AlertChannel.SLACK.value == "slack"
        assert AlertChannel.TELEGRAM.value == "telegram"
        assert AlertChannel.PUSH.value == "push"

    def test_metric_type(self):
        """Test MetricType enum."""
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.SUMMARY.value == "summary"
        assert MetricType.TIMER.value == "timer"


class TestAPIEnums:
    """Test API-related enums."""

    def test_http_method(self):
        """Test HttpMethod enum."""
        assert HttpMethod.GET.value == "GET"
        assert HttpMethod.POST.value == "POST"
        assert HttpMethod.PUT.value == "PUT"
        assert HttpMethod.PATCH.value == "PATCH"
        assert HttpMethod.DELETE.value == "DELETE"
        assert HttpMethod.HEAD.value == "HEAD"
        assert HttpMethod.OPTIONS.value == "OPTIONS"

    def test_api_version(self):
        """Test ApiVersion enum."""
        assert ApiVersion.V1.value == "v1"
        assert ApiVersion.V2.value == "v2"

    def test_response_status(self):
        """Test ResponseStatus enum."""
        assert ResponseStatus.SUCCESS.value == "success"
        assert ResponseStatus.ERROR.value == "error"
        assert ResponseStatus.FAILURE.value == "failure"
        assert ResponseStatus.PENDING.value == "pending"


class TestErrorEnums:
    """Test error-related enums."""

    def test_error_category(self):
        """Test ErrorCategory enum."""
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.AUTHENTICATION.value == "authentication"
        assert ErrorCategory.AUTHORIZATION.value == "authorization"
        assert ErrorCategory.NOT_FOUND.value == "not_found"
        assert ErrorCategory.CONFLICT.value == "conflict"
        assert ErrorCategory.RATE_LIMIT.value == "rate_limit"
        assert ErrorCategory.INTERNAL.value == "internal"
        assert ErrorCategory.EXTERNAL.value == "external"
        assert ErrorCategory.TIMEOUT.value == "timeout"


class TestEventEnums:
    """Test event-related enums."""

    def test_event_type_market_data(self):
        """Test market data event types."""
        assert EventType.TICK_RECEIVED.value == "market.tick.received"
        assert EventType.BAR_COMPLETED.value == "market.bar.completed"
        assert EventType.REGIME_CHANGED.value == "market.regime.changed"
        assert EventType.SESSION_CHANGED.value == "market.session.changed"
        assert EventType.DATA_QUALITY_ALERT.value == "market.data_quality.alert"
        assert EventType.DATA_GAP_DETECTED.value == "market.data_gap.detected"

    def test_event_type_signals(self):
        """Test signal event types."""
        assert EventType.SIGNAL_GENERATED.value == "signal.generated"
        assert EventType.SIGNAL_VALIDATED.value == "signal.validated"
        assert EventType.SIGNAL_REJECTED.value == "signal.rejected"

    def test_event_type_orders(self):
        """Test order event types."""
        assert EventType.ORDER_CREATED.value == "order.created"
        assert EventType.ORDER_SUBMITTED.value == "order.submitted"
        assert EventType.ORDER_FILLED.value == "order.filled"
        assert EventType.ORDER_PARTIALLY_FILLED.value == "order.partially_filled"
        assert EventType.ORDER_CANCELLED.value == "order.cancelled"
        assert EventType.ORDER_REJECTED.value == "order.rejected"

    def test_event_type_positions(self):
        """Test position event types."""
        assert EventType.POSITION_OPENED.value == "position.opened"
        assert EventType.POSITION_MODIFIED.value == "position.modified"
        assert EventType.POSITION_CLOSED.value == "position.closed"
        assert EventType.POSITION_RISK_ALERT.value == "position.risk_alert"

    def test_event_type_risk(self):
        """Test risk event types."""
        assert EventType.LIMIT_BREACHED.value == "risk.limit_breached"
        assert EventType.MARGIN_CALL.value == "risk.margin_call"
        assert EventType.EXPOSURE_WARNING.value == "risk.exposure_warning"
        assert EventType.CIRCUIT_BREAKER_TRIPPED.value == "risk.circuit_breaker_tripped"
        assert EventType.EMERGENCY_SHUTDOWN.value == "risk.emergency_shutdown"

    def test_event_type_accounts(self):
        """Test account event types."""
        assert EventType.ACCOUNT_CREATED.value == "account.created"
        assert EventType.ACCOUNT_UPDATED.value == "account.updated"
        assert EventType.BALANCE_CHANGED.value == "account.balance_changed"

    def test_event_type_users(self):
        """Test user event types."""
        assert EventType.USER_CREATED.value == "user.created"
        assert EventType.USER_UPDATED.value == "user.updated"
        assert EventType.USER_DELETED.value == "user.deleted"
        assert EventType.USER_LOGIN.value == "user.login"
        assert EventType.USER_LOGOUT.value == "user.logout"

    def test_event_type_system(self):
        """Test system event types."""
        assert EventType.SERVICE_HEALTHY.value == "system.service.healthy"
        assert EventType.SERVICE_DEGRADED.value == "system.service.degraded"
        assert EventType.SERVICE_DOWN.value == "system.service.down"
        assert EventType.CONFIG_CHANGED.value == "system.config.changed"
        assert EventType.DEPLOYMENT_STARTED.value == "system.deployment.started"
        assert EventType.DEPLOYMENT_COMPLETED.value == "system.deployment.completed"
        assert EventType.DEPLOYMENT_FAILED.value == "system.deployment.failed"


class TestErrorCodeEnum:
    """Test ErrorCode enum."""

    def test_validation_error_codes(self):
        """Test validation error codes."""
        assert ErrorCode.VALIDATION_ERROR.value == "VALIDATION_ERROR"
        assert ErrorCode.INVALID_INPUT.value == "INVALID_INPUT"
        assert ErrorCode.MISSING_REQUIRED_FIELD.value == "MISSING_REQUIRED_FIELD"
        assert ErrorCode.INVALID_FORMAT.value == "INVALID_FORMAT"

    def test_auth_error_codes(self):
        """Test authentication error codes."""
        assert ErrorCode.UNAUTHORIZED.value == "UNAUTHORIZED"
        assert ErrorCode.FORBIDDEN.value == "FORBIDDEN"
        assert ErrorCode.TOKEN_EXPIRED.value == "TOKEN_EXPIRED"
        assert ErrorCode.INVALID_CREDENTIALS.value == "INVALID_CREDENTIALS"
        assert ErrorCode.MFA_REQUIRED.value == "MFA_REQUIRED"
        assert ErrorCode.ACCOUNT_LOCKED.value == "ACCOUNT_LOCKED"

    def test_business_logic_error_codes(self):
        """Test business logic error codes."""
        assert ErrorCode.INSUFFICIENT_FUNDS.value == "INSUFFICIENT_FUNDS"
        assert ErrorCode.POSITION_LIMIT_EXCEEDED.value == "POSITION_LIMIT_EXCEEDED"
        assert ErrorCode.RISK_LIMIT_BREACHED.value == "RISK_LIMIT_BREACHED"
        assert ErrorCode.ORDER_REJECTED.value == "ORDER_REJECTED"
        assert ErrorCode.INVALID_STRATEGY.value == "INVALID_STRATEGY"
        assert ErrorCode.INVALID_SIGNAL.value == "INVALID_SIGNAL"

    def test_system_error_codes(self):
        """Test system error codes."""
        assert ErrorCode.INTERNAL_ERROR.value == "INTERNAL_ERROR"
        assert ErrorCode.SERVICE_UNAVAILABLE.value == "SERVICE_UNAVAILABLE"
        assert ErrorCode.EXTERNAL_API_ERROR.value == "EXTERNAL_API_ERROR"
        assert ErrorCode.RATE_LIMIT_EXCEEDED.value == "RATE_LIMIT_EXCEEDED"
        assert ErrorCode.TIMEOUT.value == "TIMEOUT"
        assert ErrorCode.DATABASE_ERROR.value == "DATABASE_ERROR"
        assert ErrorCode.CACHE_ERROR.value == "CACHE_ERROR"

    def test_data_error_codes(self):
        """Test data error codes."""
        assert ErrorCode.DATA_NOT_FOUND.value == "DATA_NOT_FOUND"
        assert ErrorCode.DATA_INTEGRITY_ERROR.value == "DATA_INTEGRITY_ERROR"
        assert ErrorCode.DATA_STALE.value == "DATA_STALE"
        assert ErrorCode.INVALID_DATA_FORMAT.value == "INVALID_DATA_FORMAT"

    def test_licensing_error_codes(self):
        """Test licensing error codes."""
        assert ErrorCode.LICENSE_EXPIRED.value == "LICENSE_EXPIRED"
        assert ErrorCode.FEATURE_NOT_AVAILABLE.value == "FEATURE_NOT_AVAILABLE"
        assert ErrorCode.SUBSCRIPTION_REQUIRED.value == "SUBSCRIPTION_REQUIRED"
        assert ErrorCode.USAGE_LIMIT_EXCEEDED.value == "USAGE_LIMIT_EXCEEDED"
