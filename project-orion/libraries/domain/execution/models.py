"""Immutable data models for the Smart Order Execution Engine.

Defines:
- Order, Fill, ExecutionResult, ExecutionReport
- OrderType, OrderStatus, OrderSide, OrderTimeInForce
- SlippageMetrics, ExecutionQualityScore
- PartialFillTracker, BrokerOrderId, OrderId
- ExecutionEvent for future Event Bus integration
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any

# ─── Identifiers ─────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class OrderId:
    """Globally unique order identifier within the system."""

    value: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def id(self) -> str:
        return self.value

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


@dataclass(frozen=True)
class Order:
    """Broker-neutral order representation.

    Immutable - state transitions produce new Order instances.
    """

    order_id: OrderId | str
    decision_id: str
    execution_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Decimal | None = None
    stop_price: Decimal | None = None
    trailing_distance: Decimal | None = None
    time_in_force: OrderTimeInForce | None = None
    expiry: datetime | None = None
    status: OrderStatus = OrderStatus.NEW
    broker_order_id: BrokerOrderId | None = None
    broker_name: str = ""
    filled_quantity: Decimal = Decimal(0)
    average_fill_price: Decimal | None = None
    commission: Decimal = Decimal(0)
    slippage: Decimal = Decimal(0)
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
    take_profit: Decimal | None = None

    def __init__(
        self,
        order_id: OrderId | str,
        decision_id: str,
        execution_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        price: Decimal | None = None,
        stop_price: Decimal | None = None,
        trailing_distance: Decimal | None = None,
        time_in_force: OrderTimeInForce | None = None,
        expiry: datetime | None = None,
        status: OrderStatus = OrderStatus.NEW,
        broker_order_id: BrokerOrderId | None = None,
        broker_name: str = "",
        filled_quantity: Decimal = Decimal(0),
        average_fill_price: Decimal | None = None,
        commission: Decimal = Decimal(0),
        slippage: Decimal = Decimal(0),
        rejection_reason: str = "",
        fills: tuple[Fill, ...] = (),
        parent_order_id: OrderId | None = None,
        child_order_ids: tuple[OrderId, ...] = (),
        oco_order_id: OrderId | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        submitted_at: datetime | None = None,
        filled_at: datetime | None = None,
        settled_at: datetime | None = None,
        completed_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
        take_profit: Decimal | None = None,
        stop_loss: Decimal | None = None,
    ) -> None:
        eff_stop = stop_price if stop_price is not None else stop_loss
        object.__setattr__(self, "order_id", order_id)
        object.__setattr__(self, "decision_id", decision_id)
        object.__setattr__(self, "execution_id", execution_id)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "side", side)
        object.__setattr__(self, "order_type", order_type)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "stop_price", eff_stop)
        object.__setattr__(self, "trailing_distance", trailing_distance)
        object.__setattr__(self, "time_in_force", time_in_force)
        object.__setattr__(self, "expiry", expiry)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "broker_order_id", broker_order_id)
        object.__setattr__(self, "broker_name", broker_name)
        object.__setattr__(self, "filled_quantity", filled_quantity)
        object.__setattr__(self, "average_fill_price", average_fill_price)
        object.__setattr__(self, "commission", commission)
        object.__setattr__(self, "slippage", slippage)
        object.__setattr__(self, "rejection_reason", rejection_reason)
        object.__setattr__(self, "fills", fills)
        object.__setattr__(self, "parent_order_id", parent_order_id)
        object.__setattr__(self, "child_order_ids", child_order_ids)
        object.__setattr__(self, "oco_order_id", oco_order_id)
        object.__setattr__(
            self,
            "created_at",
            created_at if created_at is not None else datetime.now(timezone.utc),
        )
        object.__setattr__(
            self,
            "updated_at",
            updated_at if updated_at is not None else datetime.now(timezone.utc),
        )
        object.__setattr__(self, "submitted_at", submitted_at)
        object.__setattr__(self, "filled_at", filled_at)
        object.__setattr__(self, "settled_at", settled_at)
        object.__setattr__(self, "completed_at", completed_at)
        object.__setattr__(self, "metadata", metadata if metadata is not None else {})
        object.__setattr__(self, "take_profit", take_profit)

    @property
    def stop_loss(self) -> Decimal | None:
        """Alias for stop_price."""
        return self.stop_price

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
            take_profit=self.take_profit,
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
    commission: Decimal = Decimal(0)
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
    filled_quantity: Decimal = Decimal(0)
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
    filled_quantity: Decimal = Decimal(0)
    average_price: Decimal | None = None
    commission: Decimal = Decimal(0)
    slippage: Decimal = Decimal(0)
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


@dataclass(frozen=True)
class ExecutionReport:
    """Detailed execution report from a broker or execution attempt."""

    execution_id: str
    order_id: str | OrderId = ""
    broker_order_id: str | BrokerOrderId = ""
    symbol: str = ""
    side: str | OrderSide = ""
    filled_volume: Decimal | None = None
    price: Decimal | None = None
    cost: Decimal | None = None
    commission: Decimal | None = None
    liquidity: str = ""
    status: str = ""
    decision_id: str = ""
    order: Order | None = None
    result: ExecutionResult | None = None
    validation_passed: bool = True
    validation_errors: tuple[str, ...] = ()
    route_selected: str = ""
    route_score: float = 0.0
    retry_attempts: int = 0
    total_latency_ms: float = 0.0
    broker_latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __init__(
        self,
        execution_id: str,
        order_id: str | OrderId = "",
        broker_order_id: str | BrokerOrderId = "",
        symbol: str = "",
        side: str | OrderSide = "",
        filled_volume: Decimal | None = None,
        price: Decimal | None = None,
        cost: Decimal | None = None,
        commission: Decimal | None = None,
        liquidity: str = "",
        status: str = "",
        decision_id: str = "",
        order: Order | None = None,
        result: ExecutionResult | None = None,
        validation_passed: bool = True,
        validation_errors: tuple[str, ...] = (),
        route_selected: str = "",
        route_score: float = 0.0,
        retry_attempts: int = 0,
        total_latency_ms: float = 0.0,
        broker_latency_ms: float = 0.0,
        timestamp: datetime | None = None,
        filled_quantity: Decimal | None = None,
    ) -> None:
        eff_volume = filled_volume if filled_volume is not None else filled_quantity
        object.__setattr__(self, "execution_id", execution_id)
        object.__setattr__(self, "order_id", order_id)
        object.__setattr__(self, "broker_order_id", broker_order_id)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "side", side)
        object.__setattr__(self, "filled_volume", eff_volume)
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "cost", cost)
        object.__setattr__(self, "commission", commission)
        object.__setattr__(self, "liquidity", liquidity)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "decision_id", decision_id)
        object.__setattr__(self, "order", order)
        object.__setattr__(self, "result", result)
        object.__setattr__(self, "validation_passed", validation_passed)
        object.__setattr__(self, "validation_errors", validation_errors)
        object.__setattr__(self, "route_selected", route_selected)
        object.__setattr__(self, "route_score", route_score)
        object.__setattr__(self, "retry_attempts", retry_attempts)
        object.__setattr__(self, "total_latency_ms", total_latency_ms)
        object.__setattr__(self, "broker_latency_ms", broker_latency_ms)
        object.__setattr__(
            self,
            "timestamp",
            timestamp if timestamp is not None else datetime.now(timezone.utc),
        )

    @property
    def report_id(self) -> str:
        """Alias for execution_id."""
        return self.execution_id

    @property
    def filled_quantity(self) -> Decimal | None:
        """Alias for filled_volume."""
        return self.filled_volume


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
    total_adverse_slippage: Decimal = Decimal(0)
    total_favorable_slippage: Decimal = Decimal(0)
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
    filled_quantity: Decimal = Decimal(0)
    price: Decimal | None = None
    broker_order_id: BrokerOrderId | None = None
    broker_name: str = ""
    error: str = ""
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
