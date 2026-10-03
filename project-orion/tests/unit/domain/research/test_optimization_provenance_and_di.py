"""Comprehensive tests for MarketDataService Dependency Injection and Dataset Provenance in OptimizationService."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.trading_engine.src.dependencies import get_optimization_service
from apps.trading_engine.src.schemas_optimization import (
    OptimizationRunRequest,
    WalkForwardRunRequest,
)
from apps.trading_engine.src.services.optimization_service import OptimizationService
from libraries.domain.market_data.models import OHLCV
from libraries.domain.research.models import DataSourceMode
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models.optimization import OptimizationJobModel
from libraries.infrastructure.persistence.models.organization import OrganizationModel
from libraries.infrastructure.persistence.models.user import UserModel


@pytest.fixture
async def test_session() -> AsyncSession:
    """Isolated async SQLite database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        org = OrganizationModel(
            id="org_quant_opt",
            name="Quant Fund Opt",
            slug="quant-fund-opt",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        user = UserModel(
            id="usr_quant_opt",
            username="quant_opt_researcher",
            email="opt@quantalpha.dev",
            hashed_password="hashed_pass",
            is_active=True,
        )
        session.add(org)
        session.add(user)
        await session.commit()
        yield session

    await engine.dispose()


def _generate_mock_ohlcv(
    symbol: str = "EUR/USD",
    count: int = 150,
    start: datetime | None = None,
) -> list[OHLCV]:
    """Generate deterministic OHLCV candles exhibiting cyclical movement for strategy backtesting."""
    start_dt = start or datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = []
    price = Decimal("1.1000")
    for i in range(count):
        delta = Decimal("0.0012") if (i % 6 < 4) else Decimal("-0.0008")
        o = price
        c = price + delta
        h = max(o, c) + Decimal("0.0004")
        l = min(o, c) - Decimal("0.0004")
        candles.append(
            OHLCV(
                symbol=symbol,
                timestamp=start_dt + timedelta(hours=i),
                open=o,
                high=h,
                low=l,
                close=c,
                volume=Decimal(1000),
            )
        )
        price = c
    return candles


# ─── 1. Dependency Injection Wiring ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_optimization_dependency_injection_wires_market_data_service(
    test_session: AsyncSession,
) -> None:
    """Verify get_optimization_service cleanly injects market_data_service from request.app.state."""
    mock_market_data = MagicMock()
    mock_market_data.provider_name = "twelvedata"

    mock_request = MagicMock()
    mock_request.app.state.market_data_service = mock_market_data

    service: OptimizationService = get_optimization_service(
        session=test_session,
        request=mock_request,
    )

    assert isinstance(service, OptimizationService)
    assert service.session is test_session
    assert service.market_data_service is mock_market_data
    assert service.provider._service is mock_market_data


# ─── 2. Optimization Sweep External Provider Provenance ──────────────────────


@pytest.mark.asyncio
async def test_optimization_service_external_provider_provenance_persisted(
    test_session: AsyncSession,
) -> None:
    """Verify optimization sweep captures external dataset provenance and persists into DB."""
    mock_service = MagicMock()
    mock_service.provider.provider_name = "twelvedata"
    mock_service.get_candles = AsyncMock(
        return_value=_generate_mock_ohlcv("EUR/USD", count=150)
    )

    service = OptimizationService(
        session=test_session,
        market_data_service=mock_service,
    )

    req = OptimizationRunRequest(
        strategy_id="TrendFollowing",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
        max_combinations=20,
    )

    result = await service.run_optimization(
        request=req,
        organization_id="org_quant_opt",
        user_id="usr_quant_opt",
    )

    assert result.status == "COMPLETED"
    assert result.dataset_provenance is not None

    prov = result.dataset_provenance
    assert prov["data_source"] == "external"
    assert prov["provider"] == "twelvedata"
    assert prov["symbol"] == "EUR/USD"
    assert prov["candle_count"] == 150
    assert prov["synthetic"] is False
    assert prov["deterministic"] is False
    assert prov["dataset_hash"] is not None

    # Verify database model directly
    stmt = select(OptimizationJobModel).where(OptimizationJobModel.id == result.id)
    db_res = await test_session.execute(stmt)
    job = db_res.scalar_one()

    assert job.dataset_provenance == prov
    assert "provenance" in job.optimization_config
    assert job.optimization_config["provenance"] == prov


# ─── 3. External Provider Failure Fails Explicitly ────────────────────────────


@pytest.mark.asyncio
async def test_optimization_service_external_provider_failure_fails_explicitly(
    test_session: AsyncSession,
) -> None:
    """Verify optimization sweep fails explicitly without silent synthetic PRNG fallback."""
    mock_service = MagicMock()
    mock_service.provider.provider_name = "twelvedata"
    mock_service.get_candles = AsyncMock(
        side_effect=RuntimeError("TwelveData endpoint connection timeout")
    )

    service = OptimizationService(
        session=test_session,
        market_data_service=mock_service,
    )

    req = OptimizationRunRequest(
        strategy_id="TrendFollowing",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
        max_combinations=20,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.run_optimization(
            request=req,
            organization_id="org_quant_opt",
            user_id="usr_quant_opt",
        )

    assert exc_info.value.status_code == 422
    assert "Historical data preparation failed" in exc_info.value.detail
    assert "TwelveData endpoint connection timeout" in exc_info.value.detail

    # Verify no completed job exists in the database
    stmt = select(OptimizationJobModel).where(OptimizationJobModel.organization_id == "org_quant_opt")
    db_res = await test_session.execute(stmt)
    jobs = db_res.scalars().all()
    completed_jobs = [j for j in jobs if j.status == "COMPLETED"]
    assert len(completed_jobs) == 0


# ─── 4. Empty Provider Response Fails Explicitly ─────────────────────────────


@pytest.mark.asyncio
async def test_optimization_service_empty_candles_fails_explicitly(
    test_session: AsyncSession,
) -> None:
    """Verify empty candle list raises explicit 422 instead of silent PRNG fallback."""
    mock_service = MagicMock()
    mock_service.provider.provider_name = "twelvedata"
    mock_service.get_candles = AsyncMock(return_value=[])

    service = OptimizationService(
        session=test_session,
        market_data_service=mock_service,
    )

    req = OptimizationRunRequest(
        strategy_id="TrendFollowing",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
        max_combinations=20,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.run_optimization(
            request=req,
            organization_id="org_quant_opt",
            user_id="usr_quant_opt",
        )

    assert exc_info.value.status_code == 422
    assert "zero candles" in exc_info.value.detail


# ─── 5. Explicit Synthetic Mode ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_optimization_service_explicit_synthetic_mode(
    test_session: AsyncSession,
) -> None:
    """Verify explicit synthetic mode generates PRNG candles and records synthetic provenance."""
    service = OptimizationService(session=test_session)

    req = OptimizationRunRequest(
        strategy_id="TrendFollowing",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 5, tzinfo=timezone.utc),
        max_combinations=50,
        data_source="synthetic",
    )

    result = await service.run_optimization(
        request=req,
        organization_id="org_quant_opt",
        user_id="usr_quant_opt",
    )

    assert result.status == "COMPLETED"
    prov = result.dataset_provenance
    assert prov is not None
    assert prov["data_source"] == "synthetic"
    assert prov["provider"] == "deterministic_prng"
    assert prov["synthetic"] is True
    assert prov["deterministic"] is True


# ─── 6. Walk-Forward Analysis External Provider Provenance ────────────────────


@pytest.mark.asyncio
async def test_walk_forward_external_provider_provenance_persisted(
    test_session: AsyncSession,
) -> None:
    """Verify Walk-Forward Analysis captures external dataset provenance."""
    mock_service = MagicMock()
    mock_service.provider.provider_name = "twelvedata"
    mock_service.get_candles = AsyncMock(
        return_value=_generate_mock_ohlcv("EUR/USD", count=150)
    )

    service = OptimizationService(
        session=test_session,
        market_data_service=mock_service,
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
        organization_id="org_quant_opt",
        user_id="usr_quant_opt",
    )

    assert result.status == "COMPLETED"
    assert result.dataset_provenance is not None
    prov = result.dataset_provenance
    assert prov["data_source"] == "external"
    assert prov["provider"] == "twelvedata"
    assert prov["candle_count"] == 150

    # Verify DB persistence
    stmt = select(OptimizationJobModel).where(OptimizationJobModel.id == result.id)
    db_res = await test_session.execute(stmt)
    job = db_res.scalar_one()
    assert job.dataset_provenance == prov
    assert job.optimization_config["provenance"] == prov


# ─── 7. Walk-Forward External Provider Failure Fails Explicitly ──────────────


@pytest.mark.asyncio
async def test_walk_forward_external_provider_failure_fails_explicitly(
    test_session: AsyncSession,
) -> None:
    """Verify Walk-Forward Analysis fails explicitly without silent synthetic PRNG fallback."""
    mock_service = MagicMock()
    mock_service.provider.provider_name = "twelvedata"
    mock_service.get_candles = AsyncMock(
        side_effect=ConnectionError("Provider network unreachable")
    )

    service = OptimizationService(
        session=test_session,
        market_data_service=mock_service,
    )

    req = WalkForwardRunRequest(
        strategy_id="TrendFollowing",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
        n_windows=3,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.run_walk_forward(
            request=req,
            organization_id="org_quant_opt",
            user_id="usr_quant_opt",
        )

    assert exc_info.value.status_code == 422
    assert "Historical data preparation failed" in exc_info.value.detail


# ─── 8. Walk-Forward Explicit Synthetic Mode ──────────────────────────────────


@pytest.mark.asyncio
async def test_walk_forward_explicit_synthetic_mode(
    test_session: AsyncSession,
) -> None:
    """Verify Walk-Forward Analysis with data_source='synthetic' records synthetic provenance."""
    service = OptimizationService(session=test_session)

    req = WalkForwardRunRequest(
        strategy_id="TrendFollowing",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
        n_windows=3,
        in_sample_ratio=0.70,
        max_combinations_per_window=50,
        data_source="synthetic",
    )

    result = await service.run_walk_forward(
        request=req,
        organization_id="org_quant_opt",
        user_id="usr_quant_opt",
    )

    assert result.status == "COMPLETED"
    prov = result.dataset_provenance
    assert prov is not None
    assert prov["data_source"] == "synthetic"
    assert prov["provider"] == "deterministic_prng"
    assert prov["synthetic"] is True


# ─── 9. Legacy Job Backward Compatibility ─────────────────────────────────────


@pytest.mark.asyncio
async def test_legacy_optimization_job_without_provenance_still_loads(
    test_session: AsyncSession,
) -> None:
    """Verify legacy DB jobs without 'provenance' in optimization_config load safely with None."""
    job_id = "opt-legacy-001"
    legacy_job = OptimizationJobModel(
        id=job_id,
        organization_id="org_quant_opt",
        created_by="usr_quant_opt",
        strategy_id="trend_following",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
        initial_capital=Decimal("10000.00"),
        optimization_type="GRID_SEARCH",
        fitness_objective="SHARPE_RATIO",
        parameter_space={"strategy_id": "trend_following", "ranges": []},
        optimization_config={"max_combinations": 50, "commission": 7.0},  # No provenance key
        status="COMPLETED",
        total_combinations=50,
        completed_combinations=50,
        execution_time_seconds=1.23,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    test_session.add(legacy_job)
    await test_session.commit()

    assert legacy_job.dataset_provenance is None

    service = OptimizationService(session=test_session)
    detail = await service.get_job(job_id=job_id, organization_id="org_quant_opt")

    assert detail.id == job_id
    assert detail.dataset_provenance is None
    assert detail.optimization_config["max_combinations"] == 50


# ─── 10. Credentials Leakage Prevention ───────────────────────────────────────


@pytest.mark.asyncio
async def test_no_credentials_leakage_in_optimization_error(
    test_session: AsyncSession,
) -> None:
    """Verify raw API keys or tokens are scrubbed from error details in optimization exceptions."""
    secret_key = "secret_apikey_9876543210_token"
    mock_service = MagicMock()
    mock_service.provider.provider_name = "twelvedata"
    mock_service.get_candles = AsyncMock(
        side_effect=RuntimeError(f"HTTP 401 Unauthorized with token={secret_key} and apikey={secret_key}")
    )

    service = OptimizationService(
        session=test_session,
        market_data_service=mock_service,
    )

    req = OptimizationRunRequest(
        strategy_id="TrendFollowing",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
        max_combinations=50,
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.run_optimization(
            request=req,
            organization_id="org_quant_opt",
            user_id="usr_quant_opt",
        )

    err_detail = exc_info.value.detail
    assert secret_key not in err_detail
    assert "[REDACTED]" in err_detail
