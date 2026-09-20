"""Unit tests for centralized exception handling and error responses."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from apps.trading_engine.src.config import AppSettings
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.schemas import PaperTradeRequest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient

from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.persistence.config import DatabaseManager


@pytest.fixture
def test_app() -> tuple[any, DatabaseManager, RedisClient]:
    settings = AppSettings(
        environment="testing",
        log_level="INFO",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        run_migrations=False,
        server_host="127.0.0.1",
        server_port=8000,
        paper_balance=100000,
        worker_enabled=False,
        worker_symbols="EUR/USD,GBP/USD",
        market_data_poll_interval=5.0,
        trading_cycle_interval=10.0,
        worker_timeout=30.0,
        worker_stale_threshold=30.0,
    )
    mock_db = patch("libraries.infrastructure.persistence.config.DatabaseManager").start()
    mock_db.health_check = AsyncMock(return_value=True)
    mock_db.close = AsyncMock()

    mock_redis = patch("libraries.infrastructure.caching.client.RedisClient").start()
    mock_redis.is_connected = True
    mock_redis.health_check = AsyncMock(return_value=True)
    mock_redis.connect = AsyncMock()
    mock_redis.disconnect = AsyncMock()

    app = create_app(
        settings=settings,
        db_manager=mock_db,
        redis_client=mock_redis,
    )

    # Add a route that deliberately raises an unhandled exception to test 500 handler
    debug_router = APIRouter()

    @debug_router.get("/test/boom")
    async def boom() -> None:
        raise RuntimeError("Sensitive internal database connection string leaked!")

    @debug_router.post("/test/validation")
    async def validation_route(request: PaperTradeRequest) -> None:
        pass

    app.include_router(debug_router)

    return app


@pytest.mark.asyncio
async def test_validation_error_returns_422_with_correlation_id(test_app: any) -> None:
    """Sending invalid payload returns 422 with structured ErrorResponse and correlation ID."""
    app = test_app
    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"x-correlation-id": "cid-test-1234"},
    ) as client:
        # Missing required fields
        response = await client.post("/test/validation", json={"symbol": "X"})
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "validation_error"
        assert "symbol" in data["message"]
        assert data["correlation_id"] == "cid-test-1234"
        assert response.headers["x-correlation-id"] == "cid-test-1234"


@pytest.mark.asyncio
async def test_http_404_returns_structured_json(test_app: any) -> None:
    """Requesting non-existent route returns 404 with structured JSON."""
    app = test_app
    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/non-existent-path")
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "http_error"
        assert "Not Found" in data["message"]
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_unexpected_exception_returns_safe_500_without_traceback(test_app: any) -> None:
    """Unhandled exception returns safe 500 without leaking stack traces or sensitive messages."""
    app = test_app
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
            headers={"x-correlation-id": "cid-boom-999"},
        ) as client,
    ):
        response = await client.get("/test/boom")
        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "internal_error"
        # Sensitive message must NOT be in the client response
        assert "Sensitive internal database" not in data["message"]
        assert data["message"] == "An unexpected error occurred. Please try again later."
        assert data["correlation_id"] == "cid-boom-999"
        assert response.headers["x-correlation-id"] == "cid-boom-999"
