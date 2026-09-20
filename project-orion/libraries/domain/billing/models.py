"""Domain models and value objects for Commercial Billing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any

from libraries.domain.subscription.models import PlanCode, SubscriptionStatus


class BillingSubscriptionStatus(StrEnum):
    """Normalized Stripe subscription status lifecycle states."""

    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    PAUSED = "paused"

    @classmethod
    def from_str(cls, value: str) -> BillingSubscriptionStatus:
        """Parse status string case-insensitively."""
        normalized = value.strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            valid = ", ".join(s.value for s in cls)
            raise ValueError(
                f"Invalid billing subscription status '{value}'. Must be one of: {valid}"
            ) from exc

    def to_subscription_status(self) -> SubscriptionStatus:
        """Map provider subscription status to canonical ORION SubscriptionStatus."""
        mapping = {
            self.TRIALING: SubscriptionStatus.TRIALING,
            self.ACTIVE: SubscriptionStatus.ACTIVE,
            self.PAST_DUE: SubscriptionStatus.SUSPENDED,
            self.CANCELED: SubscriptionStatus.CANCELLED,
            self.UNPAID: SubscriptionStatus.SUSPENDED,
            self.INCOMPLETE: SubscriptionStatus.SUSPENDED,
            self.INCOMPLETE_EXPIRED: SubscriptionStatus.EXPIRED,
            self.PAUSED: SubscriptionStatus.SUSPENDED,
        }
        return mapping[self]

    @property
    def is_active(self) -> bool:
        """Check if subscription is in good standing (active or trialing)."""
        return self in (self.ACTIVE, self.TRIALING)


@dataclass(frozen=True, slots=True)
class BillingCustomer:
    """Domain entity representing an organization's commercial billing customer."""

    id: str
    organization_id: str
    provider_customer_id: str
    email: str
    name: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    meta_data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("BillingCustomer id must not be empty.")
        if not self.organization_id:
            raise ValueError("BillingCustomer organization_id must not be empty.")
        if not self.provider_customer_id:
            raise ValueError("BillingCustomer provider_customer_id must not be empty.")
        if not self.email or "@" not in self.email:
            raise ValueError(f"Invalid email address: '{self.email}'")


@dataclass(frozen=True, slots=True)
class BillingSubscription:
    """Domain entity representing a commercial provider-managed subscription."""

    id: str
    organization_id: str
    provider_subscription_id: str
    provider_customer_id: str
    plan_code: PlanCode
    status: BillingSubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    latest_invoice_id: str | None = None
    meta_data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("BillingSubscription id must not be empty.")
        if not self.organization_id:
            raise ValueError("BillingSubscription organization_id must not be empty.")
        if not self.provider_subscription_id:
            raise ValueError("BillingSubscription provider_subscription_id must not be empty.")

    @property
    def is_active(self) -> bool:
        """Check if subscription grants active plan entitlements."""
        return self.status.is_active


@dataclass(frozen=True, slots=True)
class BillingInvoice:
    """Domain entity representing a commercial billing invoice."""

    id: str
    organization_id: str
    provider_invoice_id: str
    provider_customer_id: str
    provider_subscription_id: str | None = None
    amount_due: Decimal = Decimal("0.00")
    amount_paid: Decimal = Decimal("0.00")
    currency: str = "usd"
    status: str = "paid"
    hosted_invoice_url: str | None = None
    invoice_pdf: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("BillingInvoice id must not be empty.")
        if not self.organization_id:
            raise ValueError("BillingInvoice organization_id must not be empty.")
        if not self.provider_invoice_id:
            raise ValueError("BillingInvoice provider_invoice_id must not be empty.")


@dataclass(frozen=True, slots=True)
class BillingEvent:
    """Domain entity representing a verified billing webhook event for idempotency."""

    id: str
    provider_event_id: str
    event_type: str
    processed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "PROCESSED"
    meta_data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("BillingEvent id must not be empty.")
        if not self.provider_event_id:
            raise ValueError("BillingEvent provider_event_id must not be empty.")
        if not self.event_type:
            raise ValueError("BillingEvent event_type must not be empty.")


@dataclass(frozen=True, slots=True)
class CheckoutSession:
    """Value object representing a generated checkout session."""

    session_id: str
    url: str
    customer_id: str
    plan_code: PlanCode
    organization_id: str
    expires_at: datetime | None = None
