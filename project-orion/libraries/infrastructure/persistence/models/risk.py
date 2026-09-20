"""Risk limit and breach database models."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libraries.infrastructure.persistence.base import Base, TimestampMixin


class RiskLimitModel(Base, TimestampMixin):
    """Database entity defining a risk limit threshold."""

    __tablename__ = "risk_limits"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    limit_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    threshold: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    organization_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_hard_limit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    breaches = relationship(
        "RiskBreachModel", back_populates="risk_limit", cascade="all, delete-orphan"
    )


class RiskBreachModel(Base):
    """Database entity logging an event where a risk limit was breached."""

    __tablename__ = "risk_breaches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    limit_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("risk_limits.id"), index=True, nullable=False
    )
    severity: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    breach_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    action_taken: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    risk_limit = relationship("RiskLimitModel", back_populates="breaches")
