"""Integration tests for Quantitative Strategy Optimization & Walk-Forward API (EPIC-024).

Validates REST API contract, multi-tenant isolation, RBAC permissions, and export formats.
"""

from __future__ import annotations

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
            id="org_alpha_opt",
            name="Alpha Quant Org",
            slug="alpha-quant",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        user_alpha = UserModel(
            id="usr_alpha_opt",
            username="alpha_quant",
            email="quant@alpha.dev",
            hashed_password="hash",
            is_active=True,
            is_superuser=False,
        )
        mem_alpha = OrganizationMemberModel(
            id="mem_alpha_opt",
            organization_id="org_alpha_opt",
            user_id="usr_alpha_opt",
            role="TRADER",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Pre-seed Tenant 2 (Beta)
        org_beta = OrganizationModel(
            id="org_beta_opt",
            name="Beta Quant Org",
            slug="beta-quant",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        user_beta = UserModel(
            id="usr_beta_opt",
            username="beta_quant",
            email="quant@beta.dev",
            hashed_password="hash",
            is_active=True,
            is_superuser=False,
        )
        mem_beta = OrganizationMemberModel(
            id="mem_beta_opt",
            organization_id="org_beta_opt",
            user_id="usr_beta_opt",
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

    await engine.dispose()


@pytest.mark.asyncio
async def test_optimization_api_full_lifecycle(integration_db: AsyncSession) -> None:
    """Full end-to-end REST API verification of Strategy Optimization endpoints."""
    app = create_app()

    app.dependency_overrides[dependencies.get_db_session] = lambda: integration_db
    app.dependency_overrides[dependencies.get_tenant_context] = lambda: dependencies.TenantContext(
        user_id="usr_alpha_opt",
        organization_id="org_alpha_opt",
        role="TRADER",
        is_superuser=False,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /spaces/{strategy_id}
        res_space = await client.get("/api/v1/optimization/spaces/TrendFollowing")
        assert res_space.status_code == 200
        space_data = res_space.json()
        assert space_data["strategy_id"] in ("TrendFollowing", "trend_following")
        assert len(space_data["ranges"]) >= 2

        # 2. POST /run (launch optimization sweep)
        run_payload = {
            "strategy_id": "TrendFollowing",
            "symbol": "EUR/USD",
            "timeframe": "H1",
            "start_date": "2025-01-01T00:00:00Z",
            "end_date": "2025-01-10T00:00:00Z",
            "initial_capital": 10000.00,
            "optimization_type": "GRID_SEARCH",
            "fitness_objective": "SHARPE_RATIO",
            "max_combinations": 50,
        }
        res_run = await client.post("/api/v1/optimization/run", json=run_payload)
        assert res_run.status_code == 201
        job_data = res_run.json()
        job_id = job_data["id"]
        assert job_data["status"] == "COMPLETED"
        assert job_data["total_combinations"] > 0
        assert len(job_data["top_candidates"]) > 0

        # 3. GET /jobs (list tenant jobs)
        res_list = await client.get("/api/v1/optimization/jobs")
        assert res_list.status_code == 200
        jobs = res_list.json()
        assert len(jobs) >= 1
        assert any(j["id"] == job_id for j in jobs)

        # 4. GET /jobs/{id}
        res_get = await client.get(f"/api/v1/optimization/jobs/{job_id}")
        assert res_get.status_code == 200
        assert res_get.json()["id"] == job_id

        # 5. GET /jobs/{id}/heatmap
        res_hm = await client.get(f"/api/v1/optimization/jobs/{job_id}/heatmap")
        assert res_hm.status_code == 200

        # 6. GET /jobs/{id}/export?format=csv
        res_exp = await client.get(f"/api/v1/optimization/jobs/{job_id}/export?format=csv")
        assert res_exp.status_code == 200
        assert "rank,parameters,fitness_score" in res_exp.text

        # 7. POST /walk-forward
        wfa_payload = {
            "strategy_id": "TrendFollowing",
            "symbol": "EUR/USD",
            "timeframe": "H1",
            "start_date": "2025-01-01T00:00:00Z",
            "end_date": "2025-01-15T00:00:00Z",
            "n_windows": 3,
            "in_sample_ratio": 0.70,
            "max_combinations_per_window": 50,
        }
        res_wfa = await client.post("/api/v1/optimization/walk-forward", json=wfa_payload)
        assert res_wfa.status_code == 201
        wfa_data = res_wfa.json()
        assert wfa_data["status"] == "COMPLETED"
        assert wfa_data["walk_forward_result"] is not None


@pytest.mark.asyncio
async def test_optimization_api_tenant_isolation(integration_db: AsyncSession) -> None:
    """Verify fail-closed HTTP 404 on cross-tenant optimization access (IDOR defense)."""
    app = create_app()

    # Pre-run a job as Tenant Alpha
    app.dependency_overrides[dependencies.get_db_session] = lambda: integration_db
    app.dependency_overrides[dependencies.get_tenant_context] = lambda: dependencies.TenantContext(
        user_id="usr_alpha_opt",
        organization_id="org_alpha_opt",
        role="TRADER",
        is_superuser=False,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run_payload = {
            "strategy_id": "TrendFollowing",
            "symbol": "EUR/USD",
            "timeframe": "H1",
            "start_date": "2025-01-01T00:00:00Z",
            "end_date": "2025-01-10T00:00:00Z",
            "max_combinations": 50,
        }
        res = await client.post("/api/v1/optimization/run", json=run_payload)
        alpha_job_id = res.json()["id"]

    # Now switch authentication to Tenant Beta
    app.dependency_overrides[dependencies.get_tenant_context] = lambda: dependencies.TenantContext(
        user_id="usr_beta_opt",
        organization_id="org_beta_opt",
        role="TRADER",
        is_superuser=False,
    )

    async with AsyncClient(transport=transport, base_url="http://test") as beta_client:
        # Tenant Beta attempting to read Tenant Alpha's job -> 404 Not Found
        res_idor = await beta_client.get(f"/api/v1/optimization/jobs/{alpha_job_id}")
        assert res_idor.status_code == 404

        # Tenant Beta listing jobs -> must not see Tenant Alpha's job
        res_list = await beta_client.get("/api/v1/optimization/jobs")
        assert res_list.status_code == 200
        assert all(j["id"] != alpha_job_id for j in res_list.json())


@pytest.mark.asyncio
async def test_optimization_api_rbac_denial(integration_db: AsyncSession) -> None:
    """Verify HTTP 403 Forbidden when user lacks OPTIMIZATION_EXECUTE permission."""
    app = create_app()

    app.dependency_overrides[dependencies.get_db_session] = lambda: integration_db
    # VIEWER has OPTIMIZATION_READ but NOT OPTIMIZATION_EXECUTE
    app.dependency_overrides[dependencies.get_tenant_context] = lambda: dependencies.TenantContext(
        user_id="usr_alpha_opt",
        organization_id="org_alpha_opt",
        role="VIEWER",
        is_superuser=False,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run_payload = {
            "strategy_id": "TrendFollowing",
            "symbol": "EUR/USD",
            "timeframe": "H1",
            "start_date": "2025-01-01T00:00:00Z",
            "end_date": "2025-01-10T00:00:00Z",
            "max_combinations": 50,
        }
        res = await client.post("/api/v1/optimization/run", json=run_payload)
        assert res.status_code == 403
        err_msg = res.json().get("detail") or res.json().get("message") or ""
        assert "OPTIMIZATION_EXECUTE" in err_msg or "Forbidden" in err_msg
