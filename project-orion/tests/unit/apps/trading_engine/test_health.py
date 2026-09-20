"""Unit tests for /health/live and /health/ready endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from apps.trading_engine.src.config import AppSettings
from apps.trading_engine.src.main import create_app
from httpx import ASGITransport, AsyncClient

from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.persistence.config import DatabaseManager


@pytest.fixture
def mock_db_manager() -> DatabaseManager:
    manager = mock.create_autospec(DatabaseManager, instance=True)
    manager.health_check = AsyncMock(return_value=True)
    manager.close = AsyncMock()
    return manager


@pytest.fixture
def mock_redis_client() -> RedisClient:
    client = mock.create_autospec(RedisClient, instance=True)
    client.is_connected = True
    client.health_check = AsyncMock(return_value=True)
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    return client


@pytest.fixture
def test_settings() -> AppSettings:
    return AppSettings(
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


from unittest import mock


@pytest.mark.asyncio
async def test_health_live_always_returns_200(
    test_settings: AppSettings,
    mock_db_manager: DatabaseManager,
    mock_redis_client: RedisClient,
) -> None:
    """GET /health/live must always return 200 and alive status."""
    app = create_app(
        settings=test_settings,
        db_manager=mock_db_manager,
        redis_client=mock_redis_client,
    )
    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_ready_returns_200_when_all_healthy(
    test_settings: AppSettings,
    mock_db_manager: DatabaseManager,
    mock_redis_client: RedisClient,
) -> None:
    """GET /health/ready returns 200 when both PostgreSQL and Redis are healthy."""
    mock_db_manager.health_check = AsyncMock(return_value=True)
    mock_redis_client.health_check = AsyncMock(return_value=True)

    app = create_app(
        settings=test_settings,
        db_manager=mock_db_manager,
        redis_client=mock_redis_client,
    )
    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        check_names = {c["name"] for c in data["checks"]}
        assert "database" in check_names
        assert "redis" in check_names
        for c in data["checks"]:
            assert c["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_ready_returns_503_when_db_unhealthy(
    test_settings: AppSettings,
    mock_db_manager: DatabaseManager,
    mock_redis_client: RedisClient,
) -> None:
    """GET /health/ready returns 503 when database health check fails."""
    mock_db_manager.health_check = AsyncMock(return_value=False)
    mock_redis_client.health_check = AsyncMock(return_value=True)

    app = create_app(
        settings=test_settings,
        db_manager=mock_db_manager,
        redis_client=mock_redis_client,
    )
    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"

        db_check = next(c for c in data["checks"] if c["name"] == "database")
        assert db_check["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_health_ready_returns_503_when_redis_unhealthy(
    test_settings: AppSettings,
    mock_db_manager: DatabaseManager,
    mock_redis_client: RedisClient,
) -> None:
    """GET /health/ready returns 503 when Redis health check fails."""
    mock_db_manager.health_check = AsyncMock(return_value=True)
    mock_redis_client.health_check = AsyncMock(return_value=False)

    app = create_app(
        settings=test_settings,
        db_manager=mock_db_manager,
        redis_client=mock_redis_client,
    )
    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"

        redis_check = next(c for c in data["checks"] if c["name"] == "redis")
        assert redis_check["status"] == "unhealthy"
