"""Infrastructure-neutral email service abstraction for transactional notifications."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

logger = logging.getLogger("trading_engine.communication.email")


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
        logger.info(
            "[DEV EMAIL] Password reset requested for '%s' (%s). Token: %s",
            username,
            to_email,
            reset_token[:8] + "***",
        )
        return True

    async def send_verification_email(
        self,
        to_email: str,
        verification_token: str,
        username: str,
    ) -> bool:
        """Log verification link for local development."""
        logger.info(
            "[DEV EMAIL] Email verification sent to '%s' (%s). Token: %s",
            username,
            to_email,
            verification_token[:8] + "***",
        )
        return True


# Global default email service instance (Mock by default for safety)
_default_email_service: EmailServicePort = MockEmailAdapter()


def get_email_service() -> EmailServicePort:
    """Return the currently configured transactional email service."""
    return _default_email_service


def set_email_service(service: EmailServicePort) -> None:
    """Override the transactional email service (e.g. for testing)."""
    global _default_email_service
    _default_email_service = service
