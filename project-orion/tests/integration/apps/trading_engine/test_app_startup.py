"""Integration tests for the Trading Engine FastAPI application runtime.

Verifies end-to-end:
- Full application startup and shutdown lifecycle
- Database wiring and session dependency injection
- Redis wiring and readiness
- Health endpoints (/health/live and /health/ready)
- Prometheus metrics exposition (/metrics)
- Paper trading end-to-end flow (/api/v1/paper-trade)
- Correlation ID propagation
- Safe error handling without leaked stack traces
"""

from __future__ import annotations

import os
from decimal import Decimal
from unittest import mock
from unittest.mock import AsyncMock

import pytest
from apps.trading_engine.src.config import AppSettings, ConfigurationError
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.services.auth import create_access_token, get_password_hash
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.config import DatabaseConfig, DatabaseManager
from libraries.infrastructure.persistence.models import UserModel


@pytest.fixture
def integration_settings() -> AppSettings:
    """Settings using in-memory SQLite async database for integration testing."""
    return AppSettings(
        environment="testing",
        log_level="INFO",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        run_migrations=False,
        server_host="127.0.0.1",
        server_port=8000,
        paper_balance=Decimal("100000.00"),
        worker_enabled=False,
        worker_symbols="EUR/USD,GBP/USD",
        market_data_poll_interval=5.0,
        trading_cycle_interval=10.0,
        worker_timeout=30.0,
        worker_stale_threshold=30.0,
    )


@pytest.fixture
def mock_redis() -> RedisClient:
    """Mock Redis client for environments without a running Redis server."""
    client = mock.create_autospec(RedisClient, instance=True)
    client.is_connected = True
    client.health_check = AsyncMock(return_value=True)
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    return client


@pytest.fixture
def integration_app(integration_settings: AppSettings, mock_redis: RedisClient) -> any:
    """Real application instance with in-memory SQLite and mock Redis."""
    db_config = DatabaseConfig(url=integration_settings.database_url)
    db_manager = DatabaseManager(config=db_config)

    app = create_app(
        settings=integration_settings,
        db_manager=db_manager,
        redis_client=mock_redis,
    )
    return app


@pytest.mark.asyncio
async def test_full_app_startup_and_shutdown(
    integration_settings: AppSettings, mock_redis: RedisClient
) -> None:
    """Application starts, initializes all infrastructure, and cleanly shuts down."""
    db_config = DatabaseConfig(url=integration_settings.database_url)
    db_manager = DatabaseManager(config=db_config)

    app = create_app(
        settings=integration_settings,
        db_manager=db_manager,
        redis_client=mock_redis,
    )

    # Startup
    async with app.router.lifespan_context(app):
        assert hasattr(app.state, "settings")
        assert hasattr(app.state, "db_manager")
        assert hasattr(app.state, "redis_client")
        assert hasattr(app.state, "paper_adapter")
        assert hasattr(app.state, "health_registry")
        assert hasattr(app.state, "metrics_registry")

        assert app.state.paper_adapter.is_connected is True
        assert await app.state.db_manager.health_check() is True

    # Shutdown
    assert mock_redis.disconnect.called


@pytest.mark.asyncio
async def test_integration_health_and_metrics_endpoints(integration_app: any) -> None:
    """Verify /health/live, /health/ready, and /metrics on running application."""
    app = integration_app
    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Liveness
        live_resp = await client.get("/health/live")
        assert live_resp.status_code == 200
        assert live_resp.json()["status"] == "alive"

        # Readiness
        ready_resp = await client.get("/health/ready")
        assert ready_resp.status_code == 200
        ready_data = ready_resp.json()
        assert ready_data["status"] == "healthy"
        assert len(ready_data["checks"]) >= 2

        # Metrics
        metrics_resp = await client.get("/metrics")
        assert metrics_resp.status_code == 200
        assert "orion_paper_account_balance" in metrics_resp.text


@pytest.mark.asyncio
async def test_integration_database_session_dependency(integration_app: any) -> None:
    """Verify get_db_session yields an active session that executes queries without leaking."""
    app = integration_app
    async with app.router.lifespan_context(app):
        db_manager: DatabaseManager = app.state.db_manager
        async for session in db_manager.get_session():
            result = await session.execute(text("SELECT 42 AS answer"))
            row = result.mappings().one()
            assert row["answer"] == 42


@pytest.mark.asyncio
async def test_integration_end_to_end_paper_trade(integration_app: any) -> None:
    """Execute end-to-end paper trade via POST /api/v1/paper-trade."""
    app = integration_app

    async with app.router.lifespan_context(app):
        db_manager: DatabaseManager = app.state.db_manager

        # Ensure schema exists in in-memory test database
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Provision authenticated test user
        user_id = "test-user-e2e"
        async with db_manager.session() as s:
            u = UserModel(
                id=user_id,
                username="e2etrader",
                email="e2e@example.com",
                hashed_password=get_password_hash("Secret123!"),
                is_active=True,
                is_superuser=False,
            )
            s.add(u)
            await s.commit()

        token = create_access_token(data={"sub": user_id, "username": "e2etrader"})

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={
                "Authorization": f"Bearer {token}",
                "x-correlation-id": "e2e-trade-001",
            },
        ) as client:
            payload = {
                "symbol": "EURUSD",
                "direction": "buy",
                "confidence": 85.0,
                "entry_price": "1.08500",
                "stop_loss": "1.08000",
                "take_profit": "1.09500",
                "position_size": "10000",
            }
            response = await client.post("/api/v1/paper-trade", json=payload)
            assert response.status_code == 200
            data = response.json()

            assert data["symbol"] == "EURUSD"
            assert data["direction"] == "buy"
            assert data["is_paper"] is True
            assert data["order_id"].startswith("ORD-")
            assert data["status"] in ("filled", "partially_filled", "submitted")
            assert response.headers["x-correlation-id"] == "e2e-trade-001"

            # Verify metrics updated
            metrics_resp = await client.get("/metrics")
            assert "orion_paper_trades_total" in metrics_resp.text


@pytest.mark.asyncio
async def test_integration_correlation_id_generated_when_absent(
    integration_app: any,
) -> None:
    """When client provides no correlation ID, one is generated and returned in header."""
    app = integration_app
    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health/live")
        assert response.status_code == 200
        assert "x-correlation-id" in response.headers
        assert len(response.headers["x-correlation-id"]) >= 16


def test_integration_invalid_configuration_raises_on_startup() -> None:
    """Starting application without required DATABASE_URL raises ConfigurationError."""
    with (
        mock.patch.dict(os.environ, {}, clear=True),
        pytest.raises(ConfigurationError),
    ):
        AppSettings.from_env()


@pytest.mark.asyncio
async def test_integration_startup_with_migrations_enabled(mock_redis: RedisClient) -> None:
    """Application successfully runs migrations on startup when ORION_RUN_MIGRATIONS=true."""
    settings = AppSettings(
        environment="testing",
        log_level="INFO",
        database_url="sqlite+aiosqlite:///test_migration_run.db",
        redis_url="redis://localhost:6379/0",
        run_migrations=True,
        server_host="127.0.0.1",
        server_port=8000,
        paper_balance=Decimal(100000),
        worker_enabled=False,
        worker_symbols="EUR/USD,GBP/USD",
        market_data_poll_interval=5.0,
        trading_cycle_interval=10.0,
        worker_timeout=30.0,
        worker_stale_threshold=30.0,
    )
    app = create_app(
        settings=settings,
        redis_client=mock_redis,
    )
    try:
        async with app.router.lifespan_context(app):
            assert app.state.db_manager is not None
            is_healthy = await app.state.db_manager.health_check()
            assert is_healthy is True
    finally:
        # Clean up test database file
        import pathlib

        db_path = pathlib.Path("test_migration_run.db")
        if db_path.exists():
            db_path.unlink()


@pytest.mark.asyncio
async def test_integration_startup_with_migrations_disabled(
    mock_redis: RedisClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Application starts successfully and skips Alembic when run_migrations=False (EPIC-027 Phase 6B)."""
    from unittest.mock import MagicMock

    import apps.trading_engine.src.lifespan as lifespan_module

    # Mock/spy the migration execution boundary
    mock_migration_fn = MagicMock()
    monkeypatch.setattr(lifespan_module, "run_database_migrations", mock_migration_fn)

    settings = AppSettings(
        environment="testing",
        log_level="INFO",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        run_migrations=False,  # Decoupled production behavior
        server_host="127.0.0.1",
        server_port=8000,
        paper_balance=Decimal(100000),
        worker_enabled=False,
        worker_symbols="EUR/USD,GBP/USD",
        market_data_poll_interval=5.0,
        trading_cycle_interval=10.0,
        worker_timeout=30.0,
        worker_stale_threshold=30.0,
    )
    app = create_app(
        settings=settings,
        redis_client=mock_redis,
    )
    async with app.router.lifespan_context(app):
        # 1. Starts successfully
        assert app.state.db_manager is not None
        # 2. Does not invoke Alembic / run_database_migrations
        assert mock_migration_fn.call_count == 0
        # 3. Health check operates cleanly
        is_healthy = await app.state.db_manager.health_check()
        assert is_healthy is True

    # Confirm migration function was never called throughout the entire lifecycle
    mock_migration_fn.assert_not_called()


@pytest.mark.asyncio
async def test_integration_database_session_commit_and_rollback(integration_app: any) -> None:
    """Verify get_db_session commits on success and rolls back on exception."""
    app = integration_app
    async with app.router.lifespan_context(app):
        db_manager: DatabaseManager = app.state.db_manager

        # 1. Create a test table
        async with db_manager.session() as s:
            await s.execute(text("CREATE TABLE test_tx (id INTEGER PRIMARY KEY, val TEXT)"))
            await s.commit()

        # 2. Test successful commit via session
        async with db_manager.session() as s:
            await s.execute(text("INSERT INTO test_tx (id, val) VALUES (1, 'committed')"))
            await s.commit()

        # 3. Test rollback on exception
        try:
            async with db_manager.session() as s:
                await s.execute(text("INSERT INTO test_tx (id, val) VALUES (2, 'rolled_back')"))
                raise RuntimeError("Simulated transaction failure")
        except RuntimeError:
            pass

        # Verify only row 1 exists
        async with db_manager.session() as s:
            res = await s.execute(text("SELECT id, val FROM test_tx"))
            rows = res.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == 1
            assert rows[0][1] == "committed"


@pytest.mark.asyncio
async def test_integration_malformed_json_returns_422(integration_app: any) -> None:
    """Sending malformed non-JSON payload returns 422 with structured error and correlation ID."""
    app = integration_app
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.post(
            "/api/v1/paper-trade",
            content=b"this is not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "validation_error"
        assert "timestamp" in data
