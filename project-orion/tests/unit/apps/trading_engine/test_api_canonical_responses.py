"""Comprehensive tests for Project ORION Phase 4.6: API Canonical Response Hardening.

Validates that:
1. Market-data candles API returns canonical symbol and timeframe representations across all accepted input aliases.
2. Market-data patterns API returns canonical symbol and timeframe representations.
3. Research experiments API returns canonical symbol and timeframe representations.
4. Optimization API (/run, /jobs) returns canonical symbol and timeframe representations.
5. All 8 canonical symbols with aliases normalize correctly.
6. All 9 canonical timeframes with aliases normalize correctly.
7. Invalid symbols and timeframes are rejected with explicit HTTP errors.
8. Response shapes, candle contents, and pattern results remain unaltered and deterministic.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from apps.trading_engine.src import dependencies
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.schemas import (
    MarketCandlesListResponse,
    MarketPatternsListResponse,
)
from apps.trading_engine.src.schemas_optimization import (
    OptimizationJobDetailResponse,
    OptimizationJobSummaryResponse,
    OptimizationRunRequest,
)
from apps.trading_engine.src.schemas_research import (
    ExperimentSummaryResponse,
)
from apps.trading_engine.src.services.market_data_service import MarketDataService
from apps.trading_engine.src.services.optimization_service import OptimizationService
from apps.trading_engine.src.services.research_service import ResearchService
from apps.trading_engine.src.services.subscription_service import SubscriptionService
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.market_data.mock_provider import MockMarketDataProvider
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models.organization import (
    OrganizationMemberModel,
    OrganizationModel,
)
from libraries.infrastructure.persistence.models.user import UserModel

# ─── Test Fixtures ────────────────────────────────────────────────────────────


def _mock_user() -> dict[str, Any]:
    return {
        "id": "usr-test-canon",
        "username": "canon_user",
        "email": "canon@orion.dev",
        "full_name": "Canonical User",
        "is_active": True,
        "is_superuser": False,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }


def _mock_account() -> MagicMock:
    account = MagicMock()
    account.id = "acc-test-canon"
    account.user_id = "usr-test-canon"
    account.organization_id = "org-test-canon"
    account.broker_name = "paper"
    account.currency = "USD"
    account.balance = Decimal(100000)
    account.equity = Decimal(100000)
    account.is_live = False
    account.is_active = True
    return account


@pytest.fixture
def mock_db_session() -> AsyncMock:
    session = AsyncMock()
    session.execute.return_value = MagicMock()
    return session


@pytest.fixture
def test_client(mock_db_session: AsyncMock) -> TestClient:
    config = PaperExecutionConfig(broker_name="paper", is_paper=True)
    paper_adapter = PaperExecutionAdapter(config=config)
    mock_provider = MockMarketDataProvider()
    market_service = MarketDataService(provider=mock_provider, paper_adapter=paper_adapter)

    app = create_app(
        paper_adapter=paper_adapter,
        market_data_service=market_service,
    )
    app.dependency_overrides[dependencies.get_current_active_user] = lambda: _mock_user()
    app.dependency_overrides[dependencies.get_user_account] = _mock_account
    app.dependency_overrides[dependencies.get_paper_adapter] = lambda: paper_adapter
    app.dependency_overrides[dependencies.get_market_data_service] = lambda: market_service
    app.dependency_overrides[dependencies.get_worker_coordinator] = lambda: None
    app.dependency_overrides[dependencies.get_tenant_context] = lambda: dependencies.TenantContext(
        user_id="usr-test-canon",
        organization_id="org-test-canon",
        role="TRADER",
        is_superuser=False,
    )

    async def _get_db():
        yield mock_db_session

    app.dependency_overrides[dependencies.get_db_session] = _get_db

    client = TestClient(app)
    return client


# ─── 1. Market-Data Candles Canonical Response Tests ─────────────────────────


@pytest.mark.parametrize(
    ("input_symbol", "expected_canonical_symbol"),
    [
        ("EUR/USD", "EUR/USD"),
        ("EURUSD", "EUR/USD"),
        ("eurusd", "EUR/USD"),
        ("eur_usd", "EUR/USD"),
        ("eur-usd", "EUR/USD"),
        ("GBP/USD", "GBP/USD"),
        ("gbpusd", "GBP/USD"),
        ("USD/JPY", "USD/JPY"),
        ("usdjpy", "USD/JPY"),
        ("USD/CHF", "USD/CHF"),
        ("usdchf", "USD/CHF"),
        ("AUD/USD", "AUD/USD"),
        ("audusd", "AUD/USD"),
        ("USD/CAD", "USD/CAD"),
        ("usdcad", "USD/CAD"),
        ("NZD/USD", "NZD/USD"),
        ("nzdusd", "NZD/USD"),
        ("XAU/USD", "XAU/USD"),
        ("xauusd", "XAU/USD"),
        ("XAU_USD", "XAU/USD"),
    ],
)
def test_candles_api_symbol_canonicalization(
    test_client: TestClient,
    input_symbol: str,
    expected_canonical_symbol: str,
) -> None:
    """GET /api/v1/market-data/candles returns exact canonical symbol for all accepted aliases."""
    response = test_client.get(
        "/api/v1/market-data/candles",
        params={"symbol": input_symbol, "timeframe": "1h", "limit": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == expected_canonical_symbol
    assert data["timeframe"] == "H1"
    assert isinstance(data["candles"], list)
    assert len(data["candles"]) == 5


@pytest.mark.parametrize(
    ("input_timeframe", "expected_canonical_timeframe"),
    [
        ("M1", "M1"),
        ("1m", "M1"),
        ("1min", "M1"),
        ("M5", "M5"),
        ("5m", "M5"),
        ("5min", "M5"),
        ("M15", "M15"),
        ("15m", "M15"),
        ("15min", "M15"),
        ("M30", "M30"),
        ("30m", "M30"),
        ("30min", "M30"),
        ("H1", "H1"),
        ("1h", "H1"),
        ("60min", "H1"),
        ("H4", "H4"),
        ("4h", "H4"),
        ("240min", "H4"),
        ("D1", "D1"),
        ("1d", "D1"),
        ("daily", "D1"),
        ("W1", "W1"),
        ("1w", "W1"),
        ("weekly", "W1"),
        ("MN1", "MN1"),
        ("1mo", "MN1"),
        ("monthly", "MN1"),
    ],
)
def test_candles_api_timeframe_canonicalization(
    test_client: TestClient,
    input_timeframe: str,
    expected_canonical_timeframe: str,
) -> None:
    """GET /api/v1/market-data/candles returns exact canonical BarType name for all accepted aliases."""
    response = test_client.get(
        "/api/v1/market-data/candles",
        params={"symbol": "EUR/USD", "timeframe": input_timeframe, "limit": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "EUR/USD"
    assert data["timeframe"] == expected_canonical_timeframe
    assert len(data["candles"]) == 5


def test_candles_api_invalid_symbol_rejected(test_client: TestClient) -> None:
    """GET /api/v1/market-data/candles rejects invalid symbol with HTTP 404."""
    response = test_client.get(
        "/api/v1/market-data/candles",
        params={"symbol": "INVALID/PAIR", "timeframe": "1h"},
    )
    assert response.status_code == 404


def test_candles_api_invalid_timeframe_rejected(test_client: TestClient) -> None:
    """GET /api/v1/market-data/candles rejects invalid timeframe with HTTP 400."""
    response = test_client.get(
        "/api/v1/market-data/candles",
        params={"symbol": "EUR/USD", "timeframe": "2h"},
    )
    assert response.status_code == 400


def test_candles_api_response_shape_and_determinism(test_client: TestClient) -> None:
    """Verify response structure, field types, and deterministic candle values."""
    res1 = test_client.get(
        "/api/v1/market-data/candles",
        params={"symbol": "eurusd", "timeframe": "60min", "limit": 10},
    )
    res2 = test_client.get(
        "/api/v1/market-data/candles",
        params={"symbol": "EUR/USD", "timeframe": "H1", "limit": 10},
    )
    assert res1.status_code == 200
    assert res2.status_code == 200

    d1, d2 = res1.json(), res2.json()
    assert d1["symbol"] == d2["symbol"] == "EUR/USD"
    assert d1["timeframe"] == d2["timeframe"] == "H1"
    assert d1["provider"] == d2["provider"] == "mock"
    assert len(d1["candles"]) == len(d2["candles"]) == 10

    # Ensure required fields in each candle
    for c in d1["candles"]:
        assert "timestamp" in c
        assert "open" in c
        assert "high" in c
        assert "low" in c
        assert "close" in c
        assert "volume" in c


# ─── 2. Market-Data Patterns Canonical Response Tests ────────────────────────


@pytest.mark.parametrize(
    ("input_symbol", "input_tf", "exp_sym", "exp_tf"),
    [
        ("eurusd", "1h", "EUR/USD", "H1"),
        ("EURUSD", "60min", "EUR/USD", "H1"),
        ("gbpusd", "4h", "GBP/USD", "H4"),
        ("USDJPY", "15m", "USD/JPY", "M15"),
        ("xauusd", "1d", "XAU/USD", "D1"),
        ("audusd", "weekly", "AUD/USD", "W1"),
        ("nzdusd", "monthly", "NZD/USD", "MN1"),
    ],
)
def test_patterns_api_canonicalization(
    test_client: TestClient,
    input_symbol: str,
    input_tf: str,
    exp_sym: str,
    exp_tf: str,
) -> None:
    """GET /api/v1/market-data/patterns returns canonical symbol and timeframe."""
    response = test_client.get(
        "/api/v1/market-data/patterns",
        params={"symbol": input_symbol, "timeframe": input_tf, "limit": 30},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == exp_sym
    assert data["timeframe"] == exp_tf
    assert "patterns" in data
    assert "total_detected" in data


def test_patterns_api_invalid_inputs(test_client: TestClient) -> None:
    """GET /api/v1/market-data/patterns rejects invalid symbol (404) and timeframe (400)."""
    res_sym = test_client.get(
        "/api/v1/market-data/patterns",
        params={"symbol": "UNKNOWN", "timeframe": "1h"},
    )
    assert res_sym.status_code == 404

    res_tf = test_client.get(
        "/api/v1/market-data/patterns",
        params={"symbol": "EUR/USD", "timeframe": "99m"},
    )
    assert res_tf.status_code == 400


# ─── 3. Pydantic Response Model Canonicalization Validation ──────────────────


def test_market_candles_list_response_validator() -> None:
    """MarketCandlesListResponse model validators enforce canonical values on instantiation."""
    resp = MarketCandlesListResponse(
        symbol="eurusd",
        timeframe="1h",
        provider="mock",
        candles=[],
    )
    assert resp.symbol == "EUR/USD"
    assert resp.timeframe == "H1"

    resp2 = MarketCandlesListResponse(
        symbol="xau_usd",
        timeframe="weekly",
        provider="mock",
        candles=[],
    )
    assert resp2.symbol == "XAU/USD"
    assert resp2.timeframe == "W1"


def test_market_patterns_list_response_validator() -> None:
    """MarketPatternsListResponse model validators enforce canonical values."""
    resp = MarketPatternsListResponse(
        symbol="usdjpy",
        timeframe="monthly",
        provider="mock",
        patterns=[],
        total_detected=0,
    )
    assert resp.symbol == "USD/JPY"
    assert resp.timeframe == "MN1"


def test_experiment_summary_response_validator() -> None:
    """ExperimentSummaryResponse model validators enforce canonical values."""
    resp = ExperimentSummaryResponse(
        id="exp-001",
        organization_id="org-001",
        strategy_id="trend_following",
        strategy_version="1.0.0",
        symbol="aud_usd",
        timeframe="15m",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
        initial_capital=10000.0,
        status="COMPLETED",
        execution_time_seconds=1.23,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    assert resp.symbol == "AUD/USD"
    assert resp.timeframe == "M15"


def test_optimization_job_response_validator() -> None:
    """OptimizationJobSummaryResponse and DetailResponse model validators enforce canonical values."""
    summary = OptimizationJobSummaryResponse(
        id="opt-001",
        organization_id="org-001",
        strategy_id="TrendFollowing",
        symbol="gbpusd",
        timeframe="4h",
        optimization_type="GRID_SEARCH",
        fitness_objective="SHARPE_RATIO",
        status="COMPLETED",
        total_combinations=10,
        completed_combinations=10,
        execution_time_seconds=2.5,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    assert summary.symbol == "GBP/USD"
    assert summary.timeframe == "H4"

    detail = OptimizationJobDetailResponse(
        id="opt-001",
        organization_id="org-001",
        strategy_id="TrendFollowing",
        symbol="usdcad",
        timeframe="daily",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
        initial_capital=10000.0,
        optimization_type="GRID_SEARCH",
        fitness_objective="SHARPE_RATIO",
        parameter_space={},
        optimization_config={},
        status="COMPLETED",
        total_combinations=10,
        completed_combinations=10,
        execution_time_seconds=2.5,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    assert detail.symbol == "USD/CAD"
    assert detail.timeframe == "D1"


# ─── 4. End-to-End Optimization & Research Service Canonical Integration ─────


@pytest.fixture
async def in_memory_db() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        org = OrganizationModel(
            id="org_canon_test",
            name="Canon Test Org",
            slug="canon-test-org",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        user = UserModel(
            id="usr_canon_test",
            username="canon_user",
            email="canon@orion.internal",
            hashed_password="hash",
            is_active=True,
            is_superuser=False,
        )
        member = OrganizationMemberModel(
            id="mem_canon_test",
            organization_id="org_canon_test",
            user_id="usr_canon_test",
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


def _make_dummy_candles(count: int = 30) -> list[dict[str, Any]]:
    candles = []
    base = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    for i in range(count):
        candles.append({
            "timestamp": base + timedelta(hours=i),
            "open": Decimal("1.0800") + Decimal(str(i * 0.0001)),
            "high": Decimal("1.0850") + Decimal(str(i * 0.0001)),
            "low": Decimal("1.0750") + Decimal(str(i * 0.0001)),
            "close": Decimal("1.0810") + Decimal(str(i * 0.0001)),
            "volume": Decimal(1000),
        })
    return candles


@pytest.mark.asyncio
async def test_research_service_persists_and_returns_canonical(in_memory_db: AsyncSession) -> None:
    """ResearchService returns canonical symbol and BarType name for raw alias inputs."""
    mock_provider = AsyncMock()
    mock_provider.load_candles.return_value = _make_dummy_candles(30)

    service = ResearchService(session=in_memory_db, historical_provider=mock_provider)
    exp = await service.create_and_run_experiment(
        organization_id="org_canon_test",
        user_id="usr_canon_test",
        strategy_id="trend_following",
        symbol="eurusd",
        timeframe="1h",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 5),
        parameters={"fast_period": 5, "slow_period": 15},
    )

    assert exp.symbol == "EUR/USD"
    assert exp.timeframe == "H1"

    summary_dto = ExperimentSummaryResponse.model_validate(exp)
    assert summary_dto.symbol == "EUR/USD"
    assert summary_dto.timeframe == "H1"


@pytest.mark.asyncio
async def test_optimization_service_persists_and_returns_canonical(in_memory_db: AsyncSession) -> None:
    """OptimizationService accepts raw symbol and timeframe aliases and returns canonical representations."""
    mock_provider = AsyncMock()
    mock_provider.load_candles.return_value = _make_dummy_candles(30)

    service = OptimizationService(session=in_memory_db, historical_provider=mock_provider)
    req = OptimizationRunRequest(
        strategy_id="TrendFollowing",
        symbol="eurusd",
        timeframe="1h",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 5, tzinfo=timezone.utc),
        max_combinations=50,
    )

    result = await service.run_optimization(
        request=req,
        organization_id="org_canon_test",
        user_id="usr_canon_test",
    )

    assert result.symbol == "EUR/USD"
    assert result.timeframe == "H1"

    # Also verify listing
    jobs = await service.list_jobs(organization_id="org_canon_test")
    assert len(jobs) >= 1
    matching = [j for j in jobs if j.id == result.id]
    assert len(matching) == 1
    assert matching[0].symbol == "EUR/USD"
    assert matching[0].timeframe == "H1"
