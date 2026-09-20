"""Order, Fill, and ExecutionReport database models."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libraries.infrastructure.persistence.base import Base, TimestampMixin


class OrderModel(Base, TimestampMixin):
    """Database entity representing a trading order and its lifecycle state."""

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    broker_order_id: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    account_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("accounts.id"), index=True, nullable=False
    )
    organization_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    symbol: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    stop_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    status: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    filled_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal(0), nullable=False
    )
    average_fill_price: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 6), nullable=True
    )
    strategy_id: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    meta_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    account = relationship("AccountModel", back_populates="orders")
    fills = relationship("FillModel", back_populates="order", cascade="all, delete-orphan")
    execution_reports = relationship(
        "ExecutionReportModel", back_populates="order", cascade="all, delete-orphan"
    )


class FillModel(Base):
    """Database entity representing an executed fill against an order."""

    __tablename__ = "fills"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("orders.id"), index=True, nullable=False
    )
    organization_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    broker_fill_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    commission: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal(0), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    order = relationship("OrderModel", back_populates="fills")


class ExecutionReportModel(Base):
    """Database entity tracking latency, slippage, and execution audit for orders."""

    __tablename__ = "execution_reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("orders.id"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    slippage_pips: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    order = relationship("OrderModel", back_populates="execution_reports")
