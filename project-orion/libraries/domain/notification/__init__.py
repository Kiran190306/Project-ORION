"""Notification Domain — broker-agnostic notification abstraction.

This domain provides the canonical notification interfaces and models
used throughout Project ORION.  It is deliberately free of any
HTTP/network I/O — concrete notification senders (e.g. Telegram) live
in the infrastructure layer.
"""

from libraries.domain.notification.exceptions import (
    NotificationConfigurationError,
    NotificationDeliveryError,
    NotificationError,
    NotificationValidationError,
)
from libraries.domain.notification.interfaces import (
    NotificationSender,
    NotificationSink,
)
from libraries.domain.notification.models import (
    NotificationChannel,
    NotificationMessage,
    NotificationRequest,
    NotificationSeverity,
    NotificationType,
)
from libraries.domain.notification.service import (
    NotificationService,
    NotificationServiceConfig,
)

__all__ = [
    "NotificationChannel",
    "NotificationConfigurationError",
    "NotificationDeliveryError",
    "NotificationError",
    "NotificationMessage",
    "NotificationRequest",
    "NotificationSender",
    "NotificationService",
    "NotificationServiceConfig",
    "NotificationSeverity",
    "NotificationSink",
    "NotificationType",
    "NotificationValidationError",
]

__version__ = "0.1.0"