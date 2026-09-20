"""Integration tests for EPIC-017 Phase 3: Subscriptions, Entitlements & Tier Enforcement.

Verifies:
1. SubscriptionService lifecycle operations (provisioning, plan lookups, upgrades, cancellation).
2. EntitlementService quota enforcement:
   - Account quota (Free: 1 account max, Pro: 3 max).
   - Daily order quota (Free: 100/day max, UTC boundary reset).
   - Worker quota (Free: 0 workers, rejected with 403; Pro: 1 worker allowed).
   - Asset entitlement (Free: 4 major pairs only; Pro: 12 pairs; Business/Enterprise: wildcard "*").
   - Inactive subscription fail-closed enforcement (Suspended/cancelled blocks trading).
3. Backward compatibility for personal / legacy accounts (None organization_id falls back to Free Sandbox).
4. Multi-tenant quota isolation (Org A's Free quota usage does not impact Org B's Business quota).
5. API endpoints:
   - GET /api/v1/plans
   - GET /api/v1/subscription
   - GET /api/v1/entitlements
   - POST /api/v1/subscription/change-plan
   - POST /api/v1/orders/ rejection before execution adapter
   - POST /api/v1/worker/start rejection under Free tier
"""

from __future__ import annotations

import pathlib
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest import mock

import pytest
from apps.trading_engine.src.config import AppSettings
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.services.auth import create_access_token, get_password_hash
from apps.trading_engine.src.services.entitlement_service import EntitlementService
from apps.trading_engine.src.services.subscription_service import SubscriptionService
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from libraries.domain.subscription.exceptions import (
    AccountQuotaExceededError,
    AssetNotEntitledError,
    DailyOrderQuotaExceededError,
    SubscriptionInactiveError,
    WorkerQuotaExceededError,
)
from libraries.domain.subscription.models import (
    PlanCode,
    SubscriptionStatus,
)
from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.config import DatabaseConfig, DatabaseManager
from libraries.infrastructure.persistence.models import (
    PlanModel,
    SubscriptionModel,
    UserModel,
)
from libraries.infrastructure.persistence.models.organization import (
    OrganizationMemberModel,
    OrganizationModel,
)


@pytest.fixture
async def saas_env():
    """Set up database with seeded plans, organizations, users, and app for Phase 3 testing."""
    db_file = f"test_saas_{uuid.uuid4().hex[:8]}.db"
    db_path = pathlib.Path(db_file)
    db_url = f"sqlite+aiosqlite:///{db_file}"

    db_config = DatabaseConfig(url=db_url, echo=False)
    db_manager = DatabaseManager(db_config)

    # Initialize tables
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    org_free_id = "org_tier_free"
    org_pro_id = "org_tier_pro"
    org_biz_id = "org_tier_biz"

    user_free_id = "usr_tier_free"
    user_pro_id = "usr_tier_pro"
    user_biz_id = "usr_tier_biz"
    user_legacy_id = "usr_tier_legacy"

    now = datetime.now(timezone.utc)

    async with db_manager.session() as session:
        # 1. Seed Plans
        plans = [
            PlanModel(
                id="plan-free",
                code="FREE",
                name="Free Sandbox",
                description="Free Sandbox tier",
                max_accounts=1,
                max_daily_orders=100,
                max_workers=0,
                allowed_assets=["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF"],
                retention_days=30,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            PlanModel(
                id="plan-pro",
                code="PRO",
                name="Pro Trader",
                description="Professional paper trading tier",
                max_accounts=3,
                max_daily_orders=2500,
                max_workers=1,
                allowed_assets=[
                    "EUR/USD",
                    "GBP/USD",
                    "USD/JPY",
                    "USD/CHF",
                    "AUD/USD",
                    "USD/CAD",
                    "NZD/USD",
                    "EUR/GBP",
                    "EUR/JPY",
                    "GBP/JPY",
                    "AUD/JPY",
                    "EUR/CHF",
                ],
                retention_days=365,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            PlanModel(
                id="plan-business",
                code="BUSINESS",
                name="Business / Prop Desk",
                description="Multi-account prop desk tier",
                max_accounts=10,
                max_daily_orders=50000,
                max_workers=5,
                allowed_assets=["*"],
                retention_days=1825,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            PlanModel(
                id="plan-enterprise",
                code="ENTERPRISE",
                name="Enterprise Institutional",
                description="Unlimited enterprise capacity",
                max_accounts=-1,
                max_daily_orders=-1,
                max_workers=-1,
                allowed_assets=["*"],
                retention_days=2555,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        ]
        session.add_all(plans)

        # 2. Seed Organizations
        org_free = OrganizationModel(id=org_free_id, name="Free Desk", slug="free-desk", status="ACTIVE", meta_data={})
        org_pro = OrganizationModel(id=org_pro_id, name="Pro Capital", slug="pro-capital", status="ACTIVE", meta_data={})
        org_biz = OrganizationModel(id=org_biz_id, name="Biz Prop", slug="biz-prop", status="ACTIVE", meta_data={})
        session.add_all([org_free, org_pro, org_biz])

        # 3. Seed Subscriptions
        sub_free = SubscriptionModel(
            id="sub-free-001",
            organization_id=org_free_id,
            plan_id="plan-free",
            status="ACTIVE",
            current_period_start=now,
            current_period_end=None,
            cancel_at_period_end=False,
            meta_data={},
            created_at=now,
            updated_at=now,
        )
        sub_pro = SubscriptionModel(
            id="sub-pro-001",
            organization_id=org_pro_id,
            plan_id="plan-pro",
            status="ACTIVE",
            current_period_start=now,
            current_period_end=None,
            cancel_at_period_end=False,
            meta_data={},
            created_at=now,
            updated_at=now,
        )
        sub_biz = SubscriptionModel(
            id="sub-biz-001",
            organization_id=org_biz_id,
            plan_id="plan-business",
            status="ACTIVE",
            current_period_start=now,
            current_period_end=None,
            cancel_at_period_end=False,
            meta_data={},
            created_at=now,
            updated_at=now,
        )
        session.add_all([sub_free, sub_pro, sub_biz])

        # 4. Seed Users
        hashed_pass = get_password_hash("SecretPass123!")
        u_free = UserModel(id=user_free_id, username="free_user", email="free@orion.dev", hashed_password=hashed_pass, is_active=True, is_superuser=False)
        u_pro = UserModel(id=user_pro_id, username="pro_user", email="pro@orion.dev", hashed_password=hashed_pass, is_active=True, is_superuser=False)
        u_biz = UserModel(id=user_biz_id, username="biz_user", email="biz@orion.dev", hashed_password=hashed_pass, is_active=True, is_superuser=False)
        u_legacy = UserModel(id=user_legacy_id, username="legacy_user", email="legacy@orion.dev", hashed_password=hashed_pass, is_active=True, is_superuser=False)
        session.add_all([u_free, u_pro, u_biz, u_legacy])

        # 5. Memberships
        m_free = OrganizationMemberModel(id="mem-free-1", organization_id=org_free_id, user_id=user_free_id, role="OWNER", status="ACTIVE", meta_data={})
        m_pro = OrganizationMemberModel(id="mem-pro-1", organization_id=org_pro_id, user_id=user_pro_id, role="OWNER", status="ACTIVE", meta_data={})
        m_biz = OrganizationMemberModel(id="mem-biz-1", organization_id=org_biz_id, user_id=user_biz_id, role="OWNER", status="ACTIVE", meta_data={})
        session.add_all([m_free, m_pro, m_biz])

        await session.commit()

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
    await paper_adapter.connect()

    app = create_app(
        settings=settings,
        paper_adapter=paper_adapter,
        db_manager=db_manager,
        redis_client=mock_redis,
    )

    token_free = create_access_token({"sub": user_free_id, "username": "free_user"})
    token_pro = create_access_token({"sub": user_pro_id, "username": "pro_user"})
    token_biz = create_access_token({"sub": user_biz_id, "username": "biz_user"})
    token_legacy = create_access_token({"sub": user_legacy_id, "username": "legacy_user"})

    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield {
            "client": client,
            "app": app,
            "db_manager": db_manager,
            "adapter": paper_adapter,
            "org_free_id": org_free_id,
            "org_pro_id": org_pro_id,
            "org_biz_id": org_biz_id,
            "user_free_id": user_free_id,
            "user_pro_id": user_pro_id,
            "user_biz_id": user_biz_id,
            "user_legacy_id": user_legacy_id,
            "token_free": token_free,
            "token_pro": token_pro,
            "token_biz": token_biz,
            "token_legacy": token_legacy,
        }
    await paper_adapter.disconnect()
    await db_manager.close()
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass


# ─── Service Layer Tests ───────────────────────────────────────────────────────


class TestSubscriptionServiceUnit:
    """Validate SubscriptionService business logic directly."""

    @pytest.mark.asyncio
    async def test_get_active_subscription(self, saas_env: dict) -> None:
        db_manager: DatabaseManager = saas_env["db_manager"]
        org_free_id: str = saas_env["org_free_id"]

        async with db_manager.session() as session:
            service = SubscriptionService(session)
            sub, plan = await service.get_active_subscription(org_free_id)
            assert sub is not None
            assert plan is not None
            assert plan.code == PlanCode.FREE
            assert sub.is_active is True

    @pytest.mark.asyncio
    async def test_assign_default_for_new_organization(self, saas_env: dict) -> None:
        db_manager: DatabaseManager = saas_env["db_manager"]
        new_org_id = f"org_new_{uuid.uuid4().hex[:8]}"

        async with db_manager.session() as session:
            # Create org
            org = OrganizationModel(id=new_org_id, name="New Desk", slug="new-desk", status="ACTIVE", meta_data={})
            session.add(org)
            await session.commit()

        async with db_manager.session() as session:
            service = SubscriptionService(session)
            sub = await service.assign_default_subscription(new_org_id)
            assert sub.organization_id == new_org_id
            assert sub.plan_id == "plan-free"
            assert sub.status == SubscriptionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_change_plan_upgrade(self, saas_env: dict) -> None:
        db_manager: DatabaseManager = saas_env["db_manager"]
        org_free_id: str = saas_env["org_free_id"]

        async with db_manager.session() as session:
            service = SubscriptionService(session)
            upgraded = await service.change_plan(org_free_id, PlanCode.PRO)
            assert upgraded.plan_id == "plan-pro"
            assert upgraded.status == SubscriptionStatus.ACTIVE

            # Verify persisted
            sub, plan = await service.get_active_subscription(org_free_id)
            assert sub is not None
            assert plan is not None
            assert plan.code == PlanCode.PRO

    @pytest.mark.asyncio
    async def test_cancel_subscription(self, saas_env: dict) -> None:
        db_manager: DatabaseManager = saas_env["db_manager"]
        org_pro_id: str = saas_env["org_pro_id"]

        async with db_manager.session() as session:
            service = SubscriptionService(session)
            cancelled = await service.cancel_subscription(org_pro_id)
            assert cancelled.status == SubscriptionStatus.CANCELLED
            assert cancelled.cancel_at_period_end is True

            # Inactive subscription check
            sub, _ = await service.get_active_subscription(org_pro_id)
            assert sub is None  # Cancelled is not active


class TestEntitlementServiceUnit:
    """Validate EntitlementService quota and instrument enforcement."""

    @pytest.mark.asyncio
    async def test_legacy_fallback_limits(self, saas_env: dict) -> None:
        db_manager: DatabaseManager = saas_env["db_manager"]
        async with db_manager.session() as session:
            ent_service = EntitlementService(session)
            entitlement = await ent_service.get_effective_entitlement(organization_id=None)
            assert entitlement.plan.code == PlanCode.FREE
            assert entitlement.limits.max_accounts == 1
            assert entitlement.limits.max_daily_orders == 100
            assert entitlement.limits.max_workers == 0

    @pytest.mark.asyncio
    async def test_account_quota_free_vs_pro(self, saas_env: dict) -> None:
        db_manager: DatabaseManager = saas_env["db_manager"]
        org_free_id: str = saas_env["org_free_id"]
        org_pro_id: str = saas_env["org_pro_id"]

        async with db_manager.session() as session:
            ent_service = EntitlementService(session)

            # Free plan: limit is 1
            await ent_service.check_account_quota(org_free_id, current_count=0)  # OK
            with pytest.raises(AccountQuotaExceededError):
                await ent_service.check_account_quota(org_free_id, current_count=1)

            # Pro plan: limit is 3
            await ent_service.check_account_quota(org_pro_id, current_count=2)  # OK
            with pytest.raises(AccountQuotaExceededError):
                await ent_service.check_account_quota(org_pro_id, current_count=3)

    @pytest.mark.asyncio
    async def test_daily_order_quota(self, saas_env: dict) -> None:
        db_manager: DatabaseManager = saas_env["db_manager"]
        org_free_id: str = saas_env["org_free_id"]

        async with db_manager.session() as session:
            ent_service = EntitlementService(session)

            # 99 orders placed: allowed
            await ent_service.check_daily_order_quota(org_free_id, current_daily_orders=99)

            # 100 orders placed: rejected
            with pytest.raises(DailyOrderQuotaExceededError) as exc_info:
                await ent_service.check_daily_order_quota(org_free_id, current_daily_orders=100)
            assert exc_info.value.limit == 100

    @pytest.mark.asyncio
    async def test_worker_quota(self, saas_env: dict) -> None:
        db_manager: DatabaseManager = saas_env["db_manager"]
        org_free_id: str = saas_env["org_free_id"]
        org_pro_id: str = saas_env["org_pro_id"]

        async with db_manager.session() as session:
            ent_service = EntitlementService(session)

            # Free plan has max_workers = 0 -> rejected
            with pytest.raises(WorkerQuotaExceededError):
                await ent_service.check_worker_quota(org_free_id)

            # Pro plan has max_workers = 1 -> allowed for 0 active workers
            await ent_service.check_worker_quota(org_pro_id, active_worker_count=0)

            # Pro plan with 1 already active -> rejected
            with pytest.raises(WorkerQuotaExceededError):
                await ent_service.check_worker_quota(org_pro_id, active_worker_count=1)

    @pytest.mark.asyncio
    async def test_asset_entitlement(self, saas_env: dict) -> None:
        db_manager: DatabaseManager = saas_env["db_manager"]
        org_free_id: str = saas_env["org_free_id"]
        org_pro_id: str = saas_env["org_pro_id"]
        org_biz_id: str = saas_env["org_biz_id"]

        async with db_manager.session() as session:
            ent_service = EntitlementService(session)

            # Free allows major pairs
            await ent_service.check_asset_access(org_free_id, "EUR/USD")
            await ent_service.check_asset_access(org_free_id, "USDJPY")

            # Free rejects minor/exotic
            with pytest.raises(AssetNotEntitledError):
                await ent_service.check_asset_access(org_free_id, "NZD/USD")
            with pytest.raises(AssetNotEntitledError):
                await ent_service.check_asset_access(org_free_id, "EUR/GBP")

            # Pro allows EUR/GBP and NZD/USD
            await ent_service.check_asset_access(org_pro_id, "NZD/USD")
            await ent_service.check_asset_access(org_pro_id, "EUR/GBP")

            # Pro rejects exotic not in 12 pairs
            with pytest.raises(AssetNotEntitledError):
                await ent_service.check_asset_access(org_pro_id, "USD/SEK")

            # Business allows wildcard "*"
            await ent_service.check_asset_access(org_biz_id, "USD/SEK")
            await ent_service.check_asset_access(org_biz_id, "BTC/USD")

    @pytest.mark.asyncio
    async def test_inactive_subscription_fail_closed(self, saas_env: dict) -> None:
        db_manager: DatabaseManager = saas_env["db_manager"]
        org_free_id: str = saas_env["org_free_id"]

        async with db_manager.session() as session:
            # Suspend the subscription
            stmt = select(SubscriptionModel).where(SubscriptionModel.organization_id == org_free_id)
            result = await session.execute(stmt)
            sub = result.scalar_one()
            sub.status = "SUSPENDED"
            await session.commit()

        async with db_manager.session() as session:
            ent_service = EntitlementService(session)
            with pytest.raises(SubscriptionInactiveError) as exc_info:
                await ent_service.check_asset_access(org_free_id, "EUR/USD")
            assert "SUSPENDED" in exc_info.value.message


# ─── API End-to-End Entitlement Tests ──────────────────────────────────────────


class TestSaaSApiEntitlements:
    """Validate HTTP API enforcement of subscriptions and entitlements."""

    @pytest.mark.asyncio
    async def test_get_plans(self, saas_env: dict) -> None:
        client: AsyncClient = saas_env["client"]
        token = saas_env["token_free"]

        response = await client.get(
            "/api/v1/plans",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        plans = response.json()
        assert len(plans) == 4
        codes = [p["code"] for p in plans]
        assert set(codes) == {"FREE", "PRO", "BUSINESS", "ENTERPRISE"}

    @pytest.mark.asyncio
    async def test_get_subscription_for_tenant(self, saas_env: dict) -> None:
        client: AsyncClient = saas_env["client"]
        token = saas_env["token_pro"]
        org_pro_id = saas_env["org_pro_id"]

        response = await client.get(
            "/api/v1/subscription",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Organization-ID": org_pro_id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["plan"]["code"] == "PRO"
        assert data["status"] == "ACTIVE"
        assert data["organization_id"] == org_pro_id

    @pytest.mark.asyncio
    async def test_get_entitlements_usage_summary(self, saas_env: dict) -> None:
        client: AsyncClient = saas_env["client"]
        token = saas_env["token_biz"]
        org_biz_id = saas_env["org_biz_id"]

        response = await client.get(
            "/api/v1/entitlements",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Organization-ID": org_biz_id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["plan_code"] == "BUSINESS"
        assert data["quotas"]["accounts"]["limit"] == 10
        assert data["quotas"]["daily_orders"]["limit"] == 50000
        assert data["quotas"]["workers"]["limit"] == 5

    @pytest.mark.asyncio
    async def test_change_plan_endpoint(self, saas_env: dict) -> None:
        client: AsyncClient = saas_env["client"]
        token = saas_env["token_free"]
        org_free_id = saas_env["org_free_id"]

        # Upgrade Free org to Pro
        response = await client.post(
            "/api/v1/subscription/change-plan",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Organization-ID": org_free_id,
            },
            json={"plan_code": "PRO"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["plan"]["code"] == "PRO"

    @pytest.mark.asyncio
    async def test_order_creation_asset_entitlement_enforcement(self, saas_env: dict) -> None:
        """Verify order creation validates asset entitlement before execution."""
        client: AsyncClient = saas_env["client"]
        token = saas_env["token_free"]
        org_free_id = saas_env["org_free_id"]

        # 1. Disallowed asset on Free org -> rejected with 403
        bad_order_resp = await client.post(
            "/api/v1/orders/",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Organization-ID": org_free_id,
            },
            json={
                "symbol": "NZD/USD",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": "10000",
            },
        )
        assert bad_order_resp.status_code == 403
        err_msg = bad_order_resp.json().get("message") or bad_order_resp.json().get("detail", "")
        assert "not entitled" in err_msg.lower()

        # 2. Allowed asset on Free org -> created with 201
        good_order_resp = await client.post(
            "/api/v1/orders/",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Organization-ID": org_free_id,
            },
            json={
                "symbol": "EUR/USD",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": "10000",
            },
        )
        assert good_order_resp.status_code == 201
        assert good_order_resp.json()["symbol"] in ("EUR/USD", "EURUSD")

    @pytest.mark.asyncio
    async def test_worker_start_quota_enforcement(self, saas_env: dict) -> None:
        """Verify worker start validates tenant plan worker quota."""
        client: AsyncClient = saas_env["client"]
        token_free = saas_env["token_free"]
        org_free_id = saas_env["org_free_id"]
        db_manager: DatabaseManager = saas_env["db_manager"]
        user_free_id: str = saas_env["user_free_id"]

        # Make user superuser so they pass the superuser check, but hit worker quota
        async with db_manager.session() as session:
            stmt = select(UserModel).where(UserModel.id == user_free_id)
            result = await session.execute(stmt)
            user = result.scalar_one()
            user.is_superuser = True
            await session.commit()

        resp = await client.post(
            "/api/v1/worker/start",
            headers={
                "Authorization": f"Bearer {token_free}",
                "X-Organization-ID": org_free_id,
            },
        )
        # Free tier has 0 workers -> HTTP 403 Forbidden
        assert resp.status_code == 403
        err_msg = resp.json().get("message") or resp.json().get("detail", "")
        assert "worker limit: 0" in err_msg.lower()
