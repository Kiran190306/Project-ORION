"""SQLAlchemy persistence models for Commercial Billing."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libraries.domain.billing.models import (
    BillingCustomer,
    BillingEvent,
    BillingInvoice,
    BillingSubscription,
    BillingSubscriptionStatus,
)
from libraries.domain.subscription.models import PlanCode
from libraries.infrastructure.persistence.base import Base, TimestampMixin


class BillingCustomerModel(Base, TimestampMixin):
    """Database entity linking an Organization to a Stripe Customer ID."""

    __tablename__ = "billing_customers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    provider_customer_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    meta_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    organization = relationship("OrganizationModel")

    def to_domain(self) -> BillingCustomer:
        """Convert persistence model to immutable domain entity."""
        return BillingCustomer(
            id=self.id,
            organization_id=self.organization_id,
            provider_customer_id=self.provider_customer_id,
            email=self.email,
            name=self.name,
            created_at=self.created_at,
            meta_data=self.meta_data or {},
        )


class BillingSubscriptionModel(Base, TimestampMixin):
    """Database entity storing provider subscription metadata."""

    __tablename__ = "billing_subscriptions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    provider_subscription_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
    )
    provider_customer_id: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )
    plan_code: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    latest_invoice_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    meta_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    organization = relationship("OrganizationModel")

    def to_domain(self) -> BillingSubscription:
        """Convert persistence model to immutable domain entity."""
        return BillingSubscription(
            id=self.id,
            organization_id=self.organization_id,
            provider_subscription_id=self.provider_subscription_id,
            provider_customer_id=self.provider_customer_id,
            plan_code=PlanCode(self.plan_code),
            status=BillingSubscriptionStatus(self.status),
            current_period_start=self.current_period_start,
            current_period_end=self.current_period_end,
            cancel_at_period_end=self.cancel_at_period_end,
            latest_invoice_id=self.latest_invoice_id,
            meta_data=self.meta_data or {},
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class BillingInvoiceModel(Base, TimestampMixin):
    """Database entity storing invoice payment records."""

    __tablename__ = "billing_invoices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    provider_invoice_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
    )
    provider_customer_id: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )
    provider_subscription_id: Mapped[str | None] = mapped_column(
        String(128),
        index=True,
        nullable=True,
    )
    amount_due: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), default="usd", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="paid", index=True, nullable=False)
    hosted_invoice_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    invoice_pdf: Mapped[str | None] = mapped_column(String(512), nullable=True)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("OrganizationModel")

    def to_domain(self) -> BillingInvoice:
        """Convert persistence model to immutable domain entity."""
        return BillingInvoice(
            id=self.id,
            organization_id=self.organization_id,
            provider_invoice_id=self.provider_invoice_id,
            provider_customer_id=self.provider_customer_id,
            provider_subscription_id=self.provider_subscription_id,
            amount_due=self.amount_due,
            amount_paid=self.amount_paid,
            currency=self.currency,
            status=self.status,
            hosted_invoice_url=self.hosted_invoice_url,
            invoice_pdf=self.invoice_pdf,
            period_start=self.period_start,
            period_end=self.period_end,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class BillingEventModel(Base):
    """Database entity logging processed Stripe webhook events for replay protection."""

    __tablename__ = "billing_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_event_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), default="PROCESSED", nullable=False)
    meta_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    def to_domain(self) -> BillingEvent:
        """Convert persistence model to immutable domain entity."""
        return BillingEvent(
            id=self.id,
            provider_event_id=self.provider_event_id,
            event_type=self.event_type,
            processed_at=self.processed_at,
            status=self.status,
            meta_data=self.meta_data or {},
        )
