"""Unit tests for strategy management endpoints."""

from __future__ import annotations

import pytest
from apps.trading_engine.src import dependencies
from apps.trading_engine.src.main import create_app
from fastapi.testclient import TestClient
from libraries.domain.strategy.registry import StrategyRegistry


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


def test_catalog_registry_parity(client):
    """Test 100% parity between public API catalog and StrategyRegistry."""
    response = client.get("/api/v1/strategies/")
    assert response.status_code == 200
    data = response.json()

    catalog_ids = [s["id"] for s in data["strategies"]]
    registry_ids = [entry.strategy_id for entry in StrategyRegistry.list_strategies()]

    # Catalog and Registry must have identical IDs
    assert set(catalog_ids) == set(registry_ids)
    assert len(catalog_ids) == len(registry_ids)
    assert data["total"] == len(registry_ids)


def test_catalog_contains_only_executable_strategies(client):
    """Test that catalog contains exactly the registered executable strategies."""
    response = client.get("/api/v1/strategies/")
    assert response.status_code == 200
    data = response.json()

    catalog_ids = {s["id"] for s in data["strategies"]}
    expected_ids = {"trend_following", "mean_reversion", "breakout", "momentum", "candlestick_reversal"}

    assert catalog_ids == expected_ids
    assert len(catalog_ids) == 5


def test_no_metadata_only_strategies_in_catalog(client):
    """Test that non-executable metadata-only strategies are NOT exposed in catalog."""
    response = client.get("/api/v1/strategies/")
    assert response.status_code == 200
    data = response.json()

    catalog_ids = {s["id"] for s in data["strategies"]}
    unregistered_ids = {"reversal", "scalping", "swing", "carry_trade", "news_trading"}

    for unregistered_id in unregistered_ids:
        assert unregistered_id not in catalog_ids, f"{unregistered_id} should not be in catalog"


def test_every_catalog_strategy_resolves_in_registry(client):
    """Test that every strategy in the public catalog can be resolved and instantiated in StrategyRegistry."""
    response = client.get("/api/v1/strategies/")
    assert response.status_code == 200
    data = response.json()

    for strat in data["strategies"]:
        strat_id = strat["id"]
        # Must resolve entry in registry
        entry = StrategyRegistry.get(strat_id)
        assert entry.strategy_id == strat_id
        # Must instantiate cleanly
        instance = StrategyRegistry.create_strategy(strat_id)
        assert instance.metadata.strategy_id == strat_id


@pytest.mark.parametrize("strat_id", ["trend_following", "mean_reversion", "breakout", "momentum", "candlestick_reversal"])
def test_canonical_strategy_details(client, strat_id):
    """Test that GET /api/v1/strategies/{id} succeeds for each canonical strategy."""
    response = client.get(f"/api/v1/strategies/{strat_id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["id"] == strat_id
    assert "parameters" in detail
    assert len(detail["parameters"]) > 0


@pytest.mark.parametrize("strat_id", ["reversal", "scalping", "swing", "carry_trade", "news_trading", "nonexistent"])
def test_unregistered_strategies_return_404(client, strat_id):
    """Test that unregistered/metadata-only strategies return 404 from strategy detail endpoint."""
    response = client.get(f"/api/v1/strategies/{strat_id}")
    assert response.status_code == 404
