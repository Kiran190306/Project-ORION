"""Integration tests for EPIC-027 Phase 2: Public API Rate Limiting & Abuse Defense.

Verifies:
1. Endpoint rate limit enforcement (429 Too Many Requests after limit).
2. RFC-7807 error envelope and mandatory headers: Retry-After, X-RateLimit-Limit,
   X-RateLimit-Remaining, and X-RateLimit-Reset.
3. Anti-enumeration behavior preservation: 401 generic error until rate limit, then 429.
4. IP-based quota isolation: exhausting limit for IP A does not block IP B.
5. In-memory bounded fallback functioning safely when Redis is unavailable.
"""

from __future__ import annotations

import pathlib
import uuid
from decimal import Decimal
from unittest import mock

import pytest
from apps.trading_engine.src.config import AppSettings
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.services.auth import get_password_hash
from apps.trading_engine.src.services.rate_limit_service import RateLimitService
from httpx import ASGITransport, AsyncClient

from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.config import DatabaseConfig, DatabaseManager
from libraries.infrastructure.persistence.models import (
    UserModel,
    UserStatus,
)


@pytest.fixture
async def rate_limit_test_env():
    """Set up an isolated database and test client with in-memory rate limiting."""
    db_file = f"test_rate_limit_{uuid.uuid4().hex[:8]}.db"
    db_path = pathlib.Path(db_file)
    db_url = f"sqlite+aiosqlite:///{db_file}"

    db_config = DatabaseConfig(url=db_url, echo=False)
    db_manager = DatabaseManager(db_config)

    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed test user
    async with db_manager.session_factory() as session:
        user = UserModel(
            id=str(uuid.uuid4()),
            username="ratelimit_user",
            email="ratelimit@example.com",
            hashed_password=get_password_hash("ValidPass123!"),
            is_active=True,
            status=UserStatus.ACTIVE.value,
        )
        session.add(user)
        await session.commit()

    settings = AppSettings(
        environment="testing",
        log_level="INFO",
        database_url=db_url,
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
        rate_limiting_enabled=True,
        trusted_proxies=("127.0.0.1", "::1"),
    )

    mock_redis = mock.create_autospec(RedisClient, instance=True)
    mock_redis.is_connected = False
    mock_redis.eval_script = mock.AsyncMock(side_effect=ConnectionError("Redis unavailable in unit test"))

    # RateLimitService with Redis failing falls back to bounded in-memory limiter
    rate_limit_svc = RateLimitService(
        redis_client=mock_redis,
        enabled=True,
        trusted_proxies=("127.0.0.1", "::1"),
    )

    adapter_config = PaperExecutionConfig(
        broker_name="paper",
        is_paper=True,
        balance=Decimal("100000.00"),
    )
    paper_adapter = PaperExecutionAdapter(config=adapter_config)

    app = create_app(
        settings=settings,
        db_manager=db_manager,
        redis_client=mock_redis,
        paper_adapter=paper_adapter,
        rate_limit_service=rate_limit_svc,
    )

    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app, client=("198.51.100.1", 54321)),
        base_url="http://test",
    ) as client:
        yield {
            "client": client,
            "app": app,
            "rate_limit_svc": rate_limit_svc,
        }

    await paper_adapter.disconnect()
    await db_manager.close()
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass


@pytest.mark.asyncio
async def test_auth_login_rate_limiting_and_headers(rate_limit_test_env: dict):
    """5 invalid login attempts from same IP succeed (with 401), 6th attempt returns 429."""
    client: AsyncClient = rate_limit_test_env["client"]

    # Limit for AUTH_LOGIN is 5 per hour
    for i in range(5):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "wrong_user", "password": "WrongPassword1!"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid username or password"

    # 6th attempt must be rejected with 429
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "wrong_user", "password": "WrongPassword1!"},
    )
    assert resp.status_code == 429

    # Verify RFC-7807 JSON body
    body = resp.json()
    assert body["error"] == "rate_limit_exceeded"
    assert "Rate limit exceeded" in body["detail"]

    # Verify rate limit headers
    headers = resp.headers
    assert "retry-after" in headers
    assert int(headers["retry-after"]) > 0
    assert headers["x-ratelimit-limit"] == "5"
    assert headers["x-ratelimit-remaining"] == "0"
    assert "x-ratelimit-reset" in headers


@pytest.mark.asyncio
async def test_ip_isolation(rate_limit_test_env: dict):
    """Exhausting rate limit on IP A does not block IP B."""
    app = rate_limit_test_env["app"]

    # Client A from 198.51.100.10
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("198.51.100.10", 50000)),
        base_url="http://test",
    ) as client_a:
        for _ in range(5):
            resp = await client_a.post(
                "/api/v1/auth/login",
                json={"username": "user_a", "password": "Password123!"},
            )
            assert resp.status_code == 401

        # 6th request from Client A is blocked
        resp_a = await client_a.post(
            "/api/v1/auth/login",
            json={"username": "user_a", "password": "Password123!"},
        )
        assert resp_a.status_code == 429

    # Client B from 198.51.100.20 should still be allowed
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("198.51.100.20", 50000)),
        base_url="http://test",
    ) as client_b:
        resp_b = await client_b.post(
            "/api/v1/auth/login",
            json={"username": "user_b", "password": "Password123!"},
        )
        # Should be 401 (invalid credentials), NOT 429
        assert resp_b.status_code == 401


@pytest.mark.asyncio
async def test_anti_enumeration_preserved(rate_limit_test_env: dict):
    """Anti-enumeration is preserved: non-existent users return generic 401 until rate limit."""
    app = rate_limit_test_env["app"]

    async with AsyncClient(
        transport=ASGITransport(app=app, client=("198.51.100.30", 50000)),
        base_url="http://test",
    ) as client:
        # Non-existent username
        resp1 = await client.post(
            "/api/v1/auth/login",
            json={"username": "non_existent_user_9999", "password": "Password123!"},
        )
        assert resp1.status_code == 401
        assert resp1.json()["detail"] == "Invalid username or password"

        # Real username, wrong password
        resp2 = await client.post(
            "/api/v1/auth/login",
            json={"username": "ratelimit_user", "password": "WrongPassword1!"},
        )
        assert resp2.status_code == 401
        assert resp2.json()["detail"] == "Invalid username or password"
