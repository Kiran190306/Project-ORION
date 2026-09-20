"""Account database model."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libraries.infrastructure.persistence.base import Base, TimestampMixin


class AccountModel(Base, TimestampMixin):
    """Database entity representing a trading or broker account."""

    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.id"), index=True, nullable=True
    )
    organization_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    broker_name: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    account_number: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal(0), nullable=False
    )
    equity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal(0), nullable=False
    )
    margin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal(0), nullable=False
    )
    margin_free: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal(0), nullable=False
    )
    margin_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    leverage: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    meta_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    user = relationship("UserModel", backref="accounts")
    organization = relationship("OrganizationModel", backref="accounts")
    orders = relationship("OrderModel", back_populates="account", cascade="all, delete-orphan")
    positions = relationship("PositionModel", back_populates="account", cascade="all, delete-orphan")
