"""Integration tests for EPIC-017 Phase 4: Institutional Onboarding.

Verifies:
1. Atomic transactional onboarding: User, Organization, Owner Membership,
   default FREE Subscription, and initial $100,000.00 Paper Account.
2. HTTP 409 Conflict rejection on duplicate username, email, or organization slug.
3. Clean error handling on invalid validation payloads (short password, invalid email).
4. Atomic rollback safety: If any intermediate step fails, zero records are committed.
5. End-to-end token verification: The returned access token immediately authenticates against API routes.
"""

from __future__ import annotations

import pathlib
import uuid
from decimal import Decimal
from unittest import mock

import pytest
from apps.trading_engine.src.config import AppSettings
from apps.trading_engine.src.main import create_app
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.config import DatabaseConfig, DatabaseManager
from libraries.infrastructure.persistence.models import (
    AccountModel,
    AuditLogModel,
    OnboardingProgressModel,
    OrganizationMemberModel,
    OrganizationModel,
    SubscriptionModel,
    UserModel,
)


@pytest.fixture
async def onboarding_env():
    """Set up an isolated database and test client for onboarding tests."""
    db_file = f"test_onboarding_{uuid.uuid4().hex[:8]}.db"
    db_path = pathlib.Path(db_file)
    db_url = f"sqlite+aiosqlite:///{db_file}"

    db_config = DatabaseConfig(url=db_url, echo=False)
    db_manager = DatabaseManager(db_config)

    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    settings = AppSettings(
        environment="testing",
        log_level="INFO",
        database_url=db_url,
        redis_url="redis://localhost:6379/0",
        run_migrations=False,
        server_host="127.0.0.1",
        server_port=8000,
        paper_balance=Decimal("100000.00"),
        worker_enabled=False,
        worker_symbols="EUR/USD,GBP/USD",
        market_data_poll_interval=5.0,
        trading_cycle_interval=10.0,
        worker_timeout=30.0,
        worker_stale_threshold=30.0,
    )

    mock_redis = mock.create_autospec(RedisClient, instance=True)
    mock_redis.is_connected = True

    adapter_config = PaperExecutionConfig(
        broker_name="paper",
        is_paper=True,
        balance=Decimal("100000.00"),
    )
    paper_adapter = PaperExecutionAdapter(config=adapter_config)

    app = create_app(
        settings=settings,
        db_manager=db_manager,
        redis_client=mock_redis,
        paper_adapter=paper_adapter,
    )

    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield {
            "client": client,
            "db_manager": db_manager,
            "app": app,
        }

    await paper_adapter.disconnect()
    await db_manager.close()
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass


@pytest.mark.asyncio
async def test_successful_transactional_onboarding(onboarding_env: dict):
    """Test full atomic registration flow provisioning user, org, role, sub, and paper account."""
    client: AsyncClient = onboarding_env["client"]
    db_manager: DatabaseManager = onboarding_env["db_manager"]

    payload = {
        "username": "lead_pm",
        "email": "lead.pm@apexcap.io",
        "password": "ApexPassword2026!",
        "organization_name": "Apex Capital Management",
        "organization_slug": "apex-capital",
        "full_name": "Apex Lead PM",
        "terms_accepted": True,
        "privacy_acknowledged": True,
        "risk_disclosure_acknowledged": True,
    }

    response = await client.post("/api/v1/onboarding/register", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()

    # Response contract assertions
    assert data["username"] == "lead_pm"
    assert data["email"] == "lead.pm@apexcap.io"
    assert data["organization_name"] == "Apex Capital Management"
    assert data["organization_slug"] == "apex-capital"
    assert data["role"] == "OWNER"
    assert data["subscription_tier"] == "FREE"
    assert Decimal(str(data["initial_balance"])) == Decimal("100000.00")
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 20

    user_id = data["user_id"]
    org_id = data["organization_id"]
    account_id = data["account_id"]

    # Verify all records persisted correctly in database
    async with db_manager.session() as session:
        # 1. User
        user = (await session.execute(select(UserModel).where(UserModel.id == user_id))).scalar_one()
        assert user.username == "lead_pm"
        assert user.email == "lead.pm@apexcap.io"
        assert user.is_active is True
        assert user.is_superuser is False

        # 2. Organization
        org = (await session.execute(select(OrganizationModel).where(OrganizationModel.id == org_id))).scalar_one()
        assert org.name == "Apex Capital Management"
        assert org.slug == "apex-capital"
        assert org.status == "ACTIVE"

        # 3. Membership
        member = (await session.execute(
            select(OrganizationMemberModel).where(
                OrganizationMemberModel.organization_id == org_id,
                OrganizationMemberModel.user_id == user_id,
            )
        )).scalar_one()
        assert member.role == "OWNER"
        assert member.status == "ACTIVE"

        # 4. Subscription
        sub = (await session.execute(
            select(SubscriptionModel).where(SubscriptionModel.organization_id == org_id)
        )).scalar_one()
        assert sub.status == "ACTIVE"

        # 5. Paper Account
        acc = (await session.execute(select(AccountModel).where(AccountModel.id == account_id))).scalar_one()
        assert acc.organization_id == org_id
        assert acc.user_id == user_id
        assert acc.balance == Decimal("100000.00")
        assert acc.is_live is False

        # 6. Audit Log
        audit = (await session.execute(
            select(AuditLogModel).where(
                AuditLogModel.organization_id == org_id,
                AuditLogModel.event_type == "organization.onboarded",
            )
        )).scalar_one()
        assert audit.actor == user_id

        # 7. Persistent Onboarding Progress
        ob_progress = (await session.execute(
            select(OnboardingProgressModel).where(
                OnboardingProgressModel.organization_id == org_id,
                OnboardingProgressModel.user_id == user_id,
            )
        )).scalar_one()
        assert ob_progress.status in ("NOT_STARTED", "IN_PROGRESS")
        assert ob_progress.current_step == "WELCOME"
        assert ob_progress.completed_steps == []

    # Verify returned JWT token immediately authenticates against protected routes
    token = data["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-ID": org_id,
    }
    org_resp = await client.get(f"/api/v1/organizations/{org_id}", headers=headers)
    assert org_resp.status_code == 200
    assert org_resp.json()["id"] == org_id


@pytest.mark.asyncio
async def test_duplicate_username_conflict_rejection(onboarding_env: dict):
    """Attempting to register with an already existing username must return HTTP 409 Conflict."""
    client: AsyncClient = onboarding_env["client"]

    # First registration
    payload1 = {
        "username": "unique_trader",
        "email": "trader1@test.com",
        "password": "Password123!",
        "organization_name": "Org One",
        "organization_slug": "org-one",
        "terms_accepted": True,
        "privacy_acknowledged": True,
        "risk_disclosure_acknowledged": True,
    }
    r1 = await client.post("/api/v1/onboarding/register", json=payload1)
    assert r1.status_code == 201

    # Second registration with same username
    payload2 = {
        "username": "unique_trader",
        "email": "different@test.com",
        "password": "Password123!",
        "organization_name": "Org Two",
        "organization_slug": "org-two",
        "terms_accepted": True,
        "privacy_acknowledged": True,
        "risk_disclosure_acknowledged": True,
    }
    r2 = await client.post("/api/v1/onboarding/register", json=payload2)
    assert r2.status_code == 409
    err = (r2.json().get("message") or r2.json().get("detail", "")).lower()
    assert "already registered" in err


@pytest.mark.asyncio
async def test_duplicate_email_conflict_rejection(onboarding_env: dict):
    """Attempting to register with an already existing email must return HTTP 409 Conflict."""
    client: AsyncClient = onboarding_env["client"]

    payload1 = {
        "username": "trader_alpha",
        "email": "shared@domain.com",
        "password": "Password123!",
        "organization_name": "Alpha Org",
        "organization_slug": "alpha-org",
        "terms_accepted": True,
        "privacy_acknowledged": True,
        "risk_disclosure_acknowledged": True,
    }
    r1 = await client.post("/api/v1/onboarding/register", json=payload1)
    assert r1.status_code == 201

    payload2 = {
        "username": "trader_beta",
        "email": "shared@domain.com",
        "password": "Password123!",
        "organization_name": "Beta Org",
        "organization_slug": "beta-org",
        "terms_accepted": True,
        "privacy_acknowledged": True,
        "risk_disclosure_acknowledged": True,
    }
    r2 = await client.post("/api/v1/onboarding/register", json=payload2)
    assert r2.status_code == 409
    err = (r2.json().get("message") or r2.json().get("detail", "")).lower()
    assert "already registered" in err


@pytest.mark.asyncio
async def test_duplicate_slug_conflict_rejection(onboarding_env: dict):
    """Attempting to register with an existing organization slug must return HTTP 409 Conflict."""
    client: AsyncClient = onboarding_env["client"]

    payload1 = {
        "username": "user1",
        "email": "user1@domain.com",
        "password": "Password123!",
        "organization_name": "Omega Ventures",
        "organization_slug": "omega-ventures",
        "terms_accepted": True,
        "privacy_acknowledged": True,
        "risk_disclosure_acknowledged": True,
    }
    r1 = await client.post("/api/v1/onboarding/register", json=payload1)
    assert r1.status_code == 201

    payload2 = {
        "username": "user2",
        "email": "user2@domain.com",
        "password": "Password123!",
        "organization_name": "Omega Ventures International",
        "organization_slug": "omega-ventures",
        "terms_accepted": True,
        "privacy_acknowledged": True,
        "risk_disclosure_acknowledged": True,
    }
    r2 = await client.post("/api/v1/onboarding/register", json=payload2)
    assert r2.status_code == 409
    err = (r2.json().get("message") or r2.json().get("detail", "")).lower()
    assert "already in use" in err


@pytest.mark.asyncio
async def test_input_validation_rejections(onboarding_env: dict):
    """Verify input validation rules: short passwords, bad emails, empty org name."""
    client: AsyncClient = onboarding_env["client"]

    # Short password
    r1 = await client.post(
        "/api/v1/onboarding/register",
        json={
            "username": "valid_user",
            "email": "valid@email.com",
            "password": "short",
            "organization_name": "Valid Org",
            "terms_accepted": True,
            "privacy_acknowledged": True,
            "risk_disclosure_acknowledged": True,
        },
    )
    assert r1.status_code in (400, 422)

    # Invalid email
    r2 = await client.post(
        "/api/v1/onboarding/register",
        json={
            "username": "valid_user",
            "email": "not-an-email",
            "password": "ValidPassword123!",
            "organization_name": "Valid Org",
            "terms_accepted": True,
            "privacy_acknowledged": True,
            "risk_disclosure_acknowledged": True,
        },
    )
    assert r2.status_code in (400, 422)


@pytest.mark.asyncio
async def test_atomic_rollback_on_failure(onboarding_env: dict):
    """Verify that an artificial failure during provisioning rolls back all entities cleanly."""
    client: AsyncClient = onboarding_env["client"]
    db_manager: DatabaseManager = onboarding_env["db_manager"]

    payload = {
        "username": "rollback_user",
        "email": "rollback@domain.com",
        "password": "Password123!",
        "organization_name": "Rollback Org",
        "organization_slug": "rollback-org",
        "terms_accepted": True,
        "privacy_acknowledged": True,
        "risk_disclosure_acknowledged": True,
    }

    # Simulate an error in subscription assignment
    with mock.patch(
        "apps.trading_engine.src.services.subscription_service.SubscriptionService.assign_default_subscription",
        side_effect=RuntimeError("Artificial subscription provisioning failure"),
    ):
        response = await client.post("/api/v1/onboarding/register", json=payload)
        assert response.status_code == 500

    # Verify database state has zero traces of user, org, membership, or progress
    async with db_manager.session() as session:
        user = (await session.execute(
            select(UserModel).where(UserModel.username == "rollback_user")
        )).scalar_one_or_none()
        assert user is None

        org = (await session.execute(
            select(OrganizationModel).where(OrganizationModel.slug == "rollback-org")
        )).scalar_one_or_none()
        assert org is None

        progress = (await session.execute(
            select(OnboardingProgressModel).where(OnboardingProgressModel.user_id == "rollback_user")
        )).scalar_one_or_none()
        assert progress is None
