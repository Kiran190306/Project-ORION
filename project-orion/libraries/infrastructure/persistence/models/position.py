"""Position database model."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libraries.infrastructure.persistence.base import Base, TimestampMixin


class PositionModel(Base, TimestampMixin):
    """Database entity representing an open or historical trading position."""

    __tablename__ = "positions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
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
    side: Mapped[str] = mapped_column(String(8), nullable=False)  # BUY / SELL
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    open_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal(0), nullable=False
    )
    unrealized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal(0), nullable=False
    )
    commission: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal(0), nullable=False
    )
    swap: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal(0), nullable=False
    )
    is_open: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    meta_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationship
    account = relationship("AccountModel", back_populates="positions")
