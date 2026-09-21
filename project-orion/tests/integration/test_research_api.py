"""Integration tests for Strategy Lab and Backtesting Research API (EPIC-023 Phase 38).

Validates REST API contract, serialization, multi-tenant isolation, RBAC guards,
and export formats.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from apps.trading_engine.src import dependencies
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.services.subscription_service import SubscriptionService
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models.organization import (
    OrganizationMemberModel,
    OrganizationModel,
)
from libraries.infrastructure.persistence.models.user import UserModel


@pytest.fixture
async def integration_db() -> AsyncSession:
    """Isolated async SQLite database session for integration tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        # Pre-seed Tenant 1 (Alpha)
        org_alpha = OrganizationModel(
            id="org_alpha_res",
            name="Alpha Research",
            slug="alpha-research",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        user_alpha = UserModel(
            id="usr_alpha_res",
            username="alpha_researcher",
            email="res@alpha.dev",
            hashed_password="hash",
            is_active=True,
            is_superuser=False,
        )
        mem_alpha = OrganizationMemberModel(
            id="mem_alpha_res",
            organization_id="org_alpha_res",
            user_id="usr_alpha_res",
            role="TRADER",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Pre-seed Tenant 2 (Beta)
        org_beta = OrganizationModel(
            id="org_beta_res",
            name="Beta Research",
            slug="beta-research",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        user_beta = UserModel(
            id="usr_beta_res",
            username="beta_researcher",
            email="res@beta.dev",
            hashed_password="hash",
            is_active=True,
            is_superuser=False,
        )
        mem_beta = OrganizationMemberModel(
            id="mem_beta_res",
            organization_id="org_beta_res",
            user_id="usr_beta_res",
            role="TRADER",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        session.add_all([org_alpha, user_alpha, mem_alpha, org_beta, user_beta, mem_beta])
        sub_svc = SubscriptionService(session)
        await sub_svc._ensure_canonical_plans()
        await session.commit()
        yield session


@pytest.mark.asyncio
async def test_research_api_lifecycle_and_endpoints(integration_db: AsyncSession) -> None:
    """Full end-to-end REST API verification of Strategy Lab endpoints."""
    app = create_app()

    # Authenticated as Tenant Alpha
    app.dependency_overrides[dependencies.get_db_session] = lambda: integration_db
    app.dependency_overrides[dependencies.get_current_active_user] = lambda: {
        "id": "usr_alpha_res",
        "username": "alpha_researcher",
        "is_active": True,
        "is_superuser": False,
    }
    app.dependency_overrides[dependencies.get_tenant_context] = lambda: dependencies.TenantContext(
        user_id="usr_alpha_res",
        organization_id="org_alpha_res",
        role="TRADER",
        is_superuser=False,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /strategies
        res = await client.get("/api/v1/research/strategies")
        assert res.status_code == 200
        strats = res.json()
        assert len(strats) >= 4
        assert any(s["strategy_id"] == "trend_following" for s in strats)

        # 2. GET /strategies/{id}
        res_tf = await client.get("/api/v1/research/strategies/trend_following")
        assert res_tf.status_code == 200
        assert res_tf.json()["strategy_id"] == "trend_following"

        # 3. GET /strategies/unknown -> 404
        res_404 = await client.get("/api/v1/research/strategies/non_existent_123")
        assert res_404.status_code == 404

        # 4. POST /experiments (create & run experiment 1)
        create_payload = {
            "strategy_id": "trend_following",
            "symbol": "EUR/USD",
            "timeframe": "H1",
            "start_date": "2025-01-01",
            "end_date": "2025-01-15",
            "initial_capital": 10000.0,
            "parameters": {"fast_period": 5, "slow_period": 15},
            "spread_pips": 1.5,
            "adverse_slippage_pips": 0.5,
            "commission_per_lot": 7.0,
        }
        res_exp1 = await client.post("/api/v1/research/experiments", json=create_payload)
        assert res_exp1.status_code == 201
        exp1_data = res_exp1.json()
        exp1_id = exp1_data["id"]
        assert exp1_data["status"] == "COMPLETED"
        assert exp1_data["metrics"]["initial_capital"] == 10000.0

        # Create experiment 2 for comparison
        create_payload_2 = {
            "strategy_id": "mean_reversion",
            "symbol": "EUR/USD",
            "timeframe": "H1",
            "start_date": "2025-01-01",
            "end_date": "2025-01-15",
            "initial_capital": 10000.0,
            "parameters": {"lookback_period": 14, "entry_threshold": 1.5},
        }
        res_exp2 = await client.post("/api/v1/research/experiments", json=create_payload_2)
        assert res_exp2.status_code == 201
        exp2_id = res_exp2.json()["id"]

        # 5. GET /experiments (list)
        res_list = await client.get("/api/v1/research/experiments")
        assert res_list.status_code == 200
        items = res_list.json()
        assert len(items) >= 2
        exp_ids = [i["id"] for i in items]
        assert exp1_id in exp_ids
        assert exp2_id in exp_ids

        # 6. GET /experiments/{id} (detail)
        res_det = await client.get(f"/api/v1/research/experiments/{exp1_id}")
        assert res_det.status_code == 200
        assert res_det.json()["id"] == exp1_id
        assert "parameters" in res_det.json()

        # 7. GET /experiments/{id}/results
        res_res = await client.get(f"/api/v1/research/experiments/{exp1_id}/results")
        assert res_res.status_code == 200
        res_body = res_res.json()
        assert res_body["status"] == "COMPLETED"
        assert "metrics" in res_body
        assert "warnings" in res_body

        # 8. GET /experiments/{id}/equity-curve
        res_eq = await client.get(f"/api/v1/research/experiments/{exp1_id}/equity-curve")
        assert res_eq.status_code == 200
        eq_body = res_eq.json()
        assert eq_body["experiment_id"] == exp1_id
        assert len(eq_body["points"]) > 0

        # 9. GET /experiments/{id}/trades
        res_tr = await client.get(f"/api/v1/research/experiments/{exp1_id}/trades")
        assert res_tr.status_code == 200
        assert "trades" in res_tr.json()

        # 10. POST /experiments/compare
        res_comp = await client.post(
            "/api/v1/research/experiments/compare",
            json={"experiment_ids": [exp1_id, exp2_id]},
        )
        assert res_comp.status_code == 200
        comp_data = res_comp.json()
        assert len(comp_data["comparison"]) == 2
        assert exp1_id in comp_data["normalized_curves"]
        assert exp2_id in comp_data["normalized_curves"]

        # 11. GET /experiments/{id}/export?format=csv
        res_csv = await client.get(f"/api/v1/research/experiments/{exp1_id}/export?format=csv")
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["content-type"]
        assert f"experiment_{exp1_id}.csv" in res_csv.headers["content-disposition"]
        assert "EXPERIMENT SUMMARY" in res_csv.text

        # 12. GET /experiments/{id}/export?format=json
        res_json = await client.get(f"/api/v1/research/experiments/{exp1_id}/export?format=json")
        assert res_json.status_code == 200
        assert "application/json" in res_json.headers["content-type"]
        parsed = json.loads(res_json.text)
        assert parsed["id"] == exp1_id

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_research_api_cross_tenant_isolation(integration_db: AsyncSession) -> None:
    """Tenant B cannot view, query, or export Tenant A's experiment."""
    app = create_app()

    # Step 1: Create experiment as Tenant Alpha
    app.dependency_overrides[dependencies.get_db_session] = lambda: integration_db
    app.dependency_overrides[dependencies.get_current_active_user] = lambda: {
        "id": "usr_alpha_res",
        "username": "alpha_researcher",
        "is_active": True,
        "is_superuser": False,
    }
    app.dependency_overrides[dependencies.get_tenant_context] = lambda: dependencies.TenantContext(
        user_id="usr_alpha_res",
        organization_id="org_alpha_res",
        role="TRADER",
        is_superuser=False,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/research/experiments",
            json={
                "strategy_id": "trend_following",
                "symbol": "EUR/USD",
                "timeframe": "H1",
                "start_date": "2025-01-01",
                "end_date": "2025-01-10",
            },
        )
        assert res.status_code == 201
        alpha_exp_id = res.json()["id"]

    # Step 2: Switch to Tenant Beta
    app.dependency_overrides[dependencies.get_current_active_user] = lambda: {
        "id": "usr_beta_res",
        "username": "beta_researcher",
        "is_active": True,
        "is_superuser": False,
    }
    app.dependency_overrides[dependencies.get_tenant_context] = lambda: dependencies.TenantContext(
        user_id="usr_beta_res",
        organization_id="org_beta_res",
        role="TRADER",
        is_superuser=False,
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Tenant Beta listing experiments should NOT see Tenant Alpha's experiment
        list_res = await client.get("/api/v1/research/experiments")
        assert list_res.status_code == 200
        assert not any(i["id"] == alpha_exp_id for i in list_res.json())

        # Tenant Beta directly requesting Tenant Alpha's experiment gets 404
        get_res = await client.get(f"/api/v1/research/experiments/{alpha_exp_id}")
        assert get_res.status_code == 404

        # Tenant Beta attempting export gets 404
        exp_res = await client.get(f"/api/v1/research/experiments/{alpha_exp_id}/export")
        assert exp_res.status_code == 404

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_research_api_rbac_enforcement(integration_db: AsyncSession) -> None:
    """User without RESEARCH_EXECUTE role cannot create an experiment."""
    app = create_app()

    app.dependency_overrides[dependencies.get_db_session] = lambda: integration_db
    app.dependency_overrides[dependencies.get_current_active_user] = lambda: {
        "id": "usr_guest",
        "username": "guest_user",
        "is_active": True,
        "is_superuser": False,
    }
    # Role VIEWER has RESEARCH_READ but NOT RESEARCH_EXECUTE
    app.dependency_overrides[dependencies.get_tenant_context] = lambda: dependencies.TenantContext(
        user_id="usr_guest",
        organization_id="org_alpha_res",
        role="VIEWER",
        is_superuser=False,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/research/experiments",
            json={
                "strategy_id": "trend_following",
                "symbol": "EUR/USD",
                "timeframe": "H1",
                "start_date": "2025-01-01",
                "end_date": "2025-01-10",
            },
        )
        assert res.status_code == 403
        data = res.json()
        error_msg = data.get("message") or data.get("detail", "")
        assert "Forbidden" in error_msg

    app.dependency_overrides.clear()
