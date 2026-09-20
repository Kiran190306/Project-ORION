"""Stripe Billing Adapter and deterministic Mock Billing Adapter."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from libraries.domain.billing.exceptions import (
    BillingProviderError,
    InvalidWebhookSignatureError,
    SubscriptionNotFoundError,
)
from libraries.domain.billing.models import (
    BillingCustomer,
    BillingSubscription,
    BillingSubscriptionStatus,
    CheckoutSession,
)
from libraries.domain.billing.ports import BillingProvider
from libraries.domain.subscription.models import PlanCode

from .config import BillingConfig

logger = logging.getLogger("orion.billing.stripe_adapter")


class StripeBillingAdapter(BillingProvider):
    """Production implementation of BillingProvider wrapping the Stripe Python SDK (Test Mode)."""

    def __init__(self, config: BillingConfig) -> None:
        self._config = config
        import stripe  # Encapsulate Stripe import strictly inside adapter

        stripe.api_key = config.secret_key
        self._stripe = stripe

    async def create_customer(
        self,
        organization_id: str,
        email: str,
        name: str = "",
    ) -> BillingCustomer:
        """Create a new Stripe Customer in test mode."""
        try:
            customer = self._stripe.Customer.create(
                email=email,
                name=name or f"Org {organization_id}",
                metadata={"organization_id": organization_id},
                idempotency_key=f"cust_{organization_id}",
            )
            created_dt = (
                datetime.fromtimestamp(customer.created, tz=timezone.utc)
                if hasattr(customer, "created") and customer.created
                else datetime.now(timezone.utc)
            )
            return BillingCustomer(
                id=str(uuid.uuid4()),
                organization_id=organization_id,
                provider_customer_id=customer.id,
                email=email,
                name=name or f"Org {organization_id}",
                created_at=created_dt,
                meta_data=dict(customer.metadata or {}),
            )
        except self._stripe.error.StripeError as exc:
            logger.error("Stripe customer creation failed: %s", exc)
            raise BillingProviderError(f"Failed to create Stripe customer: {exc}") from exc

    async def get_customer(
        self,
        provider_customer_id: str,
    ) -> BillingCustomer | None:
        """Retrieve customer details from Stripe."""
        try:
            customer = self._stripe.Customer.retrieve(provider_customer_id)
            if getattr(customer, "deleted", False):
                return None
            org_id = (customer.metadata or {}).get("organization_id", "")
            return BillingCustomer(
                id=str(uuid.uuid4()),
                organization_id=org_id,
                provider_customer_id=customer.id,
                email=customer.email or "",
                name=customer.name or "",
                meta_data=dict(customer.metadata or {}),
            )
        except self._stripe.error.InvalidRequestError:
            return None
        except self._stripe.error.StripeError as exc:
            raise BillingProviderError(f"Stripe error retrieving customer: {exc}") from exc

    async def create_checkout_session(
        self,
        customer_id: str,
        plan_code: PlanCode,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, str],
    ) -> CheckoutSession:
        """Generate a Stripe Hosted Checkout Session in test mode."""
        price_id = self._config.get_price_id_for_plan(plan_code)
        try:
            session = self._stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata,
            )
            expires_at = (
                datetime.fromtimestamp(session.expires_at, tz=timezone.utc)
                if hasattr(session, "expires_at") and session.expires_at
                else None
            )
            return CheckoutSession(
                session_id=session.id,
                url=session.url or "",
                customer_id=customer_id,
                plan_code=plan_code,
                organization_id=metadata.get("organization_id", ""),
                expires_at=expires_at,
            )
        except self._stripe.error.StripeError as exc:
            logger.error("Failed to create Stripe checkout session: %s", exc)
            raise BillingProviderError(f"Stripe checkout creation error: {exc}") from exc

    async def get_subscription(
        self,
        provider_subscription_id: str,
    ) -> BillingSubscription | None:
        """Retrieve subscription from Stripe."""
        try:
            sub = self._stripe.Subscription.retrieve(provider_subscription_id)
            if getattr(sub, "deleted", False):
                return None
            plan_id = sub["items"]["data"][0]["price"]["id"]
            plan_code = self._config.get_plan_code_for_price_id(plan_id)
            status = BillingSubscriptionStatus.from_str(sub.status)
            start_dt = datetime.fromtimestamp(sub.current_period_start, tz=timezone.utc)
            end_dt = (
                datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc)
                if sub.current_period_end
                else None
            )
            org_id = (sub.metadata or {}).get("organization_id", "")
            latest_invoice = sub.latest_invoice
            latest_invoice_id = latest_invoice if isinstance(latest_invoice, str) else getattr(latest_invoice, "id", None)
            return BillingSubscription(
                id=str(uuid.uuid4()),
                organization_id=org_id,
                provider_subscription_id=sub.id,
                provider_customer_id=sub.customer,
                plan_code=plan_code,
                status=status,
                current_period_start=start_dt,
                current_period_end=end_dt,
                cancel_at_period_end=bool(sub.cancel_at_period_end),
                latest_invoice_id=latest_invoice_id,
                meta_data=dict(sub.metadata or {}),
            )
        except self._stripe.error.InvalidRequestError:
            return None
        except self._stripe.error.StripeError as exc:
            raise BillingProviderError(f"Stripe subscription retrieval error: {exc}") from exc

    async def cancel_subscription(
        self,
        provider_subscription_id: str,
        at_period_end: bool = True,
    ) -> BillingSubscription:
        """Cancel subscription with Stripe."""
        try:
            if at_period_end:
                sub = self._stripe.Subscription.modify(
                    provider_subscription_id,
                    cancel_at_period_end=True,
                )
            else:
                sub = self._stripe.Subscription.cancel(provider_subscription_id)

            sub_entity = await self.get_subscription(sub.id)
            if sub_entity is None:
                raise SubscriptionNotFoundError(f"Subscription {provider_subscription_id} not found after cancel.")
            return sub_entity
        except self._stripe.error.StripeError as exc:
            logger.error("Failed to cancel Stripe subscription: %s", exc)
            raise BillingProviderError(f"Stripe cancellation error: {exc}") from exc

    def construct_event_payload(
        self,
        payload_bytes: bytes,
        sig_header: str,
        webhook_secret: str,
    ) -> dict[str, Any]:
        """Verify webhook signature and decode event dictionary."""
        try:
            event = self._stripe.Webhook.construct_event(
                payload=payload_bytes,
                sig_header=sig_header,
                secret=webhook_secret,
                tolerance=300,
            )
            # Ensure return is a plain dict
            return dict(event) if isinstance(event, dict) else json.loads(str(event))
        except self._stripe.error.SignatureVerificationError as exc:
            logger.warning("Invalid Stripe webhook signature: %s", exc)
            raise InvalidWebhookSignatureError("Stripe webhook signature verification failed.") from exc
        except Exception as exc:
            logger.error("Error decoding Stripe webhook: %s", exc)
            raise InvalidWebhookSignatureError(f"Malformed webhook payload: {exc}") from exc


class MockBillingAdapter(BillingProvider):
    """Deterministic in-memory billing provider for offline testing and development."""

    def __init__(self, config: BillingConfig | None = None) -> None:
        self._config = config or BillingConfig(use_mock=True)
        self.customers: dict[str, BillingCustomer] = {}
        self.subscriptions: dict[str, BillingSubscription] = {}
        self.checkout_sessions: dict[str, CheckoutSession] = {}

    async def create_customer(
        self,
        organization_id: str,
        email: str,
        name: str = "",
    ) -> BillingCustomer:
        """Create mock customer deterministically."""
        provider_id = f"cus_mock_{organization_id[:12]}"
        customer = BillingCustomer(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            provider_customer_id=provider_id,
            email=email,
            name=name or f"Mock Customer {organization_id}",
            created_at=datetime.now(timezone.utc),
            meta_data={"organization_id": organization_id},
        )
        self.customers[provider_id] = customer
        return customer

    async def get_customer(
        self,
        provider_customer_id: str,
    ) -> BillingCustomer | None:
        return self.customers.get(provider_customer_id)

    async def create_checkout_session(
        self,
        customer_id: str,
        plan_code: PlanCode,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, str],
    ) -> CheckoutSession:
        session_id = f"cs_test_{uuid.uuid4().hex[:16]}"
        url = f"https://checkout.stripe.com/c/pay/{session_id}"
        session = CheckoutSession(
            session_id=session_id,
            url=url,
            customer_id=customer_id,
            plan_code=plan_code,
            organization_id=metadata.get("organization_id", ""),
            expires_at=datetime.now(timezone.utc),
        )
        self.checkout_sessions[session_id] = session
        return session

    async def get_subscription(
        self,
        provider_subscription_id: str,
    ) -> BillingSubscription | None:
        return self.subscriptions.get(provider_subscription_id)

    async def cancel_subscription(
        self,
        provider_subscription_id: str,
        at_period_end: bool = True,
    ) -> BillingSubscription:
        sub = self.subscriptions.get(provider_subscription_id)
        if sub is None:
            raise SubscriptionNotFoundError(f"Mock subscription '{provider_subscription_id}' not found.")
        updated = BillingSubscription(
            id=sub.id,
            organization_id=sub.organization_id,
            provider_subscription_id=sub.provider_subscription_id,
            provider_customer_id=sub.provider_customer_id,
            plan_code=sub.plan_code,
            status=sub.status if at_period_end else BillingSubscriptionStatus.CANCELED,
            current_period_start=sub.current_period_start,
            current_period_end=sub.current_period_end,
            cancel_at_period_end=at_period_end,
            latest_invoice_id=sub.latest_invoice_id,
            meta_data=sub.meta_data,
            created_at=sub.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        self.subscriptions[provider_subscription_id] = updated
        return updated

    def construct_event_payload(
        self,
        payload_bytes: bytes,
        sig_header: str,
        webhook_secret: str,
    ) -> dict[str, Any]:
        """Verify mock webhook signature or parse JSON directly."""
        if not sig_header:
            raise InvalidWebhookSignatureError("Missing Stripe-Signature header.")
        if sig_header == "invalid_signature":
            raise InvalidWebhookSignatureError("Invalid Stripe-Signature header.")

        # If a secret is specified and sig_header contains 't=...,v1=...', verify HMAC
        if webhook_secret and "v1=" in sig_header:
            try:
                elements = dict(item.split("=", 1) for item in sig_header.split(","))
                timestamp = elements.get("t", "")
                signature = elements.get("v1", "")
                signed_payload = f"{timestamp}.".encode() + payload_bytes
                expected_sig = hmac.new(
                    webhook_secret.encode("utf-8"),
                    signed_payload,
                    hashlib.sha256,
                ).hexdigest()
                if not hmac.compare_digest(signature, expected_sig):
                    raise InvalidWebhookSignatureError("HMAC verification mismatch.")
            except InvalidWebhookSignatureError:
                raise
            except Exception as exc:
                raise InvalidWebhookSignatureError(f"Signature verification parse error: {exc}") from exc

        try:
            return json.loads(payload_bytes.decode("utf-8"))
        except Exception as exc:
            raise InvalidWebhookSignatureError(f"Invalid JSON payload: {exc}") from exc


def create_billing_adapter(config: BillingConfig) -> BillingProvider:
    """Factory creating StripeBillingAdapter or MockBillingAdapter based on configuration."""
    if config.is_mock_enabled:
        logger.info("Initializing MockBillingAdapter (Stripe credentials absent or mock enabled).")
        return MockBillingAdapter(config)
    logger.info("Initializing StripeBillingAdapter in TEST MODE.")
    return StripeBillingAdapter(config)
