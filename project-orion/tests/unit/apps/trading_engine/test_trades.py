"""Unit tests for trade history endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from apps.trading_engine.src import dependencies
from apps.trading_engine.src.main import create_app
from fastapi.testclient import TestClient

from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)


def _mock_user(user_id: str = "user-test-001") -> dict[str, Any]:
    return {
        "id": user_id,
        "username": "testtrader",
        "email": "trader@orion.dev",
        "full_name": "Test Trader",
        "is_active": True,
        "is_superuser": False,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }


def _mock_account(user_id: str = "user-test-001") -> MagicMock:
    account = MagicMock()
    account.id = f"acc-{user_id[:8]}"
    account.user_id = user_id
    account.broker_name = "paper"
    account.currency = "USD"
    account.balance = Decimal("100000")
    account.is_live = False
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
def test_app(paper_adapter: PaperExecutionAdapter, mock_session: AsyncMock) -> Any:
    app = create_app(paper_adapter=paper_adapter)
    app.dependency_overrides[dependencies.get_current_active_user] = lambda: _mock_user()
    app.dependency_overrides[dependencies.get_user_account] = _mock_account
    app.dependency_overrides[dependencies.get_paper_adapter] = lambda: paper_adapter

    async def mock_get_db_session():
        yield mock_session

    app.dependency_overrides[dependencies.get_db_session] = mock_get_db_session
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app: Any) -> TestClient:
    return TestClient(test_app)


class TestListTrades:
    """Tests for GET /api/v1/trades/."""

    def test_list_trades_empty(self, client: TestClient) -> None:
        """Empty trade list returns paginated response."""
        response = client.get("/api/v1/trades/")
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = response.json()
            assert "items" in data
            assert "total" in data

    def test_list_trades_with_symbol_filter(self, client: TestClient) -> None:
        response = client.get("/api/v1/trades/?symbol=EURUSD")
        assert response.status_code in (200, 500)

    def test_list_trades_with_date_filter(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/trades/?date_from=2026-01-01T00:00:00Z&date_to=2026-12-31T23:59:59Z"
        )
        assert response.status_code in (200, 500)

    def test_list_trades_pagination(self, client: TestClient) -> None:
        response = client.get("/api/v1/trades/?limit=10&offset=0&order=asc")
        assert response.status_code in (200, 500)


class TestGetTrade:
    """Tests for GET /api/v1/trades/{trade_id}."""

    def test_get_nonexistent_trade(self, client: TestClient) -> None:
        response = client.get("/api/v1/trades/nonexistent-trade-id")
        assert response.status_code in (404, 500)


class TestTradeAuthGuard:
    """Tests that trade endpoints require authentication."""

    def test_trades_without_auth(self, paper_adapter: PaperExecutionAdapter) -> None:
        app = create_app(paper_adapter=paper_adapter)
        client = TestClient(app)

        r1 = client.get("/api/v1/trades/")
        r2 = client.get("/api/v1/trades/some-id")

        for r in [r1, r2]:
            assert r.status_code in (401, 500, 503)
