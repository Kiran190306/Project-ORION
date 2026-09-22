"""Request and response DTOs for the Trading Engine API.

All models use Pydantic v2. Domain objects are never exposed directly —
they are translated at the application boundary.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")

# ─── Enums ───────────────────────────────────────────────────────────────


class TradeDirection(StrEnum):
    """Trade direction expressed as a DTO enum."""

    BUY = "buy"
    SELL = "sell"


# ─── Request Models ───────────────────────────────────────────────────────


class PaperTradeRequest(BaseModel):
    """Request body for POST /api/v1/paper-trade."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    symbol: str = Field(
        ...,
        min_length=3,
        max_length=12,
        description="Trading symbol, e.g. EURUSD",
        examples=["EURUSD"],
    )
    direction: TradeDirection = Field(
        ...,
        description="Trade direction: buy or sell",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Signal confidence 0–100",
    )
    entry_price: Decimal = Field(
        ...,
        gt=Decimal(0),
        description="Desired entry price",
    )
    stop_loss: Decimal | None = Field(
        None,
        gt=Decimal(0),
        description="Stop-loss price (optional)",
    )
    take_profit: Decimal | None = Field(
        None,
        gt=Decimal(0),
        description="Take-profit price (optional)",
    )
    position_size: Decimal = Field(
        ...,
        gt=Decimal(0),
        description="Position size in units",
    )

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        """Normalise symbol to uppercase."""
        return v.upper()


# ─── Response Models ──────────────────────────────────────────────────────


class PaperTradeResponse(BaseModel):
    """Response body for a successful paper trade execution."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    status: str
    symbol: str
    direction: str
    fill_price: Decimal | None = None
    filled_quantity: Decimal | None = None
    commission: Decimal | None = None
    is_paper: bool = True
    executed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthCheckDetail(BaseModel):
    """Detail for a single health check component."""

    model_config = ConfigDict(frozen=True)

    name: str
    status: str
    message: str = ""
    duration_ms: float = 0.0
    checked_at: str = ""


class HealthResponse(BaseModel):
    """Standard health response payload."""

    model_config = ConfigDict(frozen=True)

    status: str
    checks: list[HealthCheckDetail] = Field(default_factory=list)
    checked_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class LivenessResponse(BaseModel):
    """Simple liveness response — process is alive."""

    model_config = ConfigDict(frozen=True)

    status: str = "alive"
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class MetricsSnapshot(BaseModel):
    """JSON snapshot of all metrics (alternative to Prometheus text format)."""

    model_config = ConfigDict(frozen=True)

    metrics: dict[str, Any] = Field(default_factory=dict)
    exported_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ErrorResponse(BaseModel):
    """Standard error response for all error paths."""

    model_config = ConfigDict(frozen=True)

    error: str
    message: str
    detail: str | None = None
    correlation_id: str = ""
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ─── Account Models ────────────────────────────────────────────────────────


class AccountSummary(BaseModel):
    """Account summary with key financial metrics."""

    model_config = ConfigDict(frozen=True)

    balance: Decimal
    equity: Decimal
    available_cash: Decimal
    used_margin: Decimal
    free_margin: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    currency: str = "USD"
    is_paper: bool = True
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class AccountResponse(BaseModel):
    """Detailed account information."""

    model_config = ConfigDict(frozen=True)

    account_id: str
    broker_name: str
    account_number: str
    balance: Decimal
    equity: Decimal
    currency: str = "USD"
    leverage: int = 100
    is_live: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


# ─── Worker Models ────────────────────────────────────────────────────────


class WorkerStatusResponse(BaseModel):
    """Worker status information."""

    model_config = ConfigDict(frozen=True)

    enabled: bool
    state: str
    is_running: bool
    last_cycle_at: datetime | None = None
    next_cycle_at: datetime | None = None
    last_error: str | None = None
    uptime_seconds: float = 0.0
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class WorkerMetricsResponse(BaseModel):
    """Worker operational metrics."""

    model_config = ConfigDict(frozen=True)

    cycles_started: int = 0
    cycles_completed: int = 0
    cycles_failed: int = 0
    market_poll_failures: int = 0
    orders_submitted: int = 0
    risk_rejections: int = 0
    execution_failures: int = 0
    uptime_seconds: float = 0.0
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ─── Strategy Models ──────────────────────────────────────────────────────


class StrategyInfo(BaseModel):
    """Information about a trading strategy."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    type: str
    description: str
    timeframes: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    is_active: bool = True


class StrategyListResponse(BaseModel):
    """Response containing list of available strategies."""

    model_config = ConfigDict(frozen=True)

    strategies: list[StrategyInfo] = Field(default_factory=list)
    total: int = 0
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ─── Risk Models ────────────────────────────────────────────────────────


class RiskStatusResponse(BaseModel):
    """Risk engine status and metrics."""

    model_config = ConfigDict(frozen=True)

    status: str
    position_count: int = 0
    total_exposure: Decimal = Decimal(0)
    used_margin: Decimal = Decimal(0)
    free_margin: Decimal = Decimal(0)
    margin_level: float = 0.0
    drawdown: float = 0.0
    daily_pnl: Decimal = Decimal(0)
    daily_loss_rate: float = 0.0
    consecutive_losses: int = 0
    emergency_stop_active: bool = False
    recovery_mode_active: bool = False
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class RiskLimitsResponse(BaseModel):
    """Configured risk limits."""

    model_config = ConfigDict(frozen=True)

    limits: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ─── Authentication Models ─────────────────────────────────────────────────


class LoginRequest(BaseModel):
    """Request body for POST /api/v1/auth/login."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    username: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="Username",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password",
    )


class LoginResponse(BaseModel):
    """Response body for POST /api/v1/auth/login."""

    model_config = ConfigDict(frozen=True)

    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    is_superuser: bool = False


class UserResponse(BaseModel):
    """Response body for GET /api/v1/auth/me."""

    model_config = ConfigDict(frozen=True)

    id: str
    username: str
    email: str
    full_name: str | None = None
    is_active: bool
    is_superuser: bool
    status: str = "ACTIVE"
    email_verified: bool = False
    password_changed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ForgotPasswordRequest(BaseModel):
    """Request body for POST /api/v1/auth/forgot-password."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Registered email address",
        examples=["trader@example.com"],
    )


class ResetPasswordRequest(BaseModel):
    """Request body for POST /api/v1/auth/reset-password."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    token: str = Field(
        ...,
        min_length=16,
        max_length=128,
        description="Cryptographic password reset token",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="New secure password",
    )


class VerifyEmailRequest(BaseModel):
    """Request body for POST /api/v1/auth/verify-email."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    token: str = Field(
        ...,
        min_length=16,
        max_length=128,
        description="Cryptographic email verification token",
    )


class ResendVerificationRequest(BaseModel):
    """Request body for POST /api/v1/auth/resend-verification."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Registered email address to resend verification link to",
        examples=["trader@example.com"],
    )


class DeactivateAccountRequest(BaseModel):
    """Request body for POST /api/v1/auth/deactivate."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Current password to authenticate deactivation",
    )
    confirmation: str = Field(
        ...,
        description="Must be strictly 'DEACTIVATE' to prevent accidental account deactivation",
        examples=["DEACTIVATE"],
    )


class GenericMessageResponse(BaseModel):
    """Standard message response for auth lifecycle operations."""

    model_config = ConfigDict(frozen=True)

    message: str


# ─── Pagination Models ───────────────────────────────────────────────────────


class PaginationParams(BaseModel):
    """Pagination and filter parameters."""

    model_config = ConfigDict(frozen=True)

    limit: int = Field(20, ge=1, le=100, description="Items per page (max 100)")
    offset: int = Field(0, ge=0, description="Offset index")
    sort_by: str = Field("created_at", description="Field to sort by")
    order: str = Field("desc", description="Sort order: asc or desc")
    date_from: datetime | None = Field(None, description="Start date filter (UTC)")
    date_to: datetime | None = Field(None, description="End date filter (UTC)")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated envelope."""

    model_config = ConfigDict(frozen=True)

    items: list[T] = Field(default_factory=list)
    total: int
    limit: int
    offset: int
    has_more: bool


# ─── Order Models ────────────────────────────────────────────────────────────


class OrderSideEnum(StrEnum):
    """Order side: BUY or SELL."""

    BUY = "BUY"
    SELL = "SELL"


class OrderTypeEnum(StrEnum):
    """Order type."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    TRAILING_STOP = "TRAILING_STOP"


class OrderStatusEnum(StrEnum):
    """Order lifecycle status."""

    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class CreateOrderRequest(BaseModel):
    """Request body for submitting a paper trading order."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    symbol: str = Field(..., min_length=3, max_length=16, description="Instrument symbol, e.g. EUR/USD")
    side: OrderSideEnum = Field(..., description="Order side: BUY or SELL")
    order_type: OrderTypeEnum = Field(default=OrderTypeEnum.MARKET, description="Order type: MARKET, LIMIT, STOP, or TRAILING_STOP")
    quantity: Decimal = Field(..., gt=Decimal(0), description="Order volume in units")
    price: Decimal | None = Field(None, gt=Decimal(0), description="Limit price if LIMIT order")
    stop_price: Decimal | None = Field(None, gt=Decimal(0), description="Trigger price if STOP order")
    stop_loss: Decimal | None = Field(None, gt=Decimal(0), description="Stop loss price")
    take_profit: Decimal | None = Field(None, gt=Decimal(0), description="Take profit price")
    trailing_distance: Decimal | None = Field(None, gt=Decimal(0), description="Trailing distance for trailing stop")
    strategy_id: str | None = Field(None, description="Originating strategy ID if applicable")

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        """Normalize symbol format."""
        s = v.upper().strip()
        if "/" not in s and len(s) == 6:
            return f"{s[:3]}/{s[3:]}"
        return s


class OrderResponse(BaseModel):
    """Structured response for an order."""

    model_config = ConfigDict(frozen=True)

    id: str
    broker_order_id: str | None = None
    account_id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None = None
    stop_price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    trailing_distance: Decimal | None = None
    status: str
    filled_quantity: Decimal = Decimal(0)
    average_fill_price: Decimal | None = None
    strategy_id: str | None = None
    is_paper: bool = True
    created_at: datetime
    updated_at: datetime
    meta_data: dict[str, Any] = Field(default_factory=dict)


class CancelOrderResponse(BaseModel):
    """Response returned when an order is cancelled."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    status: str
    message: str


# ─── Position Models ─────────────────────────────────────────────────────────


class PositionResponse(BaseModel):
    """Response representing an open or historical position."""

    model_config = ConfigDict(frozen=True)

    id: str
    account_id: str
    symbol: str
    side: str
    quantity: Decimal
    open_price: Decimal
    current_price: Decimal
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    realized_pnl: Decimal = Decimal(0)
    unrealized_pnl: Decimal = Decimal(0)
    commission: Decimal = Decimal(0)
    swap: Decimal = Decimal(0)
    is_open: bool = True
    opened_at: datetime
    closed_at: datetime | None = None


class ClosePositionResponse(BaseModel):
    """Response returned upon closing a position."""

    model_config = ConfigDict(frozen=True)

    position_id: str
    symbol: str
    closed_quantity: Decimal
    close_price: Decimal
    realized_pnl: Decimal
    closed_at: datetime
    message: str = "Position closed successfully"


# ─── Trade / Fill Models ─────────────────────────────────────────────────────


class TradeResponse(BaseModel):
    """Response representing an executed trade fill."""

    model_config = ConfigDict(frozen=True)

    trade_id: str
    order_id: str
    broker_fill_id: str | None = None
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    commission: Decimal = Decimal(0)
    timestamp: datetime
    is_paper: bool = True


# ─── Portfolio Models ────────────────────────────────────────────────────────


class CurrencyExposure(BaseModel):
    """Exposure breakdown for a single currency."""

    model_config = ConfigDict(frozen=True)

    currency: str
    long_exposure: Decimal = Decimal(0)
    short_exposure: Decimal = Decimal(0)
    net_exposure: Decimal = Decimal(0)
    position_count: int = 0


class PortfolioOverviewResponse(BaseModel):
    """Consolidated portfolio overview."""

    model_config = ConfigDict(frozen=True)

    balance: Decimal
    equity: Decimal
    used_margin: Decimal
    free_margin: Decimal
    margin_level: float
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    net_exposure: Decimal
    gross_exposure: Decimal
    open_positions_count: int
    currency: str = "USD"
    is_paper: bool = True
    updated_at: datetime


class EquityCurveResponse(BaseModel):
    """Current equity and drawdown summary."""

    model_config = ConfigDict(frozen=True)

    balance: Decimal
    equity: Decimal
    peak_equity: Decimal
    current_drawdown: float
    max_drawdown: float
    currency: str = "USD"
    updated_at: datetime


class PnLBreakdownResponse(BaseModel):
    """P&L breakdown including gross, commissions, and charges."""

    model_config = ConfigDict(frozen=True)

    realized_pnl: Decimal
    unrealized_pnl: Decimal
    gross_profit: Decimal
    gross_loss: Decimal
    commission: Decimal
    swap: Decimal
    fees: Decimal
    net_pnl: Decimal
    currency: str = "USD"
    updated_at: datetime


class ExposureResponse(BaseModel):
    """Aggregate exposure metrics."""

    model_config = ConfigDict(frozen=True)

    net_exposure: Decimal
    gross_exposure: Decimal
    long_exposure: Decimal
    short_exposure: Decimal
    currency_exposures: list[CurrencyExposure] = Field(default_factory=list)
    updated_at: datetime


# ─── Strategy Control Models ─────────────────────────────────────────────────


class StrategyDetailResponse(BaseModel):
    """Detailed metadata for a strategy."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    type: str
    description: str
    timeframes: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class StrategyConfigSchemaResponse(BaseModel):
    """JSON Schema defining configurable parameters for a strategy."""

    model_config = ConfigDict(frozen=True)

    strategy_id: str
    name: str
    schema_definition: dict[str, Any] = Field(default_factory=dict)


class AccountStrategyConfigResponse(BaseModel):
    """Current strategy configuration for an account."""

    model_config = ConfigDict(frozen=True)

    account_id: str
    strategy_id: str
    timeframe: str
    symbols: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    updated_at: datetime


class UpdateAccountStrategyRequest(BaseModel):
    """Request body for updating active account strategy."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    strategy_id: str = Field(..., min_length=1, description="Strategy identifier")
    timeframe: str = Field(default="M15", min_length=2, max_length=10, description="Execution timeframe")
    symbols: list[str] = Field(default_factory=list, description="Target currency pairs")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Validated strategy parameter overrides")
    is_active: bool = Field(default=True, description="Enable or disable strategy")


# ─── Consolidated Dashboard Models ───────────────────────────────────────────


class DashboardAccount(BaseModel):
    """Dashboard account summary block."""

    model_config = ConfigDict(frozen=True)

    balance: Decimal
    equity: Decimal
    available_cash: Decimal
    used_margin: Decimal
    free_margin: Decimal
    currency: str = "USD"
    is_paper: bool = True


class DashboardPerformance(BaseModel):
    """Dashboard performance summary block."""

    model_config = ConfigDict(frozen=True)

    realized_pnl: Decimal
    unrealized_pnl: Decimal
    daily_pnl: Decimal
    drawdown_pct: float


class DashboardTrading(BaseModel):
    """Dashboard trading summary block."""

    model_config = ConfigDict(frozen=True)

    open_positions: list[PositionResponse] = Field(default_factory=list)
    recent_trades: list[TradeResponse] = Field(default_factory=list)
    pending_orders: list[OrderResponse] = Field(default_factory=list)


class DashboardStrategy(BaseModel):
    """Dashboard strategy summary block."""

    model_config = ConfigDict(frozen=True)

    active_strategy: str
    timeframe: str
    symbols: list[str] = Field(default_factory=list)


class DashboardRisk(BaseModel):
    """Dashboard risk summary block."""

    model_config = ConfigDict(frozen=True)

    status: str
    total_exposure: Decimal
    margin_level: float
    emergency_stop_active: bool = False
    recovery_mode_active: bool = False


class DashboardWorker(BaseModel):
    """Dashboard worker summary block."""

    model_config = ConfigDict(frozen=True)

    enabled: bool
    state: str
    is_running: bool
    last_cycle_at: datetime | None = None
    uptime_seconds: float = 0.0
    last_error: str | None = None


class DashboardSystem(BaseModel):
    """Dashboard system health block."""

    model_config = ConfigDict(frozen=True)

    status: str
    market_data_status: str
    timestamp: datetime


class DashboardResponse(BaseModel):
    """Consolidated dashboard contract response."""

    model_config = ConfigDict(frozen=True)

    account: DashboardAccount
    performance: DashboardPerformance
    trading: DashboardTrading
    strategy: DashboardStrategy
    risk: DashboardRisk
    worker: DashboardWorker
    system: DashboardSystem


# ─── Onboarding Models ───────────────────────────────────────────────────────


class OnboardingRegisterRequest(BaseModel):
    """Request body for institutional onboarding."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: str = Field(..., min_length=5, max_length=255, description="Corporate email address")
    password: str = Field(..., min_length=8, max_length=128, description="Secure account password")
    organization_name: str = Field(..., min_length=2, max_length=100, description="Organization or firm name")
    organization_slug: str | None = Field(None, min_length=2, max_length=50, description="Optional custom URL slug")
    full_name: str | None = Field(None, max_length=100, description="Full name of primary owner")


class OnboardingResponse(BaseModel):
    """Response payload returned upon successful tenant registration."""

    model_config = ConfigDict(frozen=True)

    user_id: str
    username: str
    email: str
    organization_id: str
    organization_name: str
    organization_slug: str
    role: str
    subscription_tier: str
    account_id: str
    account_number: str
    initial_balance: Decimal
    access_token: str
    token_type: str = "bearer"
    created_at: datetime


# ─── Organization & Member Models ────────────────────────────────────────────


class OrganizationResponse(BaseModel):
    """Public organization summary schema."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    slug: str
    status: str
    created_at: datetime
    updated_at: datetime
    meta_data: dict[str, Any] = Field(default_factory=dict)


class UpdateOrganizationRequest(BaseModel):
    """Request body for updating organization details."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    name: str | None = Field(None, min_length=2, max_length=100, description="Updated organization name")
    meta_data: dict[str, Any] | None = Field(None, description="Updated metadata")


class OrganizationMemberResponse(BaseModel):
    """Organization membership response schema."""

    model_config = ConfigDict(frozen=True)

    id: str
    organization_id: str
    user_id: str
    role: str
    status: str
    created_at: datetime
    updated_at: datetime
    meta_data: dict[str, Any] = Field(default_factory=dict)


class UpdateMemberRoleRequest(BaseModel):
    """Request body for updating a member's role."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    role: str = Field(..., description="Target role: OWNER, ADMINISTRATOR, PORTFOLIO_MANAGER, RISK_OFFICER, TRADER, AUDITOR, VIEWER")


class CreateInvitationRequest(BaseModel):
    """Request body for inviting a new member to an organization."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    email: str = Field(..., min_length=5, max_length=255, description="Invitee email address")
    role: str = Field(..., description="Assigned role: OWNER, ADMINISTRATOR, PORTFOLIO_MANAGER, RISK_OFFICER, TRADER, AUDITOR, VIEWER")


class InvitationResponse(BaseModel):
    """Member invitation details."""

    model_config = ConfigDict(frozen=True)

    id: str
    organization_id: str
    email: str
    role: str
    status: str
    invited_by_user_id: str | None = None
    expires_at: datetime
    created_at: datetime
    invitation_token: str | None = None
    invitation_url: str | None = None


class AcceptInvitationResponse(BaseModel):
    """Response returned upon accepting an invitation."""

    model_config = ConfigDict(frozen=True)

    membership_id: str
    organization_id: str
    user_id: str
    role: str
    status: str
    accepted_at: datetime


class AuditLogResponse(BaseModel):
    """Structured response for compliance audit log entries."""

    model_config = ConfigDict(frozen=True)

    id: str
    organization_id: str | None
    event_type: str
    component: str
    actor: str | None
    details: dict[str, Any]
    timestamp: datetime


# ─── Market Data Models (EPIC-021) ─────────────────────────────────────────


class MarketInstrumentResponse(BaseModel):
    """Response model for a canonical tradeable market instrument."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    base_currency: str
    quote_currency: str
    pip_size: Decimal
    tick_size: Decimal
    display_name: str
    is_active: bool


class MarketQuoteResponse(BaseModel):
    """Response model for a real-time canonical market quote."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    bid: Decimal
    ask: Decimal
    mid: Decimal
    spread: Decimal
    spread_pips: Decimal
    timestamp: datetime
    provider: str
    is_stale: bool
    quality: str


class MarketCandleResponse(BaseModel):
    """Response model for a single OHLCV candle bar."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


class MarketCandlesListResponse(BaseModel):
    """Response model for historical market candles."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    timeframe: str
    provider: str
    candles: list[MarketCandleResponse]


class MarketHealthResponse(BaseModel):
    """Response model for market data infrastructure telemetry."""

    model_config = ConfigDict(frozen=True)

    provider: str
    status: str
    data_quality: str
    last_update_utc: datetime | None
    symbols_active: int
    latency_ms: float
    stale_count: int
    is_paper_feed: bool = True


# ─── Paper Trading Simulation Control Schemas ─────────────────────────


class PaperResetRequest(BaseModel):
    """Request model for resetting paper account balance and state."""

    model_config = ConfigDict(frozen=True)

    balance: Decimal = Field(default=Decimal("100000.00"), gt=Decimal(0), description="Initial paper capital balance")


class PaperResetResponse(BaseModel):
    """Response model for paper account reset."""

    model_config = ConfigDict(frozen=True)

    message: str
    account_id: str
    balance: Decimal
    equity: Decimal
    positions_closed: int
    orders_cancelled: int


class PaperConfigResponse(BaseModel):
    """Response model for paper trading simulation configuration."""

    model_config = ConfigDict(frozen=True)

    broker_name: str
    is_paper: bool
    spread: float
    slippage_mean: float
    slippage_std: float
    commission_rate: float
    swap_long_rate: float
    swap_short_rate: float
    latency_ms_mean: float
    latency_ms_std: float
    partial_fill_probability: float
    min_fill_ratio: float
    deterministic: bool
    leverage: int


class UpdatePaperConfigRequest(BaseModel):
    """Request model for updating paper trading simulation parameters."""

    model_config = ConfigDict(frozen=True)

    spread: float | None = None
    slippage_mean: float | None = None
    slippage_std: float | None = None
    commission_rate: float | None = None
    latency_ms_mean: float | None = None
    partial_fill_probability: float | None = None
    deterministic: bool | None = None
    leverage: int | None = None


# Re-export research and optimization schemas for unified schema access
from .schemas_broker_sandbox import *
from .schemas_optimization import *
from .schemas_research import *

