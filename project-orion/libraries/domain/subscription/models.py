"""Domain models and value objects for Subscriptions and Entitlements.

Defines:
- PlanCode, SubscriptionStatus
- PlanLimits (Value Object)
- Plan (Domain Entity)
- Subscription (Domain Entity)
- Entitlement (Aggregate Value Object)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class PlanCode(StrEnum):
    """The four canonical SaaS subscription plan tiers."""

    FREE = "FREE"
    PRO = "PRO"
    BUSINESS = "BUSINESS"
    ENTERPRISE = "ENTERPRISE"

    @classmethod
    def from_str(cls, value: str) -> PlanCode:
        """Parse plan code case-insensitively."""
        normalized = value.strip().upper()
        try:
            return cls(normalized)
        except ValueError as exc:
            valid = ", ".join(p.value for p in cls)
            raise ValueError(f"Invalid plan code '{value}'. Must be one of: {valid}") from exc


class SubscriptionStatus(StrEnum):
    """Lifecycle states for a tenant organization subscription."""

    ACTIVE = "ACTIVE"
    TRIALING = "TRIALING"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

    @classmethod
    def from_str(cls, value: str) -> SubscriptionStatus:
        """Parse subscription status case-insensitively."""
        normalized = value.strip().upper()
        try:
            return cls(normalized)
        except ValueError as exc:
            valid = ", ".join(s.value for s in cls)
            raise ValueError(f"Invalid subscription status '{value}'. Must be one of: {valid}") from exc


@dataclass(frozen=True, slots=True)
class PlanLimits:
    """Immutable quota thresholds and entitlement limits for a plan tier."""

    max_accounts: int
    max_daily_orders: int
    max_workers: int
    allowed_assets: tuple[str, ...]
    retention_days: int

    def is_account_allowed(self, current_count: int) -> bool:
        """Verify if creating another account is permitted under this quota."""
        if self.max_accounts < 0:
            return True  # Unlimited
        return current_count < self.max_accounts

    def is_daily_order_allowed(self, current_daily_orders: int) -> bool:
        """Verify if placing another order today is permitted under this quota."""
        if self.max_daily_orders < 0:
            return True  # Unlimited
        return current_daily_orders < self.max_daily_orders

    def is_worker_allowed(self, active_worker_count: int = 0) -> bool:
        """Verify if enabling an autonomous worker is permitted."""
        if self.max_workers < 0:
            return True  # Unlimited
        return active_worker_count < self.max_workers

    def is_asset_allowed(self, symbol: str) -> bool:
        """Verify if trading a given instrument symbol is permitted."""
        if "*" in self.allowed_assets:
            return True
        norm = symbol.strip().upper()
        # Handle both EURUSD and EUR/USD formats
        if "/" not in norm and len(norm) == 6:
            norm_slash = f"{norm[:3]}/{norm[3:]}"
        else:
            norm_slash = norm
        return norm in self.allowed_assets or norm_slash in self.allowed_assets


@dataclass(frozen=True, slots=True)
class Plan:
    """Domain entity defining a SaaS subscription plan."""

    id: str
    code: PlanCode
    name: str
    description: str
    limits: PlanLimits
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Plan id must not be empty.")
        if not self.name or not self.name.strip():
            raise ValueError("Plan name must not be empty.")


@dataclass(frozen=True, slots=True)
class Subscription:
    """Domain entity representing an organization's active subscription to a plan."""

    id: str
    organization_id: str
    plan_id: str
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    current_period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    meta_data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Subscription id must not be empty.")
        if not self.organization_id:
            raise ValueError("Organization id must not be empty.")
        if not self.plan_id:
            raise ValueError("Plan id must not be empty.")

    @property
    def is_active(self) -> bool:
        """Evaluate if the subscription is active or trialing."""
        return self.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)


@dataclass(frozen=True, slots=True)
class Entitlement:
    """Aggregate snapshot of effective entitlements for an organization."""

    organization_id: str
    plan: Plan
    subscription: Subscription | None
    limits: PlanLimits

    @property
    def is_subscription_active(self) -> bool:
        """Check if organization holds an active subscription."""
        return self.subscription is not None and self.subscription.is_active
