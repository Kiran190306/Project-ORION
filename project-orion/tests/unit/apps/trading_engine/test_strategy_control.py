"""Unit tests for strategy control endpoints."""

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
    session.add = MagicMock()
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


class TestListStrategies:
    """Tests for GET /api/v1/strategies/."""

    def test_list_strategies(self, client: TestClient) -> None:
        """Returns all strategies in catalogue."""
        response = client.get("/api/v1/strategies/")
        assert response.status_code == 200
        data = response.json()
        assert "strategies" in data
        assert "total" in data
        assert data["total"] > 0
        # Verify known strategies are present
        strategy_ids = {s["id"] for s in data["strategies"]}
        assert "trend_following" in strategy_ids
        assert "mean_reversion" in strategy_ids


class TestStrategyDetail:
    """Tests for GET /api/v1/strategies/{strategy_id}."""

    def test_get_strategy_detail(self, client: TestClient) -> None:
        """Returns details for a known strategy."""
        response = client.get("/api/v1/strategies/trend_following")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "trend_following"
        assert data["name"] == "Trend Following"
        assert "parameters" in data
        assert len(data["parameters"]) > 0

    def test_get_unknown_strategy(self, client: TestClient) -> None:
        """Returns 404 for unknown strategy."""
        response = client.get("/api/v1/strategies/nonexistent")
        assert response.status_code == 404


class TestStrategyConfigSchema:
    """Tests for GET /api/v1/strategies/{strategy_id}/config-schema."""

    def test_get_config_schema(self, client: TestClient) -> None:
        """Returns config schema for known strategy."""
        response = client.get("/api/v1/strategies/trend_following/config-schema")
        assert response.status_code == 200
        data = response.json()
        assert data["strategy_id"] == "trend_following"
        assert "schema_definition" in data

    def test_config_schema_unknown(self, client: TestClient) -> None:
        """Returns 404 for unknown strategy."""
        response = client.get("/api/v1/strategies/nonexistent/config-schema")
        assert response.status_code == 404


class TestAccountStrategyConfig:
    """Tests for GET/PUT /api/v1/strategies/account/config."""

    def test_get_account_config_default(self, client: TestClient) -> None:
        """Returns default config when none configured."""
        response = client.get("/api/v1/strategies/account/config")
        assert response.status_code == 200
        data = response.json()
        assert "account_id" in data
        assert "strategy_id" in data
        assert "timeframe" in data

    def test_update_account_config(self, client: TestClient, mock_session: AsyncMock) -> None:
        """Updates strategy config successfully."""
        # Configure mock to return empty for existing check
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        mock_session.execute.return_value = result

        response = client.put(
            "/api/v1/strategies/account/config",
            json={
                "strategy_id": "trend_following",
                "timeframe": "H1",
                "symbols": ["EUR/USD", "GBP/USD"],
                "parameters": {"fast_ma_period": 12},
                "is_active": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["strategy_id"] == "trend_following"
        assert data["timeframe"] == "H1"

    def test_update_unknown_strategy(self, client: TestClient) -> None:
        """Updating to unknown strategy returns 404."""
        response = client.put(
            "/api/v1/strategies/account/config",
            json={
                "strategy_id": "nonexistent_strategy",
                "timeframe": "H1",
            },
        )
        assert response.status_code == 404
