"""Unit tests for strategy management endpoints."""

from __future__ import annotations

import pytest
from apps.trading_engine.src import dependencies
from apps.trading_engine.src.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def test_app():
    """Create a test FastAPI app."""
    app = create_app()
    app.dependency_overrides[dependencies.get_current_active_user] = lambda: {
        "id": "user-test-001",
        "username": "testuser",
        "is_active": True,
        "is_superuser": False,
    }
    app.dependency_overrides[dependencies.get_tenant_context] = lambda: dependencies.TenantContext(
        user_id="user-test-001",
        organization_id=None,
        role=None,
        is_superuser=False,
    )
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


def test_list_strategies(client):
    """Test listing strategies returns expected structure."""
    response = client.get("/api/v1/strategies/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "strategies" in data
    assert "total" in data
    assert "updated_at" in data
    
    assert isinstance(data["strategies"], list)
    assert data["total"] == len(data["strategies"])
    assert data["total"] > 0
    
    # Check first strategy has required fields
    first_strategy = data["strategies"][0]
    assert "id" in first_strategy
    assert "name" in first_strategy
    assert "type" in first_strategy
    assert "description" in first_strategy
    assert "timeframes" in first_strategy
    assert "symbols" in first_strategy
    assert "is_active" in first_strategy


def test_list_strategies_content(client):
    """Test that expected strategies are present."""
    response = client.get("/api/v1/strategies/")
    
    assert response.status_code == 200
    data = response.json()
    
    strategy_ids = [s["id"] for s in data["strategies"]]
    
    assert "trend_following" in strategy_ids
    assert "mean_reversion" in strategy_ids
    assert "breakout" in strategy_ids
    assert "scalping" in strategy_ids
