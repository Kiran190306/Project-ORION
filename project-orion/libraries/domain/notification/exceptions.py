"""Domain exceptions for the Notification Domain."""

from __future__ import annotations


class NotificationError(Exception):
    """Base exception for all notification domain errors."""

    def __init__(self, message: str, **kwargs: object) -> None:
        self.details = kwargs
        super().__init__(message)


class NotificationConfigurationError(NotificationError):
    """Raised when notification service or channel configuration is invalid."""


class NotificationDeliveryError(NotificationError):
    """Raised when a notification fails to be delivered to the target channel."""


class NotificationValidationError(NotificationError):
    """Raised when a notification request or message fails validation."""
