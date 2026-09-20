"""Unit tests for authentication endpoints and auth service.

Tests use dependency overrides to mock database sessions and provide
an in-memory auth workflow without requiring a real database connection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apps.trading_engine.src import dependencies
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.services.auth import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from fastapi.testclient import TestClient

from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)


# ─── Auth Service Unit Tests ─────────────────────────────────────────────────


class TestPasswordHashing:
    """Tests for bcrypt password hashing (direct bcrypt, no passlib)."""

    def test_hash_and_verify(self) -> None:
        """Password hashing and verification round-trip."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_wrong_password(self) -> None:
        """Incorrect password fails verification."""
        hashed = get_password_hash("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_hash_is_unique(self) -> None:
        """Same password produces different hashes (bcrypt salting)."""
        h1 = get_password_hash("test_password")
        h2 = get_password_hash("test_password")
        assert h1 != h2

    def test_long_password_truncated(self) -> None:
        """Passwords longer than 72 bytes are safely truncated."""
        long_password = "a" * 200
        hashed = get_password_hash(long_password)
        assert verify_password(long_password, hashed) is True

    def test_unicode_password(self) -> None:
        """Unicode passwords work correctly."""
        password = "Ünïcödé_Pässwörd_日本語"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_empty_string_fails_gracefully(self) -> None:
        """Empty or invalid hash returns False, doesn't crash."""
        assert verify_password("password", "not_a_valid_hash") is False


class TestJWTTokens:
    """Tests for JWT token creation and decoding."""

    def test_create_and_decode(self) -> None:
        """Token round-trip preserves payload."""
        data = {"sub": "user-123", "username": "testuser"}
        token = create_access_token(data)
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["username"] == "testuser"

    def test_expired_token(self) -> None:
        """Expired tokens return None."""
        from datetime import timedelta

        data = {"sub": "user-123"}
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        payload = decode_access_token(token)
        assert payload is None

    def test_invalid_token(self) -> None:
        """Malformed tokens return None."""
        payload = decode_access_token("not.a.valid.token")
        assert payload is None

    def test_wrong_secret(self) -> None:
        """Token decoded with wrong secret returns None."""
        data = {"sub": "user-123"}
        token = create_access_token(data, secret_key="secret-one")
        payload = decode_access_token(token, secret_key="secret-two")
        assert payload is None

    def test_custom_algorithm(self) -> None:
        """Custom algorithm parameter is honoured."""
        data = {"sub": "user-123"}
        token = create_access_token(data, algorithm="HS384")
        payload = decode_access_token(token, algorithm="HS384")
        assert payload is not None
        assert payload["sub"] == "user-123"


# ─── Auth Endpoint Tests ──────────────────────────────────────────────────────


def _make_mock_user(
    user_id: str = "user-abc-123",
    username: str = "testuser",
    email: str = "test@orion.dev",
    is_active: bool = True,
    is_superuser: bool = False,
) -> MagicMock:
    """Create a mock UserModel-like object."""
    user = MagicMock()
    user.id = user_id
    user.username = username
    user.email = email
    user.full_name = "Test User"
    user.is_active = is_active
    user.is_superuser = is_superuser
    user.hashed_password = get_password_hash("TestPassword123!")
    user.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    user.updated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return user


@pytest.fixture
def mock_user() -> MagicMock:
    """A mock active user."""
    return _make_mock_user()


@pytest.fixture
def mock_session(mock_user: MagicMock) -> AsyncMock:
    """Mock async session that returns mock_user from queries."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_user
    session.execute.return_value = result
    return session


@pytest.fixture
def paper_adapter() -> PaperExecutionAdapter:
    """Create a paper execution adapter for testing."""
    config = PaperExecutionConfig(broker_name="paper", is_paper=True)
    return PaperExecutionAdapter(config=config)


@pytest.fixture
def test_app(paper_adapter: PaperExecutionAdapter) -> Any:
    """Create a test FastAPI app with mocked dependencies."""
    app = create_app(paper_adapter=paper_adapter)
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(test_app: Any, mock_session: AsyncMock) -> TestClient:
    """Create a test client with mocked DB session."""
    async def mock_get_db_session():
        yield mock_session

    test_app.dependency_overrides[dependencies.get_db_session] = mock_get_db_session
    return TestClient(test_app)


class TestMeEndpoint:
    """Tests for GET /api/v1/auth/me."""

    def test_me_valid_token(self, auth_client: TestClient) -> None:
        """Valid token returns user info."""
        token = create_access_token({"sub": "user-abc-123"})
        response = auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "user-abc-123"
        assert data["username"] == "testuser"
        assert data["email"] == "test@orion.dev"

    def test_me_no_token(self, auth_client: TestClient) -> None:
        """Missing token returns 401."""
        response = auth_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_me_invalid_token(self, auth_client: TestClient) -> None:
        """Invalid token returns 401."""
        response = auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_me_expired_token(self, auth_client: TestClient) -> None:
        """Expired token returns 401."""
        from datetime import timedelta

        token = create_access_token(
            {"sub": "user-abc-123"},
            expires_delta=timedelta(seconds=-1),
        )
        response = auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    def test_me_user_not_found(
        self, test_app: Any, paper_adapter: PaperExecutionAdapter
    ) -> None:
        """Token for non-existent user returns 401."""
        mock_session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None  # user not found
        mock_session.execute.return_value = result

        async def mock_get_db_session():
            yield mock_session

        test_app.dependency_overrides[dependencies.get_db_session] = mock_get_db_session
        client = TestClient(test_app)

        token = create_access_token({"sub": "nonexistent-user"})
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    def test_me_inactive_user(
        self, test_app: Any, paper_adapter: PaperExecutionAdapter
    ) -> None:
        """Token for disabled user returns 403."""
        inactive_user = _make_mock_user(is_active=False)
        mock_session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = inactive_user
        mock_session.execute.return_value = result

        async def mock_get_db_session():
            yield mock_session

        test_app.dependency_overrides[dependencies.get_db_session] = mock_get_db_session
        client = TestClient(test_app)

        token = create_access_token({"sub": inactive_user.id})
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login."""

    def test_login_success(self, auth_client: TestClient, mock_user: MagicMock) -> None:
        """Valid credentials return access token."""
        response = auth_client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "TestPassword123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == "testuser"

    def test_login_wrong_password(self, auth_client: TestClient) -> None:
        """Wrong password returns 401."""
        response = auth_client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "WrongPassword123!"},
        )
        assert response.status_code == 401

    def test_login_user_not_found(self, test_app: Any) -> None:
        """Login for non-existent user returns 401."""
        mock_session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result

        async def mock_get_db_session():
            yield mock_session

        test_app.dependency_overrides[dependencies.get_db_session] = mock_get_db_session
        client = TestClient(test_app)

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "ghostuser", "password": "SomePassword1!"},
        )
        assert response.status_code == 401

    def test_login_short_password_validation(self, auth_client: TestClient) -> None:
        """Password shorter than 8 chars fails validation."""
        response = auth_client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "short"},
        )
        assert response.status_code == 422  # Pydantic validation error
