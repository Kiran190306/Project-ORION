"""
Project ORION - Identifiers

Standardized identifier generation and validation for domain entities.
All identifiers follow UUID v4 format for distributed generation.

Provides:
- Entity-specific ID generation
- ID validation
- Type-safe ID wrappers
- Prefix-based identification
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class EntityId:
    """Base identifier for domain entities."""

    value: str
    prefix: str = ""

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("ID value cannot be empty")

    def __str__(self) -> str:
        if self.prefix:
            return f"{self.prefix}_{self.value}"
        return self.value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self}')"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, EntityId):
            return self.value == other.value and self.prefix == other.prefix
        if isinstance(other, str):
            return str(self) == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.prefix, self.value))

    @classmethod
    def generate(cls, prefix: str = "id") -> EntityId:
        """Generate a new unique identifier."""
        return cls(value=uuid.uuid4().hex, prefix=prefix)

    def to_dict(self) -> dict[str, str]:
        return {"id": str(self), "value": self.value, "prefix": self.prefix}


# ─── Specific Entity IDs ──────────────────────────────────────


class UserId(EntityId):
    """User entity identifier."""

    def __init__(self, value: str) -> None:
        super().__init__(value=value, prefix="usr")


class AccountId(EntityId):
    """Account entity identifier."""

    def __init__(self, value: str) -> None:
        super().__init__(value=value, prefix="acc")


class InstrumentId(EntityId):
    """Instrument entity identifier."""

    def __init__(self, value: str) -> None:
        super().__init__(value=value, prefix="ins")


class OrderId(EntityId):
    """Order entity identifier."""

    def __init__(self, value: str) -> None:
        super().__init__(value=value, prefix="ord")


class PositionId(EntityId):
    """Position entity identifier."""

    def __init__(self, value: str) -> None:
        super().__init__(value=value, prefix="pos")


class TradeId(EntityId):
    """Trade entity identifier."""

    def __init__(self, value: str) -> None:
        super().__init__(value=value, prefix="trd")


class SignalId(EntityId):
    """Signal entity identifier."""

    def __init__(self, value: str) -> None:
        super().__init__(value=value, prefix="sig")


class StrategyId(EntityId):
    """Strategy entity identifier."""

    def __init__(self, value: str) -> None:
        super().__init__(value=value, prefix="str")


class BacktestId(EntityId):
    """Backtest entity identifier."""

    def __init__(self, value: str) -> None:
        super().__init__(value=value, prefix="bkt")


class SessionId(EntityId):
    """Session entity identifier."""

    def __init__(self, value: str) -> None:
        super().__init__(value=value, prefix="sess")


class ApiKeyId(EntityId):
    """API key identifier."""

    def __init__(self, value: str) -> None:
        super().__init__(value=value, prefix="api")


class AlertId(EntityId):
    """Alert entity identifier."""

    def __init__(self, value: str) -> None:
        super().__init__(value=value, prefix="alt")


class LicenseId(EntityId):
    """License entity identifier."""

    def __init__(self, value: str) -> None:
        super().__init__(value=value, prefix="lic")


class AuditLogId(EntityId):
    """Audit log entry identifier."""

    def __init__(self, value: str) -> None:
        super().__init__(value=value, prefix="aud")


# ─── ID Generation Utility ─────────────────────────────────────


def generate_id(prefix: str = "id") -> str:
    """Generate a unique ID string with optional prefix."""
    return f"{prefix}_{uuid.uuid4().hex}"


def generate_uuid() -> str:
    """Generate a raw UUID hex string."""
    return uuid.uuid4().hex


def is_valid_id(id_str: str) -> bool:
    """Check if a string is a valid entity ID."""
    if not id_str:
        return False
    parts = id_str.split("_", 1)
    if len(parts) == 2:
        _, value = parts
    else:
        value = parts[0]
    # UUID hex is 32 characters
    return len(value) == 32 and all(c in "0123456789abcdef" for c in value)


# ─── Timestamp-based ID ───────────────────────────────────────


def generate_tsid(prefix: str = "id") -> str:
    """
    Generate a time-sorted unique ID.
    Format: {prefix}_{timestamp_ms}_{random_hex_4}
    Useful for sortable IDs.
    """
    timestamp = int(datetime.utcnow().timestamp() * 1000)
    random_part = uuid.uuid4().hex[:4]
    return f"{prefix}_{timestamp}_{random_part}"
