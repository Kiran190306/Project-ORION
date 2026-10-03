"""Unit tests for Candlestick Pattern REST API endpoint (EPIC-021).

Tests GET /api/v1/market-data/patterns covering:
1. Successful pattern endpoint response.
2. Valid symbol/timeframe normalization.
3. Multiple detected patterns in a candle sequence.
4. No detected patterns returns a valid empty collection.
5. Pattern ordering is chronological.
6. Pattern filtering (single, multiple, deduplication, whitespace).
7. Unknown pattern ID validation (400 Bad Request).
8. Invalid timeframe handling (400 Bad Request).
9. Invalid symbol handling (404 Not Found).
10. Market data / provider failure handling (502 / 500).
11. Existing candle endpoint unchanged regression test.
12. Authentication and authorization guard (401 / 503).
13. Verification that engine evaluates candles retrieved from market-data service.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from apps.trading_engine.src import dependencies
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.services.market_data_service import MarketDataService
from fastapi.testclient import TestClient

from libraries.domain.market_data.exceptions import MarketDataError
from libraries.domain.market_data.models import OHLCV, BarType
from libraries.domain.market_data.quality_engine import MarketDataQualityEngine
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.market_data.cache import MarketDataCache
from libraries.infrastructure.market_data.mock_provider import MockMarketDataProvider


def _mock_user(user_id: str = "user-market-001") -> dict[str, Any]:
    return {
        "id": user_id,
        "username": "markettrader",
        "email": "markettrader@orion.dev",
        "full_name": "Market Trader",
        "is_active": True,
        "is_superuser": False,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }


def _mock_account(user_id: str = "user-market-001") -> MagicMock:
    account = MagicMock()
    account.id = f"acc-{user_id[:8]}"
    account.user_id = user_id
    account.broker_name = "paper"
    account.currency = "USD"
    account.balance = Decimal(100000)
    account.equity = Decimal(100000)
    account.is_live = False
    account.is_active = True
    return account


def _make_ohlcv(
    index: int,
    open_p: str,
    high_p: str,
    low_p: str,
    close_p: str,
    vol: str = "1000",
    base_time: datetime | None = None,
) -> OHLCV:
    base = base_time or datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)
    return OHLCV(
        symbol="EUR/USD",
        timestamp=base + timedelta(hours=index),
        open=Decimal(open_p),
        high=Decimal(high_p),
        low=Decimal(low_p),
        close=Decimal(close_p),
        volume=Decimal(vol),
        bar_type=BarType.H1,
    )


@pytest.fixture
def paper_adapter() -> PaperExecutionAdapter:
    config = PaperExecutionConfig(broker_name="paper", is_paper=True)
    return PaperExecutionAdapter(config=config)


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
    result.scalar.return_value = 0
    session.execute.return_value = result
    return session


@pytest.fixture
def market_data_service(paper_adapter: PaperExecutionAdapter) -> MarketDataService:
    provider = MockMarketDataProvider()
    cache = MarketDataCache()  # Local memory fallback
    quality = MarketDataQualityEngine()
    return MarketDataService(
        provider=provider,
        quality_engine=quality,
        cache=cache,
        paper_adapter=paper_adapter,
    )


@pytest.fixture
def test_app(
    paper_adapter: PaperExecutionAdapter,
    mock_session: AsyncMock,
    market_data_service: MarketDataService,
) -> Any:
    app = create_app(
        paper_adapter=paper_adapter,
        market_data_service=market_data_service,
    )
    app.dependency_overrides[dependencies.get_current_active_user] = lambda: _mock_user()
    app.dependency_overrides[dependencies.get_user_account] = _mock_account
    app.dependency_overrides[dependencies.get_paper_adapter] = lambda: paper_adapter
    app.dependency_overrides[dependencies.get_market_data_service] = lambda: market_data_service
    app.dependency_overrides[dependencies.get_worker_coordinator] = lambda: None

    async def mock_get_db_session():
        yield mock_session

    app.dependency_overrides[dependencies.get_db_session] = mock_get_db_session
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app: Any) -> TestClient:
    return TestClient(test_app)


class TestMarketDataPatternsAPI:
    """Tests for GET /api/v1/market-data/patterns."""

    def test_get_patterns_success_default_params(self, client: TestClient) -> None:
        """GET /api/v1/market-data/patterns with default params returns 200 and schema conforming payload."""
        response = client.get("/api/v1/market-data/patterns", params={"symbol": "EUR/USD"})
        assert response.status_code == 200
        data = response.json()

        assert data["symbol"] == "EUR/USD"
        assert data["timeframe"] == "H1"
        assert data["provider"] == "mock"
        assert isinstance(data["patterns"], list)
        assert data["total_detected"] == len(data["patterns"])

    def test_get_patterns_symbol_and_timeframe_normalization(self, client: TestClient) -> None:
        """GET /api/v1/market-data/patterns normalizes symbol aliases and timeframe."""
        response = client.get(
            "/api/v1/market-data/patterns",
            params={"symbol": "EURUSD", "timeframe": "H1", "limit": 30},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "EUR/USD"
        assert data["timeframe"] == "H1"
        assert isinstance(data["patterns"], list)

    def test_get_patterns_multiple_detected_patterns(
        self, client: TestClient, market_data_service: MarketDataService
    ) -> None:
        """Endpoint recognizes multiple patterns across historical candle data."""
        # Build synthetic candles with a Doji at index 1 and a Hammer at index 3
        synthetic_candles = [
            # Index 0: Normal candle
            _make_ohlcv(0, "1.0850", "1.0870", "1.0840", "1.0860"),
            # Index 1: Doji (tiny body, bilateral shadows)
            _make_ohlcv(1, "1.0850", "1.0870", "1.0830", "1.0851"),
            # Index 2: Bearish setup candle for hammer
            _make_ohlcv(2, "1.0900", "1.0905", "1.0845", "1.0850"),
            # Index 3: Hammer (lower shadow >= 2x body, tiny upper shadow, previous candle bearish)
            _make_ohlcv(3, "1.0850", "1.0853", "1.0800", "1.0852"),
        ]

        market_data_service.get_candles = AsyncMock(return_value=synthetic_candles)

        response = client.get(
            "/api/v1/market-data/patterns",
            params={"symbol": "EUR/USD", "timeframe": "1h"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total_detected"] >= 2
        pattern_ids = [p["pattern_id"] for p in data["patterns"]]
        assert "doji" in pattern_ids
        assert "hammer" in pattern_ids

        # Verify pattern item fields
        doji_item = next(p for p in data["patterns"] if p["pattern_id"] == "doji")
        assert doji_item["name"] == "Doji"
        assert doji_item["direction"] == "neutral"
        assert doji_item["strength"] in ("strong", "moderate", "weak")
        assert doji_item["candle_index"] == 1
        assert "timestamp" in doji_item
        assert Decimal(str(doji_item["confidence"])) >= Decimal("0.50")

    def test_get_patterns_empty_when_no_matches(
        self, client: TestClient, market_data_service: MarketDataService
    ) -> None:
        """Endpoint returns a valid empty list and total_detected=0 when no patterns match."""
        # Flat neutral candles that do not fulfill any pattern invariants
        neutral_candles = [
            _make_ohlcv(i, "1.0850", "1.0850", "1.0850", "1.0850") for i in range(5)
        ]
        market_data_service.get_candles = AsyncMock(return_value=neutral_candles)

        response = client.get(
            "/api/v1/market-data/patterns",
            params={"symbol": "EUR/USD", "timeframe": "1h"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["patterns"] == []
        assert data["total_detected"] == 0

    def test_get_patterns_chronological_ordering(
        self, client: TestClient, market_data_service: MarketDataService
    ) -> None:
        """Patterns are strictly returned in non-decreasing chronological order."""
        synthetic_candles = [
            _make_ohlcv(0, "1.0850", "1.0870", "1.0840", "1.0860"),
            _make_ohlcv(1, "1.0850", "1.0870", "1.0830", "1.0851"),  # Doji
            _make_ohlcv(2, "1.0900", "1.0905", "1.0845", "1.0850"),
            _make_ohlcv(3, "1.0850", "1.0853", "1.0800", "1.0852"),  # Hammer
            _make_ohlcv(4, "1.0860", "1.0865", "1.0855", "1.0858"),
            _make_ohlcv(5, "1.0850", "1.0870", "1.0830", "1.0851"),  # Doji
        ]
        market_data_service.get_candles = AsyncMock(return_value=synthetic_candles)

        response = client.get(
            "/api/v1/market-data/patterns",
            params={"symbol": "EUR/USD", "timeframe": "1h"},
        )
        assert response.status_code == 200
        patterns = response.json()["patterns"]
        assert len(patterns) >= 3

        indices = [p["candle_index"] for p in patterns]
        assert indices == sorted(indices)

    def test_get_patterns_filtering_single_and_multiple(
        self, client: TestClient, market_data_service: MarketDataService
    ) -> None:
        """Endpoint accurately filters patterns by requested pattern_ids."""
        synthetic_candles = [
            _make_ohlcv(0, "1.0850", "1.0870", "1.0840", "1.0860"),
            _make_ohlcv(1, "1.0850", "1.0870", "1.0830", "1.0851"),  # Doji
            _make_ohlcv(2, "1.0900", "1.0905", "1.0845", "1.0850"),
            _make_ohlcv(3, "1.0850", "1.0853", "1.0800", "1.0852"),  # Hammer
        ]
        market_data_service.get_candles = AsyncMock(return_value=synthetic_candles)

        # 1. Filter only 'doji'
        r_doji = client.get(
            "/api/v1/market-data/patterns",
            params={"symbol": "EUR/USD", "pattern_ids": "doji"},
        )
        assert r_doji.status_code == 200
        data_doji = r_doji.json()
        assert all(p["pattern_id"] == "doji" for p in data_doji["patterns"])
        assert any(p["pattern_id"] == "doji" for p in data_doji["patterns"])

        # 2. Filter 'doji,hammer'
        r_multi = client.get(
            "/api/v1/market-data/patterns",
            params={"symbol": "EUR/USD", "pattern_ids": "doji,hammer"},
        )
        assert r_multi.status_code == 200
        ids = {p["pattern_id"] for p in r_multi.json()["patterns"]}
        assert ids.issubset({"doji", "hammer"})

        # 3. Filter with whitespace and mixed casing: ' Doji , HAMMER '
        r_clean = client.get(
            "/api/v1/market-data/patterns",
            params={"symbol": "EUR/USD", "pattern_ids": " Doji , HAMMER "},
        )
        assert r_clean.status_code == 200

        # 4. Filter with duplicate IDs: 'doji,doji'
        r_dedup = client.get(
            "/api/v1/market-data/patterns",
            params={"symbol": "EUR/USD", "pattern_ids": "doji,doji"},
        )
        assert r_dedup.status_code == 200
        assert r_dedup.json()["total_detected"] == data_doji["total_detected"]

    def test_get_patterns_filtering_invalid_pattern_id(self, client: TestClient) -> None:
        """Unknown pattern IDs return 400 Bad Request with descriptive message."""
        r_invalid = client.get(
            "/api/v1/market-data/patterns",
            params={"symbol": "EUR/USD", "pattern_ids": "nonexistent_pattern"},
        )
        assert r_invalid.status_code == 400
        msg = r_invalid.json().get("message", "")
        assert "Unknown pattern ID" in msg
        assert "Available patterns" in msg

        # Empty pattern_ids
        r_empty = client.get(
            "/api/v1/market-data/patterns",
            params={"symbol": "EUR/USD", "pattern_ids": " , "},
        )
        assert r_empty.status_code == 400

    def test_get_patterns_invalid_timeframe(self, client: TestClient) -> None:
        """Invalid timeframe returns 400 Bad Request."""
        response = client.get(
            "/api/v1/market-data/patterns",
            params={"symbol": "EUR/USD", "timeframe": "invalid_tf"},
        )
        assert response.status_code == 400

    def test_get_patterns_invalid_symbol(self, client: TestClient) -> None:
        """Unrecognized symbol returns 404 Not Found."""
        response = client.get(
            "/api/v1/market-data/patterns",
            params={"symbol": "UNKNOWN_PAIR", "timeframe": "1h"},
        )
        assert response.status_code == 404

    def test_get_patterns_market_data_failure(
        self, client: TestClient, market_data_service: MarketDataService
    ) -> None:
        """Provider failure propagates as appropriate HTTP error."""
        market_data_service.get_candles = AsyncMock(side_effect=MarketDataError("Provider down"))

        response = client.get(
            "/api/v1/market-data/patterns",
            params={"symbol": "EUR/USD", "timeframe": "1h"},
        )
        assert response.status_code == 502

    def test_candles_endpoint_remains_unchanged(self, client: TestClient) -> None:
        """GET /api/v1/market-data/candles operates identically without regression."""
        response = client.get(
            "/api/v1/market-data/candles",
            params={"symbol": "EUR/USD", "timeframe": "1h", "limit": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "EUR/USD"
        assert len(data["candles"]) == 10

    def test_patterns_engine_receives_exact_candles_from_market_service(
        self, client: TestClient, market_data_service: MarketDataService
    ) -> None:
        """Endpoint passes query parameters to market_service and evaluates its returned candles."""
        mock_candles = [
            _make_ohlcv(i, "1.0850", "1.0860", "1.0840", "1.0855") for i in range(15)
        ]
        spy_get_candles = AsyncMock(return_value=mock_candles)
        market_data_service.get_candles = spy_get_candles

        response = client.get(
            "/api/v1/market-data/patterns",
            params={"symbol": "EUR/USD", "timeframe": "1h", "limit": 15},
        )
        assert response.status_code == 200
        spy_get_candles.assert_awaited_once_with(
            symbol="EUR/USD",
            timeframe="1h",
            start=None,
            end=None,
            limit=15,
        )


class TestMarketDataPatternsAuthGuard:
    """Security verification that the patterns endpoint requires authentication."""

    def test_patterns_without_auth(self, paper_adapter: PaperExecutionAdapter) -> None:
        """Unauthenticated requests are rejected with 401 or 503."""
        app = create_app(paper_adapter=paper_adapter)
        client = TestClient(app)

        r = client.get("/api/v1/market-data/patterns?symbol=EUR/USD")
        assert r.status_code in (401, 503)
