"""
Project ORION - Shared Constants

Comprehensive constants used across the platform covering:
- Trading limits and defaults
- Market data timeframes
- Risk management thresholds
- Performance targets
- System configuration defaults
- Time and session constants

All constants are immutable by convention (UPPER_CASE naming).
"""

from typing import Final

# ──────────────────────────────────────────────
# Trading Constants
# ──────────────────────────────────────────────
MAX_POSITION_SIZE: Final[float] = 1_000_000.0
"""Maximum position size in base currency units."""

MIN_POSITION_SIZE: Final[float] = 1_000.0
"""Minimum position size in base currency units."""

DEFAULT_LEVERAGE: Final[int] = 100
"""Default leverage for Forex trading."""

MAX_LEVERAGE: Final[int] = 500
"""Maximum allowed leverage."""

MAX_CONCURRENT_STRATEGIES: Final[int] = 50
"""Maximum number of concurrent strategies."""

MAX_CONCURRENT_POSITIONS: Final[int] = 100
"""Maximum number of concurrent positions."""

DEFAULT_SLIPPAGE_PIPS: Final[float] = 2.0
"""Default slippage in pips."""

MAX_SLIPPAGE_PIPS: Final[float] = 10.0
"""Maximum allowed slippage in pips."""

# ──────────────────────────────────────────────
# Market Data Constants
# ──────────────────────────────────────────────
DEFAULT_TIMEOUT: Final[int] = 30
"""Default timeout in seconds for API calls."""

MAX_TICK_RATE: Final[int] = 10_000
"""Maximum ticks per second per currency pair."""

MAX_CURRENCY_PAIRS: Final[int] = 50
"""Maximum number of concurrent currency pairs."""

MAX_DATA_PROVIDERS: Final[int] = 5
"""Maximum number of data providers."""

DEFAULT_DATA_RETENTION_DAYS: Final[int] = 365
"""Default data retention period in days."""

TICK_DATA_RETENTION_DAYS: Final[int] = 30
"""Tick data retention in days."""

MINUTE_DATA_RETENTION_DAYS: Final[int] = 365
"""Minute data retention in days."""

HOURLY_DATA_RETENTION_DAYS: Final[int] = 1825
"""Hourly data retention in days (5 years)."""

DAILY_DATA_RETENTION_DAYS: Final[int] = 0
"""Daily data retention in days (0 = indefinite)."""

# ──────────────────────────────────────────────
# Risk Management Constants
# ──────────────────────────────────────────────
MAX_PORTFOLIO_EXPOSURE: Final[float] = 0.10
"""Maximum portfolio exposure as fraction of equity."""

MAX_POSITION_EXPOSURE: Final[float] = 0.02
"""Maximum single position exposure as fraction of equity."""

MAX_DAILY_LOSS: Final[float] = 0.05
"""Maximum daily loss as fraction of equity."""

MAX_WEEKLY_LOSS: Final[float] = 0.10
"""Maximum weekly loss as fraction of equity."""

MAX_MONTHLY_LOSS: Final[float] = 0.20
"""Maximum monthly loss as fraction of equity."""

MAX_DRAWDOWN: Final[float] = 0.25
"""Maximum drawdown as fraction of peak equity."""

DEFAULT_RISK_PER_TRADE: Final[float] = 0.01
"""Default risk per trade as fraction of equity."""

MIN_RISK_REWARD_RATIO: Final[float] = 1.5
"""Minimum risk/reward ratio for trades."""

MAX_CORRELATION_LIMIT: Final[float] = 0.70
"""Maximum correlation between simultaneous positions."""

# ──────────────────────────────────────────────
# Performance Constants
# ──────────────────────────────────────────────
MAX_MARKET_DATA_LATENCY_MS: Final[int] = 50
"""Maximum acceptable market data latency in milliseconds."""

MAX_EXECUTION_LATENCY_MS: Final[int] = 100
"""Maximum acceptable execution latency in milliseconds."""

MAX_API_RESPONSE_TIME_MS: Final[int] = 200
"""Maximum API response time (95th percentile) in milliseconds."""

MAX_DASHBOARD_LOAD_TIME_MS: Final[int] = 3_000
"""Maximum dashboard load time in milliseconds."""

MIN_UPTIME_PERCENTAGE: Final[float] = 99.5
"""Minimum system uptime percentage."""

MAX_CONCURRENT_USERS: Final[int] = 100
"""Maximum concurrent users."""

MAX_API_REQUESTS_PER_SECOND: Final[int] = 1_000
"""Maximum API requests per second."""

MAX_ORDERS_PER_SECOND: Final[int] = 100
"""Maximum orders per second."""

# ──────────────────────────────────────────────
# Backtesting Constants
# ──────────────────────────────────────────────
BACKTEST_MAX_YEARS: Final[int] = 10
"""Maximum backtest duration in years."""

BACKTEST_MIN_YEARS: Final[float] = 0.5
"""Minimum backtest duration in years."""

BACKTEST_DEFAULT_INITIAL_CAPITAL: Final[float] = 100_000.0
"""Default initial capital for backtests."""

OPTIMIZATION_MAX_PARAMETER_COMBINATIONS: Final[int] = 1_000_000
"""Maximum parameter combinations for optimization."""

MONTE_CARLO_DEFAULT_SIMULATIONS: Final[int] = 10_000
"""Default number of Monte Carlo simulations."""

# ──────────────────────────────────────────────
# Time Constants (in seconds)
# ──────────────────────────────────────────────
SECONDS_IN_MINUTE: Final[int] = 60
SECONDS_IN_HOUR: Final[int] = 3_600
SECONDS_IN_DAY: Final[int] = 86_400
SECONDS_IN_WEEK: Final[int] = 604_800
SECONDS_IN_MONTH: Final[int] = 2_592_000  # 30 days
SECONDS_IN_YEAR: Final[int] = 31_536_000  # 365 days

MINUTES_IN_HOUR: Final[int] = 60
HOURS_IN_DAY: Final[int] = 24
DAYS_IN_WEEK: Final[int] = 7
WEEKS_IN_MONTH: Final[float] = 4.33
MONTHS_IN_YEAR: Final[int] = 12

# ──────────────────────────────────────────────
# Session Constants
# ──────────────────────────────────────────────
SESSION_TOKEN_TTL_SECONDS: Final[int] = 1_800
"""Session token TTL in seconds (30 minutes)."""

REFRESH_TOKEN_TTL_SECONDS: Final[int] = 604_800
"""Refresh token TTL in seconds (7 days)."""

API_KEY_TTL_SECONDS: Final[int] = 31_536_000
"""API key TTL in seconds (1 year)."""

MAX_LOGIN_ATTEMPTS: Final[int] = 5
"""Maximum failed login attempts before lockout."""

LOGIN_LOCKOUT_SECONDS: Final[int] = 900
"""Login lockout duration in seconds (15 minutes)."""

PASSWORD_MIN_LENGTH: Final[int] = 12
"""Minimum password length."""

# ──────────────────────────────────────────────
# Retry Constants
# ──────────────────────────────────────────────
DEFAULT_RETRY_ATTEMPTS: Final[int] = 3
"""Default number of retry attempts."""

DEFAULT_RETRY_DELAY: Final[float] = 1.0
"""Default initial retry delay in seconds."""

DEFAULT_RETRY_BACKOFF: Final[float] = 2.0
"""Default retry backoff multiplier."""

MAX_RETRY_DELAY: Final[float] = 60.0
"""Maximum retry delay in seconds."""

# ──────────────────────────────────────────────
# Circuit Breaker Constants
# ──────────────────────────────────────────────
CIRCUIT_BREAKER_FAILURE_THRESHOLD: Final[int] = 5
"""Number of failures before circuit opens."""

CIRCUIT_BREAKER_RECOVERY_TIMEOUT: Final[float] = 30.0
"""Seconds before circuit breaker attempts recovery."""

CIRCUIT_BREAKER_HALF_OPEN_MAX_REQUESTS: Final[int] = 3
"""Maximum requests in half-open state."""

# ──────────────────────────────────────────────
# Database Constants
# ──────────────────────────────────────────────
DEFAULT_PAGE_SIZE: Final[int] = 100
"""Default pagination page size."""

MAX_PAGE_SIZE: Final[int] = 1_000
"""Maximum pagination page size."""

DEFAULT_QUERY_TIMEOUT_SECONDS: Final[int] = 30
"""Default database query timeout."""

MAX_BATCH_SIZE: Final[int] = 1_000
"""Maximum batch operation size."""

# ──────────────────────────────────────────────
# Cache Constants
# ──────────────────────────────────────────────
DEFAULT_CACHE_TTL_SECONDS: Final[int] = 300
"""Default cache TTL in seconds (5 minutes)."""

DEFAULT_CACHE_MAX_SIZE: Final[int] = 10_000
"""Default maximum cache entries."""

# ──────────────────────────────────────────────
# Monitoring Constants
# ──────────────────────────────────────────────
METRICS_RETENTION_DAYS: Final[int] = 90
"""Metrics retention period in days."""

LOG_RETENTION_DAYS: Final[int] = 90
"""Log retention period in days."""

AUDIT_LOG_RETENTION_YEARS: Final[int] = 7
"""Audit log retention period in years."""

HEALTH_CHECK_INTERVAL_SECONDS: Final[int] = 30
"""Health check interval in seconds."""

# ──────────────────────────────────────────────
# Precision Constants
# ──────────────────────────────────────────────
PRICE_PRECISION: Final[int] = 5
"""Decimal places for price values."""

VOLUME_PRECISION: Final[int] = 2
"""Decimal places for volume values."""

PNL_PRECISION: Final[int] = 2
"""Decimal places for P&L values."""

PERCENTAGE_PRECISION: Final[int] = 4
"""Decimal places for percentage values (e.g., 0.0123 = 1.23%)."""

RATIO_PRECISION: Final[int] = 4
"""Decimal places for ratio values."""

# ──────────────────────────────────────────────
# Default Values
# ──────────────────────────────────────────────
DEFAULT_CURRENCY: Final[str] = "USD"
"""Default base currency."""

DEFAULT_BROKER: Final[str] = "simulated"
"""Default broker name."""

DEFAULT_TIMEFRAME: Final[str] = "M5"
"""Default timeframe."""

DEFAULT_ENCODING: Final[str] = "utf-8"
"""Default text encoding."""

ORION_NAMESPACE: Final[str] = "orion"
"""Top-level namespace for all ORION resources."""
