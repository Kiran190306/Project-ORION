"""Abstract ports and provider protocols for Commercial Billing."""

from __future__ import annotations

from typing import Any, Protocol

from libraries.domain.billing.models import (
    BillingCustomer,
    BillingSubscription,
    CheckoutSession,
)
from libraries.domain.subscription.models import PlanCode


class BillingProvider(Protocol):
    """Provider-agnostic protocol decoupling billing domain logic from payment SDKs."""

    async def create_customer(
        self,
        organization_id: str,
        email: str,
        name: str = "",
    ) -> BillingCustomer:
        """Create a new billing customer with the payment provider."""
        ...

    async def get_customer(
        self,
        provider_customer_id: str,
    ) -> BillingCustomer | None:
        """Retrieve customer details from payment provider."""
        ...

    async def create_checkout_session(
        self,
        customer_id: str,
        plan_code: PlanCode,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, str],
    ) -> CheckoutSession:
        """Generate a hosted checkout session URL for upgrading/subscribing."""
        ...

    async def get_subscription(
        self,
        provider_subscription_id: str,
    ) -> BillingSubscription | None:
        """Retrieve current subscription status from payment provider."""
        ...

    async def cancel_subscription(
        self,
        provider_subscription_id: str,
        at_period_end: bool = True,
    ) -> BillingSubscription:
        """Cancel a subscription immediately or at period end."""
        ...

    def construct_event_payload(
        self,
        payload_bytes: bytes,
        sig_header: str,
        webhook_secret: str,
    ) -> dict[str, Any]:
        """Verify webhook cryptographic signature and parse event dictionary."""
        ...
