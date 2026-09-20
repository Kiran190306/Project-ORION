"""Interfaces and protocols for the Notification Domain."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from libraries.domain.notification.models import (
    NotificationChannel,
    NotificationMessage,
    NotificationRequest,
)


@runtime_checkable
class NotificationSender(Protocol):
    """Protocol for concrete notification transport senders (Telegram, Email, Webhook)."""

    @property
    def channel(self) -> NotificationChannel:
        """The channel this sender handles."""
        ...

    async def send(self, request: NotificationRequest) -> NotificationMessage:
        """Dispatch a notification request to the destination transport."""
        ...

    async def health_check(self) -> bool:
        """Check if the sender transport is connected and functional."""
        ...


@runtime_checkable
class NotificationSink(Protocol):
    """Protocol for notification storage, event streaming, or auditing."""

    async def record(self, message: NotificationMessage) -> None:
        """Record a sent or failed notification message."""
        ...

    async def get_recent(self, limit: int = 100) -> list[NotificationMessage]:
        """Retrieve recent notification records."""
        ...


class BaseNotificationSender(ABC):
    """Abstract base class for notification senders."""

    def __init__(self, channel: NotificationChannel) -> None:
        self._channel = channel

    @property
    def channel(self) -> NotificationChannel:
        return self._channel

    @abstractmethod
    async def send(self, request: NotificationRequest) -> NotificationMessage:
        """Dispatch notification."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Perform health check."""
        ...
