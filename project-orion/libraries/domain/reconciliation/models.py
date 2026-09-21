"""Domain models and value objects for broker sandbox state reconciliation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any


class ReconciliationStatus(StrEnum):
    """Institutional state classification of a broker reconciliation audit."""

    MATCHED = "MATCHED"
    DISCREPANCY = "DISCREPANCY"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"


class DiscrepancyType(StrEnum):
    """Classification of specific state divergences between ORION and the broker."""

    # Order discrepancies
    ORDER_STATUS_MISMATCH = "ORDER_STATUS_MISMATCH"
    ORDER_MISSING_ON_BROKER = "ORDER_MISSING_ON_BROKER"
    ORDER_UNTRACKED_ON_BROKER = "ORDER_UNTRACKED_ON_BROKER"
    ORDER_QTY_MISMATCH = "ORDER_QTY_MISMATCH"

    # Position discrepancies
    POSITION_QTY_MISMATCH = "POSITION_QTY_MISMATCH"
    POSITION_PRICE_MISMATCH = "POSITION_PRICE_MISMATCH"
    POSITION_MISSING_LOCAL = "POSITION_MISSING_LOCAL"
    POSITION_MISSING_REMOTE = "POSITION_MISSING_REMOTE"

    # Account balance & margin discrepancies
    BALANCE_DRIFT = "BALANCE_DRIFT"
    EQUITY_DRIFT = "EQUITY_DRIFT"
    MARGIN_DRIFT = "MARGIN_DRIFT"
    FREE_MARGIN_DRIFT = "FREE_MARGIN_DRIFT"


@dataclass(frozen=True, slots=True)
class OrderDiscrepancy:
    """Individual divergence detected between internal and broker order states."""

    discrepancy_type: DiscrepancyType
    symbol: str
    order_id: str | None = None
    broker_order_id: str | None = None
    local_status: str | None = None
    remote_status: str | None = None
    local_qty: Decimal = Decimal("0")
    remote_qty: Decimal = Decimal("0")
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "discrepancy_type": self.discrepancy_type.value,
            "symbol": self.symbol,
            "order_id": self.order_id,
            "broker_order_id": self.broker_order_id,
            "local_status": self.local_status,
            "remote_status": self.remote_status,
            "local_qty": str(self.local_qty),
            "remote_qty": str(self.remote_qty),
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class PositionDiscrepancy:
    """Individual divergence detected between internal and broker position states."""

    discrepancy_type: DiscrepancyType
    symbol: str
    position_id: str | None = None
    local_side: str | None = None
    remote_side: str | None = None
    local_qty: Decimal = Decimal("0")
    remote_qty: Decimal = Decimal("0")
    delta_qty: Decimal = Decimal("0")
    local_price: Decimal | None = None
    remote_price: Decimal | None = None
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "discrepancy_type": self.discrepancy_type.value,
            "symbol": self.symbol,
            "position_id": self.position_id,
            "local_side": self.local_side,
            "remote_side": self.remote_side,
            "local_qty": str(self.local_qty),
            "remote_qty": str(self.remote_qty),
            "delta_qty": str(self.delta_qty),
            "local_price": str(self.local_price) if self.local_price is not None else None,
            "remote_price": str(self.remote_price) if self.remote_price is not None else None,
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class AccountDiscrepancy:
    """Individual divergence detected between internal and broker account balances/margins."""

    discrepancy_type: DiscrepancyType
    field_name: str
    local_value: Decimal
    remote_value: Decimal
    delta: Decimal
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "discrepancy_type": self.discrepancy_type.value,
            "field_name": self.field_name,
            "local_value": str(self.local_value),
            "remote_value": str(self.remote_value),
            "delta": str(self.delta),
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class ReconciliationSnapshot:
    """Complete immutable audit snapshot of a reconciliation comparison."""

    id: str
    organization_id: str
    broker_account_id: str
    status: ReconciliationStatus
    order_discrepancies: tuple[OrderDiscrepancy, ...] = ()
    position_discrepancies: tuple[PositionDiscrepancy, ...] = ()
    account_discrepancies: tuple[AccountDiscrepancy, ...] = ()
    balance_delta: Decimal = Decimal("0.0000")
    equity_delta: Decimal = Decimal("0.0000")
    details: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def has_discrepancies(self) -> bool:
        return (
            len(self.order_discrepancies) > 0
            or len(self.position_discrepancies) > 0
            or len(self.account_discrepancies) > 0
            or abs(self.balance_delta) > Decimal("0.0001")
            or abs(self.equity_delta) > Decimal("0.0001")
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "broker_account_id": self.broker_account_id,
            "status": self.status.value,
            "order_discrepancies": [d.to_dict() for d in self.order_discrepancies],
            "position_discrepancies": [d.to_dict() for d in self.position_discrepancies],
            "account_discrepancies": [d.to_dict() for d in self.account_discrepancies],
            "balance_delta": str(self.balance_delta),
            "equity_delta": str(self.equity_delta),
            "details": self.details,
            "created_at": self.created_at.isoformat(),
        }
