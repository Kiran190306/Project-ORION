"""Tests for Canonical Timeframe Bridge & Propagation (PROJECT ORION Phase 4.1/4.2).

Validates:
1. Every BarType -> Timeframe mapping (all 9).
2. Every Timeframe -> BarType mapping (all 9).
3. Round-trip tests for all 9 timeframes.
4. API-style aliases (1m, m1, 5m, m5, 15m, m15, 30m, m30, 1h, h1, 4h, h4, 1d, d1, 1w, w1, weekly, 1mo, mn1, monthly).
5. Invalid timeframe rejection.
6. ResearchService M1 propagation.
7. ResearchService M15 propagation.
8. ResearchService H4 propagation.
9. ResearchService D1 propagation.
10. ResearchService W1 propagation.
11. ResearchService MN1 propagation.
12. Optimization M15 propagation.
13. Optimization H4 propagation.
14. Walk-forward M15 propagation.
15. Walk-forward H4 propagation.
16. Explicit verification that invalid timeframe does NOT become H1.
17. Provenance timeframe consistency.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest
from apps.trading_engine.src.schemas_optimization import (
    OptimizationRunRequest,
    WalkForwardRunRequest,
)
from apps.trading_engine.src.services.optimization_service import OptimizationService
from apps.trading_engine.src.services.research_service import ResearchService
from apps.trading_engine.src.services.subscription_service import SubscriptionService
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from libraries.domain.backtesting.historical_data import (
    DatasetProvenance,
    MarketDataServiceHistoricalProvider,
)
from libraries.domain.backtesting.models import Timeframe
from libraries.domain.market_data.exceptions import UnsupportedBarTypeError
from libraries.domain.market_data.models import BarType
from libraries.domain.market_data.normalization import (
    bar_type_to_timeframe,
    normalize_timeframe,
    timeframe_to_bar_type,
)
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models.organization import (
    OrganizationMemberModel,
    OrganizationModel,
)
from libraries.infrastructure.persistence.models.user import UserModel


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def test_session() -> AsyncSession:
    """Isolated in-memory SQLite database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        org = OrganizationModel(
            id="org_test_prop",
            name="Prop Test Org",
            slug="prop-test-org",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        user = UserModel(
            id="usr_test_prop",
            username="test_prop_user",
            email="prop@orion.internal",
            hashed_password="hash",
            is_active=True,
            is_superuser=False,
        )
        member = OrganizationMemberModel(
            id="mem_test_prop",
            organization_id="org_test_prop",
            user_id="usr_test_prop",
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

    await engine.dispose()


def _make_mock_candles(count: int = 50) -> list[dict[str, Any]]:
    base_time = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    price = Decimal("1.1000")
    candles: list[dict[str, Any]] = []
    for i in range(count):
        delta = Decimal("0.0010") if (i % 2 == 0) else Decimal("-0.0005")
        o = price
        c = price + delta
        h = max(o, c) + Decimal("0.0002")
        l = min(o, c) - Decimal("0.0002")
        candles.append(
            {
                "timestamp": base_time + timedelta(hours=i),
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": Decimal(100),
            }
        )
        price = c
    return candles


# ─── 1. BarType -> Timeframe Mappings ─────────────────────────────────────────


def test_bar_type_to_timeframe_all_members() -> None:
    """1. Every BarType maps deterministically to its canonical Timeframe."""
    expected = {
        BarType.M1: Timeframe.M1,
        BarType.M5: Timeframe.M5,
        BarType.M15: Timeframe.M15,
        BarType.M30: Timeframe.M30,
        BarType.H1: Timeframe.H1,
        BarType.H4: Timeframe.H4,
        BarType.D1: Timeframe.D1,
        BarType.W1: Timeframe.WEEKLY,
        BarType.MN1: Timeframe.MONTHLY,
    }
    assert len(expected) == 9
    for bt, tf in expected.items():
        assert bar_type_to_timeframe(bt) == tf


# ─── 2. Timeframe -> BarType Mappings ─────────────────────────────────────────


def test_timeframe_to_bar_type_all_members() -> None:
    """2. Every Timeframe maps deterministically to its canonical BarType."""
    expected = {
        Timeframe.M1: BarType.M1,
        Timeframe.M5: BarType.M5,
        Timeframe.M15: BarType.M15,
        Timeframe.M30: BarType.M30,
        Timeframe.H1: BarType.H1,
        Timeframe.H4: BarType.H4,
        Timeframe.D1: BarType.D1,
        Timeframe.WEEKLY: BarType.W1,
        Timeframe.MONTHLY: BarType.MN1,
    }
    assert len(expected) == 9
    for tf, bt in expected.items():
        assert timeframe_to_bar_type(tf) == bt


# ─── 3. Round-Trip Tests ──────────────────────────────────────────────────────


@pytest.mark.parametrize("bar_type", list(BarType))
def test_round_trip_bar_type(bar_type: BarType) -> None:
    """3. All 9 BarType members round-trip identically through the bridge."""
    tf = bar_type_to_timeframe(bar_type)
    assert timeframe_to_bar_type(tf) == bar_type


@pytest.mark.parametrize("timeframe", list(Timeframe))
def test_round_trip_timeframe(timeframe: Timeframe) -> None:
    """3. All 9 Timeframe members round-trip identically through the bridge."""
    bt = timeframe_to_bar_type(timeframe)
    assert bar_type_to_timeframe(bt) == timeframe


# ─── 4. API-Style Aliases ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("alias", "expected_tf", "expected_bt"),
    [
        ("1m", Timeframe.M1, BarType.M1),
        ("m1", Timeframe.M1, BarType.M1),
        ("5m", Timeframe.M5, BarType.M5),
        ("m5", Timeframe.M5, BarType.M5),
        ("15m", Timeframe.M15, BarType.M15),
        ("m15", Timeframe.M15, BarType.M15),
        ("30m", Timeframe.M30, BarType.M30),
        ("m30", Timeframe.M30, BarType.M30),
        ("1h", Timeframe.H1, BarType.H1),
        ("h1", Timeframe.H1, BarType.H1),
        ("4h", Timeframe.H4, BarType.H4),
        ("h4", Timeframe.H4, BarType.H4),
        ("1d", Timeframe.D1, BarType.D1),
        ("d1", Timeframe.D1, BarType.D1),
        ("1w", Timeframe.WEEKLY, BarType.W1),
        ("w1", Timeframe.WEEKLY, BarType.W1),
        ("weekly", Timeframe.WEEKLY, BarType.W1),
        ("1mo", Timeframe.MONTHLY, BarType.MN1),
        ("mn1", Timeframe.MONTHLY, BarType.MN1),
        ("monthly", Timeframe.MONTHLY, BarType.MN1),
    ],
)
def test_api_style_aliases(alias: str, expected_tf: Timeframe, expected_bt: BarType) -> None:
    """4. Supported string aliases resolve to exact Timeframe and BarType."""
    assert bar_type_to_timeframe(alias) == expected_tf
    assert timeframe_to_bar_type(alias) == expected_bt


# ─── 5. Invalid Timeframe Rejection ───────────────────────────────────────────


@pytest.mark.parametrize("invalid", ["2h", "90m", "foobar", "", "   ", "10m", "3d", "invalid_tf"])
def test_invalid_timeframe_rejection(invalid: str) -> None:
    """5. Unsupported timeframe strings are rejected explicitly, never defaulted."""
    with pytest.raises(UnsupportedBarTypeError):
        normalize_timeframe(invalid)
    with pytest.raises(UnsupportedBarTypeError):
        bar_type_to_timeframe(invalid)
    with pytest.raises(UnsupportedBarTypeError):
        timeframe_to_bar_type(invalid)


# ─── 6-11. ResearchService Timeframe Propagation ──────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("input_tf", "expected_domain_tf"),
    [
        ("M1", Timeframe.M1),          # 6. M1
        ("1m", Timeframe.M1),          # 6. M1 alias
        ("M15", Timeframe.M15),        # 7. M15
        ("15m", Timeframe.M15),        # 7. M15 alias
        ("H4", Timeframe.H4),          # 8. H4
        ("4h", Timeframe.H4),          # 8. H4 alias
        ("D1", Timeframe.D1),          # 9. D1
        ("1d", Timeframe.D1),          # 9. D1 alias
        ("W1", Timeframe.WEEKLY),      # 10. W1
        ("weekly", Timeframe.WEEKLY),  # 10. W1 alias
        ("MN1", Timeframe.MONTHLY),    # 11. MN1
        ("monthly", Timeframe.MONTHLY),# 11. MN1 alias
    ],
)
async def test_research_service_timeframe_propagation(
    test_session: AsyncSession,
    input_tf: str,
    expected_domain_tf: Timeframe,
) -> None:
    """6-11. ResearchService passes exact domain Timeframe to historical provider."""
    mock_provider = AsyncMock()
    mock_provider.load_candles.return_value = _make_mock_candles(50)
    mock_provider.last_provenance = DatasetProvenance(
        data_source="synthetic",
        provider="mock",
        symbol="EUR/USD",
        timeframe=expected_domain_tf.value,
        start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end=datetime(2025, 1, 10, tzinfo=timezone.utc),
        candle_count=50,
        synthetic=True,
        deterministic=True,
    )

    service = ResearchService(session=test_session, historical_provider=mock_provider)
    exp = await service.create_and_run_experiment(
        organization_id="org_test_prop",
        user_id="usr_test_prop",
        strategy_id="trend_following",
        symbol="EUR/USD",
        timeframe=input_tf,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 10),
        parameters={"fast_period": 5, "slow_period": 15},
    )

    # Verify provider was called with exact domain timeframe
    mock_provider.load_candles.assert_called_once()
    actual_tf = mock_provider.load_candles.call_args.kwargs["timeframe"]
    assert actual_tf == expected_domain_tf
    assert actual_tf.value == expected_domain_tf.value
    # Ensure it did NOT silently fall back to H1 if input was not H1
    if expected_domain_tf != Timeframe.H1:
        assert actual_tf != Timeframe.H1


# ─── 12-13. OptimizationService Timeframe Propagation ─────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("input_tf", "expected_domain_tf"),
    [
        ("M15", Timeframe.M15),  # 12. Optimization M15
        ("15m", Timeframe.M15),  # 12. Optimization 15m alias
        ("H4", Timeframe.H4),    # 13. Optimization H4
        ("4h", Timeframe.H4),    # 13. Optimization 4h alias
    ],
)
async def test_optimization_service_timeframe_propagation(
    test_session: AsyncSession,
    input_tf: str,
    expected_domain_tf: Timeframe,
) -> None:
    """12-13. OptimizationService passes exact domain Timeframe to historical provider."""
    mock_provider = AsyncMock()
    mock_provider.load_candles.return_value = _make_mock_candles(60)

    service = OptimizationService(session=test_session, historical_provider=mock_provider)
    req = OptimizationRunRequest(
        strategy_id="TrendFollowing",
        symbol="EUR/USD",
        timeframe=input_tf,
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
        max_combinations=50,
    )

    result = await service.run_optimization(
        request=req,
        organization_id="org_test_prop",
        user_id="usr_test_prop",
    )

    assert result.status == "COMPLETED"
    mock_provider.load_candles.assert_called_once()
    actual_tf = mock_provider.load_candles.call_args.kwargs["timeframe"]
    assert actual_tf == expected_domain_tf
    assert actual_tf != Timeframe.H1


# ─── 14-15. WalkForward Timeframe Propagation ─────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("input_tf", "expected_domain_tf"),
    [
        ("M15", Timeframe.M15),  # 14. Walk-forward M15
        ("15m", Timeframe.M15),  # 14. Walk-forward 15m alias
        ("H4", Timeframe.H4),    # 15. Walk-forward H4
        ("4h", Timeframe.H4),    # 15. Walk-forward 4h alias
    ],
)
async def test_walk_forward_timeframe_propagation(
    test_session: AsyncSession,
    input_tf: str,
    expected_domain_tf: Timeframe,
) -> None:
    """14-15. WalkForward execution passes exact domain Timeframe to historical provider."""
    mock_provider = AsyncMock()
    mock_provider.load_candles.return_value = _make_mock_candles(100)

    service = OptimizationService(session=test_session, historical_provider=mock_provider)
    req = WalkForwardRunRequest(
        strategy_id="TrendFollowing",
        symbol="EUR/USD",
        timeframe=input_tf,
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 20, tzinfo=timezone.utc),
        n_windows=2,
    )

    result = await service.run_walk_forward(
        request=req,
        organization_id="org_test_prop",
        user_id="usr_test_prop",
    )

    assert result.status == "COMPLETED"
    mock_provider.load_candles.assert_called_once()
    actual_tf = mock_provider.load_candles.call_args.kwargs["timeframe"]
    assert actual_tf == expected_domain_tf
    assert actual_tf != Timeframe.H1


# ─── 16. Invalid Timeframe Never Becomes H1 ───────────────────────────────────


@pytest.mark.asyncio
async def test_invalid_timeframe_never_becomes_h1_research(test_session: AsyncSession) -> None:
    """16. ResearchService rejects invalid timeframe with explicit error and NEVER calls provider with H1."""
    mock_provider = AsyncMock()
    service = ResearchService(session=test_session, historical_provider=mock_provider)

    with pytest.raises(UnsupportedBarTypeError):
        await service.create_and_run_experiment(
            organization_id="org_test_prop",
            user_id="usr_test_prop",
            strategy_id="trend_following",
            symbol="EUR/USD",
            timeframe="invalid_99h",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 10),
        )

    # Provider must NEVER have been called with H1 or any fallback
    mock_provider.load_candles.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_timeframe_never_becomes_h1_optimization(test_session: AsyncSession) -> None:
    """16. OptimizationService rejects invalid timeframe with 422 and NEVER calls provider with H1."""
    mock_provider = AsyncMock()
    service = OptimizationService(session=test_session, historical_provider=mock_provider)

    req = OptimizationRunRequest(
        strategy_id="TrendFollowing",
        symbol="EUR/USD",
        timeframe="bad_timeframe",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.run_optimization(
            request=req,
            organization_id="org_test_prop",
            user_id="usr_test_prop",
        )

    assert exc_info.value.status_code == 422
    assert "Unsupported or invalid timeframe 'bad_timeframe'" in exc_info.value.detail
    mock_provider.load_candles.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_timeframe_never_becomes_h1_walk_forward(test_session: AsyncSession) -> None:
    """16. WalkForward rejects invalid timeframe with 422 and NEVER calls provider with H1."""
    mock_provider = AsyncMock()
    service = OptimizationService(session=test_session, historical_provider=mock_provider)

    req = WalkForwardRunRequest(
        strategy_id="TrendFollowing",
        symbol="EUR/USD",
        timeframe="invalid_tf",
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.run_walk_forward(
            request=req,
            organization_id="org_test_prop",
            user_id="usr_test_prop",
        )

    assert exc_info.value.status_code == 422
    assert "Unsupported or invalid timeframe 'invalid_tf'" in exc_info.value.detail
    mock_provider.load_candles.assert_not_called()


# ─── 17. Provenance Timeframe Consistency ────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("tf", [Timeframe.M15, Timeframe.H4, Timeframe.D1])
async def test_provenance_timeframe_consistency(tf: Timeframe) -> None:
    """17. Provenance records exact normalized timeframe passed to historical provider."""
    mock_service = AsyncMock()
    mock_service.get_candles.return_value = _make_mock_candles(20)

    provider = MarketDataServiceHistoricalProvider(
        market_data_service=mock_service,
        source_mode="external",
    )

    candles = await provider.load_candles(
        symbol="EUR/USD",
        timeframe=tf,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 5),
    )

    assert len(candles) > 0
    prov = provider.last_provenance
    assert prov is not None
    assert prov.timeframe == tf.value
    assert prov.timeframe.upper() == tf.name.upper() if tf.name in ("M15", "H4", "D1") else tf.value.upper()
