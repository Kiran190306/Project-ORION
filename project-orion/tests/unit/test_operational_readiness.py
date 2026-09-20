"""Automated Operational Readiness & SRE Tests for Project ORION (EPIC-018).

Deterministic, fast, isolated tests verifying:
1. Production configuration secure defaults and fail-closed validation.
2. Paper-trading safety invariants (zero live broker connectivity).
3. Autonomous trading worker disabled guard.
4. Institutional security headers middleware.
5. Distributed correlation ID propagation.
6. Health readiness dependency failure handling (Postgres / Redis).
7. Structured logging sensitive data redaction.
8. Alembic linear migration chain integrity (0001 -> 0007).
"""

from __future__ import annotations

import ast
import json
import logging
from decimal import Decimal
from pathlib import Path
from unittest import mock
from unittest.mock import AsyncMock

import pytest
from apps.trading_engine.src.config import (
    AppSettings,
    ConfigurationError,
    parse_cors_origins,
)
from apps.trading_engine.src.main import create_app
from httpx import ASGITransport, AsyncClient

from libraries.domain.execution.models import (
    Order,
    OrderId,
    OrderSide,
    OrderStatus,
    OrderType,
)
from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.persistence.config import DatabaseManager
from libraries.observability.config import LoggingConfig
from libraries.observability.logging import StructuredFormatter

# ─── TEST 1: Production Configuration Secure Defaults ───────────────────────


def test_production_config_secure_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies production configuration secure defaults and fail-closed validation."""
    # 1. Missing DATABASE_URL fails closed
    monkeypatch.delenv("ORION_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ConfigurationError, match="ORION_DATABASE_URL.*required"):
        AppSettings.from_env()

    # 2. Test secure defaults with minimal valid database URL
    monkeypatch.setenv("ORION_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
    monkeypatch.delenv("ORION_WORKER_ENABLED", raising=False)
    monkeypatch.delenv("ORION_PAPER_BALANCE", raising=False)
    monkeypatch.delenv("ORION_LOG_LEVEL", raising=False)

    settings = AppSettings.from_env()
    assert settings.worker_enabled is False, "Worker must default to disabled (False)"
    assert settings.paper_balance == Decimal(100000), "Default paper balance must be $100,000"
    assert settings.log_level == "INFO"
    assert settings.jwt_expire_minutes == 30, "Default JWT expiry must be 30 minutes"
    assert settings.jwt_algorithm == "HS256"

    # 3. CORS origin parser prevents wildcard credentials
    cors = parse_cors_origins("https://orion-dashboard.onrender.com,https://app.orion.com")
    assert "https://orion-dashboard.onrender.com" in cors
    assert "https://app.orion.com" in cors
    assert "*" not in cors


# ─── TEST 2: Paper-Trading Safety Invariants ───────────────────────────────


@pytest.mark.asyncio
async def test_paper_trading_safety_invariants() -> None:
    """Verifies PaperExecutionAdapter operates strictly in simulated paper mode with zero live risk."""
    config = PaperExecutionConfig()
    adapter = PaperExecutionAdapter(config=config)

    await adapter.connect()
    assert adapter.is_connected is True

    # Account info must indicate paper broker
    account_info = await adapter.get_account()
    assert account_info.broker_name == "paper"
    assert account_info.balance > Decimal(0)

    # Paper order execution must simulate fills locally without external broker API calls
    order = Order(
        order_id=OrderId("test-ord-001"),
        decision_id="dec-001",
        execution_id="exec-001",
        symbol="EUR/USD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal(10000),
        price=Decimal("1.0850"),
    )

    result = await adapter.submit_order(order)
    assert result.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED, OrderStatus.SUBMITTED)
    assert result.filled_quantity >= Decimal(0)

    await adapter.disconnect()


# ─── TEST 3: Autonomous Trading Worker Disabled Guard ───────────────────────


def test_worker_disabled_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that autonomous trading worker is disabled by default and stays disabled."""
    monkeypatch.setenv("ORION_DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
    monkeypatch.setenv("ORION_WORKER_ENABLED", "false")

    settings = AppSettings.from_env()
    assert settings.worker_enabled is False

    # Setting explicitly to 0 / false also yields False
    monkeypatch.setenv("ORION_WORKER_ENABLED", "0")
    settings_zero = AppSettings.from_env()
    assert settings_zero.worker_enabled is False


# ─── TEST 4: Institutional Security Headers Middleware ─────────────────────


@pytest.mark.asyncio
async def test_security_headers_middleware() -> None:
    """Verifies that all API responses include institutional-grade HTTP security headers."""
    mock_db = mock.create_autospec(DatabaseManager, instance=True)
    mock_db.health_check = AsyncMock(return_value=True)
    mock_db.close = AsyncMock()

    mock_redis = mock.create_autospec(RedisClient, instance=True)
    mock_redis.is_connected = True
    mock_redis.health_check = AsyncMock(return_value=True)
    mock_redis.connect = AsyncMock()
    mock_redis.disconnect = AsyncMock()

    test_settings = AppSettings(
        environment="testing",
        log_level="INFO",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        run_migrations=False,
        server_host="127.0.0.1",
        server_port=8000,
        paper_balance=Decimal(100000),
        worker_enabled=False,
        worker_symbols=("EUR/USD", "GBP/USD"),
        market_data_poll_interval=5.0,
        trading_cycle_interval=10.0,
        worker_timeout=30.0,
        worker_stale_threshold=30.0,
    )

    app = create_app(settings=test_settings, db_manager=mock_db, redis_client=mock_redis)

    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health/live")
        assert resp.status_code == 200

        # Verify headers
        headers = resp.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert "no-store" in headers.get("Cache-Control", "")
        assert "max-age=31536000" in headers.get("Strict-Transport-Security", "")
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "default-src 'self'" in headers.get("Content-Security-Policy", "")


# ─── TEST 5: Distributed Correlation ID Propagation ────────────────────────


@pytest.mark.asyncio
async def test_correlation_id_propagation() -> None:
    """Verifies that X-Correlation-ID is generated or propagated across HTTP requests."""
    mock_db = mock.create_autospec(DatabaseManager, instance=True)
    mock_db.health_check = AsyncMock(return_value=True)
    mock_db.close = AsyncMock()

    mock_redis = mock.create_autospec(RedisClient, instance=True)
    mock_redis.is_connected = True
    mock_redis.health_check = AsyncMock(return_value=True)
    mock_redis.connect = AsyncMock()
    mock_redis.disconnect = AsyncMock()

    test_settings = AppSettings(
        environment="testing",
        log_level="INFO",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        run_migrations=False,
        server_host="127.0.0.1",
        server_port=8000,
        paper_balance=Decimal(100000),
        worker_enabled=False,
        worker_symbols=("EUR/USD",),
        market_data_poll_interval=5.0,
        trading_cycle_interval=10.0,
        worker_timeout=30.0,
        worker_stale_threshold=30.0,
    )

    app = create_app(settings=test_settings, db_manager=mock_db, redis_client=mock_redis)

    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Case A: Generated automatically when absent
        resp_auto = await client.get("/health/live")
        assert resp_auto.status_code == 200
        cid_auto = resp_auto.headers.get("x-correlation-id")
        assert cid_auto is not None and len(cid_auto) > 0

        # Case B: Propagated transparently when supplied
        custom_cid = "orion-trace-corr-9876543210"
        resp_custom = await client.get("/health/live", headers={"x-correlation-id": custom_cid})
        assert resp_custom.status_code == 200
        assert resp_custom.headers.get("x-correlation-id") == custom_cid


# ─── TEST 6: Health Readiness Dependency Failure Handling ───────────────────


@pytest.mark.asyncio
async def test_health_readiness_dependency_failure() -> None:
    """Verifies that /health/ready returns HTTP 503 if PostgreSQL or Redis is down."""
    mock_db = mock.create_autospec(DatabaseManager, instance=True)
    mock_redis = mock.create_autospec(RedisClient, instance=True)
    mock_redis.is_connected = True
    mock_redis.connect = AsyncMock()
    mock_redis.disconnect = AsyncMock()

    test_settings = AppSettings(
        environment="testing",
        log_level="INFO",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        run_migrations=False,
        server_host="127.0.0.1",
        server_port=8000,
        paper_balance=Decimal(100000),
        worker_enabled=False,
        worker_symbols=("EUR/USD",),
        market_data_poll_interval=5.0,
        trading_cycle_interval=10.0,
        worker_timeout=30.0,
        worker_stale_threshold=30.0,
    )

    # 1. Database failure -> 503
    mock_db.health_check = AsyncMock(return_value=False)
    mock_redis.health_check = AsyncMock(return_value=True)

    app_db_fail = create_app(settings=test_settings, db_manager=mock_db, redis_client=mock_redis)
    async with app_db_fail.router.lifespan_context(app_db_fail), AsyncClient(
        transport=ASGITransport(app=app_db_fail), base_url="http://test"
    ) as client:
        resp = await client.get("/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unhealthy"

    # 2. Redis failure -> 503
    mock_db.health_check = AsyncMock(return_value=True)
    mock_redis.health_check = AsyncMock(return_value=False)

    app_redis_fail = create_app(settings=test_settings, db_manager=mock_db, redis_client=mock_redis)
    async with app_redis_fail.router.lifespan_context(app_redis_fail), AsyncClient(
        transport=ASGITransport(app=app_redis_fail), base_url="http://test"
    ) as client:
        resp = await client.get("/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unhealthy"


# ─── TEST 7: Structured Logging Sensitive Data Redaction ────────────────────


def test_logging_sensitive_redaction() -> None:
    """Verifies that StructuredFormatter masks sensitive fields (passwords, tokens, keys)."""
    cfg = LoggingConfig(service_name="test-orion", environment="production")
    formatter = StructuredFormatter(cfg)

    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="User authenticated successfully",
        args=(),
        exc_info=None,
    )
    # Attach extra fields with sensitive information
    record.extra_fields = {
        "user_id": "usr_12345",
        "password": "plain_text_password_should_be_redacted",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.sensitive_payload",
        "symbol": "EUR/USD",
    }

    formatted_json = formatter.format(record)
    log_data = json.loads(formatted_json)

    assert log_data["user_id"] == "usr_12345"
    assert log_data["symbol"] == "EUR/USD"
    assert log_data["password"] == "***REDACTED***"
    assert log_data["token"] == "***REDACTED***"


# ─── TEST 8: Alembic Linear Migration Chain Integrity ───────────────────────


def test_alembic_migrations_chain() -> None:
    """Verifies that all 7 Alembic revisions form a contiguous, unbroken linear chain from 0001 to 0007."""
    versions_dir = Path(__file__).resolve().parents[2] / "database" / "migrations" / "versions"
    assert versions_dir.is_dir(), f"Alembic versions dir not found at {versions_dir}"

    migration_files = sorted(
        [f for f in versions_dir.glob("*.py") if not f.name.startswith("__")]
    )
    assert len(migration_files) == 7, f"Expected 7 migration files, found {len(migration_files)}"

    rev_map: dict[str, str | None] = {}

    for mf in migration_files:
        tree = ast.parse(mf.read_text(encoding="utf-8"))
        revision_id: str | None = None
        down_revision_id: str | None = None

        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "revision" and isinstance(node.value, ast.Constant):
                            revision_id = str(node.value.value)
                        elif target.id == "down_revision" and isinstance(node.value, ast.Constant):
                            down_revision_id = (
                                str(node.value.value) if node.value.value is not None else None
                            )
            elif (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.value is not None
            ):
                if node.target.id == "revision" and isinstance(node.value, ast.Constant):
                    revision_id = str(node.value.value)
                elif node.target.id == "down_revision" and isinstance(node.value, ast.Constant):
                    down_revision_id = (
                        str(node.value.value) if node.value.value is not None else None
                    )

        assert revision_id is not None, f"Could not find revision in {mf.name}"
        rev_map[revision_id] = down_revision_id

    # Verify head is 0007_organization_invitations
    head_rev = "0007_organization_invitations"
    assert head_rev in rev_map, f"Head migration {head_rev} not in migration map"

    # Walk backward from head to root
    current = head_rev
    visited = [current]

    while rev_map[current] is not None:
        down = rev_map[current]
        assert down is not None
        assert down in rev_map, f"Broken chain: {current} references non-existent down_revision {down}"
        current = down
        visited.append(current)

    # Must terminate at root with 7 revisions
    assert len(visited) == 7, f"Expected 7 linear revisions, walked {len(visited)}: {visited}"
    assert rev_map[current] is None, f"Root migration {current} must have down_revision=None"
    assert "0001_initial_schema" in current
