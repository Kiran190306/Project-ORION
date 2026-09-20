"""Unit tests for Prometheus /metrics endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from apps.trading_engine.src.config import AppSettings
from apps.trading_engine.src.main import create_app
from httpx import ASGITransport, AsyncClient


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


@pytest.fixture
def test_app(test_settings: AppSettings) -> any:
    mock_db = patch("libraries.infrastructure.persistence.config.DatabaseManager").start()
    mock_db.health_check = AsyncMock(return_value=True)
    mock_db.close = AsyncMock()

    mock_redis = patch("libraries.infrastructure.caching.client.RedisClient").start()
    mock_redis.is_connected = True
    mock_redis.health_check = AsyncMock(return_value=True)
    mock_redis.connect = AsyncMock()
    mock_redis.disconnect = AsyncMock()

    return create_app(
        settings=test_settings,
        db_manager=mock_db,
        redis_client=mock_redis,
    )


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_format(test_app: any) -> None:
    """GET /metrics returns 200 with text/plain Prometheus exposition format."""
    app = test_app
    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

        content = response.text
        # Verify Prometheus exposition format headers
        assert "# HELP orion_http_requests_total" in content
        assert "# TYPE orion_http_requests_total counter" in content
        assert "# HELP orion_paper_trades_total" in content
        assert "# TYPE orion_paper_trades_total counter" in content
        assert "# HELP orion_paper_account_balance" in content
        assert "# TYPE orion_paper_account_balance gauge" in content
        assert "orion_paper_account_balance 100000" in content


@pytest.mark.asyncio
async def test_metrics_registry_recording(test_app: any) -> None:
    """Incrementing metrics updates the exported Prometheus text."""
    app = test_app
    async with app.router.lifespan_context(app):
        registry = app.state.metrics_registry
        registry.inc("http_requests_total", 5.0)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/metrics")
            assert response.status_code == 200
            assert "orion_http_requests_total 5.0" in response.text
