"""Unit tests for account management endpoints."""

from __future__ import annotations

from decimal import Decimal

import pytest
from apps.trading_engine.src import dependencies
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.services.paper_trading import PaperTradingService
from fastapi.testclient import TestClient

from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)


@pytest.fixture
def paper_adapter():
    """Create a paper execution adapter for testing."""
    config = PaperExecutionConfig(
        broker_name="paper",
        is_paper=True,
        balance=Decimal(100000),
    )
    adapter = PaperExecutionAdapter(config=config)
    return adapter


@pytest.fixture
def paper_trading_service(paper_adapter):
    """Create a paper trading service for testing."""
    return PaperTradingService(adapter=paper_adapter)


@pytest.fixture
def test_app(paper_trading_service):
    """Create a test FastAPI app with mocked dependencies."""
    app = create_app(paper_adapter=paper_trading_service.paper_adapter)
    
    # Override dependencies
    app.dependency_overrides[dependencies.get_paper_trading_service] = lambda: paper_trading_service
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
    
    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


def test_get_account_summary(client):
    """Test getting account summary returns expected structure."""
    response = client.get("/api/v1/account/summary")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "balance" in data
    assert "equity" in data
    assert "available_cash" in data
    assert "used_margin" in data
    assert "free_margin" in data
    assert "unrealized_pnl" in data
    assert "realized_pnl" in data
    assert "currency" in data
    assert "is_paper" in data
    assert "updated_at" in data
    
    assert data["balance"] == "100000"
    assert data["equity"] == "100000"
    assert data["currency"] == "USD"
    assert data["is_paper"] is True


def test_get_account_details(client):
    """Test getting account details returns expected structure."""
    response = client.get("/api/v1/account/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "account_id" in data
    assert "broker_name" in data
    assert "account_number" in data
    assert "balance" in data
    assert "equity" in data
    assert "currency" in data
    assert "leverage" in data
    assert "is_live" in data
    assert "is_active" in data
    assert "created_at" in data
    assert "updated_at" in data
    
    assert data["broker_name"] == "paper"
    assert data["account_number"] == "PAPER-001"
    assert data["balance"] == "100000"
    assert data["equity"] == "100000"
    assert data["currency"] == "USD"
    assert data["leverage"] == 100
    assert data["is_live"] is False
    assert data["is_active"] is True


def test_account_paper_only_guard(client):
    """Test that account endpoints only return paper trading information."""
    response = client.get("/api/v1/account/")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify paper trading is enforced
    assert data["is_live"] is False
    assert data["broker_name"] == "paper"
