"""Database persistence models for institutional broker sandbox accounts and reconciliation audits."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from libraries.infrastructure.persistence.base import Base, TimestampMixin


class BrokerSandboxAccountModel(Base, TimestampMixin):
    """Database entity representing a tenant-scoped broker sandbox connection."""

    __tablename__ = "broker_sandbox_accounts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_by: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    environment: Mapped[str] = mapped_column(
        String(16), default="SANDBOX", nullable=False
    )
    account_id_external: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="DISCONNECTED", index=True, nullable=False
    )
    last_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_reconciled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    credentials_encrypted: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_broker_sandbox_org_provider", "organization_id", "provider"),
        Index("ix_broker_sandbox_org_created", "organization_id", "created_at"),
        Index("ix_broker_sandbox_org_status", "organization_id", "status"),
    )


class BrokerReconciliationSnapshotModel(Base):
    """Database entity storing immutable audit records of state reconciliation sweeps."""

    __tablename__ = "broker_reconciliation_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    broker_account_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("broker_sandbox_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32), default="MATCHED", index=True, nullable=False
    )
    order_discrepancies: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    position_discrepancies: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    account_discrepancies: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    balance_delta: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0.0000"), nullable=False
    )
    equity_delta: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0.0000"), nullable=False
    )
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_broker_recon_org_account", "organization_id", "broker_account_id"),
        Index("ix_broker_recon_org_created", "organization_id", "created_at"),
    )
