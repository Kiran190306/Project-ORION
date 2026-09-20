"""Domain models and value objects for the Notification Domain."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class NotificationChannel(StrEnum):
    """Supported notification delivery channels."""

    TELEGRAM = "telegram"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    SLACK = "slack"
    IN_APP = "in_app"


class NotificationSeverity(StrEnum):
    """Severity levels for notification routing and filtering."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationType(StrEnum):
    """Domain event types triggering notifications."""

    TRADE_OPENED = "trade_opened"
    TRADE_CLOSED = "trade_closed"
    ORDER_FILLED = "order_filled"
    ORDER_REJECTED = "order_rejected"
    ORDER_CANCELLED = "order_cancelled"
    RISK_BREACH = "risk_breach"
    MARGIN_CALL = "margin_call"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    SYSTEM_ALERT = "system_alert"
    HEARTBEAT = "heartbeat"


class NotificationStatus(StrEnum):
    """Lifecycle delivery status of a notification message."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class NotificationRequest:
    """Request payload to initiate a notification dispatch."""

    channel: NotificationChannel
    severity: NotificationSeverity
    notification_type: NotificationType
    title: str
    body: str
    recipient: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Notification title cannot be empty")
        if not self.body.strip():
            raise ValueError("Notification body cannot be empty")


@dataclass(frozen=True, slots=True)
class NotificationMessage:
    """Delivered or attempted notification message record."""

    message_id: str
    channel: NotificationChannel
    severity: NotificationSeverity
    notification_type: NotificationType
    title: str
    body: str
    status: NotificationStatus
    recipient: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_at: datetime | None = None
    error_message: str | None = None

    @classmethod
    def from_request(
        cls,
        request: NotificationRequest,
        status: NotificationStatus = NotificationStatus.PENDING,
        delivered_at: datetime | None = None,
        error_message: str | None = None,
        message_id: str | None = None,
    ) -> NotificationMessage:
        """Create a NotificationMessage from a NotificationRequest."""
        return cls(
            message_id=message_id or f"msg_{uuid.uuid4().hex[:12]}",
            channel=request.channel,
            severity=request.severity,
            notification_type=request.notification_type,
            title=request.title,
            body=request.body,
            status=status,
            recipient=request.recipient,
            metadata=dict(request.metadata),
            created_at=request.created_at,
            delivered_at=delivered_at,
            error_message=error_message,
        )
