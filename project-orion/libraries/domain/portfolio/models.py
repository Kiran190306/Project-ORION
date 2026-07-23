"""Immutable data models for the Portfolio & Position Management Engine.

Defines:
- Position, PositionSide, PositionStatus, PositionSummary
- AccountSnapshot, PortfolioSnapshot
- PnLBreakdown, CurrencyPosition
- MarginCallThresholds
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any

# ─── Enums ────────────────────────────────────────────────────────────────


class PositionSide(StrEnum):
    """Side of a position."""

    LONG = "long"
    SHORT = "short"


class PositionStatus(StrEnum):
    """Lifecycle status of a position.

    OPEN → PARTIALLY_CLOSED → CLOSED
    OPEN → CLOSED
    OPEN → LIQUIDATED
    """

    OPEN = "open"
    PARTIALLY_CLOSED = "partially_closed"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"
    PENDING = "pending"
    PENDING_CLOSE = "pending_close"
    FORCED_CLOSE = "forced_close"

    @property
    def is_active(self) -> bool:
        return self in (
            PositionStatus.OPEN,
            PositionStatus.PARTIALLY_CLOSED,
            PositionStatus.PENDING,
        )

    @property
    def is_closed(self) -> bool:
        return self in (
            PositionStatus.CLOSED,
            PositionStatus.LIQUIDATED,
            PositionStatus.FORCED_CLOSE,
        )

    @property
    def is_pending(self) -> bool:
        return self in (PositionStatus.PENDING, PositionStatus.PENDING_CLOSE)


# ─── Core Position Model ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Position:
    """A single trading position.

    Immutable — state transitions produce new Position instances.
    O(1) lookup by position_id via PositionManager dict index.
    """

    position_id: str
    symbol: str
    side: PositionSide
    status: PositionStatus = PositionStatus.OPEN
    quantity: Decimal = Decimal("0")  # Current open quantity
    initial_quantity: Decimal = Decimal("0")  # Original open quantity
    entry_price: Decimal = Decimal("0")
    current_price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    commission: Decimal = Decimal("0")
    swap: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")
    margin_used: Decimal = Decimal("0")
    leverage: Decimal = Decimal("1")
    decision_id: str = ""
    execution_id: str = ""
    strategy: str = ""
    currency: str = "USD"
    broker: str = ""
    open_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    close_time: datetime | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    close_reason: str = ""
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_long(self) -> bool:
        return self.side == PositionSide.LONG

    @property
    def is_short(self) -> bool:
        return self.side == PositionSide.SHORT

    @property
    def is_active(self) -> bool:
        return self.status.is_active

    @property
    def market_value(self) -> Decimal:
        """Current market value of the position."""
        price = self.current_price or self.entry_price
        return price * self.quantity

    @property
    def cost_basis(self) -> Decimal:
        """Cost basis of the position."""
        return self.entry_price * self.quantity

    @property
    def pnl_net(self) -> Decimal:
        """Net profit/loss including commission, swap, and fees."""
        return self.realized_pnl + self.unrealized_pnl - self.commission - self.swap - self.fees

    @property
    def holding_time_hours(self) -> float:
        """Hours the position has been open."""
        end = self.close_time or datetime.now(timezone.utc)
        return (end - self.open_time).total_seconds() / 3600.0

    @property
    def return_pct(self) -> float:
        """Return as percentage of cost basis."""
        if self.cost_basis == 0:
            return 0.0
        return float(self.pnl_net / self.cost_basis * 100)

    def with_update(
        self,
        **kwargs: Any,
    ) -> Position:
        """Return a new Position with updated fields and timestamp."""
        return Position(
            position_id=self.position_id,
            symbol=self.symbol,
            side=self.side,
            status=kwargs.get("status", self.status),
            quantity=kwargs.get("quantity", self.quantity),
            initial_quantity=kwargs.get("initial_quantity", self.initial_quantity),
            entry_price=kwargs.get("entry_price", self.entry_price),
            current_price=kwargs.get("current_price", self.current_price),
            stop_loss=kwargs.get("stop_loss", self.stop_loss),
            take_profit=kwargs.get("take_profit", self.take_profit),
            realized_pnl=kwargs.get("realized_pnl", self.realized_pnl),
            unrealized_pnl=kwargs.get("unrealized_pnl", self.unrealized_pnl),
            commission=kwargs.get("commission", self.commission),
            swap=kwargs.get("swap", self.swap),
            fees=kwargs.get("fees", self.fees),
            margin_used=kwargs.get("margin_used", self.margin_used),
            leverage=kwargs.get("leverage", self.leverage),
            decision_id=kwargs.get("decision_id", self.decision_id),
            execution_id=kwargs.get("execution_id", self.execution_id),
            strategy=kwargs.get("strategy", self.strategy),
            currency=kwargs.get("currency", self.currency),
            broker=kwargs.get("broker", self.broker),
            open_time=kwargs.get("open_time", self.open_time),
            close_time=kwargs.get("close_time", self.close_time),
            updated_at=datetime.now(timezone.utc),
            close_reason=kwargs.get("close_reason", self.close_reason),
            tags=kwargs.get("tags", self.tags),
            metadata=kwargs.get("metadata", self.metadata),
        )


# ─── Position Summary ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PositionSummary:
    """Aggregated position summary for a symbol."""

    symbol: str
    total_long_quantity: Decimal = Decimal("0")
    total_short_quantity: Decimal = Decimal("0")
    net_quantity: Decimal = Decimal("0")
    avg_long_price: Decimal = Decimal("0")
    avg_short_price: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    position_count: int = 0
    active_count: int = 0


# ─── Currency Position ────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class CurrencyPosition:
    """Exposure summary for a single currency."""

    currency: str
    long_exposure: Decimal = Decimal("0")
    short_exposure: Decimal = Decimal("0")
    net_exposure: Decimal = Decimal("0")
    position_count: int = 0


# ─── Account Snapshot ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class AccountSnapshot:
    """Immutable snapshot of account state.

    Prepared for multi-currency support.
    """

    account_id: str = "default"
    balance: Decimal = Decimal("0")
    equity: Decimal = Decimal("0")
    free_margin: Decimal = Decimal("0")
    used_margin: Decimal = Decimal("0")
    margin_level: float = 0.0  # equity / used_margin * 100
    available_funds: Decimal = Decimal("0")
    buying_power: Decimal = Decimal("0")
    leverage: float = 0.0  # current effective leverage
    currency: str = "USD"
    base_currency: str = "USD"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def margin_utilization_pct(self) -> float:
        """Margin utilization as percentage."""
        if self.equity == 0:
            return 0.0
        return float(self.used_margin / self.equity * 100)

    @property
    def is_margin_call(self) -> bool:
        """Check if margin level indicates a margin call situation."""
        return self.margin_level < 100.0

    @property
    def is_stop_out(self) -> bool:
        """Check if margin level indicates stop-out."""
        return self.margin_level < 50.0


# ─── Portfolio Snapshot ───────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    """Immutable snapshot of the complete portfolio."""

    account: AccountSnapshot = field(default_factory=AccountSnapshot)
    positions: tuple[Position, ...] = ()
    open_positions: tuple[Position, ...] = ()
    closed_positions: tuple[Position, ...] = ()
    total_realized_pnl: Decimal = Decimal("0")
    total_unrealized_pnl: Decimal = Decimal("0")
    total_commission: Decimal = Decimal("0")
    total_swap: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")
    net_exposure: Decimal = Decimal("0")
    gross_exposure: Decimal = Decimal("0")
    long_exposure: Decimal = Decimal("0")
    short_exposure: Decimal = Decimal("0")
    position_count: int = 0
    open_position_count: int = 0
    currency_exposures: tuple[CurrencyPosition, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def net_profit(self) -> Decimal:
        return self.total_realized_pnl + self.total_unrealized_pnl

    @property
    def gross_profit_and_loss(self) -> Decimal:
        return self.total_realized_pnl + self.total_unrealized_pnl


# ─── P&L Breakdown ────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PnLBreakdown:
    """Detailed breakdown of P&L.

    Computed properties:
    - net_profit = realized_pnl + unrealized_pnl - commission - swap - fees
    - total_cost = commission + swap + fees
    """

    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    floating_pnl: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    gross_loss: Decimal = Decimal("0")
    # net_profit intentionally omitted from fields — computed below
    commission: Decimal = Decimal("0")
    swap: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")
    total_charges: Decimal = Decimal("0")
    currency: str = "USD"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def net_profit(self) -> Decimal:
        """Net profit = realized + unrealized - commission - swap - fees."""
        return self.realized_pnl + self.unrealized_pnl - self.commission - self.swap - self.fees

    @property
    def total_cost(self) -> Decimal:
        return self.commission + self.swap + self.fees

    @property
    def is_profitable(self) -> bool:
        return self.net_profit > 0


# ─── Margin Call Thresholds ───────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class MarginCallThresholds:
    """Thresholds for margin call and stop-out."""

    margin_call_level: float = 100.0  # % equity / used_margin
    stop_out_level: float = 50.0  # % equity / used_margin
    warning_level: float = 200.0  # % — warning before margin call
    maintenance_margin_pct: float = 0.5  # % of position value


# ─── Margin Call Thresholds ───────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class DrawdownSnapshot:
    """Drawdown snapshot for analytics."""

    current_drawdown: float = 0.0  # % from peak
    max_drawdown: float = 0.0
    peak_equity: Decimal = Decimal("0")
    current_equity: Decimal = Decimal("0")
    recovery_factor: float = 0.0
