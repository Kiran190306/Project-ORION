"""Repository interfaces (Protocols) for Subscription and Plan domain operations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from libraries.domain.subscription.models import Plan, PlanCode, Subscription


@runtime_checkable
class PlanRepository(Protocol):
    """Protocol defining persistence operations for subscription plans."""

    async def get_plan(self, plan_id: str) -> Plan | None:
        """Fetch a plan by its primary identifier."""
        ...

    async def get_plan_by_code(self, code: PlanCode | str) -> Plan | None:
        """Fetch a plan by its unique plan code."""
        ...

    async def list_active_plans(self) -> list[Plan]:
        """List all active subscription plans."""
        ...

    async def create_plan(self, plan: Plan) -> Plan:
        """Persist a new subscription plan."""
        ...


@runtime_checkable
class SubscriptionRepository(Protocol):
    """Protocol defining persistence operations for organization subscriptions."""

    async def create_subscription(self, subscription: Subscription) -> Subscription:
        """Persist a new subscription for an organization."""
        ...

    async def get_subscription(self, subscription_id: str) -> Subscription | None:
        """Fetch a subscription by its primary identifier."""
        ...

    async def get_active_subscription_by_org(self, organization_id: str) -> Subscription | None:
        """Fetch the current active or trialing subscription for an organization."""
        ...

    async def get_latest_subscription_by_org(self, organization_id: str) -> Subscription | None:
        """Fetch the most recent subscription for an organization (active or inactive)."""
        ...

    async def list_subscriptions_by_org(self, organization_id: str) -> list[Subscription]:
        """List all historical and active subscriptions for an organization."""
        ...

    async def update_subscription(self, subscription: Subscription) -> Subscription:
        """Update an existing subscription's status, period, or metadata."""
        ...
