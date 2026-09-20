"""Notification Domain Service for routing, filtering, and dispatching notifications."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

from libraries.domain.notification.interfaces import (
    NotificationSender,
    NotificationSink,
)
from libraries.domain.notification.models import (
    NotificationChannel,
    NotificationMessage,
    NotificationRequest,
    NotificationSeverity,
    NotificationStatus,
)

_SEVERITY_ORDER: dict[NotificationSeverity, int] = {
    NotificationSeverity.INFO: 10,
    NotificationSeverity.SUCCESS: 20,
    NotificationSeverity.WARNING: 30,
    NotificationSeverity.ERROR: 40,
    NotificationSeverity.CRITICAL: 50,
}


@dataclass(frozen=True, slots=True)
class NotificationServiceConfig:
    """Configuration for the notification domain service."""

    enabled: bool = True
    min_severity: NotificationSeverity = NotificationSeverity.INFO
    allowed_channels: tuple[NotificationChannel, ...] = (
        NotificationChannel.TELEGRAM,
        NotificationChannel.EMAIL,
        NotificationChannel.WEBHOOK,
        NotificationChannel.SLACK,
        NotificationChannel.IN_APP,
    )
    suppress_duplicates: bool = True
    dedup_window_seconds: float = 60.0


class NotificationService:
    """Central domain service orchestrating notification dispatching, filtering, and audit sinks."""

    def __init__(
        self,
        config: NotificationServiceConfig | None = None,
        senders: Sequence[NotificationSender] | None = None,
        sinks: Sequence[NotificationSink] | None = None,
    ) -> None:
        self._config = config or NotificationServiceConfig()
        self._senders: dict[NotificationChannel, NotificationSender] = {}
        self._sinks: list[NotificationSink] = list(sinks or [])
        self._history: list[NotificationMessage] = []
        self._lock = asyncio.Lock()

        if senders:
            for sender in senders:
                self.register_sender(sender)

    @property
    def config(self) -> NotificationServiceConfig:
        return self._config

    def register_sender(self, sender: NotificationSender) -> None:
        """Register a transport sender for a specific notification channel."""
        self._senders[sender.channel] = sender

    def register_sink(self, sink: NotificationSink) -> None:
        """Register an audit or persistence sink."""
        self._sinks.append(sink)

    def get_sender(self, channel: NotificationChannel) -> NotificationSender | None:
        """Get the sender registered for a given channel."""
        return self._senders.get(channel)

    def is_severity_allowed(self, severity: NotificationSeverity) -> bool:
        """Check if severity meets minimum configured threshold."""
        min_level = _SEVERITY_ORDER.get(self._config.min_severity, 0)
        req_level = _SEVERITY_ORDER.get(severity, 0)
        return req_level >= min_level

    async def notify(self, request: NotificationRequest) -> NotificationMessage:
        """Process and send a notification request to its specified channel."""
        if not self._config.enabled:
            msg = NotificationMessage.from_request(
                request,
                status=NotificationStatus.REJECTED,
                error_message="Notification service is disabled",
            )
            await self._record_to_sinks(msg)
            return msg

        if not self.is_severity_allowed(request.severity):
            msg = NotificationMessage.from_request(
                request,
                status=NotificationStatus.REJECTED,
                error_message=f"Severity {request.severity} below minimum {self._config.min_severity}",
            )
            await self._record_to_sinks(msg)
            return msg

        if request.channel not in self._config.allowed_channels:
            msg = NotificationMessage.from_request(
                request,
                status=NotificationStatus.REJECTED,
                error_message=f"Channel {request.channel} is not in allowed channels",
            )
            await self._record_to_sinks(msg)
            return msg

        sender = self._senders.get(request.channel)
        if sender is None:
            msg = NotificationMessage.from_request(
                request,
                status=NotificationStatus.FAILED,
                error_message=f"No sender registered for channel {request.channel}",
            )
            await self._record_to_sinks(msg)
            return msg

        try:
            message = await sender.send(request)
        except Exception as exc:  # noqa: BLE001
            message = NotificationMessage.from_request(
                request,
                status=NotificationStatus.FAILED,
                delivered_at=datetime.now(timezone.utc),
                error_message=str(exc),
            )

        await self._record_to_sinks(message)
        return message

    async def broadcast(
        self,
        request: NotificationRequest,
        channels: Sequence[NotificationChannel] | None = None,
    ) -> list[NotificationMessage]:
        """Broadcast a notification across multiple channels simultaneously."""
        target_channels = channels or list(self._senders.keys())
        tasks = []
        for ch in target_channels:
            ch_request = NotificationRequest(
                channel=ch,
                severity=request.severity,
                notification_type=request.notification_type,
                title=request.title,
                body=request.body,
                recipient=request.recipient,
                metadata=dict(request.metadata),
                created_at=request.created_at,
            )
            tasks.append(self.notify(ch_request))

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=False)
        return list(results)

    async def _record_to_sinks(self, message: NotificationMessage) -> None:
        """Record message to internal history and registered external sinks."""
        async with self._lock:
            self._history.append(message)
            if len(self._history) > 1000:
                self._history.pop(0)

        for sink in self._sinks:
            with contextlib.suppress(Exception):
                await sink.record(message)

    async def get_history(self, limit: int = 100) -> list[NotificationMessage]:
        """Retrieve recent notification history."""
        async with self._lock:
            return list(self._history[-limit:])
