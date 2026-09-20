"""Comprehensive unit tests for the Notification Domain."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.notification import (
    NotificationChannel,
    NotificationDeliveryError,
    NotificationMessage,
    NotificationRequest,
    NotificationService,
    NotificationServiceConfig,
    NotificationSeverity,
    NotificationSink,
    NotificationType,
)
from libraries.domain.notification.interfaces import BaseNotificationSender
from libraries.domain.notification.models import NotificationStatus


class MockSender(BaseNotificationSender):
    """Mock notification sender for testing."""

    def __init__(
        self,
        channel: NotificationChannel,
        should_fail: bool = False,
        healthy: bool = True,
    ) -> None:
        super().__init__(channel)
        self.should_fail = should_fail
        self.healthy = healthy
        self.sent_requests: list[NotificationRequest] = []

    async def send(self, request: NotificationRequest) -> NotificationMessage:
        self.sent_requests.append(request)
        if self.should_fail:
            raise NotificationDeliveryError(f"Delivery to {self.channel} failed")
        return NotificationMessage.from_request(
            request,
            status=NotificationStatus.DELIVERED,
            delivered_at=datetime.now(timezone.utc),
        )

    async def health_check(self) -> bool:
        return self.healthy


class MockSink(NotificationSink):
    """Mock notification audit sink for testing."""

    def __init__(self) -> None:
        self.recorded_messages: list[NotificationMessage] = []

    async def record(self, message: NotificationMessage) -> None:
        self.recorded_messages.append(message)

    async def get_recent(self, limit: int = 100) -> list[NotificationMessage]:
        return self.recorded_messages[-limit:]


# ─── Tests for Models & Enums ────────────────────────────────────────────────


def test_notification_enums() -> None:
    """Test string representations and enum memberships."""
    assert NotificationChannel.TELEGRAM == "telegram"
    assert NotificationChannel.EMAIL == "email"
    assert NotificationSeverity.CRITICAL == "critical"
    assert NotificationType.RISK_BREACH == "risk_breach"
    assert NotificationStatus.DELIVERED == "delivered"


def test_notification_request_creation() -> None:
    """Test valid NotificationRequest creation and immutability."""
    req = NotificationRequest(
        channel=NotificationChannel.TELEGRAM,
        severity=NotificationSeverity.WARNING,
        notification_type=NotificationType.MARGIN_CALL,
        title="Margin Call Alert",
        body="Account margin level dropped below 50%",
        recipient="user_123",
        metadata={"account_id": "acc_99", "margin_level": 48.5},
    )
    assert req.channel == NotificationChannel.TELEGRAM
    assert req.severity == NotificationSeverity.WARNING
    assert req.notification_type == NotificationType.MARGIN_CALL
    assert req.title == "Margin Call Alert"
    assert req.recipient == "user_123"
    assert req.metadata["account_id"] == "acc_99"


def test_notification_request_validation() -> None:
    """Test that empty title or body raises ValueError."""
    with pytest.raises(ValueError, match="title cannot be empty"):
        NotificationRequest(
            channel=NotificationChannel.EMAIL,
            severity=NotificationSeverity.INFO,
            notification_type=NotificationType.HEARTBEAT,
            title="   ",
            body="System is alive",
        )

    with pytest.raises(ValueError, match="body cannot be empty"):
        NotificationRequest(
            channel=NotificationChannel.EMAIL,
            severity=NotificationSeverity.INFO,
            notification_type=NotificationType.HEARTBEAT,
            title="Heartbeat",
            body="",
        )


def test_notification_message_from_request() -> None:
    """Test factory creation of NotificationMessage from request."""
    req = NotificationRequest(
        channel=NotificationChannel.SLACK,
        severity=NotificationSeverity.INFO,
        notification_type=NotificationType.TRADE_OPENED,
        title="Trade Opened",
        body="EUR/USD BUY 1.00 lot @ 1.0850",
    )
    msg = NotificationMessage.from_request(
        req,
        status=NotificationStatus.DELIVERED,
        delivered_at=datetime.now(timezone.utc),
    )
    assert msg.message_id.startswith("msg_")
    assert msg.status == NotificationStatus.DELIVERED
    assert msg.channel == NotificationChannel.SLACK
    assert msg.delivered_at is not None
    assert msg.error_message is None


# ─── Tests for Notification Service ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_notification_service_successful_delivery() -> None:
    """Test successful routing and dispatching of notification."""
    telegram_sender = MockSender(NotificationChannel.TELEGRAM)
    sink = MockSink()
    service = NotificationService(senders=[telegram_sender], sinks=[sink])

    req = NotificationRequest(
        channel=NotificationChannel.TELEGRAM,
        severity=NotificationSeverity.INFO,
        notification_type=NotificationType.TRADE_OPENED,
        title="Order Executed",
        body="Order #1001 filled at 1.2050",
    )
    msg = await service.notify(req)

    assert msg.status == NotificationStatus.DELIVERED
    assert len(telegram_sender.sent_requests) == 1
    assert len(sink.recorded_messages) == 1
    assert sink.recorded_messages[0].title == "Order Executed"

    history = await service.get_history()
    assert len(history) == 1


@pytest.mark.asyncio
async def test_notification_service_no_sender_registered() -> None:
    """Test handling when target channel has no sender registered."""
    sink = MockSink()
    service = NotificationService(sinks=[sink])

    req = NotificationRequest(
        channel=NotificationChannel.EMAIL,
        severity=NotificationSeverity.ERROR,
        notification_type=NotificationType.SYSTEM_ALERT,
        title="Database Lag",
        body="Database latency spike detected",
    )
    msg = await service.notify(req)

    assert msg.status == NotificationStatus.FAILED
    assert "No sender registered" in (msg.error_message or "")
    assert len(sink.recorded_messages) == 1


@pytest.mark.asyncio
async def test_notification_service_sender_failure() -> None:
    """Test graceful handling when sender raises an exception."""
    failing_sender = MockSender(NotificationChannel.TELEGRAM, should_fail=True)
    service = NotificationService(senders=[failing_sender])

    req = NotificationRequest(
        channel=NotificationChannel.TELEGRAM,
        severity=NotificationSeverity.CRITICAL,
        notification_type=NotificationType.RISK_BREACH,
        title="Risk Breach",
        body="Daily drawdown limit exceeded",
    )
    msg = await service.notify(req)

    assert msg.status == NotificationStatus.FAILED
    assert "Delivery to telegram failed" in (msg.error_message or "")


@pytest.mark.asyncio
async def test_notification_service_severity_filtering() -> None:
    """Test filtering of notifications below minimum severity."""
    sender = MockSender(NotificationChannel.TELEGRAM)
    config = NotificationServiceConfig(min_severity=NotificationSeverity.WARNING)
    service = NotificationService(config=config, senders=[sender])

    # INFO should be rejected
    req_info = NotificationRequest(
        channel=NotificationChannel.TELEGRAM,
        severity=NotificationSeverity.INFO,
        notification_type=NotificationType.HEARTBEAT,
        title="Heartbeat",
        body="System running normally",
    )
    msg_info = await service.notify(req_info)
    assert msg_info.status == NotificationStatus.REJECTED
    assert len(sender.sent_requests) == 0

    # WARNING should pass
    req_warn = NotificationRequest(
        channel=NotificationChannel.TELEGRAM,
        severity=NotificationSeverity.WARNING,
        notification_type=NotificationType.MARGIN_CALL,
        title="Margin Warning",
        body="Margin level at 70%",
    )
    msg_warn = await service.notify(req_warn)
    assert msg_warn.status == NotificationStatus.DELIVERED
    assert len(sender.sent_requests) == 1


@pytest.mark.asyncio
async def test_notification_service_disabled() -> None:
    """Test that all notifications are rejected when service is disabled."""
    sender = MockSender(NotificationChannel.TELEGRAM)
    config = NotificationServiceConfig(enabled=False)
    service = NotificationService(config=config, senders=[sender])

    req = NotificationRequest(
        channel=NotificationChannel.TELEGRAM,
        severity=NotificationSeverity.CRITICAL,
        notification_type=NotificationType.SYSTEM_ALERT,
        title="System Down",
        body="Emergency shutdown",
    )
    msg = await service.notify(req)
    assert msg.status == NotificationStatus.REJECTED
    assert len(sender.sent_requests) == 0


@pytest.mark.asyncio
async def test_notification_service_broadcast() -> None:
    """Test broadcasting to multiple channels."""
    tg_sender = MockSender(NotificationChannel.TELEGRAM)
    email_sender = MockSender(NotificationChannel.EMAIL)
    service = NotificationService(senders=[tg_sender, email_sender])

    req = NotificationRequest(
        channel=NotificationChannel.TELEGRAM,  # Default channel in request template
        severity=NotificationSeverity.CRITICAL,
        notification_type=NotificationType.RISK_BREACH,
        title="Emergency Risk Halt",
        body="All trading halted due to maximum loss limit",
    )
    results = await service.broadcast(
        req, channels=[NotificationChannel.TELEGRAM, NotificationChannel.EMAIL]
    )

    assert len(results) == 2
    assert all(r.status == NotificationStatus.DELIVERED for r in results)
    assert len(tg_sender.sent_requests) == 1
    assert len(email_sender.sent_requests) == 1


@pytest.mark.asyncio
async def test_sender_health_check() -> None:
    """Test sender protocol health check method."""
    healthy_sender = MockSender(NotificationChannel.TELEGRAM, healthy=True)
    unhealthy_sender = MockSender(NotificationChannel.EMAIL, healthy=False)

    assert await healthy_sender.health_check() is True
    assert await unhealthy_sender.health_check() is False
