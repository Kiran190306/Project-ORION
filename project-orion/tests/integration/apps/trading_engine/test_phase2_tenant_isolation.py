"""Comprehensive integration tests for EPIC-017 Phase 2: Tenant Ownership & Isolation.

Verifies:
1. Multi-tenant resource creation and ownership scoping (Order, Fill, Position).
2. Strict cross-tenant IDOR protection (HTTP 403 Forbidden for cross-org access to orders, positions, trades).
3. Organization header spoofing / tampering protection (HTTP 403 Forbidden on invalid X-Organization-ID).
4. List query isolation (Orders, Positions, Trades lists return only the authenticated tenant's records).
5. Dashboard and Portfolio metric isolation (zero position or equity leakage between tenants).
6. Per-tenant Strategy configuration isolation (preventing cross-tenant strategy config deactivation).
7. Legacy single-user backward compatibility (unassigned users continue operating seamlessly).
"""

from __future__ import annotations

import pathlib
import uuid
from decimal import Decimal
from unittest import mock
from unittest.mock import AsyncMock

import pytest
from apps.trading_engine.src.config import AppSettings
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.services.auth import get_password_hash
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
    FillModel,
    OrderModel,
    PositionModel,
    UserModel,
)
from libraries.infrastructure.persistence.models.organization import (
    OrganizationMemberModel,
    OrganizationModel,
)


@pytest.fixture
async def tenant_env():
    """Set up an isolated database, mock Redis, paper adapter, and app for multi-tenancy testing."""
    db_file = f"test_tenant_{uuid.uuid4().hex[:8]}.db"
    db_path = pathlib.Path(db_file)
    db_url = f"sqlite+aiosqlite:///{db_file}"

    db_config = DatabaseConfig(url=db_url, echo=False)
    db_manager = DatabaseManager(db_config)

    # Initialize all database tables
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed Organizations
    org_alpha_id = "org_alpha_hedge"
    org_beta_id = "org_beta_ventures"

    # Seed Users
    user_alpha_id = "usr_alpha_trader"
    user_beta_id = "usr_beta_trader"
    user_gamma_id = "usr_gamma_legacy"

    pass_alpha = "AlphaPass123!"
    pass_beta = "BetaPass123!"
    pass_gamma = "GammaLegacy123!"

    async with db_manager.session() as session:
        # 1. Organizations
        org_alpha = OrganizationModel(
            id=org_alpha_id,
            name="Alpha Hedge Fund",
            slug="alpha-hedge",
            status="ACTIVE",
            meta_data={},
        )
        org_beta = OrganizationModel(
            id=org_beta_id,
            name="Beta Ventures",
            slug="beta-ventures",
            status="ACTIVE",
            meta_data={},
        )
        session.add_all([org_alpha, org_beta])

        # 2. Users
        user_alpha = UserModel(
            id=user_alpha_id,
            username="alpha_trader",
            email="trader@alpha-hedge.dev",
            hashed_password=get_password_hash(pass_alpha),
            full_name="Alpha Lead Trader",
            is_active=True,
            is_superuser=False,
        )
        user_beta = UserModel(
            id=user_beta_id,
            username="beta_trader",
            email="trader@beta-ventures.dev",
            hashed_password=get_password_hash(pass_beta),
            full_name="Beta Portfolio Trader",
            is_active=True,
            is_superuser=False,
        )
        user_gamma = UserModel(
            id=user_gamma_id,
            username="gamma_legacy",
            email="trader@gamma-legacy.dev",
            hashed_password=get_password_hash(pass_gamma),
            full_name="Gamma Legacy Solo Trader",
            is_active=True,
            is_superuser=False,
        )
        session.add_all([user_alpha, user_beta, user_gamma])

        # 3. Organization Memberships
        member_alpha = OrganizationMemberModel(
            id="mem_alpha_001",
            organization_id=org_alpha_id,
            user_id=user_alpha_id,
            role="TRADER",
            status="ACTIVE",
            meta_data={},
        )
        member_beta = OrganizationMemberModel(
            id="mem_beta_001",
            organization_id=org_beta_id,
            user_id=user_beta_id,
            role="TRADER",
            status="ACTIVE",
            meta_data={},
        )
        session.add_all([member_alpha, member_beta])
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
        currency="USD",
        spread=0.0001,
        slippage_std=0.0,
        latency_ms_mean=0.0,
        latency_ms_std=0.0,
        partial_fill_probability=0.0,
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
            "org_alpha_id": org_alpha_id,
            "org_beta_id": org_beta_id,
            "user_alpha_id": user_alpha_id,
            "user_beta_id": user_beta_id,
            "user_gamma_id": user_gamma_id,
            "pass_alpha": pass_alpha,
            "pass_beta": pass_beta,
            "pass_gamma": pass_gamma,
        }

    await paper_adapter.disconnect()
    await db_manager.close()
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass


async def _login(client: AsyncClient, username: str, password: str) -> dict[str, str]:
    """Helper to authenticate and retrieve Bearer authorization headers."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_tenant_order_creation_and_scoping(tenant_env: dict):
    """Verify that orders, fills, and positions retain the active organization_id."""
    client: AsyncClient = tenant_env["client"]
    db_manager: DatabaseManager = tenant_env["db_manager"]

    headers_alpha = await _login(client, "alpha_trader", tenant_env["pass_alpha"])
    headers_beta = await _login(client, "beta_trader", tenant_env["pass_beta"])
    headers_gamma = await _login(client, "gamma_legacy", tenant_env["pass_gamma"])

    # 1. Alpha places an order
    resp_a = await client.post(
        "/api/v1/orders/",
        json={"symbol": "EUR/USD", "side": "BUY", "order_type": "MARKET", "quantity": "10000.0"},
        headers=headers_alpha,
    )
    assert resp_a.status_code == 201
    order_a_id = resp_a.json()["id"]

    # 2. Beta places an order
    resp_b = await client.post(
        "/api/v1/orders/",
        json={"symbol": "GBP/USD", "side": "BUY", "order_type": "MARKET", "quantity": "20000.0"},
        headers=headers_beta,
    )
    assert resp_b.status_code == 201
    order_b_id = resp_b.json()["id"]

    # 3. Gamma (legacy user with no org) places an order
    resp_g = await client.post(
        "/api/v1/orders/",
        json={"symbol": "USD/JPY", "side": "BUY", "order_type": "MARKET", "quantity": "15000.0"},
        headers=headers_gamma,
    )
    assert resp_g.status_code == 201
    order_g_id = resp_g.json()["id"]

    # Verify database persistence and tenant tags
    async with db_manager.session() as session:
        # Check Alpha records
        ord_a = (await session.execute(select(OrderModel).where(OrderModel.id == order_a_id))).scalar_one()
        assert ord_a.organization_id == tenant_env["org_alpha_id"]
        pos_a = (await session.execute(select(PositionModel).where(PositionModel.account_id == ord_a.account_id))).scalar_one()
        assert pos_a.organization_id == tenant_env["org_alpha_id"]
        fill_a = (await session.execute(select(FillModel).where(FillModel.order_id == order_a_id))).scalars().first()
        assert fill_a is not None and fill_a.organization_id == tenant_env["org_alpha_id"]

        # Check Beta records
        ord_b = (await session.execute(select(OrderModel).where(OrderModel.id == order_b_id))).scalar_one()
        assert ord_b.organization_id == tenant_env["org_beta_id"]
        pos_b = (await session.execute(select(PositionModel).where(PositionModel.account_id == ord_b.account_id))).scalar_one()
        assert pos_b.organization_id == tenant_env["org_beta_id"]
        fill_b = (await session.execute(select(FillModel).where(FillModel.order_id == order_b_id))).scalars().first()
        assert fill_b is not None and fill_b.organization_id == tenant_env["org_beta_id"]

        # Check Gamma legacy records (must be None)
        ord_g = (await session.execute(select(OrderModel).where(OrderModel.id == order_g_id))).scalar_one()
        assert ord_g.organization_id is None
        pos_g = (await session.execute(select(PositionModel).where(PositionModel.account_id == ord_g.account_id))).scalar_one()
        assert pos_g.organization_id is None
        fill_g = (await session.execute(select(FillModel).where(FillModel.order_id == order_g_id))).scalars().first()
        assert fill_g is not None and fill_g.organization_id is None


@pytest.mark.asyncio
async def test_cross_tenant_idor_protection(tenant_env: dict):
    """Verify that User Beta receives HTTP 403 Forbidden attempting to access Alpha's resources."""
    client: AsyncClient = tenant_env["client"]

    headers_alpha = await _login(client, "alpha_trader", tenant_env["pass_alpha"])
    headers_beta = await _login(client, "beta_trader", tenant_env["pass_beta"])

    # Alpha places an order
    resp_a = await client.post(
        "/api/v1/orders/",
        json={"symbol": "EUR/USD", "side": "BUY", "order_type": "MARKET", "quantity": "10000.0"},
        headers=headers_alpha,
    )
    assert resp_a.status_code == 201
    order_a_id = resp_a.json()["id"]

    # Retrieve Alpha's position ID
    pos_resp = await client.get("/api/v1/positions/", headers=headers_alpha)
    assert pos_resp.status_code == 200
    pos_a_id = pos_resp.json()["items"][0]["id"]

    # Retrieve Alpha's trade ID
    trade_resp = await client.get("/api/v1/trades/", headers=headers_alpha)
    assert trade_resp.status_code == 200
    trade_a_id = trade_resp.json()["items"][0]["trade_id"]

    def _error_msg(res) -> str:
        d = res.json()
        return str(d.get("message") or d.get("detail") or "")

    # 1. IDOR: Beta attempts to read Alpha's order
    idor_order_get = await client.get(f"/api/v1/orders/{order_a_id}", headers=headers_beta)
    assert idor_order_get.status_code == 403
    assert "Forbidden" in _error_msg(idor_order_get)

    # 2. IDOR: Beta attempts to cancel Alpha's order
    idor_order_cancel = await client.post(f"/api/v1/orders/{order_a_id}/cancel", headers=headers_beta)
    assert idor_order_cancel.status_code == 403
    assert "Forbidden" in _error_msg(idor_order_cancel)

    # 3. IDOR: Beta attempts to read Alpha's position
    idor_pos_get = await client.get(f"/api/v1/positions/{pos_a_id}", headers=headers_beta)
    assert idor_pos_get.status_code == 403
    assert "Forbidden" in _error_msg(idor_pos_get)

    # 4. IDOR: Beta attempts to close Alpha's position
    idor_pos_close = await client.post(f"/api/v1/positions/{pos_a_id}/close", headers=headers_beta)
    assert idor_pos_close.status_code == 403
    assert "Forbidden" in _error_msg(idor_pos_close)

    # 5. IDOR: Beta attempts to read Alpha's trade
    idor_trade_get = await client.get(f"/api/v1/trades/{trade_a_id}", headers=headers_beta)
    assert idor_trade_get.status_code == 403
    assert "Forbidden" in _error_msg(idor_trade_get)


@pytest.mark.asyncio
async def test_organization_header_tampering_forbidden(tenant_env: dict):
    """Verify that spoofing X-Organization-ID header for an unassigned org results in 403 Forbidden."""
    client: AsyncClient = tenant_env["client"]

    headers_beta = await _login(client, "beta_trader", tenant_env["pass_beta"])

    # Beta attempts to inject Alpha's organization ID in the request header
    spoofed_headers = {
        **headers_beta,
        "X-Organization-ID": tenant_env["org_alpha_id"],
    }

    # Request must be rejected with HTTP 403
    resp = await client.get("/api/v1/orders/", headers=spoofed_headers)
    assert resp.status_code == 403
    d = resp.json()
    msg = str(d.get("message") or d.get("detail") or "")
    assert "Access denied to requested organization" in msg


@pytest.mark.asyncio
async def test_list_and_dashboard_isolation(tenant_env: dict):
    """Verify list endpoints, dashboard aggregations, and portfolio overviews do not leak cross-tenant data."""
    client: AsyncClient = tenant_env["client"]

    headers_alpha = await _login(client, "alpha_trader", tenant_env["pass_alpha"])
    headers_beta = await _login(client, "beta_trader", tenant_env["pass_beta"])

    # Alpha trades EUR/USD
    await client.post(
        "/api/v1/orders/",
        json={"symbol": "EUR/USD", "side": "BUY", "order_type": "MARKET", "quantity": "10000.0"},
        headers=headers_alpha,
    )

    # Beta trades GBP/USD
    await client.post(
        "/api/v1/orders/",
        json={"symbol": "GBP/USD", "side": "BUY", "order_type": "MARKET", "quantity": "25000.0"},
        headers=headers_beta,
    )

    # 1. Orders List Isolation
    alpha_orders = (await client.get("/api/v1/orders/", headers=headers_alpha)).json()
    beta_orders = (await client.get("/api/v1/orders/", headers=headers_beta)).json()

    assert alpha_orders["total"] == 1
    assert alpha_orders["items"][0]["symbol"] == "EUR/USD"

    assert beta_orders["total"] == 1
    assert beta_orders["items"][0]["symbol"] == "GBP/USD"

    # 2. Positions List Isolation
    alpha_positions = (await client.get("/api/v1/positions/", headers=headers_alpha)).json()
    beta_positions = (await client.get("/api/v1/positions/", headers=headers_beta)).json()

    assert alpha_positions["total"] == 1
    assert alpha_positions["items"][0]["symbol"] == "EUR/USD"

    assert beta_positions["total"] == 1
    assert beta_positions["items"][0]["symbol"] == "GBP/USD"

    # 3. Trades List Isolation
    alpha_trades = (await client.get("/api/v1/trades/", headers=headers_alpha)).json()
    beta_trades = (await client.get("/api/v1/trades/", headers=headers_beta)).json()

    assert alpha_trades["total"] == 1
    assert alpha_trades["items"][0]["symbol"] == "EUR/USD"

    assert beta_trades["total"] == 1
    assert beta_trades["items"][0]["symbol"] == "GBP/USD"

    # 4. Dashboard Isolation
    alpha_dash = (await client.get("/api/v1/dashboard/", headers=headers_alpha)).json()
    beta_dash = (await client.get("/api/v1/dashboard/", headers=headers_beta)).json()

    # Alpha dashboard contains only Alpha positions & trades
    alpha_trading = alpha_dash["trading"]
    assert len(alpha_trading["open_positions"]) == 1
    assert alpha_trading["open_positions"][0]["symbol"] == "EUR/USD"
    assert len(alpha_trading["recent_trades"]) == 1
    assert alpha_trading["recent_trades"][0]["symbol"] == "EUR/USD"

    # Beta dashboard contains only Beta positions & trades
    beta_trading = beta_dash["trading"]
    assert len(beta_trading["open_positions"]) == 1
    assert beta_trading["open_positions"][0]["symbol"] == "GBP/USD"
    assert len(beta_trading["recent_trades"]) == 1
    assert beta_trading["recent_trades"][0]["symbol"] == "GBP/USD"

    # 5. Portfolio Overview Isolation
    alpha_port = (await client.get("/api/v1/portfolio/", headers=headers_alpha)).json()
    beta_port = (await client.get("/api/v1/portfolio/", headers=headers_beta)).json()

    assert alpha_port["open_positions_count"] == 1
    assert beta_port["open_positions_count"] == 1
    # Positions quantities are different (10,000 vs 25,000), so gross exposure must differ
    assert Decimal(str(alpha_port["gross_exposure"])) != Decimal(str(beta_port["gross_exposure"]))


@pytest.mark.asyncio
async def test_strategy_configuration_isolation(tenant_env: dict):
    """Verify that updating strategy configuration for Tenant Beta does not deactivate Tenant Alpha's strategy."""
    client: AsyncClient = tenant_env["client"]

    headers_alpha = await _login(client, "alpha_trader", tenant_env["pass_alpha"])
    headers_beta = await _login(client, "beta_trader", tenant_env["pass_beta"])

    # Alpha activates strategy with fast_ma_period = 14
    resp_a = await client.put(
        "/api/v1/strategies/account/config",
        json={
            "strategy_id": "trend_following",
            "timeframe": "M15",
            "symbols": ["EUR/USD"],
            "parameters": {"fast_ma_period": 14},
            "is_active": True,
        },
        headers=headers_alpha,
    )
    assert resp_a.status_code == 200
    assert resp_a.json()["parameters"]["fast_ma_period"] == 14
    assert resp_a.json()["is_active"] is True

    # Beta activates strategy with fast_ma_period = 50
    resp_b = await client.put(
        "/api/v1/strategies/account/config",
        json={
            "strategy_id": "trend_following",
            "timeframe": "H1",
            "symbols": ["GBP/USD"],
            "parameters": {"fast_ma_period": 50},
            "is_active": True,
        },
        headers=headers_beta,
    )
    assert resp_b.status_code == 200
    assert resp_b.json()["parameters"]["fast_ma_period"] == 50
    assert resp_b.json()["is_active"] is True

    # Crucial assertion: Alpha's strategy config must remain ACTIVE and unchanged!
    check_a = await client.get("/api/v1/strategies/account/config", headers=headers_alpha)
    assert check_a.status_code == 200
    assert check_a.json()["is_active"] is True
    assert check_a.json()["parameters"]["fast_ma_period"] == 14
    assert check_a.json()["timeframe"] == "M15"

    # Beta's strategy config remains intact
    check_b = await client.get("/api/v1/strategies/account/config", headers=headers_beta)
    assert check_b.status_code == 200
    assert check_b.json()["is_active"] is True
    assert check_b.json()["parameters"]["fast_ma_period"] == 50
    assert check_b.json()["timeframe"] == "H1"
