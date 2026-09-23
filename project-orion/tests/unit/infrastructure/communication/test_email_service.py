"""Unit tests for transactional email service, SMTP adapter, configuration, and anti-enumeration hardening."""

from __future__ import annotations

import logging
import smtplib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apps.trading_engine.src import dependencies
from apps.trading_engine.src.main import create_app
from fastapi.testclient import TestClient

from libraries.infrastructure.communication.email_service import (
    ConsoleEmailAdapter,
    EmailConfigurationError,
    EmailServicePort,
    MockEmailAdapter,
    SmtpConfig,
    SMTPEmailAdapter,
    create_email_service,
    get_email_service,
    mask_email,
    reset_email_service,
    set_email_service,
)
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.persistence.models import UserModel

# ─── 1. Protocol Conformance & In-Memory Adapters ─────────────────────────────


def test_protocol_conformance() -> None:
    """All email adapters conform to the runtime EmailServicePort protocol."""
    mock_adapter = MockEmailAdapter()
    console_adapter = ConsoleEmailAdapter()
    smtp_adapter = SMTPEmailAdapter(config=SmtpConfig(host="smtp.example.com"))

    assert isinstance(mock_adapter, EmailServicePort)
    assert isinstance(console_adapter, EmailServicePort)
    assert isinstance(smtp_adapter, EmailServicePort)


@pytest.mark.asyncio
async def test_mock_email_adapter_lifecycle() -> None:
    """MockEmailAdapter captures sent emails, allows queries by recipient, and clears state."""
    adapter = MockEmailAdapter()

    res1 = await adapter.send_verification_email(
        to_email="alice@example.com",
        verification_token="token-ver-1234567890",
        username="alice",
    )
    assert res1 is True

    res2 = await adapter.send_password_reset_email(
        to_email="bob@example.com",
        reset_token="token-reset-0987654321",
        username="bob",
    )
    assert res2 is True

    assert len(adapter.sent_emails) == 2
    assert adapter.get_last_email() is not None
    assert adapter.get_last_email().to_email == "bob@example.com"
    assert adapter.get_last_email().template == "password_reset"

    alice_emails = adapter.get_emails_for("alice@example.com")
    assert len(alice_emails) == 1
    assert alice_emails[0].template == "email_verification"

    adapter.clear()
    assert len(adapter.sent_emails) == 0
    assert adapter.get_last_email() is None


@pytest.mark.asyncio
async def test_console_email_adapter_masks_tokens_and_emails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """ConsoleEmailAdapter logs formatted link info with masked email and masked token."""
    adapter = ConsoleEmailAdapter()

    with caplog.at_level(logging.INFO):
        res1 = await adapter.send_verification_email(
            to_email="corporate-user@institutional.org",
            verification_token="supersecretverificationtoken12345678",
            username="corp_trader",
        )
        assert res1 is True

        res2 = await adapter.send_password_reset_email(
            to_email="quant@hedgefund.com",
            reset_token="supersecretresettoken87654321",
            username="lead_quant",
        )
        assert res2 is True

    # Raw tokens must never appear in log records
    assert "supersecretverificationtoken12345678" not in caplog.text
    assert "supersecretresettoken87654321" not in caplog.text

    # Masked token prefix must appear
    assert "supersec***" in caplog.text

    # Unmasked emails must not appear
    assert "corporate-user@institutional.org" not in caplog.text
    assert "quant@hedgefund.com" not in caplog.text

    # Masked emails must appear (first char + *** + last char @ domain)
    assert "c***r@institutional.org" in caplog.text
    assert "q***t@hedgefund.com" in caplog.text


# ─── 2. Configuration & Credential Safety ──────────────────────────────────────


def test_smtp_config_defaults() -> None:
    """SmtpConfig provides secure institutional defaults."""
    config = SmtpConfig()
    assert config.host == ""
    assert config.port == 587
    assert config.username == ""
    assert config.password == ""
    assert config.use_tls is True
    assert config.from_email == "notifications@oriontrading.io"
    assert config.from_name == "Project ORION"
    assert config.timeout_seconds == 10.0
    assert config.frontend_url == "https://orion-dashboard.onrender.com"


def test_smtp_config_from_env_canonical() -> None:
    """SmtpConfig parses all canonical ORION environment variables."""
    env = {
        "ORION_SMTP_HOST": "mail.oriontrading.internal",
        "ORION_SMTP_PORT": "465",
        "ORION_SMTP_USERNAME": "orion_mailer",
        "ORION_SMTP_PASSWORD": "super-secure-smtp-password-2026",
        "ORION_SMTP_USE_TLS": "true",
        "ORION_SMTP_FROM_EMAIL": "system@oriontrading.io",
        "ORION_SMTP_FROM_NAME": "ORION Systems",
        "ORION_SMTP_TIMEOUT_SECONDS": "15.5",
        "ORION_FRONTEND_URL": "https://dashboard.oriontrading.io/",
    }
    config = SmtpConfig.from_env(env)
    assert config.host == "mail.oriontrading.internal"
    assert config.port == 465
    assert config.username == "orion_mailer"
    assert config.password == "super-secure-smtp-password-2026"
    assert config.use_tls is True
    assert config.from_email == "system@oriontrading.io"
    assert config.from_name == "ORION Systems"
    assert config.timeout_seconds == 15.5
    assert config.frontend_url == "https://dashboard.oriontrading.io"  # Trailing slash stripped


def test_smtp_config_masks_password_in_repr() -> None:
    """SmtpConfig.__repr__ masks plaintext password."""
    config = SmtpConfig(
        host="smtp.sendgrid.net",
        username="apikey",
        password="SG.very_secret_api_key_12345",
    )
    repr_str = repr(config)
    assert "SG.very_secret_api_key_12345" not in repr_str
    assert "password='***'" in repr_str


def test_smtp_config_invalid_port_raises() -> None:
    """Invalid port string raises EmailConfigurationError."""
    with pytest.raises(EmailConfigurationError, match="ORION_SMTP_PORT must be an integer"):
        SmtpConfig.from_env({"ORION_SMTP_PORT": "not_a_number"})


def test_smtp_config_invalid_timeout_raises() -> None:
    """Invalid timeout string raises EmailConfigurationError."""
    with pytest.raises(EmailConfigurationError, match="ORION_SMTP_TIMEOUT_SECONDS must be a number"):
        SmtpConfig.from_env({"ORION_SMTP_TIMEOUT_SECONDS": "invalid_float"})


# ─── 3. SMTPEmailAdapter Transport & Templates ─────────────────────────────────


@pytest.mark.asyncio
async def test_smtp_send_verification_email_success() -> None:
    """SMTPEmailAdapter connects via STARTTLS, authenticates, and dispatches verification email."""
    config = SmtpConfig(
        host="smtp.mailgun.org",
        port=587,
        username="postmaster@oriontrading.io",
        password="smtp-secret-key",
        use_tls=True,
        from_email="notifications@oriontrading.io",
        from_name="Project ORION",
        frontend_url="https://app.oriontrading.io",
    )
    adapter = SMTPEmailAdapter(config=config)

    mock_server = MagicMock()
    mock_server.__enter__.return_value = mock_server

    with patch("smtplib.SMTP", return_value=mock_server) as mock_smtp_cls:
        sent = await adapter.send_verification_email(
            to_email="trader@hedgefund.com",
            verification_token="verify_token_abc_123",
            username="trader1",
        )

        assert sent is True
        mock_smtp_cls.assert_called_once_with(host="smtp.mailgun.org", port=587, timeout=10.0)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("postmaster@oriontrading.io", "smtp-secret-key")
        mock_server.send_message.assert_called_once()

        # Inspect sent EmailMessage
        msg = mock_server.send_message.call_args[0][0]
        assert msg["Subject"] == "Project ORION — Verify Your Email Address"
        assert msg["To"] == "trader@hedgefund.com"
        assert "notifications@oriontrading.io" in msg["From"]

        # Verify link in text and HTML payloads
        expected_url = "https://app.oriontrading.io/verify-email?token=verify_token_abc_123"
        text_body = msg.get_body(preferencelist=("plain",)).get_content()
        html_body = msg.get_body(preferencelist=("html",)).get_content()
        assert expected_url in text_body
        assert expected_url in html_body
        assert "($0.00 capital at risk)" in text_body
        assert "SIMULATED PAPER EXECUTION — $0.00 REAL CAPITAL" in html_body


@pytest.mark.asyncio
async def test_smtp_send_password_reset_email_success() -> None:
    """SMTPEmailAdapter dispatches password reset email with 15-minute expiration notice."""
    config = SmtpConfig(
        host="smtp.sendgrid.net",
        port=587,
        username="apikey",
        password="secret-sendgrid-key",
        frontend_url="https://app.oriontrading.io",
    )
    adapter = SMTPEmailAdapter(config=config)

    mock_server = MagicMock()
    mock_server.__enter__.return_value = mock_server

    with patch("smtplib.SMTP", return_value=mock_server):
        sent = await adapter.send_password_reset_email(
            to_email="alice@institutional.com",
            reset_token="reset_token_xyz_987",
            username="alice",
        )

        assert sent is True
        mock_server.send_message.assert_called_once()
        msg = mock_server.send_message.call_args[0][0]
        assert msg["Subject"] == "Project ORION — Password Reset Request"

        expected_url = "https://app.oriontrading.io/reset-password?token=reset_token_xyz_987"
        text_body = msg.get_body(preferencelist=("plain",)).get_content()
        html_body = msg.get_body(preferencelist=("html",)).get_content()
        assert expected_url in text_body
        assert expected_url in html_body
        assert "15 minutes" in text_body
        assert "15 minutes" in html_body


@pytest.mark.asyncio
async def test_smtp_implicit_ssl_port_465() -> None:
    """SMTPEmailAdapter uses SMTP_SSL when port 465 is specified."""
    config = SmtpConfig(
        host="smtp.fastmail.com",
        port=465,
        username="user@fastmail.com",
        password="app-password",
    )
    adapter = SMTPEmailAdapter(config=config)

    mock_ssl_server = MagicMock()
    mock_ssl_server.__enter__.return_value = mock_ssl_server

    with patch("smtplib.SMTP_SSL", return_value=mock_ssl_server) as mock_ssl_cls:
        sent = await adapter.send_verification_email(
            to_email="test@fastmail.com",
            verification_token="tok123",
            username="fastuser",
        )
        assert sent is True
        mock_ssl_cls.assert_called_once()
        # STARTTLS should not be called when already on SSL port 465
        mock_ssl_server.starttls.assert_not_called()


@pytest.mark.asyncio
async def test_smtp_unauthenticated_connection() -> None:
    """When username and password are not supplied, server.login is bypassed."""
    config = SmtpConfig(host="localhost", port=25, use_tls=False)
    adapter = SMTPEmailAdapter(config=config)

    mock_server = MagicMock()
    mock_server.__enter__.return_value = mock_server

    with patch("smtplib.SMTP", return_value=mock_server):
        sent = await adapter.send_verification_email(
            to_email="local@dev.internal",
            verification_token="tok",
            username="localuser",
        )
        assert sent is True
        mock_server.login.assert_not_called()
        mock_server.starttls.assert_not_called()


@pytest.mark.asyncio
async def test_smtp_connection_timeout_returns_false() -> None:
    """Connection timeout is caught gracefully and returns False without crashing."""
    config = SmtpConfig(host="unreachable.smtp.host", timeout_seconds=1.0)
    adapter = SMTPEmailAdapter(config=config)

    with patch("smtplib.SMTP", side_effect=TimeoutError("Timed out")):
        sent = await adapter.send_verification_email(
            to_email="trader@hedgefund.com",
            verification_token="tok",
            username="trader",
        )
        assert sent is False


@pytest.mark.asyncio
async def test_smtp_authentication_failure_returns_false() -> None:
    """Authentication error is caught gracefully and returns False."""
    config = SmtpConfig(
        host="smtp.example.com",
        username="user",
        password="bad_password",
    )
    adapter = SMTPEmailAdapter(config=config)

    mock_server = MagicMock()
    mock_server.__enter__.return_value = mock_server
    mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Invalid credentials")

    with patch("smtplib.SMTP", return_value=mock_server):
        sent = await adapter.send_password_reset_email(
            to_email="alice@example.com",
            reset_token="tok",
            username="alice",
        )
        assert sent is False


# ─── 4. Factory Resolution ────────────────────────────────────────────────────


def test_create_email_service_selection() -> None:
    """create_email_service selects the correct adapter based on backend parameter or environment."""
    assert isinstance(create_email_service("mock"), MockEmailAdapter)
    assert isinstance(create_email_service("console"), ConsoleEmailAdapter)

    smtp_svc = create_email_service(
        "smtp",
        smtp_config=SmtpConfig(host="smtp.sendgrid.net"),
    )
    assert isinstance(smtp_svc, SMTPEmailAdapter)
    assert smtp_svc.config.host == "smtp.sendgrid.net"


def test_create_email_service_smtp_missing_host_raises() -> None:
    """Selecting SMTP backend without a configured host raises EmailConfigurationError."""
    with pytest.raises(EmailConfigurationError, match="ORION_SMTP_HOST is required"):
        create_email_service("smtp", smtp_config=SmtpConfig(host=""))


def test_create_email_service_invalid_backend_raises() -> None:
    """Invalid backend identifier raises EmailConfigurationError."""
    with pytest.raises(EmailConfigurationError, match="Invalid ORION_EMAIL_BACKEND"):
        create_email_service("unsupported_backend")


def test_get_and_set_email_service() -> None:
    """Global accessors get_email_service and set_email_service operate cleanly."""
    reset_email_service()
    default_svc = get_email_service()
    assert isinstance(default_svc, MockEmailAdapter)

    custom_mock = MockEmailAdapter()
    set_email_service(custom_mock)
    assert get_email_service() is custom_mock

    reset_email_service()


# ─── 5. Anti-Enumeration & Route Hardening ────────────────────────────────────


def _make_mock_user(email: str = "alice@example.com") -> UserModel:
    user = MagicMock(spec=UserModel)
    user.id = "usr-test-123"
    user.username = "alice"
    user.email = email
    user.is_active = True
    user.status = "ACTIVE"
    user.email_verified = False
    return user


def _make_mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


def test_forgot_password_anti_enumeration_on_smtp_failure() -> None:
    """When the email service raises an error, forgot-password returns HTTP 200 with generic response."""
    user = _make_mock_user(email="alice@example.com")
    mock_session = _make_mock_session()

    user_res = MagicMock()
    user_res.scalar_one_or_none.return_value = user
    token_res = MagicMock()
    token_res.scalars.return_value.all.return_value = []
    mock_session.execute.side_effect = [user_res, token_res]

    paper_adapter = PaperExecutionAdapter(config=PaperExecutionConfig(broker_name="paper", is_paper=True))
    app = create_app(paper_adapter=paper_adapter)
    app.dependency_overrides[dependencies.get_db_session] = lambda: mock_session

    # Configure a failing email service
    failing_adapter = MagicMock(spec=EmailServicePort)
    failing_adapter.send_password_reset_email = AsyncMock(side_effect=RuntimeError("SMTP relay is offline"))
    set_email_service(failing_adapter)

    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "alice@example.com"},
    )

    # Must return 200 with generic anti-enumeration notice, NOT 500
    assert response.status_code == 200
    assert "instructions have been sent" in response.json()["message"]


def test_resend_verification_anti_enumeration_on_smtp_failure() -> None:
    """When the email service raises an error, resend-verification returns HTTP 200 with generic response."""
    user = _make_mock_user(email="unverified@example.com")
    mock_session = _make_mock_session()

    user_res = MagicMock()
    user_res.scalar_one_or_none.return_value = user
    token_res = MagicMock()
    token_res.scalars.return_value.all.return_value = []
    mock_session.execute.side_effect = [user_res, token_res]

    paper_adapter = PaperExecutionAdapter(config=PaperExecutionConfig(broker_name="paper", is_paper=True))
    app = create_app(paper_adapter=paper_adapter)
    app.dependency_overrides[dependencies.get_db_session] = lambda: mock_session

    # Configure a failing email service
    failing_adapter = MagicMock(spec=EmailServicePort)
    failing_adapter.send_verification_email = AsyncMock(side_effect=TimeoutError("SMTP connection timed out"))
    set_email_service(failing_adapter)

    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "unverified@example.com"},
    )

    # Must return 200 with generic anti-enumeration notice, NOT 500
    assert response.status_code == 200
    assert "new verification link has been sent" in response.json()["message"]


# ─── 6. Email Masking Helper ─────────────────────────────────────────────────


def test_mask_email_helper() -> None:
    """mask_email masks local part correctly across diverse lengths."""
    assert mask_email("alice@example.com") == "a***e@example.com"
    assert mask_email("a@example.com") == "a***@example.com"
    assert mask_email("ab@example.com") == "a***@example.com"
    assert mask_email("corporate@institutional.org") == "c***e@institutional.org"
    assert mask_email("invalid_string") == "***"
