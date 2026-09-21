"""Unit tests for OptimizationService in EPIC-024."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest
from apps.trading_engine.src.schemas_optimization import (
    OptimizationRunRequest,
    WalkForwardRunRequest,
)
from apps.trading_engine.src.services.optimization_service import OptimizationService
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models import OrganizationModel, UserModel


@pytest.fixture
async def async_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        org = OrganizationModel(id="org-quant", name="Quant Fund Org", slug="quant-fund-org")
        user = UserModel(id="usr-quant", username="usr_quant", email="quant@orion.internal", hashed_password="x")
        session.add(org)
        session.add(user)
        await session.commit()
        yield session

    await engine.dispose()


@pytest.fixture
def mock_historical_provider():
    provider = AsyncMock()
    base_time = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles: list[dict[str, Any]] = []
    price = Decimal("1.1000")
    for i in range(120):
        delta = Decimal("0.0012") if (i % 6 < 4) else Decimal("-0.0008")
        o = price
        c = price + delta
        h = max(o, c) + Decimal("0.0004")
        l = min(o, c) - Decimal("0.0004")
        candles.append(
            {
                "timestamp": base_time + timedelta(hours=i),
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": Decimal(1000),
            }
        )
        price = c

    provider.load_candles.return_value = candles
    return provider


@pytest.mark.asyncio
async def test_optimization_service_run_lifecycle(async_db: AsyncSession, mock_historical_provider):
    service = OptimizationService(
        session=async_db,
        historical_provider=mock_historical_provider,
    )

    req = OptimizationRunRequest(
        strategy_id="TrendFollowing",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
        max_combinations=50,
    )

    result = await service.run_optimization(
        request=req,
        organization_id="org-quant",
        user_id="usr-quant",
    )

    assert result.status == "COMPLETED"
    assert result.total_combinations > 0
    assert result.best_parameters is not None
    assert result.top_candidates is not None
    assert len(result.top_candidates) > 0
    assert result.stability_analysis is not None
    assert result.regime_breakdowns is not None


@pytest.mark.asyncio
async def test_optimization_service_walk_forward_lifecycle(async_db: AsyncSession, mock_historical_provider):
    service = OptimizationService(
        session=async_db,
        historical_provider=mock_historical_provider,
    )

    req = WalkForwardRunRequest(
        strategy_id="TrendFollowing",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
        n_windows=3,
        in_sample_ratio=0.70,
        max_combinations_per_window=50,
    )

    result = await service.run_walk_forward(
        request=req,
        organization_id="org-quant",
        user_id="usr-quant",
    )

    assert result.status == "COMPLETED"
    assert result.walk_forward_result is not None
    assert result.walk_forward_result.total_windows >= 2


@pytest.mark.asyncio
async def test_optimization_service_tenant_isolation(async_db: AsyncSession, mock_historical_provider):
    service = OptimizationService(
        session=async_db,
        historical_provider=mock_historical_provider,
    )

    req = OptimizationRunRequest(
        strategy_id="TrendFollowing",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
        max_combinations=50,
    )

    res = await service.run_optimization(request=req, organization_id="org-quant")

    # Correct tenant can view job
    job = await service.get_job(res.id, organization_id="org-quant")
    assert job.id == res.id

    # Foreign tenant receives 404
    with pytest.raises(HTTPException) as exc_info:
        await service.get_job(res.id, organization_id="foreign-org")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_optimization_service_export(async_db: AsyncSession, mock_historical_provider):
    service = OptimizationService(
        session=async_db,
        historical_provider=mock_historical_provider,
    )

    req = OptimizationRunRequest(
        strategy_id="TrendFollowing",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
        max_combinations=50,
    )

    res = await service.run_optimization(request=req, organization_id="org-quant")

    csv_data = await service.export_job(res.id, organization_id="org-quant", format_type="csv")
    assert "rank,parameters,fitness_score" in csv_data

    json_data = await service.export_job(res.id, organization_id="org-quant", format_type="json")
    assert res.id in json_data
