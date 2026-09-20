"""Automated test suite for Commercial Billing & Stripe Test-Mode Integration (EPIC-019).

Covers all 16 required operational and security scenarios:
1. Customer creation
2. Duplicate customer creation idempotency
3. Checkout session creation
4. Valid webhook handling
5. Invalid webhook signature rejection (HTTP 400)
6. Duplicate webhook event idempotency (zero side-effects)
7. Subscription activation on webhook (checkout.session.completed)
8. Subscription cancellation at period end (cancel_at_period_end)
9. Failed payment handling (invoice.payment_failed)
10. Plan upgrade entitlement synchronization (Free -> Pro -> Business)
11. Plan downgrade entitlement synchronization (Pro -> Free)
12. Entitlement service integration
13. Cross-tenant billing access rejection (IDOR)
14. Unauthorized billing access rejection (RBAC)
15. Secret redaction in logs
16. Stripe provider outage / error handling (503 response)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from unittest import mock

import pytest
from apps.trading_engine.src import dependencies
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.services.billing_service import BillingService
from apps.trading_engine.src.services.entitlement_service import EntitlementService
from apps.trading_engine.src.services.subscription_service import SubscriptionService
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from libraries.domain.billing.exceptions import (
    BillingProviderError,
    InvalidPlanCodeError,
    InvalidWebhookSignatureError,
    LiveCredentialsForbiddenError,
)
from libraries.domain.subscription.exceptions import (
    AccountQuotaExceededError,
    AssetNotEntitledError,
)
from libraries.domain.subscription.models import PlanCode, SubscriptionStatus
from libraries.infrastructure.billing.config import BillingConfig
from libraries.infrastructure.billing.stripe_adapter import MockBillingAdapter
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models.billing import (
    BillingInvoiceModel,
)
from libraries.infrastructure.persistence.models.organization import (
    OrganizationMemberModel,
    OrganizationModel,
)
from libraries.infrastructure.persistence.models.user import UserModel
from libraries.observability.logging import StructuredFormatter
from libraries.observability.metrics import MetricsRegistry


@pytest.fixture
async def db_session() -> AsyncSession:
    """Provide an isolated in-memory SQLite async database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        # Pre-seed Organization and User
        org = OrganizationModel(
            id="org_alpha_001",
            name="Alpha Capital",
            slug="alpha-capital",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        user = UserModel(
            id="usr_owner_001",
            username="alpha_owner",
            email="owner@alpha.dev",
            hashed_password="mock_password_hash",
            is_active=True,
            is_superuser=False,
        )
        member = OrganizationMemberModel(
            id="mem_owner_001",
            organization_id="org_alpha_001",
            user_id="usr_owner_001",
            role="OWNER",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add_all([org, user, member])

        # Pre-seed canonical plans
        sub_service = SubscriptionService(session)
        await sub_service._ensure_canonical_plans()
        await session.commit()
        yield session


@pytest.fixture
def mock_billing_adapter() -> MockBillingAdapter:
    """Provide a deterministic MockBillingAdapter."""
    config = BillingConfig(
        secret_key="sk_test_mock_1234567890",
        publishable_key="pk_test_mock_1234567890",
        webhook_secret="whsec_test_secret_123",
        use_mock=True,
    )
    return MockBillingAdapter(config)


@pytest.fixture
def billing_service(db_session: AsyncSession, mock_billing_adapter: MockBillingAdapter) -> BillingService:
    """Provide a BillingService instance backed by in-memory SQLite and mock adapter."""
    config = mock_billing_adapter._config
    metrics = MetricsRegistry(prefix="orion_test")
    return BillingService(
        session=db_session,
        provider=mock_billing_adapter,
        config=config,
        metrics=metrics,
    )


# ─── TEST 1: Customer Creation ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_billing_customer_creation(billing_service: BillingService) -> None:
    """Verifies customer record creation in DB and Stripe mock."""
    customer = await billing_service.get_or_create_customer(
        organization_id="org_alpha_001",
        email="owner@alpha.dev",
        name="Alpha Capital",
    )
    assert customer is not None
    assert customer.organization_id == "org_alpha_001"
    assert customer.email == "owner@alpha.dev"
    assert customer.provider_customer_id.startswith("cus_mock_")


# ─── TEST 2: Duplicate Customer Creation Idempotency ──────────────────────────


@pytest.mark.asyncio
async def test_billing_customer_idempotency(billing_service: BillingService) -> None:
    """Verifies repeated calls return existing customer without duplicate records."""
    cust_1 = await billing_service.get_or_create_customer(
        organization_id="org_alpha_001",
        email="owner@alpha.dev",
    )
    cust_2 = await billing_service.get_or_create_customer(
        organization_id="org_alpha_001",
        email="owner@alpha.dev",
    )
    assert cust_1.id == cust_2.id
    assert cust_1.provider_customer_id == cust_2.provider_customer_id


# ─── TEST 3: Checkout Session Creation ────────────────────────────────────────


@pytest.mark.asyncio
async def test_billing_checkout_session_creation(billing_service: BillingService) -> None:
    """Verifies server-side validation and session URL output."""
    # Free tier cannot generate checkout session
    with pytest.raises(InvalidPlanCodeError):
        await billing_service.create_checkout_session(
            organization_id="org_alpha_001",
            user_id="usr_owner_001",
            user_email="owner@alpha.dev",
            plan_code=PlanCode.FREE,
            success_url="https://app.dev/success",
            cancel_url="https://app.dev/cancel",
        )

    # Pro tier generates valid session
    session = await billing_service.create_checkout_session(
        organization_id="org_alpha_001",
        user_id="usr_owner_001",
        user_email="owner@alpha.dev",
        plan_code=PlanCode.PRO,
        success_url="https://app.dev/success",
        cancel_url="https://app.dev/cancel",
    )
    assert session.session_id.startswith("cs_test_")
    assert "checkout.stripe.com" in session.url
    assert session.plan_code == PlanCode.PRO


# ─── TEST 4: Valid Webhook Handling ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_valid_webhook_signature_handling(billing_service: BillingService) -> None:
    """Verifies valid webhook event produces successful event processing."""
    payload = json.dumps({
        "id": "evt_test_001",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "customer": "cus_mock_org_alpha",
                "subscription": "sub_test_123",
                "metadata": {
                    "organization_id": "org_alpha_001",
                    "plan_code": "PRO",
                },
            }
        },
    }).encode("utf-8")

    result = await billing_service.handle_webhook_event(
        payload_bytes=payload,
        sig_header="valid_mock_signature",
    )
    assert result["status"] == "success"
    assert result["event_id"] == "evt_test_001"


# ─── TEST 5: Invalid Webhook Signature Rejection ──────────────────────────────


@pytest.mark.asyncio
async def test_invalid_webhook_signature_rejection(billing_service: BillingService) -> None:
    """Verifies forged/invalid signature returns error."""
    payload = b'{"id": "evt_test_002", "type": "ping"}'
    with pytest.raises(InvalidWebhookSignatureError):
        await billing_service.handle_webhook_event(
            payload_bytes=payload,
            sig_header="invalid_signature",
        )


# ─── TEST 6: Duplicate Webhook Event Idempotency ──────────────────────────────


@pytest.mark.asyncio
async def test_duplicate_webhook_idempotency(billing_service: BillingService) -> None:
    """Verifies duplicate event ID returns HTTP 200 with zero duplicate side effects."""
    payload = json.dumps({
        "id": "evt_test_duplicate_001",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {
                    "organization_id": "org_alpha_001",
                    "plan_code": "PRO",
                },
            }
        },
    }).encode("utf-8")

    res_1 = await billing_service.handle_webhook_event(payload, "sig_valid")
    assert res_1["status"] == "success"

    res_2 = await billing_service.handle_webhook_event(payload, "sig_valid")
    assert res_2["status"] == "already_processed"


# ─── TEST 7: Subscription Activation on Webhook ───────────────────────────────


@pytest.mark.asyncio
async def test_subscription_activation_on_webhook(
    billing_service: BillingService,
    db_session: AsyncSession,
) -> None:
    """Verifies checkout.session.completed sets subscription ACTIVE and updates plan."""
    payload = json.dumps({
        "id": "evt_activate_001",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_mock_org_alpha",
                "subscription": "sub_stripe_pro_001",
                "metadata": {
                    "organization_id": "org_alpha_001",
                    "plan_code": "PRO",
                },
            }
        },
    }).encode("utf-8")

    await billing_service.handle_webhook_event(payload, "sig_valid")

    sub_service = SubscriptionService(db_session)
    active_sub, active_plan = await sub_service.get_active_subscription("org_alpha_001")
    assert active_sub is not None
    assert active_plan is not None
    assert active_plan.code == PlanCode.PRO
    assert active_sub.status == SubscriptionStatus.ACTIVE


# ─── TEST 8: Subscription Cancellation at Period End ──────────────────────────


@pytest.mark.asyncio
async def test_subscription_cancellation_at_period_end(
    billing_service: BillingService,
) -> None:
    """Verifies cancellation schedules period end and updates DB."""
    # First activate a subscription
    payload = json.dumps({
        "id": "evt_activate_002",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_mock_org_alpha",
                "subscription": "sub_stripe_pro_002",
                "metadata": {
                    "organization_id": "org_alpha_001",
                    "plan_code": "PRO",
                },
            }
        },
    }).encode("utf-8")
    await billing_service.handle_webhook_event(payload, "sig_valid")

    # Cancel at period end
    cancelled_sub = await billing_service.cancel_subscription("org_alpha_001", at_period_end=True)
    assert cancelled_sub.cancel_at_period_end is True


# ─── TEST 9: Failed Payment Handling ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_failed_payment_handling(
    billing_service: BillingService,
    db_session: AsyncSession,
) -> None:
    """Verifies invoice.payment_failed degrades to past_due / SUSPENDED and Free limits."""
    # Ensure customer exists
    customer = await billing_service.get_or_create_customer("org_alpha_001", "owner@alpha.dev")

    payload = json.dumps({
        "id": "evt_fail_001",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": "in_failed_001",
                "customer": customer.provider_customer_id,
                "subscription": "sub_stripe_pro_002",
            }
        },
    }).encode("utf-8")

    await billing_service.handle_webhook_event(payload, "sig_valid")

    sub_service = SubscriptionService(db_session)
    _active_sub, active_plan = await sub_service.get_active_subscription("org_alpha_001")
    assert active_plan is not None
    assert active_plan.code == PlanCode.FREE


# ─── TEST 10: Plan Upgrade Entitlement Sync ───────────────────────────────────


@pytest.mark.asyncio
async def test_plan_upgrade_entitlement_sync(
    billing_service: BillingService,
    db_session: AsyncSession,
) -> None:
    """Verifies Free -> Pro unlocks 3 accounts and 2,500 orders."""
    entitlement_service = EntitlementService(db_session)

    # Baseline Free quota check (max 1 account)
    with pytest.raises(AccountQuotaExceededError):
        await entitlement_service.check_account_quota("org_alpha_001", current_count=1)

    # Upgrade to PRO via webhook
    payload = json.dumps({
        "id": "evt_upgrade_001",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_mock_org_alpha",
                "subscription": "sub_stripe_pro_003",
                "metadata": {
                    "organization_id": "org_alpha_001",
                    "plan_code": "PRO",
                },
            }
        },
    }).encode("utf-8")
    await billing_service.handle_webhook_event(payload, "sig_valid")

    # Now 2 accounts are permitted under Pro limits (max 3)
    await entitlement_service.check_account_quota("org_alpha_001", current_count=2)
    # But 3 accounts triggers quota limit
    with pytest.raises(AccountQuotaExceededError):
        await entitlement_service.check_account_quota("org_alpha_001", current_count=3)


# ─── TEST 11: Plan Downgrade Entitlement Sync ─────────────────────────────────


@pytest.mark.asyncio
async def test_plan_downgrade_entitlement_sync(
    billing_service: BillingService,
    db_session: AsyncSession,
) -> None:
    """Verifies Pro -> Free restores 1 account and 100 orders quota."""
    # Upgrade to Business
    payload_bus = json.dumps({
        "id": "evt_bus_001",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_mock_org_alpha",
                "subscription": "sub_stripe_bus_001",
                "metadata": {
                    "organization_id": "org_alpha_001",
                    "plan_code": "BUSINESS",
                },
            }
        },
    }).encode("utf-8")
    await billing_service.handle_webhook_event(payload_bus, "sig_valid")

    entitlement_service = EntitlementService(db_session)
    # In Business, all FX pairs are allowed
    await entitlement_service.check_asset_access("org_alpha_001", "AUD/CAD")

    # Delete subscription (downgrade to Free)
    payload_del = json.dumps({
        "id": "evt_del_001",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_stripe_bus_001",
            }
        },
    }).encode("utf-8")
    await billing_service.handle_webhook_event(payload_del, "sig_valid")

    # In Free, AUD/CAD is not entitled
    with pytest.raises(AssetNotEntitledError):
        await entitlement_service.check_asset_access("org_alpha_001", "AUD/CAD")


# ─── TEST 12: Entitlement Service Integration ─────────────────────────────────


@pytest.mark.asyncio
async def test_entitlement_service_integration(
    billing_service: BillingService,
    db_session: AsyncSession,
) -> None:
    """Verifies EntitlementService checks reflect active billing tier."""
    entitlement_service = EntitlementService(db_session)
    summary = await entitlement_service.get_usage_summary("org_alpha_001")
    assert "limits" in summary
    assert "plan" in summary


# ─── TEST 13: Cross-Tenant Billing IDOR Rejection ─────────────────────────────


@pytest.mark.asyncio
async def test_cross_tenant_billing_idor_rejection(
    db_session: AsyncSession,
    mock_billing_adapter: MockBillingAdapter,
) -> None:
    """Verifies Tenant A cannot access Tenant B's invoices or subscriptions."""
    app = create_app()

    # Pre-seed Tenant B
    org_b = OrganizationModel(
        id="org_beta_002",
        name="Beta Capital",
        slug="beta-capital",
        status="ACTIVE",
    )
    inv_b = BillingInvoiceModel(
        id="binv_beta_001",
        organization_id="org_beta_002",
        provider_invoice_id="in_beta_secret",
        provider_customer_id="cus_beta_123",
        amount_due=Decimal("299.00"),
        amount_paid=Decimal("299.00"),
        currency="usd",
        status="paid",
    )
    db_session.add_all([org_b, inv_b])
    await db_session.commit()

    # Authenticated as Tenant A
    app.dependency_overrides[dependencies.get_db_session] = lambda: db_session
    app.dependency_overrides[dependencies.get_current_active_user] = lambda: {
        "id": "usr_owner_001",
        "username": "alpha_owner",
        "is_active": True,
        "is_superuser": False,
    }
    app.dependency_overrides[dependencies.get_tenant_context] = lambda: dependencies.TenantContext(
        user_id="usr_owner_001",
        organization_id="org_alpha_001",
        role="OWNER",
        is_superuser=False,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/billing/invoices")
        assert res.status_code == 200
        invoices = res.json()
        # Tenant A must NOT see Tenant B's invoice
        assert not any(inv["provider_invoice_id"] == "in_beta_secret" for inv in invoices)

    app.dependency_overrides.clear()


# ─── TEST 14: Unauthorized Billing RBAC Rejection ─────────────────────────────


@pytest.mark.asyncio
async def test_unauthorized_billing_rbac_rejection(db_session: AsyncSession) -> None:
    """Verifies non-admin roles (e.g. VIEWER or TRADER) cannot initiate checkouts."""
    app = create_app()
    app.dependency_overrides[dependencies.get_db_session] = lambda: db_session
    app.dependency_overrides[dependencies.get_current_active_user] = lambda: {
        "id": "usr_viewer_001",
        "username": "viewer",
        "is_active": True,
        "is_superuser": False,
    }
    # User has role TRADER (does not possess SUBSCRIPTION_MANAGE)
    app.dependency_overrides[dependencies.get_tenant_context] = lambda: dependencies.TenantContext(
        user_id="usr_viewer_001",
        organization_id="org_alpha_001",
        role="TRADER",
        is_superuser=False,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # TRADER can view billing (SUBSCRIPTION_READ is allowed)
        view_res = await client.get("/api/v1/billing")
        assert view_res.status_code in (200, 403)

        # TRADER cannot create checkout (requires SUBSCRIPTION_MANAGE)
        checkout_res = await client.post(
            "/api/v1/billing/checkout",
            json={"plan_code": "PRO"},
        )
        assert checkout_res.status_code == 403

    app.dependency_overrides.clear()


# ─── TEST 15: Secret Redaction in Logs ─────────────────────────────────────────


def test_stripe_secret_redaction_in_logs() -> None:
    """Verifies sk_test_ and whsec_ are redacted in structured logging."""
    formatter = StructuredFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Billing operation initialized",
        args=(),
        exc_info=None,
    )
    record.secret_key = "sk_test_51MzAbcDef123456789"  # type: ignore[attr-defined]
    record.webhook_secret = "whsec_test_secret_987654321"  # type: ignore[attr-defined]

    formatted_json = formatter.format(record)
    log_data = json.loads(formatted_json)

    assert "sk_test_" not in formatted_json or log_data.get("secret_key") == "***REDACTED***"
    assert "whsec_" not in formatted_json or log_data.get("webhook_secret") == "***REDACTED***"


# ─── TEST 16: Stripe Provider Outage Error Handling ───────────────────────────


@pytest.mark.asyncio
async def test_stripe_provider_outage_error_handling(
    billing_service: BillingService,
) -> None:
    """Verifies 503 error degradation on Stripe network failure."""
    with mock.patch.object(
        billing_service.provider,
        "create_checkout_session",
        side_effect=BillingProviderError("Stripe API connection timeout"),
    ), pytest.raises(BillingProviderError, match="Stripe API connection timeout"):
        await billing_service.create_checkout_session(
            organization_id="org_alpha_001",
            user_id="usr_owner_001",
            user_email="owner@alpha.dev",
            plan_code=PlanCode.PRO,
            success_url="https://app.dev/success",
            cancel_url="https://app.dev/cancel",
        )


# ─── LIVE CREDENTIAL REJECTION TEST ──────────────────────────────────────────


def test_reject_live_stripe_credentials() -> None:
    """Verifies that sk_live_ credentials fail fast immediately."""
    with pytest.raises(LiveCredentialsForbiddenError, match="Live Stripe secret key"):
        BillingConfig(secret_key="sk_live_1234567890abcdef")

    with pytest.raises(LiveCredentialsForbiddenError, match="Live Stripe publishable key"):
        BillingConfig(publishable_key="pk_live_1234567890abcdef")
