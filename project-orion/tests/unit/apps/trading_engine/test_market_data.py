"""Unit tests for Market Data REST routes and application service integration (EPIC-021)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from apps.trading_engine.src import dependencies
from apps.trading_engine.src.config import AppSettings
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.services.market_data_service import MarketDataService
from fastapi.testclient import TestClient

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
    account.balance = Decimal("100000")
    account.equity = Decimal("100000")
    account.is_live = False
    account.is_active = True
    return account


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


class TestMarketDataRoutes:
    """Tests for /api/v1/market-data endpoints."""

    def test_list_instruments(self, client: TestClient) -> None:
        """GET /api/v1/market-data/instruments returns list of canonical instruments."""
        response = client.get("/api/v1/market-data/instruments")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 7

        symbols = [inst["symbol"] for inst in data]
        assert "EUR/USD" in symbols
        assert "GBP/USD" in symbols
        assert "USD/JPY" in symbols

        eur_usd = next(inst for inst in data if inst["symbol"] == "EUR/USD")
        assert eur_usd["base_currency"] == "EUR"
        assert eur_usd["quote_currency"] == "USD"
        assert Decimal(str(eur_usd["pip_size"])) == Decimal("0.0001")
        assert eur_usd["is_active"] is True

    def test_get_quote_eurusd(self, client: TestClient, paper_adapter: PaperExecutionAdapter) -> None:
        """GET /api/v1/market-data/quotes/EUR/USD returns validated quote and feeds paper adapter."""
        response = client.get("/api/v1/market-data/quotes/EUR/USD")
        assert response.status_code == 200
        data = response.json()

        assert data["symbol"] == "EUR/USD"
        assert Decimal(str(data["bid"])) > Decimal(0)
        assert Decimal(str(data["ask"])) > Decimal(str(data["bid"]))
        assert Decimal(str(data["spread"])) > Decimal(0)
        assert Decimal(str(data["spread_pips"])) > Decimal(0)
        assert data["provider"] == "mock"
        assert data["is_stale"] is False
        assert data["quality"] in ("EXCELLENT", "GOOD")

        # Verify paper adapter was synchronized with the quote
        assert "EUR/USD" in paper_adapter._current_prices
        assert paper_adapter._current_prices["EUR/USD"] == Decimal(str(data["mid"]))

    def test_get_quote_alias_normalization(self, client: TestClient) -> None:
        """GET /api/v1/market-data/quotes/EURUSD normalizes alias cleanly."""
        response = client.get("/api/v1/market-data/quotes/EURUSD")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "EUR/USD"

    def test_get_quote_unknown_symbol(self, client: TestClient) -> None:
        """GET /api/v1/market-data/quotes/UNKNOWN_PAIR returns 404."""
        response = client.get("/api/v1/market-data/quotes/UNKNOWN_PAIR")
        assert response.status_code == 404
        assert "Unrecognized financial symbol" in response.json().get("message", "")

    def test_get_candles(self, client: TestClient) -> None:
        """GET /api/v1/market-data/candles returns candle bars."""
        response = client.get("/api/v1/market-data/candles", params={"symbol": "EUR/USD", "timeframe": "1h", "limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "EUR/USD"
        assert data["timeframe"] == "1h"
        assert isinstance(data["candles"], list)
        assert len(data["candles"]) == 10

        candle = data["candles"][0]
        assert "timestamp" in candle
        assert "open" in candle
        assert "high" in candle
        assert "low" in candle
        assert "close" in candle
        assert "volume" in candle

    def test_get_candles_invalid_timeframe(self, client: TestClient) -> None:
        """GET /api/v1/market-data/candles with invalid timeframe returns 400."""
        response = client.get("/api/v1/market-data/candles", params={"symbol": "EUR/USD", "timeframe": "99x"})
        assert response.status_code == 400

    def test_get_market_data_health(self, client: TestClient) -> None:
        """GET /api/v1/market-data/health returns operational telemetry."""
        response = client.get("/api/v1/market-data/health")
        assert response.status_code == 200
        data = response.json()

        assert data["provider"] == "mock"
        assert data["status"].lower() == "healthy"
        assert data["data_quality"].lower() == "excellent"
        assert data["symbols_active"] >= 7
        assert data["is_paper_feed"] is True
        assert data["latency_ms"] >= 0.0


class TestMarketDataAuthGuard:
    """Tests that market data endpoints require authentication."""

    def test_market_data_without_auth(self, paper_adapter: PaperExecutionAdapter) -> None:
        """Unauthenticated requests are rejected with 401 or 503."""
        app = create_app(paper_adapter=paper_adapter)
        client = TestClient(app)

        r = client.get("/api/v1/market-data/instruments")
        assert r.status_code in (401, 503)

        r = client.get("/api/v1/market-data/quotes/EUR/USD")
        assert r.status_code in (401, 503)

        r = client.get("/api/v1/market-data/candles?symbol=EUR/USD")
        assert r.status_code in (401, 503)

        r = client.get("/api/v1/market-data/health")
        assert r.status_code in (401, 503)

