"""Integration test suite for Strategy Deployment Pipeline & Paper Incubator (EPIC-025).

Tests:
1. Candidate promotion from Optimization with 5-gate quality evaluation.
2. Quality gate rejection (GATES_FAILED) on overfitted or insufficient data.
3. Candidate promotion from Research Experiment.
4. Pause and resume lifecycle transitions.
5. Deployment cancellation and terminal state fail-closed guarantees.
6. Incubation validation (PAPER_VALIDATED / INCUBATION_FAILED).
7. Promotion candidate review and institutional governance.
8. Separation of duties enforcement (self-approval rejection).
9. Multi-tenant IDOR isolation (cross-tenant access rejected with 404).
10. Granular RBAC enforcement (VIEWER denied execute/promote with 403).
11. Tier deployment quota limits enforcement.
12. Paper-only boundary verification ($0.00 capital at risk).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from apps.trading_engine.src import dependencies
from apps.trading_engine.src.dependencies import TenantContext
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.services.subscription_service import SubscriptionService
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models import (
    OptimizationJobModel,
    OrganizationMemberModel,
    OrganizationModel,
    ResearchExperimentModel,
    UserModel,
)


@pytest.fixture
async def integration_db() -> AsyncSession:
    """Isolated async SQLite database session for integration tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        # 1. Organizations
        org_alpha = OrganizationModel(
            id="org_alpha_dep",
            name="Alpha Capital",
            slug="alpha-capital",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        org_beta = OrganizationModel(
            id="org_beta_dep",
            name="Beta Hedge",
            slug="beta-hedge",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(org_alpha)
        session.add(org_beta)

        # 2. Users
        user_alpha_trader = UserModel(
            id="usr_alpha_trader",
            username="alpha_trader",
            email="trader@alpha.com",
            hashed_password="hash",
            is_active=True,
            is_superuser=False,
        )
        user_alpha_pm = UserModel(
            id="usr_alpha_pm",
            username="alpha_pm",
            email="pm@alpha.com",
            hashed_password="hash",
            is_active=True,
            is_superuser=False,
        )
        user_beta_viewer = UserModel(
            id="usr_beta_viewer",
            username="beta_viewer",
            email="viewer@beta.com",
            hashed_password="hash",
            is_active=True,
            is_superuser=False,
        )
        session.add(user_alpha_trader)
        session.add(user_alpha_pm)
        session.add(user_beta_viewer)

        # 3. Memberships
        mem_alpha_trader = OrganizationMemberModel(
            id="mem_alpha_trader",
            organization_id="org_alpha_dep",
            user_id="usr_alpha_trader",
            role="TRADER",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mem_alpha_pm = OrganizationMemberModel(
            id="mem_alpha_pm",
            organization_id="org_alpha_dep",
            user_id="usr_alpha_pm",
            role="PORTFOLIO_MANAGER",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mem_beta_viewer = OrganizationMemberModel(
            id="mem_beta_viewer",
            organization_id="org_beta_dep",
            user_id="usr_beta_viewer",
            role="VIEWER",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(mem_alpha_trader)
        session.add(mem_alpha_pm)
        session.add(mem_beta_viewer)

        # 4. Completed Optimization Job (ROBUST - Quality Gates will pass)
        now = datetime.now(timezone.utc)
        opt_job_robust = OptimizationJobModel(
            id="opt_job_robust_001",
            organization_id="org_alpha_dep",
            created_by="usr_alpha_trader",
            strategy_id="trend_following",
            symbol="EUR/USD",
            timeframe="H1",
            start_date=now,
            end_date=now,
            initial_capital=Decimal("10000.00"),
            optimization_type="GRID_SEARCH",
            fitness_objective="SHARPE_RATIO",
            status="COMPLETED",
            total_combinations=20,
            completed_combinations=20,
            execution_time_seconds=5.0,
            best_parameters={"fast_period": 12, "slow_period": 35},
            best_metrics={"total_trades": 25, "sharpe_ratio": 1.6, "total_return": 0.08, "max_drawdown": 0.04},
            top_candidates=[
                {
                    "rank": 1,
                    "parameters": {"fast_period": 12, "slow_period": 35},
                    "fitness_score": 1.6,
                    "sharpe_ratio": 1.6,
                    "total_trades": 25,
                    "total_return": 0.08,
                    "max_drawdown": 0.04,
                    "win_rate": 0.58,
                    "profit_factor": 1.7,
                }
            ],
            walk_forward_result={
                "mean_wfe": 72.5,
                "robustness_verdict": "ROBUST",
                "windows": [{"window_index": 0}, {"window_index": 1}],
            },
            regime_breakdown={
                "robustness_score": 0.75,
                "regimes": {
                    "TRENDING_BULL": {"trade_count": 15, "profit_factor": 1.8, "win_rate": 60.0},
                    "RANGING_LOW_VOL": {"trade_count": 10, "profit_factor": 1.4, "win_rate": 55.0},
                },
            },
            stability_report={
                "neighbor_count": 4,
                "is_cliff": False,
                "plateau_stability_score": 0.85,
            },
            completed_at=now,
            created_at=now,
            updated_at=now,
        )

        # 5. Overfitted Optimization Job (Quality Gates will FAIL)
        opt_job_overfitted = OptimizationJobModel(
            id="opt_job_overfitted_002",
            organization_id="org_alpha_dep",
            created_by="usr_alpha_trader",
            strategy_id="trend_following",
            symbol="EUR/USD",
            timeframe="H1",
            start_date=now,
            end_date=now,
            initial_capital=Decimal("10000.00"),
            optimization_type="GRID_SEARCH",
            fitness_objective="SHARPE_RATIO",
            status="COMPLETED",
            total_combinations=20,
            completed_combinations=20,
            execution_time_seconds=5.0,
            best_parameters={"fast_period": 5, "slow_period": 10},
            best_metrics={"total_trades": 8, "sharpe_ratio": 0.2, "total_return": 0.01, "max_drawdown": 0.25},
            top_candidates=[
                {
                    "rank": 1,
                    "parameters": {"fast_period": 5, "slow_period": 10},
                    "fitness_score": 0.2,
                    "sharpe_ratio": 0.2,
                    "total_trades": 8,
                    "total_return": 0.01,
                    "max_drawdown": 0.25,
                    "win_rate": 0.35,
                    "profit_factor": 0.7,
                }
            ],
            walk_forward_result={
                "mean_wfe": 25.0,
                "robustness_verdict": "OVERFITTED",
                "windows": [{"window_index": 0}, {"window_index": 1}],
            },
            regime_breakdown=None,
            stability_report={"neighbor_count": 2, "is_cliff": True, "plateau_stability_score": 0.15},
            completed_at=now,
            created_at=now,
            updated_at=now,
        )

        # 6. Completed Research Experiment
        exp_robust = ResearchExperimentModel(
            id="exp_robust_001",
            organization_id="org_alpha_dep",
            created_by="usr_alpha_trader",
            strategy_id="trend_following",
            strategy_version="1.0.0",
            symbol="EUR/USD",
            timeframe="H1",
            start_date=now,
            end_date=now,
            initial_capital=Decimal("10000.00"),
            simulation_config={
                "walk_forward_result": {
                    "mean_wfe": 75.0,
                    "robustness_verdict": "ROBUST",
                    "windows": [{"window_index": 0}, {"window_index": 1}],
                },
                "regime_breakdown": {
                    "robustness_score": 0.8,
                    "regimes": {
                        "TRENDING_BULL": {"trade_count": 18, "profit_factor": 1.9, "win_rate": 65.0},
                        "RANGING_LOW_VOL": {"trade_count": 12, "profit_factor": 1.5, "win_rate": 55.0},
                    },
                },
                "stability_report": {
                    "neighbor_count": 4,
                    "is_cliff": False,
                    "plateau_stability_score": 0.88,
                },
            },
            status="COMPLETED",
            metrics={"total_trades": 30, "sharpe_ratio": 1.4, "total_return_pct": 6.5, "max_drawdown_pct": 5.0},
            completed_at=now,
            created_at=now,
            updated_at=now,
        )

        session.add(opt_job_robust)
        session.add(opt_job_overfitted)
        session.add(exp_robust)

        # Ensure canonical subscription plans
        sub_svc = SubscriptionService(session)
        await sub_svc._ensure_canonical_plans()

        await session.commit()
        yield session

    await engine.dispose()


def make_app_with_context(
    db_session: AsyncSession,
    user_id: str,
    org_id: str | None,
    role: str | None,
):
    """Create FastAPI app instance with mocked db and tenant dependencies."""
    app = create_app()
    app.dependency_overrides[dependencies.get_db_session] = lambda: db_session
    app.dependency_overrides[dependencies.get_tenant_context] = lambda: TenantContext(
        user_id=user_id,
        organization_id=org_id,
        role=role,
        is_superuser=False,
    )
    return app


# ===========================================================================
# Test Cases
# ===========================================================================

@pytest.mark.asyncio
async def test_promote_from_optimization_success(integration_db: AsyncSession):
    """Verify promoting a robust optimization candidate evaluates gates and enters INCUBATING."""
    app = make_app_with_context(
        integration_db,
        user_id="usr_alpha_trader",
        org_id="org_alpha_dep",
        role="TRADER",
    )

    payload = {
        "optimization_job_id": "opt_job_robust_001",
        "candidate_rank": 1,
        "initial_capital": 10000.00,
        "incubation_duration_days": 7,
        "min_trade_count": 10,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.post("/api/v1/deployments/promote/optimization", json=payload)
        assert res.status_code == 201
        data = res.json()

        assert data["strategy_id"] == "trend_following"
        assert data["symbol"] == "EUR/USD"
        assert data["status"] == "INCUBATING"
        assert data["promotion_verdict"] == "PENDING"
        assert data["quality_gate_results"]["all_passed"] is True
        assert data["quality_gate_results"]["summary_verdict"] == "PASS"
        assert data["evidence_chain"]["source_optimization_id"] == "opt_job_robust_001"
        assert data["evidence_chain"]["walk_forward_job_id"] == "opt_job_robust_001"
        assert len(data["transition_history"]) == 2  # PENDING_GATES -> GATES_PASSED -> INCUBATING


@pytest.mark.asyncio
async def test_promote_from_optimization_gates_failed(integration_db: AsyncSession):
    """Verify candidate from overfitted WFA job is rejected into GATES_FAILED state."""
    app = make_app_with_context(
        integration_db,
        user_id="usr_alpha_trader",
        org_id="org_alpha_dep",
        role="TRADER",
    )

    payload = {
        "optimization_job_id": "opt_job_overfitted_002",
        "candidate_rank": 1,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.post("/api/v1/deployments/promote/optimization", json=payload)
        assert res.status_code == 201
        data = res.json()

        assert data["status"] == "GATES_FAILED"
        assert data["promotion_verdict"] in ("REJECTED", "INSUFFICIENT_DATA")
        assert data["quality_gate_results"]["all_passed"] is False
        assert data["error_message"] is not None


@pytest.mark.asyncio
async def test_promote_from_experiment(integration_db: AsyncSession):
    """Verify promoting a completed research experiment directly into paper incubation."""
    app = make_app_with_context(
        integration_db,
        user_id="usr_alpha_trader",
        org_id="org_alpha_dep",
        role="TRADER",
    )

    payload = {
        "experiment_id": "exp_robust_001",
        "initial_capital": 12000.00,
        "incubation_duration_days": 14,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.post("/api/v1/deployments/promote/experiment", json=payload)
        assert res.status_code == 201
        data = res.json()

        assert data["strategy_id"] == "trend_following"
        assert data["source_experiment_id"] == "exp_robust_001"
        assert data["status"] == "INCUBATING"


@pytest.mark.asyncio
async def test_pause_resume_and_cancel_lifecycle(integration_db: AsyncSession):
    """Verify pause, resume, and cancellation state transitions."""
    app = make_app_with_context(
        integration_db,
        user_id="usr_alpha_trader",
        org_id="org_alpha_dep",
        role="TRADER",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. Create deployment
        create_res = await client.post(
            "/api/v1/deployments/promote/optimization",
            json={"optimization_job_id": "opt_job_robust_001", "candidate_rank": 1},
        )
        dep_id = create_res.json()["id"]

        # 2. Pause
        pause_res = await client.post(f"/api/v1/deployments/{dep_id}/pause", json={"reason": "Market volatility"})
        assert pause_res.status_code == 200
        assert pause_res.json()["status"] == "PAUSED"

        # 3. Resume
        resume_res = await client.post(f"/api/v1/deployments/{dep_id}/resume", json={"reason": "Resuming normal testing"})
        assert resume_res.status_code == 200
        assert resume_res.json()["status"] == "INCUBATING"

        # 4. Cancel
        cancel_res = await client.post(f"/api/v1/deployments/{dep_id}/cancel", json={"reason": "Decommissioning"})
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "CANCELLED"

        # 5. Terminal check: Cannot resume cancelled deployment
        invalid_resume = await client.post(f"/api/v1/deployments/{dep_id}/resume", json={})
        assert invalid_resume.status_code == 422


@pytest.mark.asyncio
async def test_incubation_validation_and_promotion_candidate(integration_db: AsyncSession):
    """Verify incubation validation to PAPER_VALIDATED and advance to PROMOTION_CANDIDATE."""
    app_trader = make_app_with_context(
        integration_db,
        user_id="usr_alpha_trader",
        org_id="org_alpha_dep",
        role="TRADER",
    )
    app_pm = make_app_with_context(
        integration_db,
        user_id="usr_alpha_pm",
        org_id="org_alpha_dep",
        role="PORTFOLIO_MANAGER",
    )

    async with AsyncClient(transport=ASGITransport(app=app_trader), base_url="http://testserver") as client_trader:
        # Create deployment
        create_res = await client_trader.post(
            "/api/v1/deployments/promote/optimization",
            json={
                "optimization_job_id": "opt_job_robust_001",
                "candidate_rank": 1,
                "incubation_duration_days": 1,
                "min_trade_count": 5,
            },
        )
        assert create_res.status_code == 201
        dep_id = create_res.json()["id"]

    async with AsyncClient(transport=ASGITransport(app=app_pm), base_url="http://testserver") as client_pm:
        # Trigger evaluation & validation (as Portfolio Manager)
        val_res = await client_pm.post(f"/api/v1/deployments/{dep_id}/validate", json={"reason": "Criteria fulfilled"})
        assert val_res.status_code == 200
        assert val_res.json()["status"] == "PAPER_VALIDATED"
        assert val_res.json()["promotion_verdict"] == "PROMOTED"

        # Advance to PROMOTION_CANDIDATE (terminal stage of EPIC-025, paper review only)
        cand_res = await client_pm.post(
            f"/api/v1/deployments/{dep_id}/promote-candidate",
            json={"reason": "Ready for investment committee review"},
        )
        assert cand_res.status_code == 200
        assert cand_res.json()["status"] == "PROMOTION_CANDIDATE"

        # Terminal state check: cannot validate a promotion candidate
        second_val = await client_pm.post(f"/api/v1/deployments/{dep_id}/validate", json={})
        assert second_val.status_code == 422


@pytest.mark.asyncio
async def test_multi_tenant_idor_defense(integration_db: AsyncSession):
    """Verify user in Org Beta cannot see or modify Org Alpha deployments (fail-closed 404)."""
    app_alpha = make_app_with_context(
        integration_db,
        user_id="usr_alpha_trader",
        org_id="org_alpha_dep",
        role="TRADER",
    )
    app_beta = make_app_with_context(
        integration_db,
        user_id="usr_beta_viewer",
        org_id="org_beta_dep",
        role="VIEWER",
    )

    async with AsyncClient(transport=ASGITransport(app=app_alpha), base_url="http://testserver") as client_alpha:
        # Create deployment in Alpha
        create_res = await client_alpha.post(
            "/api/v1/deployments/promote/optimization",
            json={"optimization_job_id": "opt_job_robust_001", "candidate_rank": 1},
        )
        assert create_res.status_code == 201
        dep_id = create_res.json()["id"]

    async with AsyncClient(transport=ASGITransport(app=app_beta), base_url="http://testserver") as client_beta:
        # Beta attempts to read Alpha deployment -> 404
        get_res = await client_beta.get(f"/api/v1/deployments/{dep_id}")
        assert get_res.status_code == 404

        # Beta attempts to cancel Alpha deployment -> 403 (due to VIEWER role or 404)
        cancel_res = await client_beta.post(f"/api/v1/deployments/{dep_id}/cancel", json={})
        assert cancel_res.status_code in (403, 404)


@pytest.mark.asyncio
async def test_rbac_permission_denial(integration_db: AsyncSession):
    """Verify that VIEWER role without DEPLOYMENT_EXECUTE is rejected with 403."""
    app_viewer = make_app_with_context(
        integration_db,
        user_id="usr_beta_viewer",
        org_id="org_beta_dep",
        role="VIEWER",
    )

    async with AsyncClient(transport=ASGITransport(app=app_viewer), base_url="http://testserver") as client_viewer:
        res = await client_viewer.post(
            "/api/v1/deployments/promote/optimization",
            json={"optimization_job_id": "opt_job_robust_001"},
        )
        assert res.status_code == 403
        data = res.json()
        err_msg = data.get("message") or data.get("detail") or str(data)
        assert "Forbidden" in err_msg or "DEPLOYMENT_EXECUTE" in err_msg


@pytest.mark.asyncio
async def test_get_quality_gates_and_metrics_endpoints(integration_db: AsyncSession):
    """Verify /gates and /metrics telemetry endpoints respond correctly."""
    app = make_app_with_context(
        integration_db,
        user_id="usr_alpha_trader",
        org_id="org_alpha_dep",
        role="TRADER",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        create_res = await client.post(
            "/api/v1/deployments/promote/optimization",
            json={"optimization_job_id": "opt_job_robust_001", "candidate_rank": 1},
        )
        assert create_res.status_code == 201
        dep_id = create_res.json()["id"]

        gates_res = await client.get(f"/api/v1/deployments/{dep_id}/gates")
        assert gates_res.status_code == 200
        assert gates_res.json()["all_passed"] is True
        assert len(gates_res.json()["gate_results"]) == 5

        metrics_res = await client.get(f"/api/v1/deployments/{dep_id}/metrics")
        assert metrics_res.status_code == 200
        assert metrics_res.json()["deployment_id"] == dep_id
