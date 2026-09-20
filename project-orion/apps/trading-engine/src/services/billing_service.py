"""Commercial billing service managing Stripe customer lifecycle, checkouts, and webhooks."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.billing.exceptions import (
    InvalidPlanCodeError,
    SubscriptionNotFoundError,
)
from libraries.domain.billing.models import (
    BillingSubscriptionStatus,
    CheckoutSession,
)
from libraries.domain.billing.ports import BillingProvider
from libraries.domain.subscription.models import PlanCode
from libraries.infrastructure.billing.config import BillingConfig
from libraries.infrastructure.billing.stripe_adapter import create_billing_adapter
from libraries.infrastructure.persistence.models.audit import AuditLogModel
from libraries.infrastructure.persistence.models.billing import (
    BillingCustomerModel,
    BillingEventModel,
    BillingInvoiceModel,
    BillingSubscriptionModel,
)
from libraries.observability.metrics import MetricsRegistry

from .subscription_service import SubscriptionService

logger = logging.getLogger("trading_engine.services.billing")


class BillingService:
    """Service orchestrating commercial billing, customer lifecycles, and webhook reconciliation."""

    def __init__(
        self,
        session: AsyncSession,
        provider: BillingProvider | None = None,
        config: BillingConfig | None = None,
        sub_service: SubscriptionService | None = None,
        metrics: MetricsRegistry | None = None,
    ) -> None:
        self.session = session
        self.config = config or BillingConfig.from_env()
        self.provider = provider or create_billing_adapter(self.config)
        self.sub_service = sub_service or SubscriptionService(session)
        self.metrics = metrics

    async def get_or_create_customer(
        self,
        organization_id: str,
        email: str,
        name: str = "",
    ) -> BillingCustomerModel:
        """Resolve existing Stripe customer for organization or create a new one."""
        stmt = select(BillingCustomerModel).where(
            BillingCustomerModel.organization_id == organization_id
        )
        res = await self.session.execute(stmt)
        customer_model = res.scalar_one_or_none()

        if customer_model is not None:
            return customer_model

        # Create new customer via provider
        domain_customer = await self.provider.create_customer(
            organization_id=organization_id,
            email=email,
            name=name,
        )

        now = datetime.now(timezone.utc)
        customer_model = BillingCustomerModel(
            id=f"bcust_{uuid.uuid4().hex[:16]}",
            organization_id=organization_id,
            provider_customer_id=domain_customer.provider_customer_id,
            email=email,
            name=name or f"Org {organization_id}",
            meta_data=domain_customer.meta_data,
            created_at=now,
            updated_at=now,
        )
        self.session.add(customer_model)

        # Audit log entry
        audit_entry = AuditLogModel(
            id=f"audit_{uuid.uuid4().hex[:16]}",
            organization_id=organization_id,
            event_type="BILLING_CUSTOMER_CREATED",
            component="billing_service",
            actor=email,
            details={
                "provider_customer_id": domain_customer.provider_customer_id,
                "email": email,
            },
            timestamp=now,
        )
        self.session.add(audit_entry)
        await self.session.flush()

        logger.info(
            "Created billing customer %s for org %s",
            domain_customer.provider_customer_id,
            organization_id,
        )
        return customer_model

    async def get_customer(self, organization_id: str) -> BillingCustomerModel | None:
        """Fetch billing customer for organization."""
        stmt = select(BillingCustomerModel).where(
            BillingCustomerModel.organization_id == organization_id
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_checkout_session(
        self,
        organization_id: str,
        user_id: str,
        user_email: str,
        plan_code: PlanCode,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSession:
        """Initiate server-validated Stripe Hosted Checkout session."""
        if plan_code == PlanCode.FREE:
            raise InvalidPlanCodeError("Cannot create a checkout session for Free Sandbox tier.")

        customer = await self.get_or_create_customer(organization_id, user_email)

        metadata = {
            "organization_id": organization_id,
            "user_id": user_id,
            "plan_code": plan_code.value,
        }

        session = await self.provider.create_checkout_session(
            customer_id=customer.provider_customer_id,
            plan_code=plan_code,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
        )

        now = datetime.now(timezone.utc)
        audit_entry = AuditLogModel(
            id=f"audit_{uuid.uuid4().hex[:16]}",
            organization_id=organization_id,
            event_type="BILLING_CHECKOUT_INITIATED",
            component="billing_service",
            actor=user_id,
            details={
                "session_id": session.session_id,
                "plan_code": plan_code.value,
                "customer_id": customer.provider_customer_id,
            },
            timestamp=now,
        )
        self.session.add(audit_entry)
        await self.session.flush()

        if self.metrics is not None:
            self.metrics.inc("billing_checkout_sessions_total")

        return session

    async def get_active_billing_subscription(
        self,
        organization_id: str,
    ) -> BillingSubscriptionModel | None:
        """Get the active provider-managed subscription record for an organization."""
        stmt = (
            select(BillingSubscriptionModel)
            .where(BillingSubscriptionModel.organization_id == organization_id)
            .order_by(BillingSubscriptionModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def cancel_subscription(
        self,
        organization_id: str,
        user_id: str = "system",
        at_period_end: bool = True,
    ) -> BillingSubscriptionModel:
        """Cancel active provider subscription at period end or immediately."""
        sub = await self.get_active_billing_subscription(organization_id)
        if sub is None or sub.status == "canceled":
            raise SubscriptionNotFoundError(
                f"No active billing subscription found for organization '{organization_id}'."
            )

        # Provider cancellation
        await self.provider.cancel_subscription(
            sub.provider_subscription_id,
            at_period_end=at_period_end,
        )

        now = datetime.now(timezone.utc)
        sub.cancel_at_period_end = at_period_end
        if not at_period_end:
            sub.status = "canceled"
            # Fall back to Free Sandbox immediately
            await self.sub_service.change_plan(organization_id, PlanCode.FREE)

        sub.updated_at = now
        await self.session.flush()

        audit_entry = AuditLogModel(
            id=f"audit_{uuid.uuid4().hex[:16]}",
            organization_id=organization_id,
            event_type="BILLING_SUBSCRIPTION_CANCELLED",
            component="billing_service",
            actor=user_id,
            details={
                "provider_subscription_id": sub.provider_subscription_id,
                "at_period_end": at_period_end,
            },
            timestamp=now,
        )
        self.session.add(audit_entry)
        await self.session.flush()

        logger.info(
            "Subscription %s cancelled (at_period_end=%s) for org %s",
            sub.provider_subscription_id,
            at_period_end,
            organization_id,
        )
        return sub

    async def list_invoices(
        self,
        organization_id: str,
    ) -> list[BillingInvoiceModel]:
        """List billing invoices for an organization."""
        stmt = (
            select(BillingInvoiceModel)
            .where(BillingInvoiceModel.organization_id == organization_id)
            .order_by(BillingInvoiceModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def handle_webhook_event(
        self,
        payload_bytes: bytes,
        sig_header: str,
    ) -> dict[str, Any]:
        """Ingest, cryptographically verify, and idempotently process Stripe webhook events."""
        event = self.provider.construct_event_payload(
            payload_bytes=payload_bytes,
            sig_header=sig_header,
            webhook_secret=self.config.webhook_secret,
        )

        event_id = event.get("id", "")
        event_type = event.get("type", "")
        event_obj = (event.get("data") or {}).get("object") or {}

        # 1. Deduplication check against billing_events
        stmt = select(BillingEventModel).where(BillingEventModel.provider_event_id == event_id)
        res = await self.session.execute(stmt)
        existing_event = res.scalar_one_or_none()
        if existing_event is not None:
            logger.info("Webhook event %s (%s) already processed. Skipping.", event_id, event_type)
            return {"status": "already_processed", "event_id": event_id}

        # 2. Dispatch event processing
        processed_status = "PROCESSED"
        now = datetime.now(timezone.utc)

        if event_type == "checkout.session.completed":
            await self._process_checkout_completed(event_obj)
        elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
            await self._process_subscription_updated(event_obj)
        elif event_type == "customer.subscription.deleted":
            await self._process_subscription_deleted(event_obj)
        elif event_type == "invoice.payment_succeeded":
            await self._process_invoice_payment_succeeded(event_obj)
        elif event_type == "invoice.payment_failed":
            await self._process_invoice_payment_failed(event_obj)
        else:
            logger.info("Ignored unhandled billing webhook event type: %s", event_type)
            processed_status = "IGNORED"

        # 3. Record event in billing_events table for replay protection
        billing_event = BillingEventModel(
            id=f"bevt_{uuid.uuid4().hex[:16]}",
            provider_event_id=event_id,
            event_type=event_type,
            processed_at=now,
            status=processed_status,
            meta_data={"object_id": event_obj.get("id")},
        )
        self.session.add(billing_event)
        await self.session.flush()

        if self.metrics is not None:
            self.metrics.inc("billing_webhook_events_total")

        return {"status": "success", "event_id": event_id, "event_type": event_type}

    # ─── Private Webhook Handlers ─────────────────────────────────────────────

    async def _process_checkout_completed(self, session_obj: dict[str, Any]) -> None:
        """Handle checkout.session.completed: activate subscription and unlock quotas."""
        metadata = session_obj.get("metadata") or {}
        org_id = metadata.get("organization_id")
        plan_code_raw = metadata.get("plan_code")
        subscription_id = session_obj.get("subscription")
        customer_id = session_obj.get("customer")

        if not org_id or not plan_code_raw:
            logger.warning("checkout.session.completed missing organization_id or plan_code in metadata.")
            return

        plan_code = PlanCode.from_str(plan_code_raw)
        now = datetime.now(timezone.utc)

        # Record or update billing_subscriptions
        if subscription_id:
            sub_stmt = select(BillingSubscriptionModel).where(
                BillingSubscriptionModel.provider_subscription_id == subscription_id
            )
            sub_res = await self.session.execute(sub_stmt)
            billing_sub = sub_res.scalar_one_or_none()

            if billing_sub is None:
                billing_sub = BillingSubscriptionModel(
                    id=f"bsub_{uuid.uuid4().hex[:16]}",
                    organization_id=org_id,
                    provider_subscription_id=subscription_id,
                    provider_customer_id=customer_id or "",
                    plan_code=plan_code.value,
                    status="active",
                    current_period_start=now,
                    current_period_end=None,
                    cancel_at_period_end=False,
                    meta_data=metadata,
                    created_at=now,
                    updated_at=now,
                )
                self.session.add(billing_sub)
            else:
                billing_sub.plan_code = plan_code.value
                billing_sub.status = "active"
                billing_sub.updated_at = now

        # Synchronize core subscription and unlock plan quotas in EntitlementService
        await self.sub_service.change_plan(org_id, plan_code)
        logger.info("Successfully activated %s tier for org %s via checkout session", plan_code.value, org_id)

    async def _process_subscription_updated(self, sub_obj: dict[str, Any]) -> None:
        """Handle customer.subscription.created/updated: sync status and quotas."""
        sub_id = sub_obj.get("id")
        customer_id = sub_obj.get("customer")
        status_raw = sub_obj.get("status", "active")
        status = BillingSubscriptionStatus.from_str(status_raw)

        metadata = sub_obj.get("metadata") or {}
        org_id = metadata.get("organization_id")

        if not org_id and customer_id:
            # Look up customer
            cust_stmt = select(BillingCustomerModel).where(
                BillingCustomerModel.provider_customer_id == customer_id
            )
            cust_res = await self.session.execute(cust_stmt)
            customer = cust_res.scalar_one_or_none()
            if customer is not None:
                org_id = customer.organization_id

        if not org_id:
            logger.warning("Could not resolve organization_id for subscription %s", sub_id)
            return

        # Resolve plan code
        plan_code_raw = metadata.get("plan_code")
        if plan_code_raw:
            plan_code = PlanCode.from_str(plan_code_raw)
        else:
            # Inspect price ID
            items = (sub_obj.get("items") or {}).get("data") or []
            if items:
                price_id = items[0].get("price", {}).get("id", "")
                plan_code = self.config.get_plan_code_for_price_id(price_id)
            else:
                plan_code = PlanCode.PRO

        now = datetime.now(timezone.utc)
        sub_stmt = select(BillingSubscriptionModel).where(
            BillingSubscriptionModel.provider_subscription_id == sub_id
        )
        sub_res = await self.session.execute(sub_stmt)
        billing_sub = sub_res.scalar_one_or_none()

        period_start = (
            datetime.fromtimestamp(sub_obj["current_period_start"], tz=timezone.utc)
            if sub_obj.get("current_period_start")
            else now
        )
        period_end = (
            datetime.fromtimestamp(sub_obj["current_period_end"], tz=timezone.utc)
            if sub_obj.get("current_period_end")
            else None
        )

        if billing_sub is None:
            billing_sub = BillingSubscriptionModel(
                id=f"bsub_{uuid.uuid4().hex[:16]}",
                organization_id=org_id,
                provider_subscription_id=sub_id,
                provider_customer_id=customer_id or "",
                plan_code=plan_code.value,
                status=status.value,
                current_period_start=period_start,
                current_period_end=period_end,
                cancel_at_period_end=bool(sub_obj.get("cancel_at_period_end", False)),
                meta_data=metadata,
                created_at=now,
                updated_at=now,
            )
            self.session.add(billing_sub)
        else:
            billing_sub.plan_code = plan_code.value
            billing_sub.status = status.value
            billing_sub.current_period_start = period_start
            billing_sub.current_period_end = period_end
            billing_sub.cancel_at_period_end = bool(sub_obj.get("cancel_at_period_end", False))
            billing_sub.updated_at = now

        # Entitlement State Synchronization
        if status.is_active:
            await self.sub_service.change_plan(org_id, plan_code)
        else:
            # Payment failure, uncollectible, or paused -> fall back fail-closed to Free tier
            logger.warning(
                "Subscription %s is in non-active status '%s'. Degrading org %s to Free limits.",
                sub_id,
                status.value,
                org_id,
            )
            await self.sub_service.change_plan(org_id, PlanCode.FREE)

    async def _process_subscription_deleted(self, sub_obj: dict[str, Any]) -> None:
        """Handle customer.subscription.deleted: reset organization to Free tier."""
        sub_id = sub_obj.get("id")
        sub_stmt = select(BillingSubscriptionModel).where(
            BillingSubscriptionModel.provider_subscription_id == sub_id
        )
        sub_res = await self.session.execute(sub_stmt)
        billing_sub = sub_res.scalar_one_or_none()

        if billing_sub is not None:
            billing_sub.status = "canceled"
            billing_sub.updated_at = datetime.now(timezone.utc)
            org_id = billing_sub.organization_id
            await self.sub_service.change_plan(org_id, PlanCode.FREE)
            logger.info("Subscription %s deleted. Org %s reset to Free Sandbox tier.", sub_id, org_id)

    async def _process_invoice_payment_succeeded(self, invoice_obj: dict[str, Any]) -> None:
        """Handle invoice.payment_succeeded: record invoice payment."""
        invoice_id = invoice_obj.get("id")
        customer_id = invoice_obj.get("customer")
        subscription_id = invoice_obj.get("subscription")

        cust_stmt = select(BillingCustomerModel).where(
            BillingCustomerModel.provider_customer_id == customer_id
        )
        cust_res = await self.session.execute(cust_stmt)
        customer = cust_res.scalar_one_or_none()
        if customer is None:
            logger.warning("Cannot find customer for invoice %s", invoice_id)
            return

        org_id = customer.organization_id
        amount_due = Decimal(str(invoice_obj.get("amount_due", 0))) / Decimal(100)
        amount_paid = Decimal(str(invoice_obj.get("amount_paid", 0))) / Decimal(100)
        currency = str(invoice_obj.get("currency", "usd")).lower()
        now = datetime.now(timezone.utc)

        inv_stmt = select(BillingInvoiceModel).where(
            BillingInvoiceModel.provider_invoice_id == invoice_id
        )
        inv_res = await self.session.execute(inv_stmt)
        inv_model = inv_res.scalar_one_or_none()

        if inv_model is None:
            inv_model = BillingInvoiceModel(
                id=f"binv_{uuid.uuid4().hex[:16]}",
                organization_id=org_id,
                provider_invoice_id=invoice_id,
                provider_customer_id=customer_id,
                provider_subscription_id=subscription_id,
                amount_due=amount_due,
                amount_paid=amount_paid,
                currency=currency,
                status="paid",
                hosted_invoice_url=invoice_obj.get("hosted_invoice_url"),
                invoice_pdf=invoice_obj.get("invoice_pdf"),
                created_at=now,
                updated_at=now,
            )
            self.session.add(inv_model)
        else:
            inv_model.amount_paid = amount_paid
            inv_model.status = "paid"
            inv_model.updated_at = now

        if self.metrics is not None:
            self.metrics.inc("billing_invoices_paid_total")

        logger.info("Recorded paid invoice %s ($%s) for org %s", invoice_id, amount_paid, org_id)

    async def _process_invoice_payment_failed(self, invoice_obj: dict[str, Any]) -> None:
        """Handle invoice.payment_failed: degrade subscription status and enforce Free limits."""
        invoice_id = invoice_obj.get("id")
        customer_id = invoice_obj.get("customer")
        subscription_id = invoice_obj.get("subscription")

        cust_stmt = select(BillingCustomerModel).where(
            BillingCustomerModel.provider_customer_id == customer_id
        )
        cust_res = await self.session.execute(cust_stmt)
        customer = cust_res.scalar_one_or_none()
        if customer is None:
            return

        org_id = customer.organization_id
        now = datetime.now(timezone.utc)

        # Update billing_subscriptions status to past_due
        if subscription_id:
            sub_stmt = select(BillingSubscriptionModel).where(
                BillingSubscriptionModel.provider_subscription_id == subscription_id
            )
            sub_res = await self.session.execute(sub_stmt)
            sub = sub_res.scalar_one_or_none()
            if sub is not None:
                sub.status = "past_due"
                sub.updated_at = now

        # Degrade to Free Sandbox fail-closed
        await self.sub_service.change_plan(org_id, PlanCode.FREE)

        if self.metrics is not None:
            self.metrics.inc("billing_payment_failures_total")

        logger.warning(
            "Invoice payment failed for invoice %s (org %s). Entitlements degraded to Free tier.",
            invoice_id,
            org_id,
        )
