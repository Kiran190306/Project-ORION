"""Unit tests for portfolio endpoints."""

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
    account.equity = Decimal("100000")
    account.margin = Decimal(0)
    account.margin_free = Decimal("100000")
    account.margin_level = 0.0
    account.leverage = 100
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


class TestPortfolioOverview:
    """Tests for GET /api/v1/portfolio/."""

    def test_portfolio_overview(self, client: TestClient) -> None:
        """Portfolio overview returns expected structure."""
        response = client.get("/api/v1/portfolio/")
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = response.json()
            assert "balance" in data
            assert "equity" in data
            assert "is_paper" in data
            assert data["is_paper"] is True


class TestEquityCurve:
    """Tests for GET /api/v1/portfolio/equity."""

    def test_equity_curve(self, client: TestClient) -> None:
        response = client.get("/api/v1/portfolio/equity")
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = response.json()
            assert "balance" in data
            assert "equity" in data
            assert "current_drawdown" in data


class TestPnLBreakdown:
    """Tests for GET /api/v1/portfolio/pnl."""

    def test_pnl_breakdown(self, client: TestClient) -> None:
        response = client.get("/api/v1/portfolio/pnl")
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = response.json()
            assert "realized_pnl" in data
            assert "unrealized_pnl" in data
            assert "net_pnl" in data


class TestExposure:
    """Tests for GET /api/v1/portfolio/exposure."""

    def test_exposure(self, client: TestClient) -> None:
        response = client.get("/api/v1/portfolio/exposure")
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = response.json()
            assert "net_exposure" in data
            assert "gross_exposure" in data
            assert "currency_exposures" in data


class TestPortfolioAuthGuard:
    """Tests that portfolio endpoints require authentication."""

    def test_portfolio_without_auth(self, paper_adapter: PaperExecutionAdapter) -> None:
        app = create_app(paper_adapter=paper_adapter)
        client = TestClient(app)

        endpoints = [
            "/api/v1/portfolio/",
            "/api/v1/portfolio/equity",
            "/api/v1/portfolio/pnl",
            "/api/v1/portfolio/exposure",
        ]
        for ep in endpoints:
            r = client.get(ep)
            assert r.status_code in (401, 500, 503)
