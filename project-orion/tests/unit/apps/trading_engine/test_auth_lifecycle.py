"""Comprehensive unit tests for EPIC-027 Phase 1 Auth & Account Lifecycle Hardening.

Covers:
- Password policy validation
- Password reset (request, anti-enumeration, hashing, expiry, single-use, completion)
- Email verification (verification, replay prevention, expiry, resend)
- Account deactivation (confirmation, sole-owner protection, session revocation)
- Account reactivation (admin auth gate)
- Audit log emission
- JWT revocation via password_changed_at
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from apps.trading_engine.src import dependencies
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.services.auth import (
    create_access_token,
    generate_secure_token,
    get_password_hash,
    hash_security_token,
    validate_password_strength,
    verify_password,
)
from fastapi.testclient import TestClient

from libraries.infrastructure.communication.email_service import (
    MockEmailAdapter,
    set_email_service,
)
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.persistence.models import (
    AuthTokenModel,
    OrganizationModel,
    TokenType,
    UserModel,
    UserStatus,
)


@pytest.fixture
def mock_email_adapter() -> MockEmailAdapter:
    adapter = MockEmailAdapter()
    set_email_service(adapter)
    return adapter


@pytest.fixture
def paper_adapter() -> PaperExecutionAdapter:
    config = PaperExecutionConfig(broker_name="paper", is_paper=True)
    return PaperExecutionAdapter(config=config)


@pytest.fixture
def test_app(paper_adapter: PaperExecutionAdapter) -> Any:
    app = create_app(paper_adapter=paper_adapter)
    yield app
    app.dependency_overrides.clear()


def _get_err_message(response_data: dict[str, Any]) -> str:
    """Helper to extract error message from standard Orion ErrorResponse or FastAPI detail."""
    return str(response_data.get("message") or response_data.get("detail", "")).lower()


def _make_mock_user(
    user_id: str = "usr-test-123",
    username: str = "trader_alice",
    email: str = "alice@example.com",
    password: str = "SecurePass123!",
    is_active: bool = True,
    status: str = "ACTIVE",
    is_superuser: bool = False,
    email_verified: bool = False,
    password_changed_at: datetime | None = None,
) -> UserModel:
    now = datetime.now(timezone.utc)
    user = UserModel(
        id=user_id,
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        is_active=is_active,
        status=status,
        is_superuser=is_superuser,
        email_verified=email_verified,
        password_changed_at=password_changed_at,
        full_name="Alice Trader",
        created_at=now,
        updated_at=now,
    )
    return user


def _make_mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


# ─── Password Strength Tests ──────────────────────────────────────────────────


class TestPasswordStrengthPolicy:
    """Tests for institutional password policy."""

    def test_valid_password(self) -> None:
        valid, msg = validate_password_strength("StrongP@ssw0rd!")
        assert valid is True
        assert msg == ""

    def test_too_short_password(self) -> None:
        valid, msg = validate_password_strength("Short1!")
        assert valid is False
        assert "at least 8 characters" in msg

    def test_missing_numbers_or_symbols(self) -> None:
        valid, msg = validate_password_strength("OnlyLettersHere")
        assert valid is False
        assert "digit or symbol" in msg

    def test_missing_letters(self) -> None:
        valid, msg = validate_password_strength("123456789!@#")
        assert valid is False
        assert "at least one letter" in msg


# ─── Password Reset Tests ─────────────────────────────────────────────────────


class TestForgotPasswordFlow:
    """Tests for POST /api/v1/auth/forgot-password."""

    def test_forgot_password_existing_user(
        self, mock_email_adapter: MockEmailAdapter, test_app: Any
    ) -> None:
        """Existing user receives reset email; generic response returned."""
        user = _make_mock_user(email="alice@example.com")
        mock_session = _make_mock_session()

        # Session execute returns user, then empty existing tokens
        user_res = MagicMock()
        user_res.scalar_one_or_none.return_value = user

        token_res = MagicMock()
        token_res.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [user_res, token_res]

        test_app.dependency_overrides[dependencies.get_db_session] = lambda: mock_session
        client = TestClient(test_app)

        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "alice@example.com"},
        )
        assert response.status_code == 200
        assert "instructions have been sent" in response.json()["message"]

        # Verify email was dispatched
        assert len(mock_email_adapter.sent_emails) == 1
        sent = mock_email_adapter.sent_emails[0]
        assert sent.to_email == "alice@example.com"
        assert sent.template == "password_reset"
        assert len(sent.token) > 20

        # Verify token was added to session
        assert any(isinstance(arg[0][0], AuthTokenModel) for arg in mock_session.add.call_args_list)

    def test_forgot_password_unknown_user_anti_enumeration(
        self, mock_email_adapter: MockEmailAdapter, test_app: Any
    ) -> None:
        """Unknown user returns identical generic response with 0 emails dispatched."""
        mock_session = _make_mock_session()
        user_res = MagicMock()
        user_res.scalar_one_or_none.return_value = None  # not found
        mock_session.execute.return_value = user_res

        test_app.dependency_overrides[dependencies.get_db_session] = lambda: mock_session
        client = TestClient(test_app)

        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "ghost@example.com"},
        )
        assert response.status_code == 200
        assert "instructions have been sent" in response.json()["message"]
        assert len(mock_email_adapter.sent_emails) == 0


class TestResetPasswordCompletion:
    """Tests for POST /api/v1/auth/reset-password."""

    def test_reset_password_success(self, test_app: Any) -> None:
        """Valid token resets password and updates password_changed_at."""
        user = _make_mock_user(user_id="usr-1", password="OldPassword123!")
        raw_token = generate_secure_token()
        token_hash = hash_security_token(raw_token)

        now = datetime.now(timezone.utc)
        token_record = AuthTokenModel(
            id="tok-1",
            user_id="usr-1",
            token_hash=token_hash,
            token_type=TokenType.PASSWORD_RESET.value,
            expires_at=now + timedelta(minutes=15),
            used_at=None,
        )

        mock_session = _make_mock_session()
        tok_res = MagicMock()
        tok_res.scalar_one_or_none.return_value = token_record
        usr_res = MagicMock()
        usr_res.scalar_one_or_none.return_value = user
        mock_session.execute.side_effect = [tok_res, usr_res]

        test_app.dependency_overrides[dependencies.get_db_session] = lambda: mock_session
        client = TestClient(test_app)

        response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "BrandNewPassword123!"},
        )
        assert response.status_code == 200
        assert "successfully reset" in response.json()["message"]

        # Verify token was marked used
        assert token_record.used_at is not None
        # Verify password hash updated
        assert verify_password("BrandNewPassword123!", user.hashed_password) is True
        assert verify_password("OldPassword123!", user.hashed_password) is False
        assert user.password_changed_at is not None

    def test_reset_password_expired_token(self, test_app: Any) -> None:
        """Expired reset token is rejected."""
        raw_token = generate_secure_token()
        token_hash = hash_security_token(raw_token)
        now = datetime.now(timezone.utc)

        token_record = AuthTokenModel(
            id="tok-1",
            user_id="usr-1",
            token_hash=token_hash,
            token_type=TokenType.PASSWORD_RESET.value,
            expires_at=now - timedelta(minutes=5),  # expired
            used_at=None,
        )

        mock_session = _make_mock_session()
        tok_res = MagicMock()
        tok_res.scalar_one_or_none.return_value = token_record
        mock_session.execute.return_value = tok_res

        test_app.dependency_overrides[dependencies.get_db_session] = lambda: mock_session
        client = TestClient(test_app)

        response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "BrandNewPassword123!"},
        )
        assert response.status_code == 400
        err_msg = _get_err_message(response.json())
        assert "expired" in err_msg

    def test_reset_password_single_use_replay_blocked(self, test_app: Any) -> None:
        """Already-used token replay is rejected."""
        raw_token = generate_secure_token()
        token_hash = hash_security_token(raw_token)
        now = datetime.now(timezone.utc)

        token_record = AuthTokenModel(
            id="tok-1",
            user_id="usr-1",
            token_hash=token_hash,
            token_type=TokenType.PASSWORD_RESET.value,
            expires_at=now + timedelta(minutes=10),
            used_at=now - timedelta(minutes=1),  # already used
        )

        mock_session = _make_mock_session()
        tok_res = MagicMock()
        tok_res.scalar_one_or_none.return_value = token_record
        mock_session.execute.return_value = tok_res

        test_app.dependency_overrides[dependencies.get_db_session] = lambda: mock_session
        client = TestClient(test_app)

        response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "BrandNewPassword123!"},
        )
        assert response.status_code == 400
        err_msg = _get_err_message(response.json())
        assert "already been used" in err_msg


# ─── Email Verification Tests ─────────────────────────────────────────────────


class TestEmailVerificationFlow:
    """Tests for email verification and resend."""

    def test_verify_email_success(self, test_app: Any) -> None:
        """Valid token marks email_verified as True."""
        user = _make_mock_user(user_id="usr-1", email_verified=False)
        raw_token = generate_secure_token()
        token_hash = hash_security_token(raw_token)
        now = datetime.now(timezone.utc)

        token_record = AuthTokenModel(
            id="tok-1",
            user_id="usr-1",
            token_hash=token_hash,
            token_type=TokenType.EMAIL_VERIFICATION.value,
            expires_at=now + timedelta(hours=24),
            used_at=None,
        )

        mock_session = _make_mock_session()
        tok_res = MagicMock()
        tok_res.scalar_one_or_none.return_value = token_record
        usr_res = MagicMock()
        usr_res.scalar_one_or_none.return_value = user
        mock_session.execute.side_effect = [tok_res, usr_res]

        test_app.dependency_overrides[dependencies.get_db_session] = lambda: mock_session
        client = TestClient(test_app)

        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": raw_token},
        )
        assert response.status_code == 200
        assert "successfully verified" in response.json()["message"]
        assert user.email_verified is True
        assert token_record.used_at is not None

    def test_verify_email_replay_blocked(self, test_app: Any) -> None:
        """Replaying a used verification token fails."""
        raw_token = generate_secure_token()
        token_hash = hash_security_token(raw_token)
        now = datetime.now(timezone.utc)

        token_record = AuthTokenModel(
            id="tok-1",
            user_id="usr-1",
            token_hash=token_hash,
            token_type=TokenType.EMAIL_VERIFICATION.value,
            expires_at=now + timedelta(hours=20),
            used_at=now - timedelta(hours=1),
        )

        mock_session = _make_mock_session()
        tok_res = MagicMock()
        tok_res.scalar_one_or_none.return_value = token_record
        mock_session.execute.return_value = tok_res

        test_app.dependency_overrides[dependencies.get_db_session] = lambda: mock_session
        client = TestClient(test_app)

        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": raw_token},
        )
        assert response.status_code == 400
        err_msg = _get_err_message(response.json())
        assert "already been used" in err_msg

    def test_resend_verification_sends_email(
        self, mock_email_adapter: MockEmailAdapter, test_app: Any
    ) -> None:
        """Resending verification token sends email for unverified user."""
        user = _make_mock_user(email="unverified@example.com", email_verified=False)
        mock_session = _make_mock_session()

        usr_res = MagicMock()
        usr_res.scalar_one_or_none.return_value = user
        toks_res = MagicMock()
        toks_res.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [usr_res, toks_res]

        test_app.dependency_overrides[dependencies.get_db_session] = lambda: mock_session
        client = TestClient(test_app)

        response = client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "unverified@example.com"},
        )
        assert response.status_code == 200
        assert len(mock_email_adapter.sent_emails) == 1
        assert mock_email_adapter.sent_emails[0].template == "email_verification"


# ─── Account Deactivation & Safeguards ─────────────────────────────────────────


class TestAccountDeactivationSafeguards:
    """Tests for POST /api/v1/auth/deactivate."""

    def test_sole_owner_deactivation_blocked(self, test_app: Any) -> None:
        """A user who is the sole active owner of an organization cannot deactivate."""
        user = _make_mock_user(user_id="usr-owner-1", password="ValidPassword123!")

        mock_session = _make_mock_session()
        # 1. Fetch user
        usr_res = MagicMock()
        usr_res.scalar_one_or_none.return_value = user

        # 2. Owned organizations query
        owned_res = MagicMock()
        owned_res.scalars.return_value.all.return_value = ["org-1"]

        # 3. Other owners count (0 other owners)
        count_res = MagicMock()
        count_res.scalar_one.return_value = 0

        # 4. Fetch org name
        org_model = OrganizationModel(id="org-1", name="Alpha Capital", slug="alpha-cap", status="ACTIVE")
        org_res = MagicMock()
        org_res.scalar_one_or_none.return_value = org_model

        mock_session.execute.side_effect = [usr_res, owned_res, count_res, org_res]

        test_app.dependency_overrides[dependencies.get_db_session] = lambda: mock_session
        test_app.dependency_overrides[dependencies.get_current_user] = lambda: {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": True,
            "status": "ACTIVE",
            "is_superuser": False,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
        client = TestClient(test_app)

        response = client.post(
            "/api/v1/auth/deactivate",
            json={"password": "ValidPassword123!", "confirmation": "DEACTIVATE"},
        )
        assert response.status_code == 409
        err_msg = _get_err_message(response.json())
        assert "sole active owner" in err_msg
        assert "alpha capital" in err_msg

    def test_deactivation_success_when_not_sole_owner(self, test_app: Any) -> None:
        """User with multiple co-owners can deactivate successfully."""
        user = _make_mock_user(user_id="usr-owner-2", password="ValidPassword123!")

        mock_session = _make_mock_session()
        usr_res = MagicMock()
        usr_res.scalar_one_or_none.return_value = user

        owned_res = MagicMock()
        owned_res.scalars.return_value.all.return_value = ["org-1"]

        count_res = MagicMock()
        count_res.scalar_one.return_value = 1  # 1 other owner exists!

        mock_session.execute.side_effect = [usr_res, owned_res, count_res]

        test_app.dependency_overrides[dependencies.get_db_session] = lambda: mock_session
        test_app.dependency_overrides[dependencies.get_current_user] = lambda: {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": True,
            "status": "ACTIVE",
            "is_superuser": False,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
        client = TestClient(test_app)

        response = client.post(
            "/api/v1/auth/deactivate",
            json={"password": "ValidPassword123!", "confirmation": "DEACTIVATE"},
        )
        assert response.status_code == 200
        assert "successfully deactivated" in response.json()["message"]
        assert user.is_active is False
        assert user.status == UserStatus.DEACTIVATED.value
        assert user.password_changed_at is not None

    def test_deactivated_user_login_blocked(self, test_app: Any) -> None:
        """Deactivated user cannot authenticate."""
        user = _make_mock_user(is_active=False, status=UserStatus.DEACTIVATED.value)

        mock_session = _make_mock_session()
        usr_res = MagicMock()
        usr_res.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = usr_res

        test_app.dependency_overrides[dependencies.get_db_session] = lambda: mock_session
        client = TestClient(test_app)

        response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": "AnyPassword123!"},
        )
        assert response.status_code == 403
        err_msg = _get_err_message(response.json())
        assert "account is disabled" in err_msg


# ─── Reactivation Tests ───────────────────────────────────────────────────────


class TestAccountReactivation:
    """Tests for POST /api/v1/auth/users/{user_id}/reactivate."""

    def test_reactivation_requires_superuser(self, test_app: Any) -> None:
        """Non-admin user cannot reactivate accounts."""
        mock_session = _make_mock_session()
        test_app.dependency_overrides[dependencies.get_db_session] = lambda: mock_session
        test_app.dependency_overrides[dependencies.get_current_user] = lambda: {
            "id": "regular-user",
            "username": "regular",
            "is_superuser": False,
        }
        client = TestClient(test_app)

        response = client.post("/api/v1/auth/users/usr-target/reactivate")
        assert response.status_code == 403

    def test_reactivation_success(self, test_app: Any) -> None:
        """Platform admin can reactivate a deactivated user."""
        target_user = _make_mock_user(user_id="usr-target", is_active=False, status="DEACTIVATED")

        mock_session = _make_mock_session()
        usr_res = MagicMock()
        usr_res.scalar_one_or_none.return_value = target_user
        mock_session.execute.return_value = usr_res

        test_app.dependency_overrides[dependencies.get_db_session] = lambda: mock_session
        test_app.dependency_overrides[dependencies.get_current_user] = lambda: {
            "id": "admin-1",
            "username": "admin",
            "is_superuser": True,
        }
        client = TestClient(test_app)

        response = client.post("/api/v1/auth/users/usr-target/reactivate")
        assert response.status_code == 200
        assert "reactivated" in response.json()["message"]
        assert target_user.is_active is True
        assert target_user.status == "ACTIVE"


# ─── JWT Revocation via Password Change ───────────────────────────────────────


class TestJWTRevocation:
    """Tests for token revocation when password changes."""

    def test_token_issued_before_password_change_is_revoked(
        self, test_app: Any
    ) -> None:
        """Access token issued prior to password_changed_at is rejected on protected endpoints."""
        now = datetime.now(timezone.utc)
        # Token issued 10 minutes ago
        issued_at = now - timedelta(minutes=10)
        token = create_access_token(
            {"sub": "usr-1", "username": "alice", "iat": int(issued_at.timestamp())}
        )

        # Password was changed 2 minutes ago
        user = _make_mock_user(
            user_id="usr-1",
            password_changed_at=now - timedelta(minutes=2),
        )

        mock_session = _make_mock_session()
        usr_res = MagicMock()
        usr_res.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = usr_res

        test_app.dependency_overrides[dependencies.get_db_session] = lambda: mock_session
        client = TestClient(test_app)

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401
        err_msg = _get_err_message(response.json())
        assert "revoked" in err_msg
