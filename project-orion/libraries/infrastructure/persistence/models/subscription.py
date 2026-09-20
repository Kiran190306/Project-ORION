"""Subscription and Plan database models for SaaS tier enforcement."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libraries.domain.subscription.models import (
    Plan,
    PlanCode,
    PlanLimits,
    Subscription,
    SubscriptionStatus,
)
from libraries.infrastructure.persistence.base import Base, TimestampMixin


class PlanModel(Base, TimestampMixin):
    """Database entity defining a subscription tier and its quota limits."""

    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    max_accounts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_daily_orders: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    max_workers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    allowed_assets: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    # Relationships
    subscriptions = relationship("SubscriptionModel", back_populates="plan")

    def to_domain(self) -> Plan:
        """Convert persistence model to immutable domain entity."""
        return Plan(
            id=self.id,
            code=PlanCode(self.code),
            name=self.name,
            description=self.description,
            limits=PlanLimits(
                max_accounts=self.max_accounts,
                max_daily_orders=self.max_daily_orders,
                max_workers=self.max_workers,
                allowed_assets=tuple(self.allowed_assets),
                retention_days=self.retention_days,
            ),
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class SubscriptionModel(Base, TimestampMixin):
    """Database entity representing a tenant organization's subscription."""

    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    plan_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("plans.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True, nullable=False)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    meta_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    organization = relationship("OrganizationModel", back_populates="subscriptions")
    plan = relationship("PlanModel", back_populates="subscriptions")

    def to_domain(self) -> Subscription:
        """Convert persistence model to immutable domain entity."""
        return Subscription(
            id=self.id,
            organization_id=self.organization_id,
            plan_id=self.plan_id,
            status=SubscriptionStatus(self.status),
            current_period_start=self.current_period_start,
            current_period_end=self.current_period_end,
            cancel_at_period_end=self.cancel_at_period_end,
            created_at=self.created_at,
            updated_at=self.updated_at,
            meta_data=self.meta_data or {},
        )
