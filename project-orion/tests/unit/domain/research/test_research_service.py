"""Unit tests for ResearchService orchestration (EPIC-023 Phases 21-24, 31, 34)."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from apps.trading_engine.src.services.research_service import ResearchService
from apps.trading_engine.src.services.subscription_service import SubscriptionService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from libraries.domain.research.models import ResearchExperimentStatus
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models.organization import (
    OrganizationMemberModel,
    OrganizationModel,
)
from libraries.infrastructure.persistence.models.user import UserModel


@pytest.fixture
async def test_session() -> AsyncSession:
    """Isolated async SQLite database session for ResearchService testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        # Pre-seed Organization and User
        org = OrganizationModel(
            id="org_quant_001",
            name="Quant Fund Alpha",
            slug="quant-fund-alpha",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        user = UserModel(
            id="usr_researcher_001",
            username="quant_researcher",
            email="research@quantalpha.dev",
            hashed_password="hashed_pass",
            is_active=True,
            is_superuser=False,
        )
        member = OrganizationMemberModel(
            id="mem_res_001",
            organization_id="org_quant_001",
            user_id="usr_researcher_001",
            role="RESEARCHER",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add_all([org, user, member])

        sub_service = SubscriptionService(session)
        await sub_service._ensure_canonical_plans()
        await session.commit()
        yield session


@pytest.mark.asyncio
async def test_research_service_catalogue(test_session: AsyncSession) -> None:
    """ResearchService lists available strategies and retrieves details."""
    service = ResearchService(session=test_session)
    strategies = await service.list_available_strategies()
    assert len(strategies) >= 4
    strat_ids = {s["strategy_id"] for s in strategies}
    assert "trend_following" in strat_ids

    detail = await service.get_strategy_detail("trend_following")
    assert detail["strategy_id"] == "trend_following"
    assert "parameters" in detail
    assert any(p["name"] == "fast_period" for p in detail["parameters"])


@pytest.mark.asyncio
async def test_create_and_run_experiment_lifecycle(test_session: AsyncSession) -> None:
    """Executes a backtest experiment end-to-end, persisting metrics, curve, and trades."""
    service = ResearchService(session=test_session)
    exp = await service.create_and_run_experiment(
        organization_id="org_quant_001",
        user_id="usr_researcher_001",
        strategy_id="trend_following",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 15),
        initial_capital=Decimal("10000.00"),
        parameters={"fast_period": 5, "slow_period": 15},
    )

    assert exp.id.startswith("exp-")
    assert exp.status == ResearchExperimentStatus.COMPLETED.value
    assert exp.metrics is not None
    assert exp.metrics["initial_capital"] == 10000.0
    assert exp.metrics["final_balance"] > 0.0
    assert exp.execution_time_seconds > 0.0
    assert exp.completed_at is not None
    assert len(exp.equity_curve) > 0
    assert isinstance(exp.warnings, list)


@pytest.mark.asyncio
async def test_tenant_isolation_boundary(test_session: AsyncSession) -> None:
    """Accessing an experiment belonging to another tenant must raise KeyError."""
    service = ResearchService(session=test_session)
    exp = await service.create_and_run_experiment(
        organization_id="org_quant_001",
        user_id="usr_researcher_001",
        strategy_id="trend_following",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 10),
    )

    # Valid tenant access
    retrieved = await service.get_experiment(exp.id, organization_id="org_quant_001")
    assert retrieved.id == exp.id

    # Foreign tenant access is denied
    with pytest.raises(KeyError, match="not found or inaccessible"):
        await service.get_experiment(exp.id, organization_id="org_competitor_999")


@pytest.mark.asyncio
async def test_list_experiments_and_status_filtering(test_session: AsyncSession) -> None:
    """Experiments are listed with pagination and optional status filter."""
    service = ResearchService(session=test_session)
    exp = await service.create_and_run_experiment(
        organization_id="org_quant_001",
        user_id="usr_researcher_001",
        strategy_id="breakout",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 10),
    )

    items, total = await service.list_experiments(
        organization_id="org_quant_001",
        status=ResearchExperimentStatus.COMPLETED.value,
    )
    assert total >= 1
    assert any(i.id == exp.id for i in items)

    # Filter with non-matching status
    items_none, total_none = await service.list_experiments(
        organization_id="org_quant_001",
        status="RUNNING",
    )
    assert total_none == 0
    assert len(items_none) == 0


@pytest.mark.asyncio
async def test_compare_experiments(test_session: AsyncSession) -> None:
    """Comparing completed experiments produces comparison matrix and normalized curves."""
    service = ResearchService(session=test_session)
    exp1 = await service.create_and_run_experiment(
        organization_id="org_quant_001",
        user_id="usr_researcher_001",
        strategy_id="trend_following",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 10),
        parameters={"fast_period": 5, "slow_period": 15},
    )
    exp2 = await service.create_and_run_experiment(
        organization_id="org_quant_001",
        user_id="usr_researcher_001",
        strategy_id="mean_reversion",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 10),
        parameters={"lookback_period": 14, "entry_threshold": 1.5},
    )

    comp = await service.compare_experiments(
        experiment_ids=[exp1.id, exp2.id],
        organization_id="org_quant_001",
    )
    assert "comparison" in comp
    assert len(comp["comparison"]) == 2
    assert "normalized_curves" in comp
    assert exp1.id in comp["normalized_curves"]
    assert exp2.id in comp["normalized_curves"]


@pytest.mark.asyncio
async def test_export_experiment(test_session: AsyncSession) -> None:
    """Exporting experiment produces CSV and JSON formats."""
    service = ResearchService(session=test_session)
    exp = await service.create_and_run_experiment(
        organization_id="org_quant_001",
        user_id="usr_researcher_001",
        strategy_id="trend_following",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 10),
    )

    # CSV Export
    csv_content, csv_mime, _csv_name = await service.export_experiment(
        experiment_id=exp.id,
        organization_id="org_quant_001",
        export_format="csv",
    )
    assert csv_mime == "text/csv"
    assert "EXPERIMENT SUMMARY" in csv_content
    assert exp.id in csv_content

    # JSON Export
    json_content, json_mime, _json_name = await service.export_experiment(
        experiment_id=exp.id,
        organization_id="org_quant_001",
        export_format="json",
    )
    assert json_mime == "application/json"
    parsed = json.loads(json_content)
    assert parsed["id"] == exp.id
    assert "metrics" in parsed
