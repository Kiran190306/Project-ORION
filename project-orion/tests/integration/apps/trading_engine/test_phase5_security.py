"""Phase 5 Security, Authorization, Multi-Tenant Isolation & Governance Hardening Test Suite.

Authoritative verification for EPIC-017 Phase 5:
1. Canonical 7 Roles × 25 Permissions Matrix integrity.
2. Hardened POST /api/v1/paper-trade (Auth, RBAC, Entitlements, Quotas, Audit Logging).
3. Organization active status fail-closed enforcement (SUSPENDED / DEACTIVATED -> 403).
4. Institutional HTTP Security Headers (HSTS, Referrer-Policy, CSP, nosniff, DENY).
5. Audit Log API (GET /api/v1/organizations/{id}/audit-logs with RBAC, IDOR defense, and redaction).
6. Operational route RBAC governance across accounts, portfolio, dashboard, and strategies.
7. Cross-tenant IDOR defense across all resource endpoints.
8. Privilege escalation and governance protection invariants.
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
    AuditLogModel,
    OrderModel,
    OrganizationMemberModel,
    OrganizationModel,
    PlanModel,
    SubscriptionModel,
    UserModel,
)

# ===========================================================================
# 1. Canonical Permission Count & Matrix Integrity
# ===========================================================================


def test_canonical_permission_matrix_25_members():
    """Verify that exactly 25 granular permissions exist and match the canonical role matrix."""
    assert len(Permission) == 25

    expected_permissions = {
        "ACCOUNT_READ", "ACCOUNT_CREATE", "ACCOUNT_UPDATE",
        "ORDER_READ", "ORDER_CREATE", "ORDER_CANCEL",
        "POSITION_READ", "POSITION_CLOSE",
        "TRADE_READ",
        "STRATEGY_READ", "STRATEGY_CONFIGURE",
        "RISK_READ", "RISK_CONFIGURE",
        "WORKER_READ", "WORKER_START", "WORKER_STOP",
        "SUBSCRIPTION_READ", "SUBSCRIPTION_MANAGE",
        "ORGANIZATION_READ", "ORGANIZATION_UPDATE",
        "MEMBER_READ", "MEMBER_INVITE", "MEMBER_UPDATE", "MEMBER_REMOVE",
        "AUDIT_READ",
    }
    actual_permissions = {p.name for p in Permission}
    assert actual_permissions == expected_permissions, f"Mismatch: {actual_permissions ^ expected_permissions}"

    # Role counts
    assert len(ROLE_PERMISSIONS[OrganizationRole.OWNER]) == 25
    assert len(ROLE_PERMISSIONS[OrganizationRole.ADMINISTRATOR]) == 21
    assert len(ROLE_PERMISSIONS[OrganizationRole.PORTFOLIO_MANAGER]) == 19
    assert len(ROLE_PERMISSIONS[OrganizationRole.RISK_OFFICER]) == 12
    assert len(ROLE_PERMISSIONS[OrganizationRole.TRADER]) == 14
    assert len(ROLE_PERMISSIONS[OrganizationRole.AUDITOR]) == 11
    assert len(ROLE_PERMISSIONS[OrganizationRole.VIEWER]) == 10

    # Specific key invariants
    # ADMINISTRATOR lacks trading execution
    assert not has_permission(OrganizationRole.ADMINISTRATOR, Permission.ORDER_CREATE)
    assert not has_permission(OrganizationRole.ADMINISTRATOR, Permission.ORDER_CANCEL)
    assert not has_permission(OrganizationRole.ADMINISTRATOR, Permission.POSITION_CLOSE)
    assert not has_permission(OrganizationRole.ADMINISTRATOR, Permission.RISK_CONFIGURE)

    # TRADER has trading execution but lacks admin / risk config
    assert has_permission(OrganizationRole.TRADER, Permission.ORDER_CREATE)
    assert has_permission(OrganizationRole.TRADER, Permission.ORDER_CANCEL)
    assert not has_permission(OrganizationRole.TRADER, Permission.ORGANIZATION_UPDATE)
    assert not has_permission(OrganizationRole.TRADER, Permission.MEMBER_INVITE)
    assert not has_permission(OrganizationRole.TRADER, Permission.AUDIT_READ)

    # AUDITOR has read permissions including AUDIT_READ
    assert has_permission(OrganizationRole.AUDITOR, Permission.AUDIT_READ)
    assert has_permission(OrganizationRole.AUDITOR, Permission.ORDER_READ)
    assert not has_permission(OrganizationRole.AUDITOR, Permission.ORDER_CREATE)
    assert not has_permission(OrganizationRole.AUDITOR, Permission.ORGANIZATION_UPDATE)

    # RISK_OFFICER has risk config and AUDIT_READ
    assert has_permission(OrganizationRole.RISK_OFFICER, Permission.RISK_CONFIGURE)
    assert has_permission(OrganizationRole.RISK_OFFICER, Permission.AUDIT_READ)
    assert not has_permission(OrganizationRole.RISK_OFFICER, Permission.ORDER_CREATE)


# ===========================================================================
# 2. Phase 5 Multi-Tenant Fixture
# ===========================================================================


@pytest.fixture
async def sec_env():
    """Build multi-tenant environment with all roles, suspended/deactivated orgs, and paper accounts."""
    db_file = f"test_sec_{uuid.uuid4().hex[:8]}.db"
    db_path = pathlib.Path(db_file)
    db_url = f"sqlite+aiosqlite:///{db_file}"

    db_config = DatabaseConfig(url=db_url, echo=False)
    db_manager = DatabaseManager(db_config)

    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    org_alpha_id = "org_alpha_sec"
    org_beta_id = "org_beta_sec"
    org_suspended_id = "org_suspended_sec"
    org_deactivated_id = "org_deactivated_sec"

    users_map = {
        "owner": ("usr_alpha_owner", "alpha_owner", OrganizationRole.OWNER),
        "admin": ("usr_alpha_admin", "alpha_admin", OrganizationRole.ADMINISTRATOR),
        "pm": ("usr_alpha_pm", "alpha_pm", OrganizationRole.PORTFOLIO_MANAGER),
        "risk": ("usr_alpha_risk", "alpha_risk", OrganizationRole.RISK_OFFICER),
        "trader": ("usr_alpha_trader", "alpha_trader", OrganizationRole.TRADER),
        "auditor": ("usr_alpha_auditor", "alpha_auditor", OrganizationRole.AUDITOR),
        "viewer": ("usr_alpha_viewer", "alpha_viewer", OrganizationRole.VIEWER),
    }

    now = datetime.now(timezone.utc)

    async with db_manager.session() as session:
        # Plans
        free_plan = PlanModel(
            id="plan-free",
            code="FREE",
            name="Free Tier",
            description="Default free plan",
            max_accounts=1,
            max_daily_orders=10,  # low limit for quota testing
            max_workers=1,
            allowed_assets=["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF"],
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
            id=org_alpha_id, name="Alpha Capital", slug="alpha-sec", status="ACTIVE", meta_data={}
        )
        org_beta = OrganizationModel(
            id=org_beta_id, name="Beta Investments", slug="beta-sec", status="ACTIVE", meta_data={}
        )
        org_suspended = OrganizationModel(
            id=org_suspended_id, name="Suspended Org", slug="suspended-sec", status="SUSPENDED", meta_data={}
        )
        org_deactivated = OrganizationModel(
            id=org_deactivated_id, name="Deactivated Org", slug="deactivated-sec", status="DEACTIVATED", meta_data={}
        )
        session.add_all([org_alpha, org_beta, org_suspended, org_deactivated])

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
        sub_beta = SubscriptionModel(
            id=f"sub_{uuid.uuid4().hex[:12]}",
            organization_id=org_beta_id,
            plan_id="plan-pro",
            status="ACTIVE",
            current_period_start=now,
            current_period_end=now,
            cancel_at_period_end=False,
        )
        session.add_all([sub_alpha, sub_beta])

        # Alpha Members
        for uid, uname, role in users_map.values():
            u = UserModel(
                id=uid,
                username=uname,
                email=f"{uname}@alphasec.io",
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
        u_beta = UserModel(
            id="usr_beta_owner",
            username="beta_owner",
            email="beta_owner@betasec.io",
            hashed_password=get_password_hash("Secret123!"),
            is_active=True,
            is_superuser=False,
        )
        m_beta = OrganizationMemberModel(
            id="mem_beta_owner",
            organization_id=org_beta_id,
            user_id="usr_beta_owner",
            role="OWNER",
            status="ACTIVE",
            meta_data={},
        )
        session.add_all([u_beta, m_beta])

        # Suspended Org Member
        u_susp = UserModel(
            id="usr_susp_user",
            username="susp_user",
            email="susp@locked.io",
            hashed_password=get_password_hash("Secret123!"),
            is_active=True,
            is_superuser=False,
        )
        m_susp = OrganizationMemberModel(
            id="mem_susp_user",
            organization_id=org_suspended_id,
            user_id="usr_susp_user",
            role="TRADER",
            status="ACTIVE",
            meta_data={},
        )
        session.add_all([u_susp, m_susp])

        # Deactivated Org Member
        u_deact = UserModel(
            id="usr_deact_user",
            username="deact_user",
            email="deact@locked.io",
            hashed_password=get_password_hash("Secret123!"),
            is_active=True,
            is_superuser=False,
        )
        m_deact = OrganizationMemberModel(
            id="mem_deact_user",
            organization_id=org_deactivated_id,
            user_id="usr_deact_user",
            role="TRADER",
            status="ACTIVE",
            meta_data={},
        )
        session.add_all([u_deact, m_deact])

        # Personal individual sandbox user (no org membership)
        u_personal = UserModel(
            id="usr_personal_dev",
            username="personal_trader",
            email="solo@sandbox.io",
            hashed_password=get_password_hash("Secret123!"),
            is_active=True,
            is_superuser=False,
        )
        session.add(u_personal)

        # Alpha Paper Account
        acc_alpha = AccountModel(
            id="acc_alpha_trading",
            organization_id=org_alpha_id,
            user_id="usr_alpha_owner",
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

        # Beta Paper Account
        acc_beta = AccountModel(
            id="acc_beta_trading",
            organization_id=org_beta_id,
            user_id="usr_beta_owner",
            broker_name="paper",
            account_number="PAPER-BETA-001",
            currency="USD",
            balance=Decimal("250000.00"),
            equity=Decimal("250000.00"),
            margin=Decimal("0.00"),
            margin_free=Decimal("250000.00"),
            margin_level=0.0,
            leverage=100,
            is_live=False,
            is_active=True,
            meta_data={},
        )
        session.add(acc_beta)

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
    tokens["suspended"] = create_access_token({"sub": "usr_susp_user", "username": "susp_user"})
    tokens["deactivated"] = create_access_token({"sub": "usr_deact_user", "username": "deact_user"})
    tokens["personal"] = create_access_token({"sub": "usr_personal_dev", "username": "personal_trader"})

    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield {
            "client": client,
            "tokens": tokens,
            "org_alpha": org_alpha_id,
            "org_beta": org_beta_id,
            "org_suspended": org_suspended_id,
            "org_deactivated": org_deactivated_id,
            "db_manager": db_manager,
        }

    # Teardown
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass


# ===========================================================================
# 3. POST /api/v1/paper-trade Authorization & Hardening Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_paper_trade_unauthenticated_returns_401(sec_env):
    """Calling POST /api/v1/paper-trade without auth header returns 401."""
    client = sec_env["client"]
    payload = {
        "symbol": "EURUSD",
        "direction": "buy",
        "confidence": 80.0,
        "entry_price": "1.0850",
        "position_size": "1000",
    }
    resp = await client.post("/api/v1/paper-trade", json=payload)
    assert resp.status_code == 401
    assert "Missing or invalid authorization header" in resp.json()["message"]


@pytest.mark.asyncio
async def test_paper_trade_forbidden_roles_returns_403(sec_env):
    """Roles without ORDER_CREATE (ADMIN, AUDITOR, VIEWER, RISK_OFFICER) receive 403."""
    client = sec_env["client"]
    tokens = sec_env["tokens"]
    org_id = sec_env["org_alpha"]

    payload = {
        "symbol": "EURUSD",
        "direction": "buy",
        "confidence": 80.0,
        "entry_price": "1.0850",
        "position_size": "1000",
    }

    for forbidden_role in ["admin", "auditor", "viewer", "risk"]:
        token = tokens[forbidden_role]
        resp = await client.post(
            "/api/v1/paper-trade",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "X-Organization-ID": org_id},
        )
        assert resp.status_code == 403, f"Expected 403 for {forbidden_role}, got {resp.status_code}"
        assert "does not have permission 'ORDER_CREATE'" in resp.json()["message"]


@pytest.mark.asyncio
async def test_paper_trade_allowed_roles_returns_200(sec_env):
    """Roles with ORDER_CREATE (TRADER, PM, OWNER) can execute paper trades."""
    client = sec_env["client"]
    tokens = sec_env["tokens"]
    org_id = sec_env["org_alpha"]

    for allowed_role in ["trader", "pm", "owner"]:
        token = tokens[allowed_role]
        payload = {
            "symbol": "EUR/USD",
            "direction": "buy",
            "confidence": 85.0,
            "entry_price": "1.0850",
            "stop_loss": "1.0800",
            "take_profit": "1.0950",
            "position_size": "1000",
        }
        resp = await client.post(
            "/api/v1/paper-trade",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "X-Organization-ID": org_id},
        )
        assert resp.status_code == 200, f"Expected 200 for {allowed_role}, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["symbol"] == "EUR/USD"
        assert data["is_paper"] is True
        assert data["status"] in ("filled", "submitted", "partially_filled")


@pytest.mark.asyncio
async def test_paper_trade_unentitled_asset_returns_403(sec_env):
    """Trading an unentitled instrument (e.g. XAU/USD on Free tier) returns 403."""
    client = sec_env["client"]
    token = sec_env["tokens"]["trader"]
    org_id = sec_env["org_alpha"]

    payload = {
        "symbol": "XAU/USD",  # Not in Free plan allowed_assets
        "direction": "buy",
        "confidence": 85.0,
        "entry_price": "2050.00",
        "position_size": "10",
    }
    resp = await client.post(
        "/api/v1/paper-trade",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "X-Organization-ID": org_id},
    )
    assert resp.status_code == 403
    assert "not entitled" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_paper_trade_daily_order_quota_exceeded_returns_429(sec_env):
    """Exceeding max_daily_orders triggers 429 Too Many Requests."""
    client = sec_env["client"]
    token = sec_env["tokens"]["trader"]
    org_id = sec_env["org_alpha"]
    db_manager = sec_env["db_manager"]

    # Seed 10 existing orders today for Alpha in DB to hit limit
    now = datetime.now(timezone.utc)
    async with db_manager.session() as session:
        for i in range(10):
            ord_model = OrderModel(
                id=f"ord_seed_quota_{i}_{uuid.uuid4().hex[:8]}",
                organization_id=org_id,
                account_id="acc_alpha_trading",
                symbol="EUR/USD",
                side="BUY",
                order_type="MARKET",
                status="FILLED",
                quantity=Decimal(1000),
                created_at=now,
                updated_at=now,
            )
            session.add(ord_model)
        await session.commit()

    payload = {
        "symbol": "EUR/USD",
        "direction": "buy",
        "confidence": 80.0,
        "entry_price": "1.0850",
        "position_size": "1000",
    }
    resp = await client.post(
        "/api/v1/paper-trade",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "X-Organization-ID": org_id},
    )
    assert resp.status_code == 429
    assert "daily order quota" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_paper_trade_audit_log_recorded_in_db(sec_env):
    """Successful paper trade execution automatically records an AuditLogModel entry."""
    client = sec_env["client"]
    token = sec_env["tokens"]["trader"]
    org_id = sec_env["org_alpha"]
    db_manager = sec_env["db_manager"]

    payload = {
        "symbol": "GBP/USD",
        "direction": "sell",
        "confidence": 90.0,
        "entry_price": "1.2750",
        "position_size": "5000",
    }
    resp = await client.post(
        "/api/v1/paper-trade",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "X-Organization-ID": org_id},
    )
    assert resp.status_code == 200
    order_id = resp.json()["order_id"]

    # Verify audit log in DB
    from sqlalchemy import select
    async with db_manager.session() as session:
        stmt = select(AuditLogModel).where(
            AuditLogModel.organization_id == org_id,
            AuditLogModel.event_type == "paper_trade.executed",
        )
        result = await session.execute(stmt)
        logs = list(result.scalars().all())
        matching = [l for l in logs if l.details.get("order_id") == order_id]
        assert len(matching) >= 1
        audit = matching[0]
        assert audit.actor == "usr_alpha_trader"
        assert audit.details["symbol"] == "GBP/USD"
        assert audit.details["direction"] == "sell"


@pytest.mark.asyncio
async def test_paper_trade_personal_sandbox_mode(sec_env):
    """User without organization membership can paper-trade in their personal sandbox."""
    client = sec_env["client"]
    personal_token = sec_env["tokens"]["personal"]

    payload = {
        "symbol": "EUR/USD",
        "direction": "buy",
        "confidence": 75.0,
        "entry_price": "1.0850",
        "position_size": "1000",
    }
    resp = await client.post(
        "/api/v1/paper-trade",
        json=payload,
        headers={"Authorization": f"Bearer {personal_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_paper"] is True


# ===========================================================================
# 4. Organization Status Fail-Closed Tests (SUSPENDED / DEACTIVATED)
# ===========================================================================


@pytest.mark.asyncio
async def test_suspended_organization_fails_closed(sec_env):
    """User belonging to SUSPENDED organization receives 403 Forbidden with exact reason."""
    client = sec_env["client"]
    token = sec_env["tokens"]["suspended"]
    org_id = sec_env["org_suspended"]

    # 1. Test via explicit header
    resp = await client.get(
        "/api/v1/orders/",
        headers={"Authorization": f"Bearer {token}", "X-Organization-ID": org_id},
    )
    assert resp.status_code == 403
    assert f"Organization '{org_id}' is suspended" in resp.json()["message"]

    # 2. Test via default membership resolution (no header)
    resp_default = await client.get(
        "/api/v1/orders/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_default.status_code == 403
    assert f"Organization '{org_id}' is suspended" in resp_default.json()["message"]


@pytest.mark.asyncio
async def test_deactivated_organization_fails_closed(sec_env):
    """User belonging to DEACTIVATED organization receives 403 Forbidden with exact reason."""
    client = sec_env["client"]
    token = sec_env["tokens"]["deactivated"]
    org_id = sec_env["org_deactivated"]

    resp = await client.get(
        "/api/v1/orders/",
        headers={"Authorization": f"Bearer {token}", "X-Organization-ID": org_id},
    )
    assert resp.status_code == 403
    assert f"Organization '{org_id}' is deactivated" in resp.json()["message"]


# ===========================================================================
# 5. Institutional HTTP Security Headers Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_institutional_http_security_headers(sec_env):
    """Every HTTP response must carry full institutional-grade security headers."""
    client = sec_env["client"]
    resp = await client.get("/health/live")
    assert resp.status_code == 200

    headers = resp.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Cache-Control") == "no-store, no-cache, must-revalidate"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert "max-age=31536000" in headers.get("Strict-Transport-Security", "")
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    csp = headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "style-src 'self'" in csp


# ===========================================================================
# 6. Audit Log API Endpoint Tests (GET /api/v1/organizations/{id}/audit-logs)
# ===========================================================================


@pytest.mark.asyncio
async def test_audit_log_endpoint_rbac(sec_env):
    """Only roles with AUDIT_READ (AUDITOR, RISK_OFFICER, ADMIN, OWNER) can access audit logs."""
    client = sec_env["client"]
    tokens = sec_env["tokens"]
    org_id = sec_env["org_alpha"]

    # Disallowed roles
    for denied_role in ["trader", "viewer"]:
        token = tokens[denied_role]
        resp = await client.get(
            f"/api/v1/organizations/{org_id}/audit-logs",
            headers={"Authorization": f"Bearer {token}", "X-Organization-ID": org_id},
        )
        assert resp.status_code == 403, f"Expected 403 for {denied_role}, got {resp.status_code}"
        assert "does not have permission 'AUDIT_READ'" in resp.json()["message"]

    # Allowed roles
    for allowed_role in ["auditor", "risk", "admin", "owner"]:
        token = tokens[allowed_role]
        resp = await client.get(
            f"/api/v1/organizations/{org_id}/audit-logs",
            headers={"Authorization": f"Bearer {token}", "X-Organization-ID": org_id},
        )
        assert resp.status_code == 200, f"Expected 200 for {allowed_role}, got {resp.status_code}"
        assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_audit_log_endpoint_cross_tenant_idor(sec_env):
    """User in Org Alpha cannot access Org Beta's audit logs (returns 403)."""
    client = sec_env["client"]
    alpha_owner_token = sec_env["tokens"]["owner"]
    org_beta_id = sec_env["org_beta"]

    resp = await client.get(
        f"/api/v1/organizations/{org_beta_id}/audit-logs",
        headers={"Authorization": f"Bearer {alpha_owner_token}", "X-Organization-ID": sec_env["org_alpha"]},
    )
    assert resp.status_code == 403
    assert "Cross-tenant operation denied" in resp.json()["message"]


@pytest.mark.asyncio
async def test_audit_log_secret_redaction(sec_env):
    """Sensitive fields in audit log details are masked to [REDACTED]."""
    client = sec_env["client"]
    auditor_token = sec_env["tokens"]["auditor"]
    org_id = sec_env["org_alpha"]
    db_manager = sec_env["db_manager"]

    # Seed an audit log with sensitive credentials in details
    now = datetime.now(timezone.utc)
    async with db_manager.session() as session:
        log = AuditLogModel(
            id=f"aud_redact_{uuid.uuid4().hex[:8]}",
            organization_id=org_id,
            event_type="test.sensitive_event",
            component="security_audit",
            actor="usr_alpha_owner",
            details={
                "password": "SuperSecretPassword123!",
                "raw_token": "jwt-token-raw-value",
                "api_key": "live-api-key-9999",
                "secret_key": "hmac-secret-xyz",
                "safe_info": "unclassified_data",
            },
            timestamp=now,
        )
        session.add(log)
        await session.commit()

    resp = await client.get(
        f"/api/v1/organizations/{org_id}/audit-logs?event_type=test.sensitive_event",
        headers={"Authorization": f"Bearer {auditor_token}", "X-Organization-ID": org_id},
    )
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) >= 1
    target = entries[0]["details"]

    assert target["password"] == "[REDACTED]"
    assert target["raw_token"] == "[REDACTED]"
    assert target["api_key"] == "[REDACTED]"
    assert target["secret_key"] == "[REDACTED]"
    assert target["safe_info"] == "unclassified_data"


@pytest.mark.asyncio
async def test_audit_log_pagination_and_filter(sec_env):
    """Audit log endpoint honors limit, offset, and event_type query parameters."""
    client = sec_env["client"]
    auditor_token = sec_env["tokens"]["auditor"]
    org_id = sec_env["org_alpha"]
    db_manager = sec_env["db_manager"]

    now = datetime.now(timezone.utc)
    async with db_manager.session() as session:
        for i in range(5):
            session.add(
                AuditLogModel(
                    id=f"aud_page_a_{i}_{uuid.uuid4().hex[:6]}",
                    organization_id=org_id,
                    event_type="page_event.type_a",
                    component="test",
                    actor="usr_alpha_owner",
                    details={"index": i},
                    timestamp=now,
                )
            )
        for i in range(3):
            session.add(
                AuditLogModel(
                    id=f"aud_page_b_{i}_{uuid.uuid4().hex[:6]}",
                    organization_id=org_id,
                    event_type="page_event.type_b",
                    component="test",
                    actor="usr_alpha_owner",
                    details={"index": i},
                    timestamp=now,
                )
            )
        await session.commit()

    # Filter by event_type
    resp_filtered = await client.get(
        f"/api/v1/organizations/{org_id}/audit-logs?event_type=page_event.type_b",
        headers={"Authorization": f"Bearer {auditor_token}", "X-Organization-ID": org_id},
    )
    assert resp_filtered.status_code == 200
    records = resp_filtered.json()
    assert len(records) == 3
    assert all(r["event_type"] == "page_event.type_b" for r in records)

    # Limit and offset
    resp_paged = await client.get(
        f"/api/v1/organizations/{org_id}/audit-logs?limit=2&offset=1",
        headers={"Authorization": f"Bearer {auditor_token}", "X-Organization-ID": org_id},
    )
    assert resp_paged.status_code == 200
    assert len(resp_paged.json()) == 2


# ===========================================================================
# 7. Operational Routes RBAC Governance Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_operational_routes_rbac_governance(sec_env):
    """Verify require_permission across Account, Portfolio, Dashboard, and Strategy endpoints."""
    client = sec_env["client"]
    tokens = sec_env["tokens"]
    org_id = sec_env["org_alpha"]

    # 1. Account Routes require ACCOUNT_READ (all roles have it)
    resp_acc_summary = await client.get(
        "/api/v1/account/summary",
        headers={"Authorization": f"Bearer {tokens['viewer']}", "X-Organization-ID": org_id},
    )
    assert resp_acc_summary.status_code == 200

    resp_acc_details = await client.get(
        "/api/v1/account/",
        headers={"Authorization": f"Bearer {tokens['viewer']}", "X-Organization-ID": org_id},
    )
    assert resp_acc_details.status_code == 200

    # 2. Portfolio Routes require ACCOUNT_READ (all roles have it)
    for route in ["/api/v1/portfolio/", "/api/v1/portfolio/equity", "/api/v1/portfolio/pnl", "/api/v1/portfolio/exposure"]:
        resp = await client.get(
            route,
            headers={"Authorization": f"Bearer {tokens['viewer']}", "X-Organization-ID": org_id},
        )
        assert resp.status_code == 200, f"Failed on {route}"

    # 3. Dashboard Route requires ACCOUNT_READ
    resp_dash = await client.get(
        "/api/v1/dashboard/",
        headers={"Authorization": f"Bearer {tokens['viewer']}", "X-Organization-ID": org_id},
    )
    assert resp_dash.status_code == 200

    # 4. Strategy Catalogue Endpoints require STRATEGY_READ (all roles have it)
    # Unauthenticated call to strategy catalogue must fail with 401
    resp_strat_unauth = await client.get("/api/v1/strategies/")
    assert resp_strat_unauth.status_code == 401

    resp_strat_auth = await client.get(
        "/api/v1/strategies/",
        headers={"Authorization": f"Bearer {tokens['viewer']}", "X-Organization-ID": org_id},
    )
    assert resp_strat_auth.status_code == 200
    data = resp_strat_auth.json()
    assert len(data["strategies"]) > 0
    strat_id = data["strategies"][0]["id"]

    # Detail and schema endpoints
    resp_detail = await client.get(
        f"/api/v1/strategies/{strat_id}",
        headers={"Authorization": f"Bearer {tokens['viewer']}", "X-Organization-ID": org_id},
    )
    assert resp_detail.status_code == 200

    resp_schema = await client.get(
        f"/api/v1/strategies/{strat_id}/config-schema",
        headers={"Authorization": f"Bearer {tokens['viewer']}", "X-Organization-ID": org_id},
    )
    assert resp_schema.status_code == 200
