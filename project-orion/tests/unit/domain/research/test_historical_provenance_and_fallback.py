"""Tests for Phase 2: Historical Data Provenance & Silent Fallback Hardening.

Verifies:
1. Real provider success produces external provenance.
2. Real provider failure raises explicit HistoricalDataUnavailableError.
3. Real provider failure NEVER silently returns synthetic candles.
4. Explicit synthetic mode produces synthetic provenance.
5. Synthetic data is marked deterministic.
6. Provider identity is persisted correctly.
7. Candle count is actual validated count.
8. Date range is persisted in UTC.
9. Legacy experiment without provenance still loads.
10. No credentials appear in exceptions or provenance.
11. Empty real provider response fails explicitly.
12. 429 rate limit failure remains distinguishable.
13. ResearchService persists provenance into experiment model.
14. ResearchService marks experiment as FAILED on real provider failure.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.backtesting.exceptions import (
    HistoricalDataError,
    HistoricalDataUnavailableError,
)
from libraries.domain.backtesting.historical_data import (
    MarketDataServiceHistoricalProvider,
    _sanitize_error_message,
)
from libraries.domain.backtesting.models import Timeframe
from libraries.domain.market_data.exceptions import RateLimitExceededError
from libraries.domain.market_data.models import OHLCV
from apps.trading_engine.src.services.research_service import ResearchService
from libraries.domain.research.models import (
    DataSourceMode,
    DatasetProvenance,
    ResearchExperimentStatus,
)
from libraries.infrastructure.persistence.models.research import ResearchExperimentModel
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models.organization import OrganizationModel
from libraries.infrastructure.persistence.models.user import UserModel
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.fixture
async def test_session() -> AsyncSession:
    """Isolated async SQLite database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        org = OrganizationModel(
            id="org_quant_prov",
            name="Quant Fund Alpha",
            slug="quant-fund-alpha",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        user = UserModel(
            id="usr_prov",
            username="quant_researcher",
            email="research@quantalpha.dev",
            hashed_password="hashed_pass",
            is_active=True,
        )
        session.add(org)
        session.add(user)
        await session.commit()
        yield session



def _generate_mock_ohlcv(
    symbol: str, count: int = 50, start: datetime | None = None
) -> list[OHLCV]:
    """Generate simple valid OHLCV models for offline testing."""
    start_dt = start or datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = []
    curr = start_dt
    price = Decimal("1.0850")
    for i in range(count):
        candles.append(
            OHLCV(
                symbol=symbol,
                timestamp=curr,
                open=price,
                high=price + Decimal("0.0010"),
                low=price - Decimal("0.0010"),
                close=price + Decimal("0.0005"),
                volume=Decimal("150"),
            )
        )
        curr += timedelta(hours=1)
        price += Decimal("0.0002")
    return candles


# ─── 1. Real Provider Success Produces External Provenance ────────────────────


@pytest.mark.asyncio
async def test_real_provider_success_produces_external_provenance() -> None:
    mock_service = MagicMock()
    mock_service.provider_name = "twelvedata"
    mock_candles = _generate_mock_ohlcv("EUR/USD", count=60)
    mock_service.get_candles = AsyncMock(return_value=mock_candles)

    provider = MarketDataServiceHistoricalProvider(
        market_data_service=mock_service,
        source_mode=DataSourceMode.EXTERNAL,
    )

    start = date(2025, 1, 1)
    end = date(2025, 1, 10)
    result = await provider.load_candles("EUR/USD", Timeframe.H1, start, end)

    assert len(result) == 60
    assert provider.last_provenance is not None
    prov = provider.last_provenance
    assert prov.data_source == "external"
    assert prov.provider == "twelvedata"
    assert prov.symbol == "EUR/USD"
    assert prov.timeframe.upper() == "H1"
    assert prov.candle_count == 60
    assert prov.synthetic is False
    assert prov.deterministic is False
    assert prov.data_quality == "excellent"
    assert prov.dataset_hash is not None
    assert prov.start.tzinfo == timezone.utc
    assert prov.end.tzinfo == timezone.utc


# ─── 2. Real Provider Failure Raises Explicit HistoricalDataUnavailableError ──


@pytest.mark.asyncio
async def test_real_provider_failure_raises_explicit_error() -> None:
    mock_service = MagicMock()
    mock_service.provider_name = "twelvedata"
    mock_service.get_candles = AsyncMock(side_effect=ConnectionResetError("Socket reset by peer"))

    provider = MarketDataServiceHistoricalProvider(
        market_data_service=mock_service,
        source_mode=DataSourceMode.EXTERNAL,
    )

    with pytest.raises(HistoricalDataUnavailableError) as exc_info:
        await provider.load_candles("EUR/USD", Timeframe.H1, date(2025, 1, 1), date(2025, 1, 5))

    err = exc_info.value
    assert isinstance(err, HistoricalDataError)
    assert err.symbol == "EUR/USD"
    assert err.timeframe.upper() == "H1"
    assert err.provider == "twelvedata"
    assert "Socket reset by peer" in err.reason
    assert "Silent fallback to synthetic data is prohibited" in str(err)


# ─── 3. Real Provider Failure NEVER Returns Synthetic Candles ─────────────────


@pytest.mark.asyncio
async def test_real_provider_failure_never_returns_synthetic_candles() -> None:
    mock_service = MagicMock()
    mock_service.provider_name = "twelvedata"
    mock_service.get_candles = AsyncMock(side_effect=TimeoutError("TwelveData gateway timeout"))

    provider = MarketDataServiceHistoricalProvider(
        market_data_service=mock_service,
        source_mode=DataSourceMode.EXTERNAL,
    )

    # Spy on deterministic generator
    orig_synth = provider._generate_deterministic_candles
    synthetic_called = False

    def spy_synth(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        nonlocal synthetic_called
        synthetic_called = True
        return orig_synth(*args, **kwargs)

    provider._generate_deterministic_candles = spy_synth  # type: ignore[assignment]

    with pytest.raises(HistoricalDataUnavailableError):
        await provider.load_candles("EUR/USD", Timeframe.H1, date(2025, 1, 1), date(2025, 1, 5))

    assert synthetic_called is False, "Synthetic generator must NEVER be invoked after external failure"


# ─── 4. Explicit Synthetic Mode Produces Synthetic Provenance ─────────────────


@pytest.mark.asyncio
async def test_explicit_synthetic_mode_produces_synthetic_provenance() -> None:
    provider = MarketDataServiceHistoricalProvider(
        market_data_service=None,
        source_mode=DataSourceMode.SYNTHETIC,
    )

    candles = await provider.load_candles("EUR/USD", Timeframe.H1, date(2025, 1, 1), date(2025, 1, 5))

    assert len(candles) > 0
    prov = provider.last_provenance
    assert prov is not None
    assert prov.data_source == "synthetic"
    assert prov.provider == "deterministic_prng"
    assert prov.synthetic is True
    assert prov.deterministic is True
    assert prov.data_quality is None
    assert prov.candle_count == len(candles)


# ─── 5. Synthetic Data Is Marked Deterministic ────────────────────────────────


@pytest.mark.asyncio
async def test_synthetic_data_marked_deterministic() -> None:
    provider = MarketDataServiceHistoricalProvider(source_mode="synthetic")
    candles_1 = await provider.load_candles("GBP/USD", Timeframe.H1, date(2025, 2, 1), date(2025, 2, 5))
    prov_1 = provider.last_provenance

    provider_2 = MarketDataServiceHistoricalProvider(source_mode="synthetic")
    candles_2 = await provider_2.load_candles("GBP/USD", Timeframe.H1, date(2025, 2, 1), date(2025, 2, 5))
    prov_2 = provider_2.last_provenance

    assert prov_1.deterministic is True
    assert prov_2.deterministic is True
    assert prov_1.dataset_hash == prov_2.dataset_hash
    assert len(candles_1) == len(candles_2)


# ─── 6. Provider Identity Is Persisted Correctly ──────────────────────────────


@pytest.mark.asyncio
async def test_provider_identity_persisted_correctly() -> None:
    # Test provider with custom provider_name
    mock_service_custom = MagicMock()
    mock_service_custom.provider_name = "bloomberg_enterprise"
    mock_service_custom.get_candles = AsyncMock(
        return_value=_generate_mock_ohlcv("EUR/USD", count=10)
    )

    provider = MarketDataServiceHistoricalProvider(market_data_service=mock_service_custom)
    await provider.load_candles("EUR/USD", Timeframe.H1, date(2025, 1, 1), date(2025, 1, 2))

    assert provider.last_provenance is not None
    assert provider.last_provenance.provider == "bloomberg_enterprise"
    assert provider.last_provenance.data_source == "external"


# ─── 7. Candle Count Is Actual Validated Count ────────────────────────────────


@pytest.mark.asyncio
async def test_candle_count_is_actual_validated_count() -> None:
    exact_count = 37
    mock_service = MagicMock()
    mock_service.provider_name = "twelvedata"
    mock_service.get_candles = AsyncMock(
        return_value=_generate_mock_ohlcv("EUR/USD", count=exact_count)
    )

    provider = MarketDataServiceHistoricalProvider(market_data_service=mock_service)
    candles = await provider.load_candles("EUR/USD", Timeframe.H1, date(2025, 1, 1), date(2025, 1, 10))

    assert len(candles) == exact_count
    assert provider.last_provenance.candle_count == exact_count


# ─── 8. Date Range Persisted in UTC ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_date_range_persisted_in_utc() -> None:
    provider = MarketDataServiceHistoricalProvider(source_mode="synthetic")
    await provider.load_candles("EUR/USD", Timeframe.H1, date(2025, 3, 1), date(2025, 3, 5))

    prov = provider.last_provenance
    assert prov is not None
    assert prov.start.tzinfo == timezone.utc
    assert prov.end.tzinfo == timezone.utc
    assert prov.start.year == 2025
    assert prov.start.month == 3
    assert prov.start.day == 1
    assert prov.end.day == 5


# ─── 9. Legacy Experiment Without Provenance Still Loads ──────────────────────


def test_legacy_experiment_without_provenance_still_loads() -> None:
    # Simulate legacy database model without provenance in simulation_config
    legacy_model = ResearchExperimentModel(
        id="exp-legacy-001",
        organization_id="org_test",
        strategy_id="trend_following",
        strategy_version="1.0.0",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 1, 10, tzinfo=timezone.utc),
        parameters={"fast_period": 5, "slow_period": 15},
        simulation_config={"initial_capital": 10000.0, "spread_pips": 1.5},
        status=ResearchExperimentStatus.COMPLETED.value,
    )

    assert legacy_model.dataset_provenance is None
    # DatasetProvenance.from_dict handles None/missing gracefully
    prov = DatasetProvenance.from_dict(legacy_model.dataset_provenance)
    assert prov is None


# ─── 10. No Credentials Appear in Exceptions or Provenance ────────────────────


@pytest.mark.asyncio
async def test_no_credentials_appear_in_exceptions_or_provenance() -> None:
    leaked_secret = "td_secret_key_9876543210"
    raw_error_message = (
        f"API Error: 401 Unauthorized for URL https://api.twelvedata.com/time_series?"
        f"symbol=EUR/USD&apikey={leaked_secret}&interval=1h"
    )

    mock_service = MagicMock()
    mock_service.provider_name = "twelvedata"
    mock_service.get_candles = AsyncMock(side_effect=RuntimeError(raw_error_message))

    provider = MarketDataServiceHistoricalProvider(market_data_service=mock_service)

    with pytest.raises(HistoricalDataUnavailableError) as exc_info:
        await provider.load_candles("EUR/USD", Timeframe.H1, date(2025, 1, 1), date(2025, 1, 5))

    err = exc_info.value
    err_str = str(err)

    # Leaked credential must be redacted
    assert leaked_secret not in err_str
    assert leaked_secret not in err.reason
    assert "[REDACTED]" in err_str

    # Test standalone sanitizer
    sanitized = _sanitize_error_message(f"Bearer token: bearer_token_xyz999, api_key: {leaked_secret}")
    assert leaked_secret not in sanitized
    assert "bearer_token_xyz999" not in sanitized


# ─── 11. Empty Real Provider Response Fails Explicitly ────────────────────────


@pytest.mark.asyncio
async def test_empty_real_provider_response_fails_explicitly() -> None:
    mock_service = MagicMock()
    mock_service.provider_name = "twelvedata"
    mock_service.get_candles = AsyncMock(return_value=[])

    provider = MarketDataServiceHistoricalProvider(
        market_data_service=mock_service,
        source_mode=DataSourceMode.EXTERNAL,
    )

    with pytest.raises(HistoricalDataUnavailableError) as exc_info:
        await provider.load_candles("EUR/USD", Timeframe.H1, date(2025, 1, 1), date(2025, 1, 5))

    err = exc_info.value
    assert "zero candles" in err.reason.lower()
    assert err.provider == "twelvedata"


# ─── 12. 429 Provider Failure Remains Distinguishable ─────────────────────────


@pytest.mark.asyncio
async def test_429_provider_failure_remains_distinguishable() -> None:
    mock_service = MagicMock()
    mock_service.provider_name = "twelvedata"
    rate_limit_exc = RateLimitExceededError("HTTP 429 Too Many Requests: Rate limit exceeded")
    mock_service.get_candles = AsyncMock(side_effect=rate_limit_exc)

    provider = MarketDataServiceHistoricalProvider(
        market_data_service=mock_service,
        source_mode=DataSourceMode.EXTERNAL,
    )

    with pytest.raises(HistoricalDataUnavailableError) as exc_info:
        await provider.load_candles("EUR/USD", Timeframe.H1, date(2025, 1, 1), date(2025, 1, 5))

    err = exc_info.value
    assert err.status_code == 429
    assert isinstance(err.cause, RateLimitExceededError)


# ─── 13. ResearchService Persists Provenance in Experiment ────────────────────


@pytest.mark.asyncio
async def test_research_service_persists_provenance_in_experiment(
    test_session: AsyncSession,
) -> None:
    mock_service = MagicMock()
    mock_service.provider_name = "twelvedata"
    mock_service.get_candles = AsyncMock(
        return_value=_generate_mock_ohlcv("EUR/USD", count=50)
    )

    service = ResearchService(
        session=test_session,
        market_data_service=mock_service,
    )

    exp = await service.create_and_run_experiment(
        organization_id="org_quant_prov",
        user_id="usr_prov",
        strategy_id="trend_following",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 10),
        parameters={"fast_period": 5, "slow_period": 15},
    )

    assert exp.status == ResearchExperimentStatus.COMPLETED.value
    assert "provenance" in exp.simulation_config
    prov_dict = exp.simulation_config["provenance"]
    assert prov_dict["data_source"] == "external"
    assert prov_dict["provider"] == "twelvedata"
    assert prov_dict["candle_count"] == 50
    assert prov_dict["synthetic"] is False
    assert prov_dict["deterministic"] is False
    assert exp.dataset_provenance == prov_dict


# ─── 14. ResearchService Real Provider Failure Marks Experiment Failed ────────


@pytest.mark.asyncio
async def test_research_service_real_provider_failure_marks_experiment_failed(
    test_session: AsyncSession,
) -> None:
    mock_service = MagicMock()
    mock_service.provider_name = "twelvedata"
    mock_service.get_candles = AsyncMock(
        side_effect=ConnectionError("TwelveData endpoint connection refused")
    )

    service = ResearchService(
        session=test_session,
        market_data_service=mock_service,
    )

    exp = await service.create_and_run_experiment(
        organization_id="org_quant_fail",
        user_id="usr_prov",
        strategy_id="trend_following",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 10),
        parameters={"fast_period": 5, "slow_period": 15},
    )

    assert exp.status == ResearchExperimentStatus.FAILED.value
    assert "Historical data unavailable" in exp.error_message
    assert "TwelveData endpoint connection refused" in exp.error_message
    assert exp.trades is None or len(exp.trades) == 0


# ─── 15. ResearchService Explicit Synthetic Mode ──────────────────────────────


@pytest.mark.asyncio
async def test_research_service_explicit_synthetic_mode(
    test_session: AsyncSession,
) -> None:
    service = ResearchService(session=test_session)

    exp = await service.create_and_run_experiment(
        organization_id="org_quant_synth",
        user_id="usr_prov",
        strategy_id="trend_following",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 10),
        parameters={"fast_period": 5, "slow_period": 15},
        data_source=DataSourceMode.SYNTHETIC,
    )

    assert exp.status == ResearchExperimentStatus.COMPLETED.value
    prov_dict = exp.dataset_provenance
    assert prov_dict is not None
    assert prov_dict["data_source"] == "synthetic"
    assert prov_dict["provider"] == "deterministic_prng"
    assert prov_dict["synthetic"] is True
    assert prov_dict["deterministic"] is True
