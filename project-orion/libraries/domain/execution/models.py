"""Immutable data models for the Smart Order Execution Engine.

Defines:
- Order, Fill, ExecutionResult, ExecutionReport
- OrderType, OrderStatus, OrderSide, OrderTimeInForce
- SlippageMetrics, ExecutionQualityScore
- PartialFillTracker, BrokerOrderId, OrderId
- ExecutionEvent for future Event Bus integration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any

# ─── Identifiers ─────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class OrderId:
    """Globally unique order identifier within the system."""

    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class BrokerOrderId:
    """Order identifier assigned by the broker/exchange."""

    value: str

    def __str__(self) -> str:
        return self.value


# ─── Enums ───────────────────────────────────────────────────────────────


class OrderSide(StrEnum):
    """Side of the order."""

    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    """Supported order types."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    OCO = "oco"
    IOC = "ioc"
    FOK = "fok"
    GTC = "gtc"
    GTD = "gtd"


class OrderTimeInForce(StrEnum):
    """Time-in-force instructions."""

    GTC = "gtc"  # Good Till Cancelled
    DAY = "day"  # Good for the trading day
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill
    GTD = "gtd"  # Good Till Date


class OrderStatus(StrEnum):
    """Immutable lifecycle status for an order.

    NEW → VALIDATED → BUILT → SUBMITTED → ACKNOWLEDGED → PARTIALLY_FILLED → FILLED
                                ↘            ↘
                             REJECTED     CANCELLED
                                              ↘
                                           EXPIRED
    """

    NEW = "new"
    VALIDATED = "validated"
    BUILT = "built"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ROUTED = "routed"
    SETTLED = "settled"
    COMPLETED = "completed"


class ExecutionResultStatus(StrEnum):
    """Status of an execution attempt."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    PENDING = "pending"
    TIMEOUT = "timeout"


class ExecutionEventType(StrEnum):
    """Types of execution events for Event Bus integration."""

    ORDER_SUBMITTED = "order_submitted"
    ORDER_ACKNOWLEDGED = "order_acknowledged"
    ORDER_REJECTED = "order_rejected"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_EXPIRED = "order_expired"
    FILL_REPORTED = "fill_reported"
    PARTIAL_FILL = "partial_fill"
    FULL_FILL = "full_fill"
    ORDER_SETTLED = "order_settled"
    ORDER_COMPLETED = "order_completed"
    RETRY_ATTEMPTED = "retry_attempted"
    RETRY_EXHAUSTED = "retry_exhausted"
    BROKER_DISCONNECTED = "broker_disconnected"
    EXECUTION_FAILED = "execution_failed"
    ROUTING_DECISION = "routing_decision"


# ─── Core Order Model ────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Order:
    """Broker-neutral order representation.

    Immutable - state transitions produce new Order instances.
    """

    order_id: OrderId
    decision_id: str
    execution_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Decimal | None = None
    stop_price: Decimal | None = None
    trailing_distance: Decimal | None = None
    time_in_force: OrderTimeInForce = OrderTimeInForce.GTC
    expiry: datetime | None = None
    status: OrderStatus = OrderStatus.NEW
    broker_order_id: BrokerOrderId | None = None
    broker_name: str = ""
    filled_quantity: Decimal = Decimal("0")
    average_fill_price: Decimal | None = None
    commission: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")
    rejection_reason: str = ""
    fills: tuple[Fill, ...] = ()
    parent_order_id: OrderId | None = None
    child_order_ids: tuple[OrderId, ...] = ()
    oco_order_id: OrderId | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: datetime | None = None
    filled_at: datetime | None = None
    settled_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity - self.filled_quantity

    @property
    def is_fully_filled(self) -> bool:
        return self.filled_quantity >= self.quantity

    @property
    def is_finalized(self) -> bool:
        return self.status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
            OrderStatus.SETTLED,
            OrderStatus.COMPLETED,
        )

    @property
    def fill_count(self) -> int:
        return len(self.fills)

    def with_status(self, new_status: OrderStatus) -> Order:
        """Return a new Order with updated status and timestamp."""
        return Order(
            order_id=self.order_id,
            decision_id=self.decision_id,
            execution_id=self.execution_id,
            symbol=self.symbol,
            side=self.side,
            order_type=self.order_type,
            quantity=self.quantity,
            price=self.price,
            stop_price=self.stop_price,
            trailing_distance=self.trailing_distance,
            time_in_force=self.time_in_force,
            expiry=self.expiry,
            status=new_status,
            broker_order_id=self.broker_order_id,
            broker_name=self.broker_name,
            filled_quantity=self.filled_quantity,
            average_fill_price=self.average_fill_price,
            commission=self.commission,
            slippage=self.slippage,
            rejection_reason=self.rejection_reason,
            fills=self.fills,
            parent_order_id=self.parent_order_id,
            child_order_ids=self.child_order_ids,
            oco_order_id=self.oco_order_id,
            created_at=self.created_at,
            updated_at=datetime.now(timezone.utc),
            submitted_at=self.submitted_at,
            filled_at=self.filled_at,
            settled_at=self.settled_at,
            completed_at=self.completed_at,
            metadata=self.metadata,
        )


# ─── Fill Model ──────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Fill:
    """A single fill on an order (supports multiple fills per order)."""

    fill_id: str
    order_id: OrderId
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    commission: Decimal = Decimal("0")
    broker_fill_id: str = ""
    liquidity: str = ""  # maker / taker
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


# ─── Partial Fill Tracker ────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PartialFillTracker:
    """Tracks cumulative fill state for an order."""

    order_id: OrderId
    total_quantity: Decimal
    filled_quantity: Decimal = Decimal("0")
    fills: tuple[Fill, ...] = ()
    average_price: Decimal | None = None
    last_fill_at: datetime | None = None
    fill_count: int = 0

    @property
    def remaining(self) -> Decimal:
        return self.total_quantity - self.filled_quantity

    @property
    def is_complete(self) -> bool:
        return self.filled_quantity >= self.total_quantity

    def add_fill(self, fill: Fill) -> PartialFillTracker:
        """Return a new tracker with the fill applied."""
        new_filled = self.filled_quantity + fill.quantity
        all_fills = list(self.fills) + [fill]
        new_avg = (
            sum(f.price * f.quantity for f in all_fills) / new_filled if new_filled > 0 else None
        )
        return PartialFillTracker(
            order_id=self.order_id,
            total_quantity=self.total_quantity,
            filled_quantity=new_filled,
            fills=tuple(all_fills),
            average_price=new_avg,
            last_fill_at=fill.timestamp,
            fill_count=self.fill_count + 1,
        )


# ─── Execution Result ────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Result of executing an order through the full pipeline."""

    execution_id: str
    decision_id: str
    order_id: OrderId
    symbol: str
    side: OrderSide
    quantity: Decimal
    status: ExecutionResultStatus
    filled_quantity: Decimal = Decimal("0")
    average_price: Decimal | None = None
    commission: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")
    slippage_bps: float = 0.0
    fills: tuple[Fill, ...] = ()
    broker_order_id: BrokerOrderId | None = None
    broker_name: str = ""
    rejection_reason: str = ""
    quality_score: ExecutionQualityScore | None = None
    latency_ms: float = 0.0
    retry_count: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == ExecutionResultStatus.SUCCESS

    @property
    def is_partial(self) -> bool:
        return self.status == ExecutionResultStatus.PARTIAL

    @property
    def is_failure(self) -> bool:
        return self.status == ExecutionResultStatus.FAILURE


# ─── Execution Report ────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    """Detailed execution report for a single order execution attempt."""

    execution_id: str
    decision_id: str
    order: Order
    result: ExecutionResult
    validation_passed: bool = True
    validation_errors: tuple[str, ...] = ()
    route_selected: str = ""
    route_score: float = 0.0
    retry_attempts: int = 0
    total_latency_ms: float = 0.0
    broker_latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ─── Execution Quality Score ─────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ExecutionQualityScore:
    """Quality assessment of an execution (0-100)."""

    overall: float = 100.0
    slippage_score: float = 100.0
    fill_speed_score: float = 100.0
    commission_score: float = 100.0
    route_quality_score: float = 100.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_excellent(self) -> bool:
        return self.overall >= 90.0

    @property
    def is_good(self) -> bool:
        return 70.0 <= self.overall < 90.0

    @property
    def is_poor(self) -> bool:
        return self.overall < 50.0


# ─── Slippage Models ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SlippageMetrics:
    """Slippage tracking for a single execution."""

    expected_price: Decimal
    actual_price: Decimal
    slippage_abs: Decimal
    slippage_bps: float
    slippage_pct: float
    direction: str = ""  # positive = adverse, negative = favorable
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class SlippageReport:
    """Aggregated slippage report across executions."""

    total_executions: int = 0
    total_adverse_slippage: Decimal = Decimal("0")
    total_favorable_slippage: Decimal = Decimal("0")
    average_slippage_bps: float = 0.0
    max_adverse_bps: float = 0.0
    max_favorable_bps: float = 0.0
    slippage_events: tuple[SlippageMetrics, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ─── Execution Event ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    """Execution event for Event Bus integration.

    Designed for future publishing to the Event Bus infrastructure.
    """

    event_id: str
    event_type: ExecutionEventType
    execution_id: str
    decision_id: str
    order_id: OrderId
    symbol: str
    side: OrderSide
    quantity: Decimal
    status: OrderStatus
    filled_quantity: Decimal = Decimal("0")
    price: Decimal | None = None
    broker_order_id: BrokerOrderId | None = None
    broker_name: str = ""
    error: str = ""
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
