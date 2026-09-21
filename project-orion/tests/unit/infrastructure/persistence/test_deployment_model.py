"""Unit tests for StrategyDeploymentModel persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models.deployment import (
    StrategyDeploymentModel,
)
from libraries.infrastructure.persistence.models.organization import OrganizationModel
from libraries.infrastructure.persistence.models.user import UserModel


@pytest.fixture
async def async_session() -> AsyncSession:
    """Provide an in-memory SQLite database session with all tables created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        # Create organization and user for foreign keys
        org = OrganizationModel(
            id="org_persist_test",
            name="Persist Test Org",
            slug="persist-test",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        user = UserModel(
            id="usr_persist_test",
            username="persist_user",
            email="persist@test.com",
            hashed_password="hash",
            is_active=True,
            is_superuser=False,
        )
        session.add(org)
        session.add(user)
        await session.commit()
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_strategy_deployment_model_crud(async_session: AsyncSession):
    """Verify create, read, update, and query operations on StrategyDeploymentModel."""
    now = datetime.now(timezone.utc)
    dep = StrategyDeploymentModel(
        id="dep-test-123",
        organization_id="org_persist_test",
        created_by="usr_persist_test",
        strategy_id="trend_following",
        strategy_version="1.0.0",
        symbol="EUR/USD",
        timeframe="H1",
        status="INCUBATING",
        parameters={"fast_period": 10, "slow_period": 30},
        evidence_chain={"strategy_id": "trend_following", "version": "1.0.0"},
        quality_gate_policy={"policy_id": "standard_v1"},
        quality_gate_results={"all_passed": True, "summary_verdict": "PASS"},
        initial_capital=Decimal("15000.00"),
        incubation_config={"min_duration_days": 7, "min_trade_count": 10},
        incubation_metrics={"net_pnl": "250.00", "total_trades": 12},
        benchmark_comparison={"return_ratio": 0.85},
        backtest_benchmark={"total_return_pct": 5.0},
        promotion_verdict="PENDING",
        transition_history=[
            {
                "from_status": "PENDING_GATES",
                "to_status": "INCUBATING",
                "actor_id": "usr_persist_test",
                "timestamp": now.isoformat(),
            }
        ],
        started_at=now,
        created_at=now,
        updated_at=now,
    )

    async_session.add(dep)
    await async_session.commit()

    # Query back
    stmt = select(StrategyDeploymentModel).where(StrategyDeploymentModel.id == "dep-test-123")
    res = await async_session.execute(stmt)
    retrieved = res.scalar_one_or_none()

    assert retrieved is not None
    assert retrieved.id == "dep-test-123"
    assert retrieved.strategy_id == "trend_following"
    assert retrieved.parameters == {"fast_period": 10, "slow_period": 30}
    assert retrieved.initial_capital == Decimal("15000.00")
    assert retrieved.incubation_config["min_duration_days"] == 7
    assert retrieved.quality_gate_results["all_passed"] is True
    assert len(retrieved.transition_history) == 1
