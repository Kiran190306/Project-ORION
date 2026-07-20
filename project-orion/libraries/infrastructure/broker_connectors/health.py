"""Health monitoring for broker connectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class ConnectorHealth:
    """Connector health snapshot."""

    connector_name: str
    running: bool
    transport_connected: bool
    last_error: str | None
    last_tick_timestamp: str | None
    reconnect_attempts: int
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "connector_name": self.connector_name,
            "running": self.running,
            "transport_connected": self.transport_connected,
            "last_error": self.last_error,
            "last_tick_timestamp": self.last_tick_timestamp,
            "reconnect_attempts": self.reconnect_attempts,
            "checked_at": self.checked_at,
        }
