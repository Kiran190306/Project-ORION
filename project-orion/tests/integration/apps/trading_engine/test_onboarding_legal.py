"""Integration tests for Onboarding registration legal consent enforcement."""

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
from sqlalchemy import select

from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.config import DatabaseConfig, DatabaseManager
from libraries.infrastructure.persistence.models import (
    LegalAcceptanceModel,
    UserModel,
    UserStatus,
)


@pytest.fixture
async def onboarding_legal_env():
    """Set up an isolated database and test client for onboarding verification."""
    db_file = f"test_onboarding_legal_{uuid.uuid4().hex[:8]}.db"
    db_path = pathlib.Path(db_file)
    db_url = f"sqlite+aiosqlite:///{db_file}"

    db_config = DatabaseConfig(url=db_url, echo=False)
    db_manager = DatabaseManager(db_config)

    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed existing user to test that login is unaffected
    existing_user_id = str(uuid.uuid4())
    async with db_manager.session_factory() as session:
        existing_user = UserModel(
            id=existing_user_id,
            username="existing_trader",
            email="existing@orion.legal",
            hashed_password=get_password_hash("Password123!"),
            is_active=True,
            status=UserStatus.ACTIVE.value,
            email_verified=True,
        )
        session.add(existing_user)
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
            "db_manager": db_manager,
            "existing_user_id": existing_user_id,
        }

    # Cleanup DB
    await db_manager.engine.dispose()
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass


class TestOnboardingLegalConsent:
    """Test suite verifying mandatory legal consent during registration."""

    async def test_registration_succeeds_with_all_consents_accepted(self, onboarding_legal_env) -> None:
        client = onboarding_legal_env["client"]
        db_manager = onboarding_legal_env["db_manager"]

        payload = {
            "username": "new_beta_user",
            "email": "beta_user@orion.legal",
            "password": "SecurePassword123!",
            "organization_name": "Orion Beta Desk",
            "organization_slug": "orion-beta-desk",
            "full_name": "Beta Trader",
            "terms_accepted": True,
            "privacy_acknowledged": True,
            "risk_disclosure_acknowledged": True,
        }

        res = await client.post("/api/v1/onboarding/register", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["username"] == "new_beta_user"
        user_id = data["user_id"]

        # Verify that exactly 3 legal acceptances were persisted in DB
        async with db_manager.session_factory() as session:
            stmt = select(LegalAcceptanceModel).where(LegalAcceptanceModel.user_id == user_id)
            res_db = await session.execute(stmt)
            acceptances = res_db.scalars().all()
            assert len(acceptances) == 3

            types = {a.document_type for a in acceptances}
            assert types == {
                "TERMS_OF_SERVICE",
                "PRIVACY_POLICY",
                "PAPER_RISK_DISCLOSURE",
            }
            for a in acceptances:
                assert a.document_version == "1.0"
                assert a.acceptance_method == "WEB_REGISTRATION"
                assert a.organization_id == data["organization_id"]

    async def test_registration_fails_if_terms_not_accepted(self, onboarding_legal_env) -> None:
        client = onboarding_legal_env["client"]

        payload = {
            "username": "declining_user_1",
            "email": "decline1@orion.legal",
            "password": "SecurePassword123!",
            "organization_name": "Declining Desk",
            "terms_accepted": False,
            "privacy_acknowledged": True,
            "risk_disclosure_acknowledged": True,
        }

        res = await client.post("/api/v1/onboarding/register", json=payload)
        assert res.status_code == 422
        assert "accept the Terms of Service" in res.text

    async def test_registration_fails_if_privacy_not_acknowledged(self, onboarding_legal_env) -> None:
        client = onboarding_legal_env["client"]

        payload = {
            "username": "declining_user_2",
            "email": "decline2@orion.legal",
            "password": "SecurePassword123!",
            "organization_name": "Declining Desk 2",
            "terms_accepted": True,
            "privacy_acknowledged": False,
            "risk_disclosure_acknowledged": True,
        }

        res = await client.post("/api/v1/onboarding/register", json=payload)
        assert res.status_code == 422
        assert "acknowledge the Privacy Policy" in res.text

    async def test_registration_fails_if_risk_disclosure_not_acknowledged(self, onboarding_legal_env) -> None:
        client = onboarding_legal_env["client"]

        payload = {
            "username": "declining_user_3",
            "email": "decline3@orion.legal",
            "password": "SecurePassword123!",
            "organization_name": "Declining Desk 3",
            "terms_accepted": True,
            "privacy_acknowledged": True,
            "risk_disclosure_acknowledged": False,
        }

        res = await client.post("/api/v1/onboarding/register", json=payload)
        assert res.status_code == 422
        assert "acknowledge the Paper Trading Risk Disclosure" in res.text

    async def test_existing_user_login_unaffected(self, onboarding_legal_env) -> None:
        """Confirm that existing Phase 1 user login is unaffected and not blocked."""
        client = onboarding_legal_env["client"]

        res = await client.post(
            "/api/v1/auth/login",
            json={"username": "existing_trader", "password": "Password123!"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
