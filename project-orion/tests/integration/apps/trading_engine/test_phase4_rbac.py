"""Integration test suite for EPIC-017 Phase 4: RBAC Route Governance & Invariants.

Verifies:
1. Canonical 7-Role Permission Matrix integrity (25 granular permissions).
2. Centralized declarative route governance across operational subsystems.
3. Last-owner protection invariants (cannot demote or remove sole owner).
4. Self-escalation and self-demotion prevention.
5. Non-owner demotion/removal protection (only OWNER can modify/remove OWNER).
6. Cross-tenant isolation and IDOR defense.
7. Superuser vs tenant role separation.
8. Personal sandbox backward compatibility.
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
from httpx import ASGITransport, AsyncClient

from libraries.domain.organization.models import OrganizationRole
from libraries.domain.organization.permissions import (
    ROLE_PERMISSIONS,
    Permission,
    has_permission,
)
from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.config import DatabaseConfig, DatabaseManager
from libraries.infrastructure.persistence.models import (
    AccountModel,
    OrganizationMemberModel,
    OrganizationModel,
    PlanModel,
    SubscriptionModel,
    UserModel,
)

# ===========================================================================
# 1. Permission Matrix Property Verification
# ===========================================================================

def test_canonical_permission_matrix_integrity():
    """Verify the 41 granular permissions across the 7 canonical roles."""
    assert len(Permission) == 41

    # OWNER: exactly 41 permissions
    assert len(ROLE_PERMISSIONS[OrganizationRole.OWNER]) == 41
    for perm in Permission:
        assert has_permission(OrganizationRole.OWNER, perm) is True

    # ADMINISTRATOR: 36 permissions (all except ORDER_CREATE, ORDER_CANCEL, POSITION_CLOSE, RISK_CONFIGURE, BROKER_SANDBOX_EXECUTE)
    assert len(ROLE_PERMISSIONS[OrganizationRole.ADMINISTRATOR]) == 36
    assert has_permission(OrganizationRole.ADMINISTRATOR, Permission.ORDER_CREATE) is False
    assert has_permission(OrganizationRole.ADMINISTRATOR, Permission.ORDER_CANCEL) is False
    assert has_permission(OrganizationRole.ADMINISTRATOR, Permission.POSITION_CLOSE) is False
    assert has_permission(OrganizationRole.ADMINISTRATOR, Permission.RISK_CONFIGURE) is False
    assert has_permission(OrganizationRole.ADMINISTRATOR, Permission.ORGANIZATION_UPDATE) is True
    assert has_permission(OrganizationRole.ADMINISTRATOR, Permission.MEMBER_INVITE) is True
    assert has_permission(OrganizationRole.ADMINISTRATOR, Permission.MEMBER_UPDATE) is True
    assert has_permission(OrganizationRole.ADMINISTRATOR, Permission.MEMBER_REMOVE) is True

    # PORTFOLIO_MANAGER: 35 permissions
    assert len(ROLE_PERMISSIONS[OrganizationRole.PORTFOLIO_MANAGER]) == 35
    assert has_permission(OrganizationRole.PORTFOLIO_MANAGER, Permission.ORDER_CREATE) is True
    assert has_permission(OrganizationRole.PORTFOLIO_MANAGER, Permission.ORDER_CANCEL) is True
    assert has_permission(OrganizationRole.PORTFOLIO_MANAGER, Permission.POSITION_CLOSE) is True
    assert has_permission(OrganizationRole.PORTFOLIO_MANAGER, Permission.WORKER_START) is True
    assert has_permission(OrganizationRole.PORTFOLIO_MANAGER, Permission.ORGANIZATION_UPDATE) is False
    assert has_permission(OrganizationRole.PORTFOLIO_MANAGER, Permission.MEMBER_INVITE) is False
    assert has_permission(OrganizationRole.PORTFOLIO_MANAGER, Permission.RISK_CONFIGURE) is False

    # RISK_OFFICER: 19 permissions
    assert len(ROLE_PERMISSIONS[OrganizationRole.RISK_OFFICER]) == 19
    assert has_permission(OrganizationRole.RISK_OFFICER, Permission.RISK_CONFIGURE) is True
    assert has_permission(OrganizationRole.RISK_OFFICER, Permission.RISK_READ) is True
    assert has_permission(OrganizationRole.RISK_OFFICER, Permission.AUDIT_READ) is True
    assert has_permission(OrganizationRole.RISK_OFFICER, Permission.ORDER_CREATE) is False
    assert has_permission(OrganizationRole.RISK_OFFICER, Permission.ORDER_CANCEL) is False
    assert has_permission(OrganizationRole.RISK_OFFICER, Permission.POSITION_CLOSE) is False
    assert has_permission(OrganizationRole.RISK_OFFICER, Permission.ORGANIZATION_UPDATE) is False

    # TRADER: 27 permissions
    assert len(ROLE_PERMISSIONS[OrganizationRole.TRADER]) == 27
    assert has_permission(OrganizationRole.TRADER, Permission.ORDER_CREATE) is True
    assert has_permission(OrganizationRole.TRADER, Permission.ORDER_CANCEL) is True
    assert has_permission(OrganizationRole.TRADER, Permission.POSITION_CLOSE) is True
    assert has_permission(OrganizationRole.TRADER, Permission.STRATEGY_CONFIGURE) is True
    assert has_permission(OrganizationRole.TRADER, Permission.RISK_CONFIGURE) is False
    assert has_permission(OrganizationRole.TRADER, Permission.ORGANIZATION_UPDATE) is False
    assert has_permission(OrganizationRole.TRADER, Permission.MEMBER_INVITE) is False

    # AUDITOR: 18 permissions
    assert len(ROLE_PERMISSIONS[OrganizationRole.AUDITOR]) == 18
    assert has_permission(OrganizationRole.AUDITOR, Permission.AUDIT_READ) is True
    assert has_permission(OrganizationRole.AUDITOR, Permission.ORDER_READ) is True
    assert has_permission(OrganizationRole.AUDITOR, Permission.TRADE_READ) is True
    assert has_permission(OrganizationRole.AUDITOR, Permission.ORDER_CREATE) is False
    assert has_permission(OrganizationRole.AUDITOR, Permission.RISK_CONFIGURE) is False

    # VIEWER: 14 permissions
    assert len(ROLE_PERMISSIONS[OrganizationRole.VIEWER]) == 14
    assert has_permission(OrganizationRole.VIEWER, Permission.ORDER_READ) is True
    assert has_permission(OrganizationRole.VIEWER, Permission.POSITION_READ) is True
    assert has_permission(OrganizationRole.VIEWER, Permission.AUDIT_READ) is False
    assert has_permission(OrganizationRole.VIEWER, Permission.ORDER_CREATE) is False


# ===========================================================================
# 2. RBAC Integration Environment Fixture
# ===========================================================================

@pytest.fixture
async def rbac_env():
    """Build multi-tenant environment with all 7 roles, personal users, and superusers."""
    db_file = f"test_rbac_{uuid.uuid4().hex[:8]}.db"
    db_path = pathlib.Path(db_file)
    db_url = f"sqlite+aiosqlite:///{db_file}"

    db_config = DatabaseConfig(url=db_url, echo=False)
    db_manager = DatabaseManager(db_config)

    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    org_alpha_id = "org_alpha_rbac"
    org_beta_id = "org_beta_rbac"

    users_map = {
        "owner": ("usr_owner", "owner_u", OrganizationRole.OWNER),
        "admin": ("usr_admin", "admin_u", OrganizationRole.ADMINISTRATOR),
        "pm": ("usr_pm", "pm_u", OrganizationRole.PORTFOLIO_MANAGER),
        "risk": ("usr_risk", "risk_u", OrganizationRole.RISK_OFFICER),
        "trader": ("usr_trader", "trader_u", OrganizationRole.TRADER),
        "auditor": ("usr_auditor", "auditor_u", OrganizationRole.AUDITOR),
        "viewer": ("usr_viewer", "viewer_u", OrganizationRole.VIEWER),
    }

    now = datetime.now(timezone.utc)

    async with db_manager.session() as session:
        # Default Plan
        free_plan = PlanModel(
            id="plan-free",
            code="FREE",
            name="Free Tier",
            description="Default free plan",
            max_accounts=1,
            max_daily_orders=100,
            max_workers=1,
            allowed_assets=["EUR/USD", "GBP/USD", "USD/JPY"],
            retention_days=30,
            is_active=True,
        )
        pro_plan = PlanModel(
            id="plan-pro",
            code="PRO",
            name="Pro Tier",
            description="Professional plan",
            max_accounts=5,
            max_daily_orders=5000,
            max_workers=5,
            allowed_assets=["*"],
            retention_days=180,
            is_active=True,
        )
        session.add_all([free_plan, pro_plan])

        # Organizations
        org_alpha = OrganizationModel(
            id=org_alpha_id, name="Alpha Hedge Fund", slug="alpha-hedge", status="ACTIVE", meta_data={}
        )
        org_beta = OrganizationModel(
            id=org_beta_id, name="Beta Capital", slug="beta-cap", status="ACTIVE", meta_data={}
        )
        session.add_all([org_alpha, org_beta])

        # Subscriptions
        sub_alpha = SubscriptionModel(
            id=f"sub_{uuid.uuid4().hex[:12]}",
            organization_id=org_alpha_id,
            plan_id="plan-free",
            status="ACTIVE",
            current_period_start=now,
            current_period_end=now,
            cancel_at_period_end=False,
        )
        session.add(sub_alpha)

        # Alpha Members
        for uid, uname, role in users_map.values():
            u = UserModel(
                id=uid,
                username=uname,
                email=f"{uname}@alpha.com",
                hashed_password=get_password_hash("Secret123!"),
                is_active=True,
                is_superuser=False,
            )
            m = OrganizationMemberModel(
                id=f"mem_{uname}",
                organization_id=org_alpha_id,
                user_id=uid,
                role=role.value,
                status="ACTIVE",
                meta_data={},
            )
            session.add_all([u, m])

        # Beta Owner
        u_beta_owner = UserModel(
            id="usr_beta_owner",
            username="beta_owner",
            email="owner@beta.com",
            hashed_password=get_password_hash("Secret123!"),
            is_active=True,
            is_superuser=False,
        )
        m_beta_owner = OrganizationMemberModel(
            id="mem_beta_owner",
            organization_id=org_beta_id,
            user_id="usr_beta_owner",
            role="OWNER",
            status="ACTIVE",
            meta_data={},
        )
        session.add_all([u_beta_owner, m_beta_owner])

        # Superuser with NO organization membership
        u_superuser = UserModel(
            id="usr_platform_admin",
            username="superadmin",
            email="root@platform.io",
            hashed_password=get_password_hash("Secret123!"),
            is_active=True,
            is_superuser=True,
        )
        session.add(u_superuser)

        # Personal individual trader (no organization membership)
        u_personal = UserModel(
            id="usr_personal_dev",
            username="personal_trader",
            email="solo@trader.io",
            hashed_password=get_password_hash("Secret123!"),
            is_active=True,
            is_superuser=False,
        )
        session.add(u_personal)

        # Organization-scoped paper account
        acc_alpha = AccountModel(
            id="acc_alpha_trading",
            organization_id=org_alpha_id,
            user_id="usr_owner",
            broker_name="paper",
            account_number="PAPER-ALPHA-001",
            currency="USD",
            balance=Decimal("100000.00"),
            equity=Decimal("100000.00"),
            margin=Decimal("0.00"),
            margin_free=Decimal("100000.00"),
            margin_level=0.0,
            leverage=100,
            is_live=False,
            is_active=True,
            meta_data={},
        )
        session.add(acc_alpha)

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

    app = create_app(
        settings=settings,
        db_manager=db_manager,
        redis_client=mock_redis,
        paper_adapter=paper_adapter,
    )

    tokens = {
        key: create_access_token({"sub": uid, "username": uname})
        for key, (uid, uname, _) in users_map.items()
    }
    tokens["beta_owner"] = create_access_token({"sub": "usr_beta_owner", "username": "beta_owner"})
    tokens["superuser"] = create_access_token({"sub": "usr_platform_admin", "username": "superadmin"})
    tokens["personal"] = create_access_token({"sub": "usr_personal_dev", "username": "personal_trader"})

    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield {
            "client": client,
            "db_manager": db_manager,
            "org_alpha_id": org_alpha_id,
            "org_beta_id": org_beta_id,
            "tokens": tokens,
            "users_map": users_map,
        }

    await paper_adapter.disconnect()
    await db_manager.close()
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass


# ===========================================================================
# 3. Route Permission Governance Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_order_creation_rbac(rbac_env: dict):
    """ORDER_CREATE is permitted for OWNER, PM, TRADER; forbidden for others."""
    client: AsyncClient = rbac_env["client"]
    tokens: dict[str, str] = rbac_env["tokens"]

    order_payload = {
        "symbol": "EUR/USD",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": "10000",
    }

    # Permitted roles
    for role_key in ["owner", "pm", "trader"]:
        resp = await client.post(
            "/api/v1/orders/",
            headers={"Authorization": f"Bearer {tokens[role_key]}"},
            json=order_payload,
        )
        assert resp.status_code == 201, f"Expected 201 for {role_key}, got {resp.status_code}: {resp.text}"

    # Denied roles
    for role_key in ["admin", "risk", "auditor", "viewer"]:
        resp = await client.post(
            "/api/v1/orders/",
            headers={"Authorization": f"Bearer {tokens[role_key]}"},
            json=order_payload,
        )
        assert resp.status_code == 403, f"Expected 403 for {role_key}, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_risk_configuration_rbac(rbac_env: dict):
    """RISK_CONFIGURE is permitted for OWNER and RISK_OFFICER; forbidden for others."""
    client: AsyncClient = rbac_env["client"]
    tokens: dict[str, str] = rbac_env["tokens"]

    # Permitted roles
    for role_key in ["owner", "risk"]:
        resp = await client.put(
            "/api/v1/risk/limits",
            headers={"Authorization": f"Bearer {tokens[role_key]}"},
        )
        assert resp.status_code == 200, f"Expected 200 for {role_key}, got {resp.status_code}: {resp.text}"

    # Denied roles
    for role_key in ["admin", "pm", "trader", "auditor", "viewer"]:
        resp = await client.put(
            "/api/v1/risk/limits",
            headers={"Authorization": f"Bearer {tokens[role_key]}"},
        )
        assert resp.status_code == 403, f"Expected 403 for {role_key}, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_organization_update_rbac(rbac_env: dict):
    """ORGANIZATION_UPDATE is permitted for OWNER and ADMINISTRATOR; forbidden for others."""
    client: AsyncClient = rbac_env["client"]
    tokens: dict[str, str] = rbac_env["tokens"]
    org_id: str = rbac_env["org_alpha_id"]

    # Permitted roles
    for role_key in ["owner", "admin"]:
        resp = await client.patch(
            f"/api/v1/organizations/{org_id}",
            headers={"Authorization": f"Bearer {tokens[role_key]}"},
            json={"name": f"Alpha Hedge Updated by {role_key}"},
        )
        assert resp.status_code == 200, f"Expected 200 for {role_key}, got {resp.status_code}: {resp.text}"

    # Denied roles
    for role_key in ["pm", "risk", "trader", "auditor", "viewer"]:
        resp = await client.patch(
            f"/api/v1/organizations/{org_id}",
            headers={"Authorization": f"Bearer {tokens[role_key]}"},
            json={"name": "Disallowed Name"},
        )
        assert resp.status_code == 403, f"Expected 403 for {role_key}, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_member_invite_rbac(rbac_env: dict):
    """MEMBER_INVITE is permitted for OWNER and ADMINISTRATOR; forbidden for others."""
    client: AsyncClient = rbac_env["client"]
    tokens: dict[str, str] = rbac_env["tokens"]
    org_id: str = rbac_env["org_alpha_id"]

    # Permitted roles
    for role_key in ["owner", "admin"]:
        resp = await client.post(
            f"/api/v1/organizations/{org_id}/members/invite",
            headers={"Authorization": f"Bearer {tokens[role_key]}"},
            json={"email": f"new_{role_key}@alpha.com", "role": "VIEWER"},
        )
        assert resp.status_code == 201, f"Expected 201 for {role_key}, got {resp.status_code}: {resp.text}"

    # Denied roles
    for role_key in ["pm", "risk", "trader", "auditor", "viewer"]:
        resp = await client.post(
            f"/api/v1/organizations/{org_id}/members/invite",
            headers={"Authorization": f"Bearer {tokens[role_key]}"},
            json={"email": f"blocked_{role_key}@alpha.com", "role": "VIEWER"},
        )
        assert resp.status_code == 403, f"Expected 403 for {role_key}, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_subscription_manage_rbac(rbac_env: dict):
    """SUBSCRIPTION_MANAGE is permitted for OWNER and ADMINISTRATOR; forbidden for others."""
    client: AsyncClient = rbac_env["client"]
    tokens: dict[str, str] = rbac_env["tokens"]

    # Permitted roles
    for role_key in ["owner", "admin"]:
        resp = await client.post(
            "/api/v1/subscription/change-plan",
            headers={"Authorization": f"Bearer {tokens[role_key]}"},
            json={"plan_code": "PRO"},
        )
        assert resp.status_code == 200, f"Expected 200 for {role_key}, got {resp.status_code}: {resp.text}"

    # Denied roles
    for role_key in ["pm", "risk", "trader", "auditor", "viewer"]:
        resp = await client.post(
            "/api/v1/subscription/change-plan",
            headers={"Authorization": f"Bearer {tokens[role_key]}"},
            json={"plan_code": "FREE"},
        )
        assert resp.status_code == 403, f"Expected 403 for {role_key}, got {resp.status_code}: {resp.text}"


# ===========================================================================
# 4. Governance Invariants: Last-Owner & Self-Escalation
# ===========================================================================

@pytest.mark.asyncio
async def test_last_owner_protection(rbac_env: dict):
    """Cannot demote or remove the last active OWNER of an organization."""
    client: AsyncClient = rbac_env["client"]
    tokens: dict[str, str] = rbac_env["tokens"]
    org_id: str = rbac_env["org_alpha_id"]
    owner_user_id = "usr_owner"
    pm_user_id = "usr_pm"

    # 1. Sole owner demotion attempt (even by owner himself or admin) fails
    resp = await client.patch(
        f"/api/v1/organizations/{org_id}/members/{owner_user_id}/role",
        headers={"Authorization": f"Bearer {tokens['owner']}"},
        json={"role": "TRADER"},
    )
    assert resp.status_code == 400
    msg = (resp.json().get("message") or resp.json().get("detail", "")).lower()
    assert "last owner" in msg or "cannot modify" in msg

    # 2. Sole owner removal attempt fails
    resp_del = await client.delete(
        f"/api/v1/organizations/{org_id}/members/{owner_user_id}",
        headers={"Authorization": f"Bearer {tokens['owner']}"},
    )
    assert resp_del.status_code == 400
    msg_del = (resp_del.json().get("message") or resp_del.json().get("detail", "")).lower()
    assert "last owner" in msg_del or "cannot remove" in msg_del

    # 3. Promote a second owner
    promote_resp = await client.patch(
        f"/api/v1/organizations/{org_id}/members/{pm_user_id}/role",
        headers={"Authorization": f"Bearer {tokens['owner']}"},
        json={"role": "OWNER"},
    )
    assert promote_resp.status_code == 200
    assert promote_resp.json()["role"] == "OWNER"

    # 4. Now demoting the second owner succeeds because 2 owners exist
    demote_resp = await client.patch(
        f"/api/v1/organizations/{org_id}/members/{pm_user_id}/role",
        headers={"Authorization": f"Bearer {tokens['owner']}"},
        json={"role": "PORTFOLIO_MANAGER"},
    )
    assert demote_resp.status_code == 200
    assert demote_resp.json()["role"] == "PORTFOLIO_MANAGER"


@pytest.mark.asyncio
async def test_self_escalation_and_self_modification_prevention(rbac_env: dict):
    """Users cannot modify their own role or remove themselves via member endpoints."""
    client: AsyncClient = rbac_env["client"]
    tokens: dict[str, str] = rbac_env["tokens"]
    org_id: str = rbac_env["org_alpha_id"]
    admin_user_id = "usr_admin"

    # Administrator attempts to self-promote to OWNER
    resp = await client.patch(
        f"/api/v1/organizations/{org_id}/members/{admin_user_id}/role",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json={"role": "OWNER"},
    )
    assert resp.status_code == 400
    msg = (resp.json().get("message") or resp.json().get("detail", "")).lower()
    assert "cannot modify" in msg

    # Administrator attempts to self-remove
    resp_remove = await client.delete(
        f"/api/v1/organizations/{org_id}/members/{admin_user_id}",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
    )
    assert resp_remove.status_code == 400
    msg_remove = (resp_remove.json().get("message") or resp_remove.json().get("detail", "")).lower()
    assert "cannot remove" in msg_remove


@pytest.mark.asyncio
async def test_non_owner_cannot_modify_or_remove_owner(rbac_env: dict):
    """An ADMINISTRATOR cannot modify or remove an OWNER."""
    client: AsyncClient = rbac_env["client"]
    tokens: dict[str, str] = rbac_env["tokens"]
    org_id: str = rbac_env["org_alpha_id"]
    owner_user_id = "usr_owner"

    # Admin attempts to demote Owner
    resp = await client.patch(
        f"/api/v1/organizations/{org_id}/members/{owner_user_id}/role",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json={"role": "ADMINISTRATOR"},
    )
    assert resp.status_code == 403
    msg = (resp.json().get("message") or resp.json().get("detail", "")).lower()
    assert "only an owner" in msg

    # Admin attempts to remove Owner
    resp_remove = await client.delete(
        f"/api/v1/organizations/{org_id}/members/{owner_user_id}",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
    )
    assert resp_remove.status_code == 403
    msg_remove = (resp_remove.json().get("message") or resp_remove.json().get("detail", "")).lower()
    assert "only an owner" in msg_remove


# ===========================================================================
# 5. Cross-Tenant IDOR & Superuser Separation
# ===========================================================================

@pytest.mark.asyncio
async def test_cross_tenant_isolation_and_idor_defense(rbac_env: dict):
    """User in Org B cannot read, update, or administer Org A."""
    client: AsyncClient = rbac_env["client"]
    tokens: dict[str, str] = rbac_env["tokens"]
    org_alpha_id: str = rbac_env["org_alpha_id"]

    headers_beta_owner = {"Authorization": f"Bearer {tokens['beta_owner']}"}

    # 1. Attempt to view Org A members
    r1 = await client.get(f"/api/v1/organizations/{org_alpha_id}/members", headers=headers_beta_owner)
    assert r1.status_code == 403

    # 2. Attempt to update Org A details
    r2 = await client.patch(
        f"/api/v1/organizations/{org_alpha_id}",
        headers=headers_beta_owner,
        json={"name": "Hacked Org A"},
    )
    assert r2.status_code == 403

    # 3. Attempt to inject X-Organization-ID header for Org A
    headers_injected = {
        "Authorization": f"Bearer {tokens['beta_owner']}",
        "X-Organization-ID": org_alpha_id,
    }
    r3 = await client.get("/api/v1/orders/", headers=headers_injected)
    assert r3.status_code == 403
    msg3 = (r3.json().get("message") or r3.json().get("detail", "")).lower()
    assert "denied" in msg3 or "forbidden" in msg3


@pytest.mark.asyncio
async def test_superuser_tenant_role_separation(rbac_env: dict):
    """Platform superuser has no automatic tenant OWNER role and cannot access tenant org routes."""
    client: AsyncClient = rbac_env["client"]
    tokens: dict[str, str] = rbac_env["tokens"]
    org_alpha_id: str = rbac_env["org_alpha_id"]

    headers_superuser = {"Authorization": f"Bearer {tokens['superuser']}"}

    # Platform superuser has NO membership in org_alpha
    resp = await client.get(
        f"/api/v1/organizations/{org_alpha_id}/members",
        headers=headers_superuser,
    )
    assert resp.status_code == 403

    # Attempting to pass X-Organization-ID for org_alpha without membership is rejected
    headers_with_org = {
        "Authorization": f"Bearer {tokens['superuser']}",
        "X-Organization-ID": org_alpha_id,
    }
    resp_org = await client.get("/api/v1/orders/", headers=headers_with_org)
    assert resp_org.status_code == 403


# ===========================================================================
# 6. Backward Compatibility: Personal Sandbox Mode
# ===========================================================================

@pytest.mark.asyncio
async def test_personal_sandbox_trading_and_org_restrictions(rbac_env: dict):
    """Personal individual user without org membership can trade in sandbox but cannot access org governance."""
    client: AsyncClient = rbac_env["client"]
    tokens: dict[str, str] = rbac_env["tokens"]
    org_alpha_id: str = rbac_env["org_alpha_id"]

    headers_personal = {"Authorization": f"Bearer {tokens['personal']}"}

    # 1. Personal user can list orders (sandbox paper account auto-provisioned)
    r_orders = await client.get("/api/v1/orders/", headers=headers_personal)
    assert r_orders.status_code == 200

    # 2. Personal user can place paper orders
    r_place = await client.post(
        "/api/v1/orders/",
        headers=headers_personal,
        json={"symbol": "EUR/USD", "side": "BUY", "order_type": "MARKET", "quantity": "1000"},
    )
    assert r_place.status_code == 201

    # 3. Personal user can inspect positions and trades
    r_pos = await client.get("/api/v1/positions/", headers=headers_personal)
    assert r_pos.status_code == 200
    r_trades = await client.get("/api/v1/trades/", headers=headers_personal)
    assert r_trades.status_code == 200

    # 4. Personal user can read risk telemetry
    r_risk = await client.get("/api/v1/risk/status", headers=headers_personal)
    assert r_risk.status_code == 200

    # 5. Personal user CANNOT access institutional organization endpoints
    r_org = await client.get(f"/api/v1/organizations/{org_alpha_id}/members", headers=headers_personal)
    assert r_org.status_code == 403
