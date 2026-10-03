"""Domain ports and contract models for Institutional Broker Sandbox Reconciliation.

Decouples domain state audit and divergence detection from infrastructure broker adapters.
Domain components depend only on these domain ports and models; infrastructure adapters
implement them.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from libraries.domain.execution.models import (
    BrokerOrderId,
    Fill,
    OrderSide,
    OrderStatus,
)


@dataclass(frozen=True, slots=True)
class AccountInfo:
    """Broker account state information for reconciliation audits."""

    account_id: str
    broker_name: str
    balance: Decimal
    equity: Decimal
    margin: Decimal
    margin_free: Decimal
    margin_level: float
    currency: str
    leverage: int
    is_live: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PositionInfo:
    """Open position state information for reconciliation audits."""

    position_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    open_price: Decimal
    current_price: Decimal
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    commission: Decimal = Decimal(0)
    swap: Decimal = Decimal(0)
    profit: Decimal = Decimal(0)
    open_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OrderExecutionInfo:
    """Order execution information returned by broker for reconciliation audits."""

    broker_order_id: BrokerOrderId
    status: OrderStatus
    filled_quantity: Decimal = Decimal(0)
    average_fill_price: Decimal | None = None
    commission: Decimal = Decimal(0)
    fills: tuple[Fill, ...] = ()
    rejection_reason: str = ""
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class BrokerReconciliationPort(Protocol):
    """Port interface defining the contract required for broker state reconciliation."""

    async def get_account(self) -> AccountInfo:
        """Fetch remote account balances and margin state."""
        ...

    async def get_open_positions(self) -> Sequence[PositionInfo]:
        """Fetch remote active open positions."""
        ...

    async def get_execution_history(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> Sequence[OrderExecutionInfo]:
        """Fetch remote order execution history for discrepancy detection."""
        ...
