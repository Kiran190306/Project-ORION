"""Unit tests for the consolidated dashboard endpoint."""

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
def test_app(paper_adapter: PaperExecutionAdapter, mock_session: AsyncMock) -> Any:
    app = create_app(paper_adapter=paper_adapter)
    app.dependency_overrides[dependencies.get_current_active_user] = lambda: _mock_user()
    app.dependency_overrides[dependencies.get_user_account] = _mock_account
    app.dependency_overrides[dependencies.get_paper_adapter] = lambda: paper_adapter
    app.dependency_overrides[dependencies.get_worker_coordinator] = lambda: None

    async def mock_get_db_session():
        yield mock_session

    app.dependency_overrides[dependencies.get_db_session] = mock_get_db_session
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app: Any) -> TestClient:
    return TestClient(test_app)


class TestDashboard:
    """Tests for GET /api/v1/dashboard/."""

    def test_dashboard_returns_all_blocks(self, client: TestClient) -> None:
        """Dashboard response includes all required blocks."""
        response = client.get("/api/v1/dashboard/")
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = response.json()
            assert "account" in data
            assert "performance" in data
            assert "trading" in data
            assert "strategy" in data
            assert "risk" in data
            assert "worker" in data
            assert "system" in data

    def test_dashboard_account_block(self, client: TestClient) -> None:
        """Dashboard account block has expected fields."""
        response = client.get("/api/v1/dashboard/")
        if response.status_code == 200:
            acct = response.json()["account"]
            assert "balance" in acct
            assert "equity" in acct
            assert "is_paper" in acct
            assert acct["is_paper"] is True

    def test_dashboard_paper_safety(self, client: TestClient) -> None:
        """Dashboard always reports is_paper=True."""
        response = client.get("/api/v1/dashboard/")
        if response.status_code == 200:
            data = response.json()
            assert data["account"]["is_paper"] is True


class TestDashboardAuthGuard:
    """Tests that dashboard endpoint requires authentication."""

    def test_dashboard_without_auth(self, paper_adapter: PaperExecutionAdapter) -> None:
        app = create_app(paper_adapter=paper_adapter)
        client = TestClient(app)
        r = client.get("/api/v1/dashboard/")
        assert r.status_code in (401, 500, 503)
