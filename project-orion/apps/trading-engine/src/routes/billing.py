"""Commercial billing API routes including Stripe checkout and webhook ingestion."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from libraries.domain.billing.exceptions import (
    InvalidWebhookSignatureError,
    SubscriptionNotFoundError,
)
from libraries.domain.organization.permissions import Permission
from libraries.domain.security.rate_limit import RateLimitPolicies
from libraries.domain.subscription.models import PlanCode

from ..dependencies import (
    TenantContext,
    get_billing_service,
    get_current_active_user,
    rate_limit,
    require_permission,
)
from ..services.billing_service import BillingService

logger = logging.getLogger("trading_engine.routes.billing")

router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])


# ─── Schemas ──────────────────────────────────────────────────────────────────


class CreateCheckoutRequest(BaseModel):
    plan_code: str = Field(
        description="Target plan tier to purchase (PRO, BUSINESS, ENTERPRISE)"
    )
    success_url: str | None = Field(
        default=None,
        description="Custom redirect URL on successful payment",
    )
    cancel_url: str | None = Field(
        default=None,
        description="Custom redirect URL on checkout cancellation",
    )


class CheckoutResponse(BaseModel):
    session_id: str
    url: str
    plan_code: str
    customer_id: str


class CancelSubscriptionRequest(BaseModel):
    at_period_end: bool = Field(
        default=True,
        description="Whether to cancel at the end of the current billing cycle",
    )


class BillingCustomerResponse(BaseModel):
    id: str
    organization_id: str
    provider_customer_id: str
    email: str
    name: str


class BillingSubscriptionResponse(BaseModel):
    id: str
    organization_id: str
    provider_subscription_id: str
    plan_code: str
    status: str
    current_period_start: str
    current_period_end: str | None = None
    cancel_at_period_end: bool = False


class BillingInvoiceResponse(BaseModel):
    id: str
    provider_invoice_id: str
    amount_due: float
    amount_paid: float
    currency: str
    status: str
    hosted_invoice_url: str | None = None
    invoice_pdf: str | None = None
    created_at: str


class BillingOverviewResponse(BaseModel):
    customer: BillingCustomerResponse | None = None
    subscription: BillingSubscriptionResponse | None = None
    recent_invoices: list[BillingInvoiceResponse] = []


# ─── Webhook Ingestion (Zero JWT dependency, raw bytes) ───────────────────────


@router.post(
    "/webhooks/stripe",
    status_code=status.HTTP_200_OK,
    summary="Stripe Webhook Receiver",
    description="Ingests raw Stripe webhook events, verifies HMAC signatures, and deduplicates event IDs.",
)
async def stripe_webhook(
    request: Request,
    billing_service: Annotated[BillingService, Depends(get_billing_service)],
) -> dict[str, Any]:
    """Ingest raw Stripe webhook bytes and process subscription/invoice lifecycle events."""
    sig_header = request.headers.get("Stripe-Signature") or request.headers.get("stripe-signature") or ""
    if not sig_header:
        logger.warning("Stripe webhook received without Stripe-Signature header.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header",
        )

    # Ingest raw body bytes unaltered for byte-accurate HMAC verification
    payload_bytes = await request.body()

    try:
        result = await billing_service.handle_webhook_event(
            payload_bytes=payload_bytes,
            sig_header=sig_header,
        )
        return result
    except InvalidWebhookSignatureError as exc:
        logger.warning("Invalid webhook signature: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        ) from exc
    except Exception as exc:
        logger.exception("Unhandled error processing Stripe webhook")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error processing webhook payload",
        ) from exc


# ─── Tenant-Scoped Billing Endpoints ──────────────────────────────────────────


@router.get(
    "",
    response_model=BillingOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Billing Overview",
    description="Returns aggregated customer, active subscription, and invoice history for current tenant.",
)
async def get_billing_overview(
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.SUBSCRIPTION_READ))],
    billing_service: Annotated[BillingService, Depends(get_billing_service)],
) -> BillingOverviewResponse:
    """Get aggregated billing status for current tenant organization."""
    org_id = tenant_context.organization_id
    if not org_id:
        return BillingOverviewResponse()

    customer = await billing_service.get_customer(org_id)
    sub = await billing_service.get_active_billing_subscription(org_id)
    invoices = await billing_service.list_invoices(org_id)

    customer_resp = (
        BillingCustomerResponse(
            id=customer.id,
            organization_id=customer.organization_id,
            provider_customer_id=customer.provider_customer_id,
            email=customer.email,
            name=customer.name,
        )
        if customer
        else None
    )

    sub_resp = (
        BillingSubscriptionResponse(
            id=sub.id,
            organization_id=sub.organization_id,
            provider_subscription_id=sub.provider_subscription_id,
            plan_code=sub.plan_code,
            status=sub.status,
            current_period_start=sub.current_period_start.isoformat(),
            current_period_end=sub.current_period_end.isoformat() if sub.current_period_end else None,
            cancel_at_period_end=sub.cancel_at_period_end,
        )
        if sub
        else None
    )

    invoice_resps = [
        BillingInvoiceResponse(
            id=inv.id,
            provider_invoice_id=inv.provider_invoice_id,
            amount_due=float(inv.amount_due),
            amount_paid=float(inv.amount_paid),
            currency=inv.currency,
            status=inv.status,
            hosted_invoice_url=inv.hosted_invoice_url,
            invoice_pdf=inv.invoice_pdf,
            created_at=inv.created_at.isoformat(),
        )
        for inv in invoices
    ]

    return BillingOverviewResponse(
        customer=customer_resp,
        subscription=sub_resp,
        recent_invoices=invoice_resps,
    )


@router.get(
    "/invoices",
    response_model=list[BillingInvoiceResponse],
    status_code=status.HTTP_200_OK,
    summary="List Billing Invoices",
    description="Returns invoice history for current tenant organization.",
)
async def list_billing_invoices(
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.SUBSCRIPTION_READ))],
    billing_service: Annotated[BillingService, Depends(get_billing_service)],
) -> list[BillingInvoiceResponse]:
    """List invoices for current tenant organization."""
    org_id = tenant_context.organization_id
    if not org_id:
        return []

    invoices = await billing_service.list_invoices(org_id)
    return [
        BillingInvoiceResponse(
            id=inv.id,
            provider_invoice_id=inv.provider_invoice_id,
            amount_due=float(inv.amount_due),
            amount_paid=float(inv.amount_paid),
            currency=inv.currency,
            status=inv.status,
            hosted_invoice_url=inv.hosted_invoice_url,
            invoice_pdf=inv.invoice_pdf,
            created_at=inv.created_at.isoformat(),
        )
        for inv in invoices
    ]


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Create Stripe Checkout Session",
    description="Initiates a hosted Stripe checkout session for plan upgrade. Requires SUBSCRIPTION_MANAGE.",
    dependencies=[Depends(rate_limit(RateLimitPolicies.BILLING_CHECKOUT))],
)
async def create_checkout(
    req: CreateCheckoutRequest,
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.SUBSCRIPTION_MANAGE))],
    billing_service: Annotated[BillingService, Depends(get_billing_service)],
) -> CheckoutResponse:
    """Create a server-validated Stripe Hosted Checkout Session."""
    org_id = tenant_context.organization_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header 'X-Organization-ID' is required to initiate checkout.",
        )

    try:
        plan_code = PlanCode.from_str(req.plan_code)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if plan_code == PlanCode.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Free Sandbox tier does not require checkout.",
        )

    success_url = req.success_url or "https://orion-dashboard-6d3z.onrender.com/billing?session_id={CHECKOUT_SESSION_ID}&status=success"
    cancel_url = req.cancel_url or "https://orion-dashboard-6d3z.onrender.com/billing?status=cancelled"

    try:
        session = await billing_service.create_checkout_session(
            organization_id=org_id,
            user_id=str(user["id"]),
            user_email=str(user.get("email", "trader@orion.internal")),
            plan_code=plan_code,
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return CheckoutResponse(
            session_id=session.session_id,
            url=session.url,
            plan_code=plan_code.value,
            customer_id=session.customer_id,
        )
    except Exception as exc:
        logger.exception("Checkout session creation failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to initiate checkout session: {exc}",
        ) from exc


@router.post(
    "/subscription/cancel",
    response_model=BillingSubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Subscription",
    description="Cancels active commercial subscription at period end or immediately. Requires SUBSCRIPTION_MANAGE.",
)
async def cancel_subscription(
    req: CancelSubscriptionRequest,
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.SUBSCRIPTION_MANAGE))],
    billing_service: Annotated[BillingService, Depends(get_billing_service)],
) -> BillingSubscriptionResponse:
    """Cancel subscription for tenant organization."""
    org_id = tenant_context.organization_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header 'X-Organization-ID' is required to cancel subscriptions.",
        )

    try:
        sub = await billing_service.cancel_subscription(
            organization_id=org_id,
            user_id=str(user["id"]),
            at_period_end=req.at_period_end,
        )
        return BillingSubscriptionResponse(
            id=sub.id,
            organization_id=sub.organization_id,
            provider_subscription_id=sub.provider_subscription_id,
            plan_code=sub.plan_code,
            status=sub.status,
            current_period_start=sub.current_period_start.isoformat(),
            current_period_end=sub.current_period_end.isoformat() if sub.current_period_end else None,
            cancel_at_period_end=sub.cancel_at_period_end,
        )
    except SubscriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Subscription cancellation failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Subscription cancellation failed: {exc}",
        ) from exc
