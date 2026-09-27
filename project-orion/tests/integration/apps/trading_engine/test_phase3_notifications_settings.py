"""Integration tests for Phase 3: Notification Center & User Settings.

Verifies:
1. Notification Center:
   - GET /api/v1/notifications/unread-count: accurate unread count.
   - GET /api/v1/notifications: paginated notifications with severity, channel, status.
   - GET /api/v1/notifications?unread_only=true: unread filtering.
   - POST /api/v1/notifications/{id}/read: marks single notification as read.
   - POST /api/v1/notifications/read-all: marks all user/tenant notifications read.
   - Strict tenant & user isolation: prevents cross-user visibility and mutations.
2. User Profile:
   - GET /api/v1/users/me: retrieves authenticated profile and preferences.
   - PATCH /api/v1/users/me: updates full name and timezone, writes audit log.
3. Password Change & Session Revocation:
   - POST /api/v1/auth/change-password:
     - Enforces current password verification (HTTP 400).
     - Enforces password confirmation match (HTTP 422).
     - Enforces institutional password policy (HTTP 422).
     - Successfully updates password and sets password_changed_at (HTTP 200).
     - Revokes prior JWT sessions issued before password_changed_at (HTTP 401).
     - Writes AUTH_PASSWORD_CHANGED audit record.
4. Notification Preferences:
   - GET /api/v1/users/me/preferences: retrieves alert settings.
   - PUT /api/v1/users/me/preferences: updates preferences with persistence and audit logging.
"""

from __future__ import annotations

import pathlib
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest import mock
from unittest.mock import AsyncMock

import pytest
from apps.trading_engine.src.config import AppSettings
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.services.auth import get_password_hash
from apps.trading_engine.src.services.notification_service import NotificationService
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
    UserModel,
)
from libraries.infrastructure.persistence.models.organization import (
    OrganizationMemberModel,
    OrganizationModel,
)


@pytest.fixture
async def phase3_env():
    """Set up an isolated database, mock Redis, paper adapter, and app for testing."""
    db_file = f"test_phase3_{uuid.uuid4().hex[:8]}.db"
    db_path = pathlib.Path(db_file)
    db_url = f"sqlite+aiosqlite:///{db_file}"

    db_config = DatabaseConfig(url=db_url, echo=False)
    db_manager = DatabaseManager(db_config)

    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    org_a_id = "org_notif_alpha"
    org_b_id = "org_notif_beta"

    user_a_id = "usr_trader_alpha"
    user_b_id = "usr_trader_beta"

    pass_a = "AlphaPass2026!"
    pass_b = "BetaPass2026!"

    async with db_manager.session() as session:
        org_a = OrganizationModel(
            id=org_a_id,
            name="Alpha Capital",
            slug="alpha-capital",
            status="ACTIVE",
            meta_data={},
        )
        org_b = OrganizationModel(
            id=org_b_id,
            name="Beta Capital",
            slug="beta-capital",
            status="ACTIVE",
            meta_data={},
        )
        session.add_all([org_a, org_b])

        user_a = UserModel(
            id=user_a_id,
            username="trader_alpha",
            email="alpha@institutional.test",
            hashed_password=get_password_hash(pass_a),
            full_name="Trader Alpha",
            is_active=True,
            is_superuser=False,
            email_verified=True,
            meta_data={"timezone": "UTC"},
        )
        user_b = UserModel(
            id=user_b_id,
            username="trader_beta",
            email="beta@institutional.test",
            hashed_password=get_password_hash(pass_b),
            full_name="Trader Beta",
            is_active=True,
            is_superuser=False,
            email_verified=False,
            meta_data={"timezone": "Europe/London"},
        )
        session.add_all([user_a, user_b])

        member_a = OrganizationMemberModel(
            id="mem_alpha_01",
            organization_id=org_a_id,
            user_id=user_a_id,
            role="OWNER",
            status="ACTIVE",
            meta_data={},
        )
        member_b = OrganizationMemberModel(
            id="mem_beta_01",
            organization_id=org_b_id,
            user_id=user_b_id,
            role="OWNER",
            status="ACTIVE",
            meta_data={},
        )
        session.add_all([member_a, member_b])

        acc_a = AccountModel(
            id="acc_alpha_01",
            broker_name="paper",
            account_number="ACC-P3-ALPHA",
            user_id=user_a_id,
            organization_id=org_a_id,
            currency="USD",
            balance=Decimal("100000.00"),
            equity=Decimal("100000.00"),
            margin=Decimal("0.00"),
            margin_free=Decimal("100000.00"),
            margin_level=0.0,
            is_active=True,
            is_live=False,
            leverage=100,
            meta_data={},
        )
        acc_b = AccountModel(
            id="acc_beta_01",
            broker_name="paper",
            account_number="ACC-P3-BETA",
            user_id=user_b_id,
            organization_id=org_b_id,
            currency="USD",
            balance=Decimal("100000.00"),
            equity=Decimal("100000.00"),
            margin=Decimal("0.00"),
            margin_free=Decimal("100000.00"),
            margin_level=0.0,
            is_active=True,
            is_live=False,
            leverage=100,
            meta_data={},
        )
        session.add_all([acc_a, acc_b])
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
    mock_redis.health_check = AsyncMock(return_value=True)
    mock_redis.connect = AsyncMock()
    mock_redis.disconnect = AsyncMock()

    paper_config = PaperExecutionConfig(
        broker_name="paper",
        is_paper=True,
        balance=Decimal("100000.00"),
    )
    paper_adapter = PaperExecutionAdapter(config=paper_config)
    await paper_adapter.connect()

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
            "org_a_id": org_a_id,
            "org_b_id": org_b_id,
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
            "pass_a": pass_a,
            "pass_b": pass_b,
        }

    await paper_adapter.disconnect()
    await db_manager.close()
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass


async def _login(client: AsyncClient, username: str, password: str) -> dict[str, str]:
    """Helper to authenticate and return auth headers."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_notifications_crud_and_unread_count(phase3_env):
    """Test notification listing, unread count, single read, and batch read-all."""
    client: AsyncClient = phase3_env["client"]
    db_manager: DatabaseManager = phase3_env["db_manager"]
    user_a_id: str = phase3_env["user_a_id"]
    org_a_id: str = phase3_env["org_a_id"]

    headers_a = await _login(client, "trader_alpha", phase3_env["pass_a"])

    # 1. Zero notifications -> unread count = 0
    resp = await client.get("/api/v1/notifications/unread-count", headers=headers_a)
    assert resp.status_code == 200
    assert resp.json()["unread_count"] == 0

    # 2. Seed 3 notifications for User A
    async with db_manager.session() as session:
        svc = NotificationService(session=session, user_id=user_a_id, organization_id=org_a_id)
        notif1 = await svc.create_notification(
            notification_type="ORDER_FILLED",
            title="Order Filled: BUY EUR/USD",
            body="Executed 10,000 units at 1.08500",
            severity="info",
        )
        notif2 = await svc.create_notification(
            notification_type="RISK_BREACH",
            title="Margin Warning: 75% Used",
            body="Margin utilization exceeds 70% soft threshold",
            severity="warning",
        )
        notif3 = await svc.create_notification(
            notification_type="SECURITY_ALERT",
            title="Login from New IP",
            body="New session detected",
            severity="critical",
        )
        await session.commit()
        notif1_id = notif1.id
        notif2_id = notif2.id

    # 3. Verify unread count = 3
    resp = await client.get("/api/v1/notifications/unread-count", headers=headers_a)
    assert resp.status_code == 200
    assert resp.json()["unread_count"] == 3

    # 4. List notifications
    resp = await client.get("/api/v1/notifications/", headers=headers_a)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert data["items"][0]["status"] == "unread"
    assert data["items"][0]["is_read"] is False

    # 5. Mark single notification as read (notif1)
    resp = await client.post(f"/api/v1/notifications/{notif1_id}/read", headers=headers_a)
    assert resp.status_code == 200
    updated_notif = resp.json()
    assert updated_notif["id"] == notif1_id
    assert updated_notif["status"] == "read"
    assert updated_notif["is_read"] is True
    assert updated_notif["read_at"] is not None

    # 6. Verify unread count reduced to 2
    resp = await client.get("/api/v1/notifications/unread-count", headers=headers_a)
    assert resp.status_code == 200
    assert resp.json()["unread_count"] == 2

    # 7. Test unread_only filter
    resp = await client.get("/api/v1/notifications/?unread_only=true", headers=headers_a)
    assert resp.status_code == 200
    unread_data = resp.json()
    assert unread_data["total"] == 2
    for item in unread_data["items"]:
        assert item["is_read"] is False

    # 8. Mark all read
    resp = await client.post("/api/v1/notifications/read-all", headers=headers_a)
    assert resp.status_code == 200
    assert resp.json()["marked_count"] == 2

    # 9. Verify unread count is now 0
    resp = await client.get("/api/v1/notifications/unread-count", headers=headers_a)
    assert resp.status_code == 200
    assert resp.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_notifications_tenant_and_user_isolation(phase3_env):
    """Test that notifications are strictly scoped and inaccessible across users/tenants."""
    client: AsyncClient = phase3_env["client"]
    db_manager: DatabaseManager = phase3_env["db_manager"]
    user_b_id: str = phase3_env["user_b_id"]
    org_b_id: str = phase3_env["org_b_id"]

    headers_a = await _login(client, "trader_alpha", phase3_env["pass_a"])
    headers_b = await _login(client, "trader_beta", phase3_env["pass_b"])

    # Seed notification specifically for User B
    async with db_manager.session() as session:
        svc = NotificationService(session=session, user_id=user_b_id, organization_id=org_b_id)
        notif_b = await svc.create_notification(
            notification_type="CONFIDENTIAL_TRADE",
            title="User B Confidential Alert",
            body="Private order fill for Beta Capital",
            severity="info",
        )
        await session.commit()
        notif_b_id = notif_b.id

    # User A lists notifications -> should be empty
    resp_a = await client.get("/api/v1/notifications/", headers=headers_a)
    assert resp_a.status_code == 200
    assert resp_a.json()["total"] == 0

    # User B lists notifications -> sees 1 item
    resp_b = await client.get("/api/v1/notifications/", headers=headers_b)
    assert resp_b.status_code == 200
    assert resp_b.json()["total"] == 1
    assert resp_b.json()["items"][0]["id"] == notif_b_id

    # User A attempts to mark User B's notification read -> 403 Forbidden
    resp_hack = await client.post(f"/api/v1/notifications/{notif_b_id}/read", headers=headers_a)
    assert resp_hack.status_code == 403
    assert "Forbidden" in resp_hack.json()["detail"]


@pytest.mark.asyncio
async def test_get_and_patch_user_profile(phase3_env):
    """Test retrieving and updating personal user profile."""
    client: AsyncClient = phase3_env["client"]
    db_manager: DatabaseManager = phase3_env["db_manager"]
    headers_a = await _login(client, "trader_alpha", phase3_env["pass_a"])

    # GET /api/v1/users/me
    resp = await client.get("/api/v1/users/me", headers=headers_a)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "trader_alpha"
    assert data["email"] == "alpha@institutional.test"
    assert data["email_verified"] is True
    assert data["full_name"] == "Trader Alpha"
    assert data["timezone"] == "UTC"

    # PATCH /api/v1/users/me
    patch_req = {
        "full_name": "Alexander Alpha, CFA",
        "timezone": "America/New_York",
    }
    resp = await client.patch("/api/v1/users/me", json=patch_req, headers=headers_a)
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["full_name"] == "Alexander Alpha, CFA"
    assert updated["timezone"] == "America/New_York"

    # Verify audit log entry
    async with db_manager.session() as session:
        res = await session.execute(
            select(AuditLogModel).where(AuditLogModel.event_type == "USER_PROFILE_UPDATED")
        )
        audit = res.scalar_one_or_none()
        assert audit is not None
        assert audit.actor == phase3_env["user_a_id"]
        assert "full_name" in audit.details["updated_fields"]


@pytest.mark.asyncio
async def test_change_password_and_token_revocation(phase3_env):
    """Test password update validation, policy enforcement, and fail-closed session revocation."""
    client: AsyncClient = phase3_env["client"]
    db_manager: DatabaseManager = phase3_env["db_manager"]
    old_pass = phase3_env["pass_a"]
    headers_a = await _login(client, "trader_alpha", old_pass)

    # 1. Incorrect current password -> 400
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "WrongPassword123!",
            "new_password": "NewSecurePass2026!",
            "confirm_password": "NewSecurePass2026!",
        },
        headers=headers_a,
    )
    assert resp.status_code == 400
    assert "Current password is incorrect" in resp.json()["detail"]

    # 2. Confirmation mismatch -> 422
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": old_pass,
            "new_password": "NewSecurePass2026!",
            "confirm_password": "DifferentPass2026!",
        },
        headers=headers_a,
    )
    assert resp.status_code == 422
    assert "New passwords do not match" in resp.json()["detail"]

    # 3. Weak password policy violation (no digit or symbol) -> 422
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": old_pass,
            "new_password": "justlettersonly",
            "confirm_password": "justlettersonly",
        },
        headers=headers_a,
    )
    assert resp.status_code == 422
    assert "digit or symbol" in resp.json()["detail"].lower()

    # 4. Successful password update -> 200 (wait 2s so iat < password_changed_at - 1)
    import asyncio
    await asyncio.sleep(2.1)
    new_pass = "BrandNewSecureP@ss2026!"
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": old_pass,
            "new_password": new_pass,
            "confirm_password": new_pass,
        },
        headers=headers_a,
    )
    assert resp.status_code == 200
    assert "Password has been successfully updated" in resp.json()["message"]

    # 5. Verify audit log entry
    async with db_manager.session() as session:
        res = await session.execute(
            select(AuditLogModel).where(AuditLogModel.event_type == "AUTH_PASSWORD_CHANGED")
        )
        audit = res.scalar_one_or_none()
        assert audit is not None
        assert audit.actor == phase3_env["user_a_id"]

    # 6. Verify old token is now REVOKED on subsequent requests -> 401
    resp_revoked = await client.get("/api/v1/users/me", headers=headers_a)
    assert resp_revoked.status_code == 401
    assert "Session revoked" in resp_revoked.json()["detail"]

    # 7. Login with old password fails -> 401
    resp_old_login = await client.post(
        "/api/v1/auth/login",
        json={"username": "trader_alpha", "password": old_pass},
    )
    assert resp_old_login.status_code == 401

    # 8. Login with new password succeeds -> 200
    resp_new_login = await client.post(
        "/api/v1/auth/login",
        json={"username": "trader_alpha", "password": new_pass},
    )
    assert resp_new_login.status_code == 200
    new_token = resp_new_login.json()["access_token"]

    # 9. Verify new token works on protected endpoints
    resp_protected = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {new_token}"}
    )
    assert resp_protected.status_code == 200
    assert resp_protected.json()["username"] == "trader_alpha"


@pytest.mark.asyncio
async def test_get_and_update_notification_preferences(phase3_env):
    """Test retrieving and updating notification delivery preferences."""
    client: AsyncClient = phase3_env["client"]
    db_manager: DatabaseManager = phase3_env["db_manager"]
    headers_b = await _login(client, "trader_beta", phase3_env["pass_b"])

    # 1. GET /api/v1/users/me/preferences -> defaults are all True
    resp = await client.get("/api/v1/users/me/preferences", headers=headers_b)
    assert resp.status_code == 200
    prefs = resp.json()
    assert prefs["trade_events"] is True
    assert prefs["risk_alerts"] is True
    assert prefs["strategy_events"] is True
    assert prefs["security_alerts"] is True

    # 2. PUT /api/v1/users/me/preferences -> toggle trade_events to False
    update_req = {
        "trade_events": False,
        "risk_alerts": True,
        "strategy_events": False,
        "security_alerts": True,
    }
    resp = await client.put(
        "/api/v1/users/me/preferences", json=update_req, headers=headers_b
    )
    assert resp.status_code == 200
    updated_prefs = resp.json()
    assert updated_prefs["trade_events"] is False
    assert updated_prefs["strategy_events"] is False
    assert updated_prefs["risk_alerts"] is True
    assert updated_prefs["security_alerts"] is True

    # 3. Verify persistence on subsequent GET
    resp = await client.get("/api/v1/users/me/preferences", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json()["trade_events"] is False

    # 4. Verify audit log entry
    async with db_manager.session() as session:
        res = await session.execute(
            select(AuditLogModel).where(
                AuditLogModel.event_type == "NOTIFICATION_PREFERENCES_UPDATED"
            )
        )
        audit = res.scalar_one_or_none()
        assert audit is not None
        assert audit.actor == phase3_env["user_b_id"]
        assert audit.details["preferences"]["trade_events"] is False
