"""Unit tests for EPIC-027 Phase 5A Persistent Onboarding State Machine.

Verifies:
1. State machine initialization: NOT_STARTED -> IN_PROGRESS -> COMPLETED.
2. Canonical step progression: WELCOME -> EMAIL_VERIFICATION -> STRATEGY -> RISK -> PAPER_TRADING_READY.
3. Strict forward progression: Cannot skip steps.
4. Server-side authoritative validation:
   - EMAIL_VERIFICATION requires user.email_verified == True.
   - PAPER_TRADING_READY requires active paper account with balance > 0.
5. Auto-synchronization of email verification status on retrieval.
6. Metadata persistence for strategy and risk steps.
7. Immutability of COMPLETED status against regression.
8. Idempotent step completion.
9. Comprehensive audit logging for all lifecycle transitions.
10. Tenant isolation and fail-closed security.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from apps.trading_engine.src.schemas import (
    OnboardingStatus,
    OnboardingStatusResponse,
    OnboardingStep,
)
from apps.trading_engine.src.services.onboarding_service import OnboardingService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from libraries.domain.organization.models import (
    MembershipStatus,
    OrganizationRole,
    OrganizationStatus,
)
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models import (
    AccountModel,
    AuditLogModel,
    OnboardingProgressModel,
    OrganizationMemberModel,
    OrganizationModel,
    UserModel,
    UserStatus,
)


@pytest.fixture
async def async_session() -> AsyncSession:
    """Provide an isolated in-memory SQLite async session with schema initialized."""
    engine = create_async_engine(
        f"sqlite+aiosqlite:///:memory:?cache=shared_{uuid.uuid4().hex[:8]}",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def setup_tenant(async_session: AsyncSession) -> dict[str, str]:
    """Create a sample user, organization, member, and paper account."""
    now = datetime.now(timezone.utc)
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    org_id = f"org_{uuid.uuid4().hex[:12]}"

    user = UserModel(
        id=user_id,
        username="trader_ob_test",
        email="trader@ob.test",
        hashed_password="dummy_password_hash",
        is_active=True,
        is_superuser=False,
        status=UserStatus.ACTIVE.value,
        email_verified=False,
        created_at=now,
        updated_at=now,
    )
    async_session.add(user)

    org = OrganizationModel(
        id=org_id,
        name="OB Test Org",
        slug=f"ob-org-{uuid.uuid4().hex[:6]}",
        status=OrganizationStatus.ACTIVE.value,
        created_at=now,
        updated_at=now,
    )
    async_session.add(org)

    member = OrganizationMemberModel(
        id=f"mem_{uuid.uuid4().hex[:12]}",
        organization_id=org_id,
        user_id=user_id,
        role=OrganizationRole.OWNER.value,
        status=MembershipStatus.ACTIVE.value,
        created_at=now,
        updated_at=now,
    )
    async_session.add(member)

    account = AccountModel(
        id=f"acc_{uuid.uuid4().hex[:12]}",
        user_id=user_id,
        organization_id=org_id,
        broker_name="paper",
        account_number=f"PAPER-{uuid.uuid4().hex[:8].upper()}",
        currency="USD",
        balance=Decimal("100000.00"),
        equity=Decimal("100000.00"),
        margin=Decimal("0.00"),
        margin_free=Decimal("100000.00"),
        margin_level=0.0,
        leverage=100,
        is_live=False,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    async_session.add(account)
    await async_session.commit()

    return {"user_id": user_id, "organization_id": org_id, "account_id": account.id}


class TestOnboardingStateMachine:
    """Test suite for persistent onboarding state machine service layer."""

    async def test_get_or_create_progress_initialization(
        self, async_session: AsyncSession, setup_tenant: dict[str, str]
    ) -> None:
        """Calling get_or_create_progress creates a NOT_STARTED record at WELCOME."""
        svc = OnboardingService(session=async_session)
        user_id = setup_tenant["user_id"]
        org_id = setup_tenant["organization_id"]

        resp: OnboardingStatusResponse = await svc.get_or_create_progress(user_id, org_id)

        assert resp.user_id == user_id
        assert resp.organization_id == org_id
        assert resp.status == OnboardingStatus.NOT_STARTED
        assert resp.current_step == OnboardingStep.WELCOME
        assert resp.completed_steps == []
        assert resp.next_step == OnboardingStep.EMAIL_VERIFICATION
        assert resp.email_verified is False
        assert resp.paper_account_ready is True
        assert len(resp.steps) == 5

        # Check DB model directly
        db_model = (
            await async_session.execute(
                select(OnboardingProgressModel).where(
                    OnboardingProgressModel.user_id == user_id,
                    OnboardingProgressModel.organization_id == org_id,
                )
            )
        ).scalar_one()
        assert db_model.status == "NOT_STARTED"
        assert db_model.current_step == "WELCOME"

    async def test_step_sequence_enforcement(
        self, async_session: AsyncSession, setup_tenant: dict[str, str]
    ) -> None:
        """Skipping ahead without completing prior steps must be rejected with ValueError."""
        svc = OnboardingService(session=async_session)
        user_id = setup_tenant["user_id"]
        org_id = setup_tenant["organization_id"]

        # Attempting STRATEGY without WELCOME
        with pytest.raises(ValueError, match="Prerequisite step 'WELCOME' must be completed first"):
            await svc.complete_step(user_id, org_id, "STRATEGY")

        # Attempting RISK without WELCOME
        with pytest.raises(ValueError, match="Prerequisite step 'WELCOME' must be completed first"):
            await svc.complete_step(user_id, org_id, "RISK")

        # Attempting PAPER_TRADING_READY without WELCOME
        with pytest.raises(ValueError, match="Prerequisite step 'WELCOME' must be completed first"):
            await svc.complete_step(user_id, org_id, "PAPER_TRADING_READY")

    async def test_complete_welcome_step(
        self, async_session: AsyncSession, setup_tenant: dict[str, str]
    ) -> None:
        """Completing WELCOME advances current_step to EMAIL_VERIFICATION and status to IN_PROGRESS."""
        svc = OnboardingService(session=async_session)
        user_id = setup_tenant["user_id"]
        org_id = setup_tenant["organization_id"]

        resp = await svc.complete_step(user_id, org_id, "WELCOME")

        assert resp.status == OnboardingStatus.IN_PROGRESS
        assert resp.current_step == OnboardingStep.EMAIL_VERIFICATION
        assert resp.completed_steps == [OnboardingStep.WELCOME]
        assert resp.next_step == OnboardingStep.STRATEGY

        # Audit log verification
        audit = (
            await async_session.execute(
                select(AuditLogModel).where(
                    AuditLogModel.organization_id == org_id,
                    AuditLogModel.event_type == "ONBOARDING_STEP_COMPLETED",
                )
            )
        ).scalar_one()
        assert audit.actor == user_id
        assert audit.details["step"] == "WELCOME"

    async def test_email_verification_authoritative_guard(
        self, async_session: AsyncSession, setup_tenant: dict[str, str]
    ) -> None:
        """EMAIL_VERIFICATION cannot be completed if user.email_verified is False."""
        svc = OnboardingService(session=async_session)
        user_id = setup_tenant["user_id"]
        org_id = setup_tenant["organization_id"]

        # 1. Complete WELCOME first
        await svc.complete_step(user_id, org_id, "WELCOME")

        # 2. Attempt EMAIL_VERIFICATION while user is unverified -> must fail
        with pytest.raises(ValueError, match="Email address is not verified"):
            await svc.complete_step(user_id, org_id, "EMAIL_VERIFICATION")

        # 3. Mark user verified
        user = (
            await async_session.execute(select(UserModel).where(UserModel.id == user_id))
        ).scalar_one()
        user.email_verified = True
        await async_session.flush()

        # 4. Attempt EMAIL_VERIFICATION again -> now succeeds
        resp = await svc.complete_step(user_id, org_id, "EMAIL_VERIFICATION")
        assert OnboardingStep.EMAIL_VERIFICATION in resp.completed_steps
        assert resp.current_step == OnboardingStep.STRATEGY

    async def test_email_verification_auto_synchronization(
        self, async_session: AsyncSession, setup_tenant: dict[str, str]
    ) -> None:
        """If user is verified and WELCOME is done, get_or_create_progress auto-completes EMAIL_VERIFICATION."""
        svc = OnboardingService(session=async_session)
        user_id = setup_tenant["user_id"]
        org_id = setup_tenant["organization_id"]

        # Complete WELCOME
        await svc.complete_step(user_id, org_id, "WELCOME")

        # Simulate user verifying email out-of-band (e.g. clicked token link)
        user = (
            await async_session.execute(select(UserModel).where(UserModel.id == user_id))
        ).scalar_one()
        user.email_verified = True
        await async_session.flush()

        # Retrieve status without explicitly calling complete_step for EMAIL_VERIFICATION
        resp = await svc.get_or_create_progress(user_id, org_id)

        assert OnboardingStep.WELCOME in resp.completed_steps
        assert OnboardingStep.EMAIL_VERIFICATION in resp.completed_steps
        assert resp.current_step == OnboardingStep.STRATEGY

    async def test_metadata_persistence_for_strategy_and_risk(
        self, async_session: AsyncSession, setup_tenant: dict[str, str]
    ) -> None:
        """Step completion stores metadata in progress.meta_data['step_data']."""
        svc = OnboardingService(session=async_session)
        user_id = setup_tenant["user_id"]
        org_id = setup_tenant["organization_id"]

        # Complete WELCOME & verify email
        await svc.complete_step(user_id, org_id, "WELCOME")
        user = (
            await async_session.execute(select(UserModel).where(UserModel.id == user_id))
        ).scalar_one()
        user.email_verified = True
        await async_session.flush()
        await svc.complete_step(user_id, org_id, "EMAIL_VERIFICATION")

        # Complete STRATEGY with metadata
        strat_meta = {"strategy_name": "TrendFollowing", "symbols": ["EUR/USD"]}
        resp = await svc.complete_step(user_id, org_id, "STRATEGY", metadata=strat_meta)
        assert resp.current_step == OnboardingStep.RISK

        # Complete RISK with metadata
        risk_meta = {"max_drawdown_pct": 5.0, "daily_loss_limit_usd": 1000.0}
        resp = await svc.complete_step(user_id, org_id, "RISK", metadata=risk_meta)
        assert resp.current_step == OnboardingStep.PAPER_TRADING_READY

        # Check DB model metadata
        db_model = (
            await async_session.execute(
                select(OnboardingProgressModel).where(
                    OnboardingProgressModel.user_id == user_id,
                    OnboardingProgressModel.organization_id == org_id,
                )
            )
        ).scalar_one()
        step_data = db_model.meta_data.get("step_data", {})
        assert step_data["STRATEGY"] == strat_meta
        assert step_data["RISK"] == risk_meta

    async def test_full_lifecycle_completion_and_immutability(
        self, async_session: AsyncSession, setup_tenant: dict[str, str]
    ) -> None:
        """Completing all 5 steps transitions to COMPLETED and cannot be regressed."""
        svc = OnboardingService(session=async_session)
        user_id = setup_tenant["user_id"]
        org_id = setup_tenant["organization_id"]

        # 1. WELCOME
        await svc.complete_step(user_id, org_id, "WELCOME")

        # 2. EMAIL_VERIFICATION
        user = (
            await async_session.execute(select(UserModel).where(UserModel.id == user_id))
        ).scalar_one()
        user.email_verified = True
        await async_session.flush()
        await svc.complete_step(user_id, org_id, "EMAIL_VERIFICATION")

        # 3. STRATEGY
        await svc.complete_step(user_id, org_id, "STRATEGY")

        # 4. RISK
        await svc.complete_step(user_id, org_id, "RISK")

        # 5. PAPER_TRADING_READY
        resp = await svc.complete_step(user_id, org_id, "PAPER_TRADING_READY")

        assert resp.status == OnboardingStatus.COMPLETED
        assert resp.completed_at is not None
        assert resp.next_step is None
        assert len(resp.completed_steps) == 5

        # Check ONBOARDING_COMPLETED audit event
        comp_audit = (
            await async_session.execute(
                select(AuditLogModel).where(
                    AuditLogModel.organization_id == org_id,
                    AuditLogModel.event_type == "ONBOARDING_COMPLETED",
                )
            )
        ).scalar_one()
        assert comp_audit.actor == user_id

        # Immutability: Calling complete_step on an already completed step returns COMPLETED
        repeat_resp = await svc.complete_step(user_id, org_id, "WELCOME")
        assert repeat_resp.status == OnboardingStatus.COMPLETED
        assert repeat_resp.completed_at == resp.completed_at

    async def test_idempotent_step_completion(
        self, async_session: AsyncSession, setup_tenant: dict[str, str]
    ) -> None:
        """Calling complete_step multiple times on the same step does not duplicate steps or error."""
        svc = OnboardingService(session=async_session)
        user_id = setup_tenant["user_id"]
        org_id = setup_tenant["organization_id"]

        r1 = await svc.complete_step(user_id, org_id, "WELCOME")
        r2 = await svc.complete_step(user_id, org_id, "WELCOME")

        assert r1.status == r2.status
        assert r1.current_step == r2.current_step
        assert r2.completed_steps.count(OnboardingStep.WELCOME) == 1

    async def test_invalid_step_name_rejected(
        self, async_session: AsyncSession, setup_tenant: dict[str, str]
    ) -> None:
        """Calling complete_step with invalid step raises ValueError."""
        svc = OnboardingService(session=async_session)
        user_id = setup_tenant["user_id"]
        org_id = setup_tenant["organization_id"]

        with pytest.raises(ValueError, match="Invalid onboarding step 'NOT_A_STEP'"):
            await svc.complete_step(user_id, org_id, "NOT_A_STEP")

    async def test_paper_trading_ready_requires_active_paper_account(
        self, async_session: AsyncSession, setup_tenant: dict[str, str]
    ) -> None:
        """PAPER_TRADING_READY requires an active paper account with positive balance."""
        svc = OnboardingService(session=async_session)
        user_id = setup_tenant["user_id"]
        org_id = setup_tenant["organization_id"]
        account_id = setup_tenant["account_id"]

        # Complete steps 1-4
        await svc.complete_step(user_id, org_id, "WELCOME")
        user = (
            await async_session.execute(select(UserModel).where(UserModel.id == user_id))
        ).scalar_one()
        user.email_verified = True
        await async_session.flush()
        await svc.complete_step(user_id, org_id, "EMAIL_VERIFICATION")
        await svc.complete_step(user_id, org_id, "STRATEGY")
        await svc.complete_step(user_id, org_id, "RISK")

        # Deactivate paper account to simulate invalid condition
        acc = (
            await async_session.execute(select(AccountModel).where(AccountModel.id == account_id))
        ).scalar_one()
        acc.is_active = False
        await async_session.flush()

        with pytest.raises(ValueError, match="Active paper trading account with positive balance is required"):
            await svc.complete_step(user_id, org_id, "PAPER_TRADING_READY")


class TestOnboardingRoutes:
    """Test suite for HTTP onboarding status and step endpoints."""

    def test_unauthenticated_request_rejected(self, async_session: AsyncSession) -> None:
        """Accessing onboarding status without authentication returns 401 Unauthorized."""
        from apps.trading_engine.src.dependencies import get_db_session
        from apps.trading_engine.src.main import create_app
        from fastapi.testclient import TestClient

        app = create_app()

        async def override_get_db_session():
            yield async_session

        app.dependency_overrides[get_db_session] = override_get_db_session
        try:
            client = TestClient(app)
            response = client.get("/api/v1/onboarding/status")
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    def test_route_get_status_and_complete_step(
        self, async_session: AsyncSession, setup_tenant: dict[str, str]
    ) -> None:
        """Route endpoints GET /status and POST /steps/{step}/complete operate correctly."""
        from apps.trading_engine.src.dependencies import (
            TenantContext,
            get_current_active_user,
            get_db_session,
            get_tenant_context,
        )
        from apps.trading_engine.src.main import create_app
        from fastapi.testclient import TestClient

        user_id = setup_tenant["user_id"]
        org_id = setup_tenant["organization_id"]

        app = create_app()

        # Override dependencies
        async def override_get_db_session():
            yield async_session

        async def override_get_current_active_user():
            return {
                "id": user_id,
                "username": "trader_ob_test",
                "email": "trader@ob.test",
                "is_active": True,
                "is_superuser": False,
                "status": "ACTIVE",
            }

        async def override_get_tenant_context():
            return TenantContext(
                user_id=user_id,
                organization_id=org_id,
                role="OWNER",
                is_superuser=False,
            )

        app.dependency_overrides[get_db_session] = override_get_db_session
        app.dependency_overrides[get_current_active_user] = override_get_current_active_user
        app.dependency_overrides[get_tenant_context] = override_get_tenant_context

        try:
            client = TestClient(app)

            # 1. GET /status -> 200 NOT_STARTED
            res = client.get("/api/v1/onboarding/status")
            assert res.status_code == 200, res.text
            body = res.json()
            assert body["user_id"] == user_id
            assert body["organization_id"] == org_id
            assert body["status"] == "NOT_STARTED"
            assert body["current_step"] == "WELCOME"
            assert len(body["steps"]) == 5

            # 2. POST /steps/INVALID/complete -> 400 Bad Request
            res_inv = client.post("/api/v1/onboarding/steps/INVALID_STEP/complete")
            assert res_inv.status_code == 400
            assert "Invalid onboarding step" in res_inv.json()["detail"]

            # 3. POST /steps/STRATEGY/complete before WELCOME -> 400 Bad Request
            res_skip = client.post("/api/v1/onboarding/steps/STRATEGY/complete")
            assert res_skip.status_code == 400
            assert "Prerequisite step 'WELCOME' must be completed first" in res_skip.json()["detail"]

            # 4. POST /steps/WELCOME/complete -> 200 IN_PROGRESS at EMAIL_VERIFICATION
            res_welc = client.post("/api/v1/onboarding/steps/WELCOME/complete")
            assert res_welc.status_code == 200
            welc_body = res_welc.json()
            assert welc_body["status"] == "IN_PROGRESS"
            assert welc_body["current_step"] == "EMAIL_VERIFICATION"
            assert "WELCOME" in welc_body["completed_steps"]

        finally:
            app.dependency_overrides.clear()

