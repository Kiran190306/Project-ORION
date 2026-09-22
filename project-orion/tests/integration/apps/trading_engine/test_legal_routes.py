"""Integration tests for Legal, Trust & Risk Disclosure API routes."""

from __future__ import annotations

import pathlib
import uuid
from decimal import Decimal
from unittest import mock

import pytest
from apps.trading_engine.src.config import AppSettings
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.services.auth import create_access_token, get_password_hash
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
async def legal_test_env():
    """Set up an isolated database and test client."""
    db_file = f"test_legal_routes_{uuid.uuid4().hex[:8]}.db"
    db_path = pathlib.Path(db_file)
    db_url = f"sqlite+aiosqlite:///{db_file}"

    db_config = DatabaseConfig(url=db_url, echo=False)
    db_manager = DatabaseManager(db_config)

    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed test user
    user_id = str(uuid.uuid4())
    async with db_manager.session_factory() as session:
        user = UserModel(
            id=user_id,
            username="legal_tester",
            email="tester@orion.legal",
            hashed_password=get_password_hash("ValidPass123!"),
            is_active=True,
            status=UserStatus.ACTIVE.value,
            email_verified=True,
        )
        session.add(user)
        await session.commit()

    token = create_access_token(data={"sub": user_id, "username": "legal_tester"})

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
        rate_limiting_enabled=False,
    )

    mock_redis = mock.create_autospec(RedisClient, instance=True)
    mock_redis.is_connected = False
    mock_redis.eval_script = mock.AsyncMock(side_effect=ConnectionError("Redis unavailable in unit test"))

    rate_limit_svc = RateLimitService(
        redis_client=mock_redis,
        enabled=False,
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

    transport = ASGITransport(app=app)
    async with app.router.lifespan_context(app), AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        yield {
            "client": client,
            "user_id": user_id,
            "token": token,
            "auth_headers": {"Authorization": f"Bearer {token}"},
        }

    # Cleanup DB
    await db_manager.engine.dispose()
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass


class TestLegalRoutes:
    """Test suite verifying public legal endpoints and authenticated acceptance."""

    async def test_list_active_documents(self, legal_test_env) -> None:
        client = legal_test_env["client"]
        res = await client.get("/api/v1/legal/documents")
        assert res.status_code == 200
        docs = res.json()
        assert len(docs) == 5
        types = {d["document_type"] for d in docs}
        assert "TERMS_OF_SERVICE" in types
        assert "PRIVACY_POLICY" in types
        assert "PAPER_RISK_DISCLOSURE" in types
        assert "REFUND_POLICY" in types
        assert "SECURITY_DISCLOSURE" in types

    async def test_get_document_detail_markdown(self, legal_test_env) -> None:
        client = legal_test_env["client"]
        res = await client.get("/api/v1/legal/documents/TERMS_OF_SERVICE")
        assert res.status_code == 200
        data = res.json()
        assert data["document_type"] == "TERMS_OF_SERVICE"
        assert data["version"] == "1.0"
        assert "content_markdown" in data
        assert "$0.00 Capital at Risk" in data["content_markdown"]

    async def test_get_unknown_document_returns_404(self, legal_test_env) -> None:
        client = legal_test_env["client"]
        res = await client.get("/api/v1/legal/documents/UNKNOWN_POLICY")
        assert res.status_code == 404

    async def test_submit_acceptance_requires_authentication(self, legal_test_env) -> None:
        client = legal_test_env["client"]
        res = await client.post(
            "/api/v1/legal/acceptances",
            json={"document_type": "TERMS_OF_SERVICE", "version": "1.0"},
        )
        assert res.status_code == 401

    async def test_submit_acceptance_and_list(self, legal_test_env) -> None:
        client = legal_test_env["client"]
        auth_headers = legal_test_env["auth_headers"]

        # Submit acceptance
        res = await client.post(
            "/api/v1/legal/acceptances",
            json={"document_type": "TERMS_OF_SERVICE", "version": "1.0"},
            headers=auth_headers,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["document_type"] == "TERMS_OF_SERVICE"
        assert data["document_version"] == "1.0"
        assert data["acceptance_method"] == "WEB_IN_APP"

        # List acceptances
        list_res = await client.get("/api/v1/legal/acceptances", headers=auth_headers)
        assert list_res.status_code == 200
        acceptances = list_res.json()
        assert len(acceptances) == 1
        assert acceptances[0]["document_type"] == "TERMS_OF_SERVICE"

    async def test_submit_acceptance_invalid_version_returns_400(self, legal_test_env) -> None:
        client = legal_test_env["client"]
        auth_headers = legal_test_env["auth_headers"]

        res = await client.post(
            "/api/v1/legal/acceptances",
            json={"document_type": "TERMS_OF_SERVICE", "version": "999.0"},
            headers=auth_headers,
        )
        assert res.status_code == 400
        assert "not an active version" in res.json()["detail"]
