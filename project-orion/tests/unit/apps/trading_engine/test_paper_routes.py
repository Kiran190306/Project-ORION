"""Unit tests for paper trading control routes."""

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


def _mock_user(user_id: str = "user-paper-001") -> dict[str, Any]:
    return {
        "id": user_id,
        "username": "papertrader",
        "email": "paper@orion.dev",
        "full_name": "Paper Trader",
        "is_active": True,
        "is_superuser": True,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }


def _mock_account(user_id: str = "user-paper-001") -> MagicMock:
    account = MagicMock()
    account.id = f"acc-{user_id[:8]}"
    account.user_id = user_id
    account.organization_id = "org-paper-001"
    account.broker_name = "paper"
    account.account_number = "PAPER-RESET-001"
    account.currency = "USD"
    account.balance = Decimal("100000")
    account.equity = Decimal("100000")
    account.margin = Decimal(0)
    account.margin_free = Decimal("100000")
    account.margin_level = 0.0
    account.leverage = 100
    account.is_live = False
    account.is_active = True
    account.meta_data = {}
    return account


@pytest.fixture
def paper_adapter() -> PaperExecutionAdapter:
    config = PaperExecutionConfig(broker_name="paper", is_paper=True, deterministic=True)
    return PaperExecutionAdapter(config=config)


@pytest.fixture
def mock_account() -> MagicMock:
    return _mock_account()


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    res = MagicMock()
    res.rowcount = 2
    session.execute.return_value = res
    return session


@pytest.fixture
def test_app(
    paper_adapter: PaperExecutionAdapter,
    mock_account: MagicMock,
    mock_session: AsyncMock,
) -> Any:
    app = create_app(paper_adapter=paper_adapter)
    app.dependency_overrides[dependencies.get_current_active_user] = lambda: _mock_user()
    app.dependency_overrides[dependencies.get_user_account] = lambda: mock_account
    app.dependency_overrides[dependencies.get_paper_adapter] = lambda: paper_adapter
    app.dependency_overrides[dependencies.get_db_session] = lambda: mock_session
    return app


@pytest.fixture
def client(test_app: Any) -> TestClient:
    return TestClient(test_app)


def test_get_paper_config(client: TestClient) -> None:
    """GET /api/v1/trading/paper/config returns simulation parameters."""
    response = client.get("/api/v1/trading/paper/config")
    assert response.status_code == 200
    data = response.json()
    assert data["broker_name"] == "paper"
    assert data["is_paper"] is True
    assert "spread" in data
    assert "slippage_mean" in data
    assert "deterministic" in data


def test_update_paper_config(client: TestClient) -> None:
    """PATCH /api/v1/trading/paper/config updates simulation parameters."""
    payload = {
        "spread": 0.0002,
        "slippage_mean": 0.00005,
        "deterministic": True,
        "leverage": 200,
    }
    response = client.patch("/api/v1/trading/paper/config", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["spread"] == 0.0002
    assert data["slippage_mean"] == 0.00005
    assert data["deterministic"] is True
    assert data["leverage"] == 200


def test_reset_paper_account(client: TestClient, mock_account: MagicMock) -> None:
    """POST /api/v1/trading/paper/reset resets balance and clears state."""
    payload = {"balance": 50000.0}
    response = client.post("/api/v1/trading/paper/reset", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Paper account successfully reset"
    assert Decimal(str(data["balance"])) == Decimal("50000.0")
    assert Decimal(str(data["equity"])) == Decimal("50000.0")
    assert data["positions_closed"] == 2
    assert data["orders_cancelled"] == 2
