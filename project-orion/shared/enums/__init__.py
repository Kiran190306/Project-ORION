"""
Project ORION - Shared Enums

Comprehensive enumeration definitions covering the entire platform domain.
Organized by domain context with clear naming conventions.

Usage:
    from shared.enums import OrderSide, OrderStatus, PositionDirection
"""

from enum import Enum, IntEnum, auto
from typing import Any, cast


class StrEnum(str, Enum):
    """Base string enum with mixin for JSON serialization."""

    def __str__(self) -> str:
        return cast(str, self.value)

    @staticmethod
    def _generate_next_value_(
        name: str, start: int, count: int, last_values: list[Any]
    ) -> Any:
        return name.lower()


# ─── Trading Enums ────────────────────────────────────────────


class OrderSide(StrEnum):
    """Direction of an order."""

    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    """Type of trading order."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    OCO = "one_cancels_other"


class OrderStatus(StrEnum):
    """Lifecycle status of an order."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionDirection(StrEnum):
    """Direction of a trading position."""

    LONG = "long"
    SHORT = "short"


class PositionStatus(StrEnum):
    """Lifecycle status of a position."""

    PENDING = "pending"
    OPEN = "open"
    MODIFIED = "modified"
    CLOSING = "closing"
    CLOSED = "closed"
    REJECTED = "rejected"


class TradeStatus(StrEnum):
    """Status of a completed trade."""

    OPENED = "opened"
    CLOSED = "closed"
    PARTIALLY_CLOSED = "partially_closed"


# ─── Signal Enums ─────────────────────────────────────────────


class SignalType(StrEnum):
    """Type of trading signal."""

    ENTRY = "entry"
    EXIT = "exit"
    MODIFY = "modify"
    CANCEL = "cancel"


class SignalConfidence(IntEnum):
    """Confidence level of a signal."""

    VERY_LOW = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    VERY_HIGH = 5


class SignalSource(StrEnum):
    """Source of a trading signal."""

    STRATEGY = "strategy"
    MANUAL = "manual"
    AI_ASSIST = "ai_assist"
    SYSTEM = "system"


# ─── Market Data Enums ────────────────────────────────────────


class Timeframe(StrEnum):
    """OHLC candle timeframe."""

    TICK = "tick"
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"
    MN = "MN"


class DataProvider(StrEnum):
    """Market data provider."""

    BROKER = "broker"
    DUKASCOPY = "dukascopy"
    OANDA = "oanda"
    FXCM = "fxcm"
    FOREX_COM = "forex_com"
    HISTORICAL_FILE = "historical_file"


class DataQuality(StrEnum):
    """Quality level of market data."""

    GOOD = "good"
    SUSPECT = "suspect"
    BAD = "bad"
    MISSING = "missing"
    RECOVERED = "recovered"


class MarketSession(StrEnum):
    """Forex market trading session."""

    ASIAN = "asian"
    EUROPEAN = "european"
    LONDON = "london"
    NEW_YORK = "new_york"
    OVERLAP = "overlap"
    CLOSED = "closed"


# ─── Instrument Enums ─────────────────────────────────────────


class AssetClass(StrEnum):
    """Asset class for trading instruments."""

    FOREX = "forex"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    INDEX = "index"
    STOCK = "stock"
    CFD = "cfd"


class CurrencyPair(StrEnum):
    """Major and minor currency pairs."""

    EUR_USD = "EUR/USD"
    GBP_USD = "GBP/USD"
    USD_JPY = "USD/JPY"
    USD_CHF = "USD/CHF"
    AUD_USD = "AUD/USD"
    NZD_USD = "NZD/USD"
    USD_CAD = "USD/CAD"
    EUR_GBP = "EUR/GBP"
    EUR_JPY = "EUR/JPY"
    EUR_CHF = "EUR/CHF"
    GBP_JPY = "GBP/JPY"
    GBP_CHF = "GBP/CHF"
    AUD_JPY = "AUD/JPY"
    NZD_JPY = "NZD/JPY"
    EUR_AUD = "EUR/AUD"
    GBP_AUD = "GBP/AUD"


# ─── Risk Enums ───────────────────────────────────────────────


class RiskRuleType(StrEnum):
    """Type of risk management rule."""

    POSITION_SIZING = "position_sizing"
    PORTFOLIO_EXPOSURE = "portfolio_exposure"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    WEEKLY_LOSS_LIMIT = "weekly_loss_limit"
    MONTHLY_LOSS_LIMIT = "monthly_loss_limit"
    MAX_DRAWDOWN = "max_drawdown"
    CORRELATION_LIMIT = "correlation_limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class RiskSeverity(StrEnum):
    """Severity level of a risk event."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PositionSizingMethod(StrEnum):
    """Method for calculating position size."""

    FIXED = "fixed"
    PERCENTAGE_EQUITY = "percentage_equity"
    VOLATILITY_BASED = "volatility_based"
    KELLY_CAPPED = "kelly_capped"
    RISK_PARITY = "risk_parity"


# ─── Execution Enums ──────────────────────────────────────────


class ExecutionStrategy(StrEnum):
    """Strategy for order execution."""

    MARKET = "market"
    LIMIT = "limit"
    ICEBERG = "iceberg"
    TWAP = "twap"
    VWAP = "vwap"
    SMART = "smart"


class BrokerStatus(StrEnum):
    """Status of a broker connection."""

    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    RATE_LIMITED = "rate_limited"
    MAINTENANCE = "maintenance"


# ─── Market Regime Enums ──────────────────────────────────────


class MarketRegime(StrEnum):
    """Detected market regime state."""

    TRENDING_BULLISH = "trending_bullish"
    TRENDING_BEARISH = "trending_bearish"
    RANGING = "ranging"
    VOLATILE = "volatile"
    QUIET = "quiet"
    UNKNOWN = "unknown"
    TRANSITIONING = "transitioning"


class RegimeDetectionMethod(StrEnum):
    """Method used to detect market regime."""

    ADF_TEST = "adf_test"
    HURST_EXPONENT = "hurst_exponent"
    HIDDEN_MARKOV = "hidden_markov"
    GAUSSIAN_MIXTURE = "gaussian_mixture"
    BOLLINGER_BANDS = "bollinger_bands"
    ATR_VOLATILITY = "atr_volatility"
    RANDOM_FOREST = "random_forest"


# ─── Account Enums ────────────────────────────────────────────


class AccountType(StrEnum):
    """Type of trading account."""

    LIVE = "live"
    PAPER = "paper"
    BACKTEST = "backtest"
    DEMO = "demo"


class AccountStatus(StrEnum):
    """Status of a trading account."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    CLOSED = "closed"


# ─── User Enums ───────────────────────────────────────────────


class UserRole(StrEnum):
    """Role of a platform user."""

    ADMIN = "admin"
    TRADER = "trader"
    ANALYST = "analyst"
    VIEWER = "viewer"
    API_ONLY = "api_only"


class UserStatus(StrEnum):
    """Status of a user account."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"
    PENDING_VERIFICATION = "pending_verification"


# ─── Strategy Enums ───────────────────────────────────────────


class StrategyStatus(StrEnum):
    """Status of a trading strategy."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PAUSED = "paused"
    STOPPED = "stopped"
    INITIALIZING = "initializing"


class StrategyType(StrEnum):
    """Type of trading strategy."""

    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    MOMENTUM = "momentum"
    GRID = "grid"
    MARTINGALE = "martingale"
    ARBITRAGE = "arbitrage"
    CUSTOM = "custom"


class StrategyExecutionMode(StrEnum):
    """Execution mode for a strategy."""

    REAL_TIME = "real_time"
    BACKTEST = "backtest"
    PAPER = "paper"
    OPTIMIZATION = "optimization"
    WALK_FORWARD = "walk_forward"


# ─── System Enums ─────────────────────────────────────────────


class ServiceStatus(StrEnum):
    """Operational status of a microservice."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    STARTING = "starting"
    MAINTENANCE = "maintenance"


class CacheStrategy(StrEnum):
    """Cache invalidation strategy."""

    CACHE_ASIDE = "cache_aside"
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"
    TTL_ONLY = "ttl_only"


class CircuitBreakerState(StrEnum):
    """State of a circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class EventPriority(IntEnum):
    """Priority level for event bus messages."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


# ─── Subscription/License Enums ───────────────────────────────


class SubscriptionTier(StrEnum):
    """Subscription tier for platform access."""

    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class LicenseStatus(StrEnum):
    """Status of a platform license."""

    ACTIVE = "active"
    EXPIRED = "expired"
    GRACE = "grace"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


# ─── Backtest Enums ───────────────────────────────────────────


class BacktestStatus(StrEnum):
    """Status of a backtest run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WalkForwardType(StrEnum):
    """Type of walk-forward analysis window."""

    ROLLING = "rolling"
    ANCHORED = "anchored"
    CUSTOM = "custom"


# ─── Monitoring Enums ─────────────────────────────────────────


class AlertSeverity(StrEnum):
    """Severity level of a monitoring alert."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(StrEnum):
    """Delivery channel for alerts."""

    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TELEGRAM = "telegram"
    PUSH = "push"


class MetricType(StrEnum):
    """Type of monitoring metric."""

    GAUGE = "gauge"
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    TIMER = "timer"


# ─── API Enums ────────────────────────────────────────────────


class HttpMethod(StrEnum):
    """HTTP method for API endpoints."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ApiVersion(StrEnum):
    """API version identifiers."""

    V1 = "v1"
    V2 = "v2"


class ResponseStatus(StrEnum):
    """Standard API response status."""

    SUCCESS = "success"
    ERROR = "error"
    FAILURE = "failure"
    PENDING = "pending"


# ─── Error/Domain Enums ───────────────────────────────────────


class ErrorCategory(StrEnum):
    """Category of system error."""

    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    RATE_LIMIT = "rate_limit"
    INTERNAL = "internal"
    EXTERNAL = "external"
    TIMEOUT = "timeout"


# ─── Event Enums ──────────────────────────────────────────────


class EventType(StrEnum):
    """Type of domain event for event bus."""

    # Market Data Events
    TICK_RECEIVED = "market.tick.received"
    BAR_COMPLETED = "market.bar.completed"
    REGIME_CHANGED = "market.regime.changed"
    SESSION_CHANGED = "market.session.changed"
    DATA_QUALITY_ALERT = "market.data_quality.alert"
    DATA_GAP_DETECTED = "market.data_gap.detected"

    # Signal Events
    SIGNAL_GENERATED = "signal.generated"
    SIGNAL_VALIDATED = "signal.validated"
    SIGNAL_REJECTED = "signal.rejected"

    # Order Events
    ORDER_CREATED = "order.created"
    ORDER_SUBMITTED = "order.submitted"
    ORDER_FILLED = "order.filled"
    ORDER_PARTIALLY_FILLED = "order.partially_filled"
    ORDER_CANCELLED = "order.cancelled"
    ORDER_REJECTED = "order.rejected"

    # Position Events
    POSITION_OPENED = "position.opened"
    POSITION_MODIFIED = "position.modified"
    POSITION_CLOSED = "position.closed"
    POSITION_RISK_ALERT = "position.risk_alert"

    # Risk Events
    LIMIT_BREACHED = "risk.limit_breached"
    MARGIN_CALL = "risk.margin_call"
    EXPOSURE_WARNING = "risk.exposure_warning"
    CIRCUIT_BREAKER_TRIPPED = "risk.circuit_breaker_tripped"
    EMERGENCY_SHUTDOWN = "risk.emergency_shutdown"

    # Account Events
    ACCOUNT_CREATED = "account.created"
    ACCOUNT_UPDATED = "account.updated"
    BALANCE_CHANGED = "account.balance_changed"

    # User Events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"

    # System Events
    SERVICE_HEALTHY = "system.service.healthy"
    SERVICE_DEGRADED = "system.service.degraded"
    SERVICE_DOWN = "system.service.down"
    CONFIG_CHANGED = "system.config.changed"
    DEPLOYMENT_STARTED = "system.deployment.started"
    DEPLOYMENT_COMPLETED = "system.deployment.completed"
    DEPLOYMENT_FAILED = "system.deployment.failed"


# ─── Error Code / Domain Enums ────────────────────────────────


class ErrorCode(StrEnum):
    """Standard error codes for the platform."""

    # Validation Errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"

    # Auth Errors
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    MFA_REQUIRED = "MFA_REQUIRED"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"

    # Business Logic Errors
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    POSITION_LIMIT_EXCEEDED = "POSITION_LIMIT_EXCEEDED"
    RISK_LIMIT_BREACHED = "RISK_LIMIT_BREACHED"
    ORDER_REJECTED = "ORDER_REJECTED"
    INVALID_STRATEGY = "INVALID_STRATEGY"
    INVALID_SIGNAL = "INVALID_SIGNAL"

    # System Errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    TIMEOUT = "TIMEOUT"
    DATABASE_ERROR = "DATABASE_ERROR"
    CACHE_ERROR = "CACHE_ERROR"

    # Data Errors
    DATA_NOT_FOUND = "DATA_NOT_FOUND"
    DATA_INTEGRITY_ERROR = "DATA_INTEGRITY_ERROR"
    DATA_STALE = "DATA_STALE"
    INVALID_DATA_FORMAT = "INVALID_DATA_FORMAT"

    # Licensing Errors
    LICENSE_EXPIRED = "LICENSE_EXPIRED"
    FEATURE_NOT_AVAILABLE = "FEATURE_NOT_AVAILABLE"
    SUBSCRIPTION_REQUIRED = "SUBSCRIPTION_REQUIRED"
    USAGE_LIMIT_EXCEEDED = "USAGE_LIMIT_EXCEEDED"
