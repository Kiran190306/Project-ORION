"""Unit and contract tests for Broker Sandbox REST API endpoints and RBAC enforcement (EPIC-026)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.trading_engine.src import dependencies
from apps.trading_engine.src.dependencies import TenantContext
from apps.trading_engine.src.main import create_app
from libraries.domain.organization.permissions import Permission
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models.organization import (
    OrganizationMemberModel,
    OrganizationModel,
)
from libraries.infrastructure.persistence.models.user import UserModel


@pytest.fixture
async def async_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        # Create organizations
        org_a = OrganizationModel(
            id="org-alpha",
            name="Alpha Fund",
            slug="alpha-fund",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        org_b = OrganizationModel(
            id="org-beta",
            name="Beta Hedge",
            slug="beta-hedge",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add_all([org_a, org_b])

        # Create users
        user_owner = UserModel(id="usr-owner", username="owner", email="owner@alpha.com", hashed_password="pw", is_active=True)
        user_trader = UserModel(id="usr-trader", username="trader", email="trader@alpha.com", hashed_password="pw", is_active=True)
        user_viewer = UserModel(id="usr-viewer", username="viewer", email="viewer@alpha.com", hashed_password="pw", is_active=True)
        user_beta = UserModel(id="usr-beta", username="beta_trader", email="trader@beta.com", hashed_password="pw", is_active=True)
        session.add_all([user_owner, user_trader, user_viewer, user_beta])

        # Memberships
        mem_owner = OrganizationMemberModel(id="mem-1", organization_id="org-alpha", user_id="usr-owner", role="OWNER", status="ACTIVE")
        mem_trader = OrganizationMemberModel(id="mem-2", organization_id="org-alpha", user_id="usr-trader", role="TRADER", status="ACTIVE")
        mem_viewer = OrganizationMemberModel(id="mem-3", organization_id="org-alpha", user_id="usr-viewer", role="VIEWER", status="ACTIVE")
        mem_beta = OrganizationMemberModel(id="mem-4", organization_id="org-beta", user_id="usr-beta", role="OWNER", status="ACTIVE")
        session.add_all([mem_owner, mem_trader, mem_viewer, mem_beta])

        await session.commit()
        yield session

    await engine.dispose()


def make_client(session: AsyncSession, user_id: str, org_id: str, role: str) -> AsyncClient:
    app = create_app()
    app.dependency_overrides[dependencies.get_db_session] = lambda: session
    app.dependency_overrides[dependencies.get_tenant_context] = lambda: TenantContext(
        user_id=user_id,
        organization_id=org_id,
        role=role,
        is_superuser=False,
    )
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_list_providers_viewer_allowed(async_session: AsyncSession) -> None:
    """VIEWER can list approved providers (requires BROKER_READ)."""
    async with make_client(async_session, "usr-viewer", "org-alpha", "VIEWER") as client:
        resp = await client.get("/api/v1/broker-sandbox/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        provider_ids = [p["provider"] for p in data]
        assert "MOCK" in provider_ids
        assert "OANDA_PRACTICE" in provider_ids


@pytest.mark.asyncio
async def test_create_account_rbac(async_session: AsyncSession) -> None:
    """Only OWNER/ADMIN can connect/create sandbox account (requires BROKER_SANDBOX_CONNECT)."""
    payload = {
        "name": "Alpha Mock Sandbox",
        "provider": "MOCK",
        "environment": "SANDBOX",
        "account_id_external": "alpha-mock-01",
        "credentials": {"api_key": "secret-test-token-12345"},
    }

    # VIEWER cannot create account
    async with make_client(async_session, "usr-viewer", "org-alpha", "VIEWER") as client:
        resp = await client.post("/api/v1/broker-sandbox/accounts", json=payload)
        assert resp.status_code == 403

    # TRADER cannot create account (separation of duties)
    async with make_client(async_session, "usr-trader", "org-alpha", "TRADER") as client:
        resp = await client.post("/api/v1/broker-sandbox/accounts", json=payload)
        assert resp.status_code == 403

    # OWNER can create account
    async with make_client(async_session, "usr-owner", "org-alpha", "OWNER") as client:
        resp = await client.post("/api/v1/broker-sandbox/accounts", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"].startswith("bsa_")
        assert data["name"] == "Alpha Mock Sandbox"
        assert data["provider"] == "MOCK"
        assert data["status"] == "DISCONNECTED"
        # Credentials must be masked!
        assert data["credentials_masked"]["api_key"] == "***"


@pytest.mark.asyncio
async def test_live_environment_rejected_fail_closed(async_session: AsyncSession) -> None:
    """LIVE environment requests fail closed immediately."""
    payload = {
        "name": "Forbidden Live Account",
        "provider": "MOCK",
        "environment": "LIVE",
        "account_id_external": "live-001",
    }
    async with make_client(async_session, "usr-owner", "org-alpha", "OWNER") as client:
        resp = await client.post("/api/v1/broker-sandbox/accounts", json=payload)
        assert resp.status_code in (400, 422)
        assert "LIVE environment is strictly prohibited" in resp.text


@pytest.mark.asyncio
async def test_account_lifecycle_and_cross_tenant_idor(async_session: AsyncSession) -> None:
    """Full lifecycle: create, connect, disconnect, cross-tenant isolation (IDOR -> 404)."""
    # 1. Create account as Org Alpha OWNER
    account_id = ""
    async with make_client(async_session, "usr-owner", "org-alpha", "OWNER") as client:
        resp = await client.post(
            "/api/v1/broker-sandbox/accounts",
            json={
                "name": "Alpha Testing Connection",
                "provider": "MOCK",
                "environment": "SANDBOX",
                "account_id_external": "alpha-conn-01",
            },
        )
        assert resp.status_code == 201
        account_id = resp.json()["id"]

        # 2. Connect account
        conn_resp = await client.post(f"/api/v1/broker-sandbox/accounts/{account_id}/connect")
        assert conn_resp.status_code == 200
        conn_data = conn_resp.json()
        assert conn_data["connected"] is True
        assert conn_data["status"] == "CONNECTED"
        assert conn_data["balance"] is not None

        # 3. Disconnect account
        disc_resp = await client.post(f"/api/v1/broker-sandbox/accounts/{account_id}/disconnect")
        assert disc_resp.status_code == 200
        assert disc_resp.json()["status"] == "DISCONNECTED"

    # 4. Cross-Tenant IDOR: Org Beta OWNER tries to access Org Alpha's account
    async with make_client(async_session, "usr-beta", "org-beta", "OWNER") as beta_client:
        # GET account -> 404
        get_resp = await beta_client.get(f"/api/v1/broker-sandbox/accounts/{account_id}")
        assert get_resp.status_code == 404

        # CONNECT account -> 404
        post_conn = await beta_client.post(f"/api/v1/broker-sandbox/accounts/{account_id}/connect")
        assert post_conn.status_code == 404

        # ORDER on account -> 404
        order_resp = await beta_client.post(
            f"/api/v1/broker-sandbox/accounts/{account_id}/orders",
            json={"symbol": "EUR/USD", "side": "BUY", "quantity": 1000},
        )
        assert order_resp.status_code == 404


@pytest.mark.asyncio
async def test_order_execution_and_positions_flow(async_session: AsyncSession) -> None:
    """Submit sandbox order through pipeline, verify response and positions endpoint."""
    account_id = ""
    # 1. Setup connected account
    async with make_client(async_session, "usr-owner", "org-alpha", "OWNER") as owner_client:
        resp = await owner_client.post(
            "/api/v1/broker-sandbox/accounts",
            json={
                "name": "Trading Flow Account",
                "provider": "MOCK",
                "environment": "SANDBOX",
                "account_id_external": "trade-flow-01",
            },
        )
        assert resp.status_code == 201
        account_id = resp.json()["id"]
        await owner_client.post(f"/api/v1/broker-sandbox/accounts/{account_id}/connect")

    # 2. VIEWER cannot execute orders (403)
    async with make_client(async_session, "usr-viewer", "org-alpha", "VIEWER") as viewer_client:
        resp = await viewer_client.post(
            f"/api/v1/broker-sandbox/accounts/{account_id}/orders",
            json={"symbol": "EUR/USD", "side": "BUY", "quantity": 10000, "price": 1.08500},
        )
        assert resp.status_code == 403

    # 3. TRADER can execute orders (201, FILLED)
    async with make_client(async_session, "usr-trader", "org-alpha", "TRADER") as trader_client:
        resp = await trader_client.post(
            f"/api/v1/broker-sandbox/accounts/{account_id}/orders",
            json={
                "symbol": "EUR/USD",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": 10000,
                "price": 1.08500,
            },
        )
        assert resp.status_code == 201
        order_data = resp.json()
        assert order_data["symbol"] == "EUR/USD"
        assert order_data["side"] == "BUY"
        assert order_data["status"] == "FILLED"
        assert Decimal(str(order_data["filled_quantity"])) == Decimal("10000")

        # 4. TRADER can inspect open positions
        pos_resp = await trader_client.get(f"/api/v1/broker-sandbox/accounts/{account_id}/positions")
        assert pos_resp.status_code == 200
        positions = pos_resp.json()
        assert len(positions) >= 1
        assert positions[0]["symbol"] == "EUR/USD"
        assert Decimal(str(positions[0]["quantity"])) == Decimal("10000")


@pytest.mark.asyncio
async def test_reconciliation_endpoint_rbac(async_session: AsyncSession) -> None:
    """Test on-demand reconciliation endpoint and RBAC."""
    account_id = ""
    async with make_client(async_session, "usr-owner", "org-alpha", "OWNER") as owner_client:
        resp = await owner_client.post(
            "/api/v1/broker-sandbox/accounts",
            json={
                "name": "Reconciliation Account",
                "provider": "MOCK",
                "environment": "SANDBOX",
                "account_id_external": "recon-ext-01",
            },
        )
        account_id = resp.json()["id"]
        await owner_client.post(f"/api/v1/broker-sandbox/accounts/{account_id}/connect")

    # TRADER cannot trigger reconciliation (requires BROKER_SANDBOX_RECONCILE)
    async with make_client(async_session, "usr-trader", "org-alpha", "TRADER") as trader_client:
        resp = await trader_client.post(f"/api/v1/broker-sandbox/accounts/{account_id}/reconcile")
        assert resp.status_code == 403

    # OWNER can trigger reconciliation
    async with make_client(async_session, "usr-owner", "org-alpha", "OWNER") as owner_client:
        resp = await owner_client.post(f"/api/v1/broker-sandbox/accounts/{account_id}/reconcile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["broker_account_id"] == account_id
        assert data["status"] == "MATCHED"
        assert data["has_discrepancies"] is False

        # List reconciliations history
        hist_resp = await owner_client.get(f"/api/v1/broker-sandbox/accounts/{account_id}/reconciliations")
        assert hist_resp.status_code == 200
        history = hist_resp.json()
        assert len(history) == 1
        assert history[0]["id"] == data["id"]
