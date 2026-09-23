"""Infrastructure-neutral email service abstraction for transactional notifications."""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
import ssl
import urllib.parse
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Protocol, runtime_checkable

logger = logging.getLogger("trading_engine.communication.email")


class EmailConfigurationError(ValueError):
    """Raised when email or SMTP configuration is invalid or missing required values."""


def mask_email(email: str) -> str:
    """Mask email for privacy-safe storage and logging."""
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "***"
    else:
        masked_local = local[0] + "***" + local[-1]
    return f"{masked_local}@{domain}"


@dataclass(frozen=True)
class SmtpConfig:
    """Strongly-typed immutable configuration for SMTP transactional email transport."""

    host: str = ""
    port: int = 587
    username: str = ""
    password: str = ""
    use_tls: bool = True
    from_email: str = "notifications@oriontrading.io"
    from_name: str = "Project ORION"
    timeout_seconds: float = 10.0
    frontend_url: str = "https://orion-dashboard.onrender.com"

    def __repr__(self) -> str:
        masked_pwd = "***" if self.password else ""
        return (
            f"SmtpConfig(host={self.host!r}, port={self.port}, "
            f"username={self.username!r}, password={masked_pwd!r}, "
            f"use_tls={self.use_tls}, from_email={self.from_email!r}, "
            f"from_name={self.from_name!r}, timeout_seconds={self.timeout_seconds}, "
            f"frontend_url={self.frontend_url!r})"
        )

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> SmtpConfig:
        """Load and validate SMTP configuration from canonical ORION environment variables."""
        source = env if env is not None else os.environ

        host = source.get("ORION_SMTP_HOST", "").strip()

        port_raw = source.get("ORION_SMTP_PORT", "587").strip()
        try:
            port = int(port_raw)
        except ValueError as err:
            raise EmailConfigurationError(
                f"ORION_SMTP_PORT must be an integer, got {port_raw!r}"
            ) from err

        username = source.get("ORION_SMTP_USERNAME", "").strip()
        password = source.get("ORION_SMTP_PASSWORD", "").strip()

        use_tls_raw = source.get("ORION_SMTP_USE_TLS", "true").strip().lower()
        use_tls = use_tls_raw in ("true", "1", "yes")

        from_email = source.get(
            "ORION_SMTP_FROM_EMAIL", "notifications@oriontrading.io"
        ).strip()
        from_name = source.get("ORION_SMTP_FROM_NAME", "Project ORION").strip()

        timeout_raw = source.get("ORION_SMTP_TIMEOUT_SECONDS", "10.0").strip()
        try:
            timeout_seconds = float(timeout_raw)
        except ValueError as err:
            raise EmailConfigurationError(
                f"ORION_SMTP_TIMEOUT_SECONDS must be a number, got {timeout_raw!r}"
            ) from err

        frontend_url = (
            source.get("ORION_FRONTEND_URL", "https://orion-dashboard.onrender.com")
            .strip()
            .rstrip("/")
        )

        return cls(
            host=host,
            port=port,
            username=username,
            password=password,
            use_tls=use_tls,
            from_email=from_email,
            from_name=from_name,
            timeout_seconds=timeout_seconds,
            frontend_url=frontend_url,
        )


@dataclass(frozen=True)
class SentEmail:
    """Record of an email dispatched through an email adapter."""

    to_email: str
    subject: str
    token: str
    template: str
    sent_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@runtime_checkable
class EmailServicePort(Protocol):
    """Protocol defining the transactional email communication boundary."""

    async def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        username: str,
    ) -> bool:
        """Send a password reset instructions email with a secure token link."""
        ...

    async def send_verification_email(
        self,
        to_email: str,
        verification_token: str,
        username: str,
    ) -> bool:
        """Send an email verification link with a secure single-use token."""
        ...


class MockEmailAdapter:
    """Deterministic, in-memory email adapter for CI, local tests, and mock execution."""

    def __init__(self) -> None:
        self.sent_emails: list[SentEmail] = []

    async def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        username: str,
    ) -> bool:
        """Record dispatched password reset email in memory."""
        self.sent_emails.append(
            SentEmail(
                to_email=to_email,
                subject="Project ORION — Password Reset Request",
                token=reset_token,
                template="password_reset",
            )
        )
        return True

    async def send_verification_email(
        self,
        to_email: str,
        verification_token: str,
        username: str,
    ) -> bool:
        """Record dispatched email verification in memory."""
        self.sent_emails.append(
            SentEmail(
                to_email=to_email,
                subject="Project ORION — Verify Your Email Address",
                token=verification_token,
                template="email_verification",
            )
        )
        return True

    def clear(self) -> None:
        """Clear all in-memory sent emails."""
        self.sent_emails.clear()

    def get_last_email(self) -> SentEmail | None:
        """Retrieve the most recently dispatched email."""
        return self.sent_emails[-1] if self.sent_emails else None

    def get_emails_for(self, email: str) -> list[SentEmail]:
        """Retrieve all emails dispatched to a specific recipient."""
        return [e for e in self.sent_emails if e.to_email.lower() == email.lower()]


class ConsoleEmailAdapter:
    """Development email adapter printing formatted reset/verification links to stdout."""

    async def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        username: str,
    ) -> bool:
        """Log password reset link for local development."""
        masked_email = mask_email(to_email)
        masked_token = reset_token[:8] + "***" if len(reset_token) >= 8 else "***"
        logger.info(
            "[DEV EMAIL] Password reset requested for '%s' (%s). Token: %s",
            username,
            masked_email,
            masked_token,
        )
        return True

    async def send_verification_email(
        self,
        to_email: str,
        verification_token: str,
        username: str,
    ) -> bool:
        """Log verification link for local development."""
        masked_email = mask_email(to_email)
        masked_token = (
            verification_token[:8] + "***" if len(verification_token) >= 8 else "***"
        )
        logger.info(
            "[DEV EMAIL] Email verification sent to '%s' (%s). Token: %s",
            username,
            masked_email,
            masked_token,
        )
        return True


class SMTPEmailAdapter:
    """Production transactional email adapter using standard-library smtplib offloaded to thread."""

    def __init__(self, config: SmtpConfig) -> None:
        self._config = config

    @property
    def config(self) -> SmtpConfig:
        """Retrieve the active configuration."""
        return self._config

    async def send_verification_email(
        self,
        to_email: str,
        verification_token: str,
        username: str,
    ) -> bool:
        """Send an email verification link with a secure single-use token via SMTP."""
        msg = self._build_verification_message(to_email, verification_token, username)
        return await asyncio.to_thread(self._send_sync, msg)

    async def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        username: str,
    ) -> bool:
        """Send a password reset instructions email with a secure token link via SMTP."""
        msg = self._build_password_reset_message(to_email, reset_token, username)
        return await asyncio.to_thread(self._send_sync, msg)

    def _build_verification_message(
        self,
        to_email: str,
        verification_token: str,
        username: str,
    ) -> EmailMessage:
        quoted_token = urllib.parse.quote(verification_token)
        verify_url = f"{self._config.frontend_url}/verify-email?token={quoted_token}"
        subject = "Project ORION — Verify Your Email Address"

        text_content = (
            f"Hello {username},\n\n"
            f"Thank you for creating an account with Project ORION.\n"
            f"Please verify your email address by opening the following link in your browser:\n\n"
            f"{verify_url}\n\n"
            f"Security Notice:\n"
            f"This verification link is single-use and will expire in 24 hours.\n"
            f"If you did not create an account on Project ORION, please disregard this email.\n\n"
            f"Institutional Trading Disclaimer:\n"
            f"Project ORION operates strictly in simulated paper execution mode ($0.00 capital at risk).\n"
            f"All market transactions and balances are virtual simulations.\n"
        )

        html_content = (
            f"<!DOCTYPE html><html><body style=\"font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f17; color: #e2e8f0; margin: 0; padding: 24px;\">"
            f"<div style=\"max-width: 560px; margin: 0 auto; background-color: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 32px;\">"
            f"<div style=\"margin-bottom: 24px;\">"
            f"<h1 style=\"color: #f8fafc; font-size: 20px; font-weight: 700; margin: 0 0 8px;\">Project ORION</h1>"
            f"<span style=\"display: inline-block; background-color: rgba(245, 158, 11, 0.1); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px;\">SIMULATED PAPER EXECUTION — $0.00 REAL CAPITAL</span>"
            f"</div>"
            f"<p style=\"color: #cbd5e1; font-size: 14px; line-height: 1.6; margin: 0 0 16px;\">Hello <strong>{username}</strong>,</p>"
            f"<p style=\"color: #cbd5e1; font-size: 14px; line-height: 1.6; margin: 0 0 24px;\">Thank you for registering an institutional organization on Project ORION. Please verify your email address to confirm your account.</p>"
            f"<div style=\"margin: 0 0 24px;\">"
            f"<a href=\"{verify_url}\" style=\"display: inline-block; background-color: #0284c7; color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 600; padding: 12px 24px; border-radius: 6px;\">Verify Email Address</a>"
            f"</div>"
            f"<p style=\"color: #94a3b8; font-size: 12px; line-height: 1.5; margin: 0 0 16px;\">If the button above does not work, copy and paste this URL into your browser:<br/><a href=\"{verify_url}\" style=\"color: #38bdf8; word-break: break-all;\">{verify_url}</a></p>"
            f"<hr style=\"border: none; border-top: 1px solid #1f2937; margin: 24px 0;\" />"
            f"<p style=\"color: #64748b; font-size: 11px; line-height: 1.4; margin: 0;\">This single-use link expires in 24 hours. If you did not create this account, you can safely ignore this email.<br/><br/>Project ORION is a quantitative research and simulated paper trading platform. $0.00 capital is at risk.</p>"
            f"</div></body></html>"
        )

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = (
            f"{self._config.from_name} <{self._config.from_email}>"
            if self._config.from_name
            else self._config.from_email
        )
        msg["To"] = to_email
        msg.set_content(text_content)
        msg.add_alternative(html_content, subtype="html")
        return msg

    def _build_password_reset_message(
        self,
        to_email: str,
        reset_token: str,
        username: str,
    ) -> EmailMessage:
        quoted_token = urllib.parse.quote(reset_token)
        reset_url = f"{self._config.frontend_url}/reset-password?token={quoted_token}"
        subject = "Project ORION — Password Reset Request"

        text_content = (
            f"Hello {username},\n\n"
            f"We received a request to reset the password for your Project ORION account.\n"
            f"You can choose a new password by opening the following link in your browser:\n\n"
            f"{reset_url}\n\n"
            f"Security Notice:\n"
            f"This password reset link is single-use and will expire in 15 minutes.\n"
            f"If you did not request a password reset, please ignore this email. Your password will remain unchanged.\n\n"
            f"Institutional Trading Disclaimer:\n"
            f"Project ORION operates strictly in simulated paper execution mode ($0.00 capital at risk).\n"
            f"All market transactions and balances are virtual simulations.\n"
        )

        html_content = (
            f"<!DOCTYPE html><html><body style=\"font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f17; color: #e2e8f0; margin: 0; padding: 24px;\">"
            f"<div style=\"max-width: 560px; margin: 0 auto; background-color: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 32px;\">"
            f"<div style=\"margin-bottom: 24px;\">"
            f"<h1 style=\"color: #f8fafc; font-size: 20px; font-weight: 700; margin: 0 0 8px;\">Project ORION</h1>"
            f"<span style=\"display: inline-block; background-color: rgba(245, 158, 11, 0.1); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px;\">SIMULATED PAPER EXECUTION — $0.00 REAL CAPITAL</span>"
            f"</div>"
            f"<p style=\"color: #cbd5e1; font-size: 14px; line-height: 1.6; margin: 0 0 16px;\">Hello <strong>{username}</strong>,</p>"
            f"<p style=\"color: #cbd5e1; font-size: 14px; line-height: 1.6; margin: 0 0 24px;\">A password reset was requested for your Project ORION user account. Click the button below to choose a new password.</p>"
            f"<div style=\"margin: 0 0 24px;\">"
            f"<a href=\"{reset_url}\" style=\"display: inline-block; background-color: #0284c7; color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 600; padding: 12px 24px; border-radius: 6px;\">Reset Password</a>"
            f"</div>"
            f"<p style=\"color: #94a3b8; font-size: 12px; line-height: 1.5; margin: 0 0 16px;\">If the button above does not work, copy and paste this URL into your browser:<br/><a href=\"{reset_url}\" style=\"color: #38bdf8; word-break: break-all;\">{reset_url}</a></p>"
            f"<hr style=\"border: none; border-top: 1px solid #1f2937; margin: 24px 0;\" />"
            f"<p style=\"color: #64748b; font-size: 11px; line-height: 1.4; margin: 0;\">This single-use link expires in 15 minutes. If you did not request this change, you can safely ignore this email; your credentials remain secure.<br/><br/>Project ORION is a quantitative research and simulated paper trading platform. $0.00 capital is at risk.</p>"
            f"</div></body></html>"
        )

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = (
            f"{self._config.from_name} <{self._config.from_email}>"
            if self._config.from_name
            else self._config.from_email
        )
        msg["To"] = to_email
        msg.set_content(text_content)
        msg.add_alternative(html_content, subtype="html")
        return msg

    def _send_sync(self, msg: EmailMessage) -> bool:
        """Synchronous SMTP transport executed in a worker thread."""
        masked_to = mask_email(str(msg.get("To", "")))
        try:
            if self._config.port == 465:
                context = ssl.create_default_context()
                server: smtplib.SMTP = smtplib.SMTP_SSL(
                    host=self._config.host,
                    port=self._config.port,
                    timeout=self._config.timeout_seconds,
                    context=context,
                )
            else:
                server = smtplib.SMTP(
                    host=self._config.host,
                    port=self._config.port,
                    timeout=self._config.timeout_seconds,
                )

            with server:
                server.ehlo()
                if self._config.use_tls and self._config.port != 465:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()

                if self._config.username and self._config.password:
                    server.login(self._config.username, self._config.password)

                server.send_message(msg)
                logger.info(
                    "Transactional email successfully dispatched to %s via SMTP (subject: %s)",
                    masked_to,
                    msg.get("Subject", ""),
                )
                return True

        except smtplib.SMTPAuthenticationError as auth_err:
            logger.error(
                "SMTP authentication failed for host %s:%s (user: %s): %s",
                self._config.host,
                self._config.port,
                self._config.username,
                getattr(auth_err, "smtp_error", str(auth_err)),
            )
            return False
        except (smtplib.SMTPConnectError, TimeoutError) as timeout_err:
            logger.error(
                "SMTP connection timeout or error connecting to %s:%s: %s",
                self._config.host,
                self._config.port,
                timeout_err,
            )
            return False
        except smtplib.SMTPException as smtp_err:
            logger.error(
                "SMTP protocol error while sending to %s: %s",
                masked_to,
                smtp_err,
            )
            return False
        except OSError as os_err:
            logger.error(
                "Socket or network OS error during SMTP send to %s: %s",
                masked_to,
                os_err,
            )
            return False
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Unexpected error during SMTP send to %s: %s",
                masked_to,
                exc.__class__.__name__,
            )
            return False


def create_email_service(
    backend: str | None = None,
    smtp_config: SmtpConfig | None = None,
) -> EmailServicePort:
    """Create an EmailServicePort implementation based on configured backend.

    Supported backends:
      - 'mock': deterministic in-memory adapter (CI / testing default)
      - 'console': logs formatted emails to standard output / logger
      - 'smtp': production SMTPEmailAdapter offloaded to worker threads
    """
    raw_backend = (
        backend
        if backend is not None
        else os.environ.get("ORION_EMAIL_BACKEND", "mock")
    ).strip().lower()

    if raw_backend == "mock":
        return MockEmailAdapter()
    elif raw_backend == "console":
        return ConsoleEmailAdapter()
    elif raw_backend == "smtp":
        config = smtp_config if smtp_config is not None else SmtpConfig.from_env()
        if not config.host:
            raise EmailConfigurationError(
                "ORION_SMTP_HOST is required when ORION_EMAIL_BACKEND is set to 'smtp'."
            )
        return SMTPEmailAdapter(config=config)
    else:
        raise EmailConfigurationError(
            f"Invalid ORION_EMAIL_BACKEND '{raw_backend}'. "
            "Supported backends are: 'mock', 'console', 'smtp'."
        )


# Global default email service instance (lazily resolved via create_email_service)
_default_email_service: EmailServicePort | None = None


def get_email_service() -> EmailServicePort:
    """Return the currently configured transactional email service.

    Lazily resolves the adapter via create_email_service() if not previously set.
    """
    global _default_email_service
    if _default_email_service is None:
        _default_email_service = create_email_service()
    return _default_email_service


def set_email_service(service: EmailServicePort | None) -> None:
    """Override the transactional email service (e.g. for testing)."""
    global _default_email_service
    _default_email_service = service


def reset_email_service() -> None:
    """Reset the global email service instance to None."""
    global _default_email_service
    _default_email_service = None
