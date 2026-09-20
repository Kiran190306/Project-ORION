"""Domain models and value objects for Multi-Tenant Organizations and Memberships.

Defines:
- OrganizationStatus, OrganizationRole, MembershipStatus
- Organization (Domain Entity)
- OrganizationMember (Domain Entity)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class OrganizationStatus(StrEnum):
    """Lifecycle states for an organization tenant."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class OrganizationRole(StrEnum):
    """Seven institutional roles governing tenant-level separation of duties."""

    OWNER = "OWNER"
    ADMINISTRATOR = "ADMINISTRATOR"
    PORTFOLIO_MANAGER = "PORTFOLIO_MANAGER"
    RISK_OFFICER = "RISK_OFFICER"
    TRADER = "TRADER"
    AUDITOR = "AUDITOR"
    VIEWER = "VIEWER"

    @classmethod
    def from_str(cls, value: str) -> OrganizationRole:
        """Parse role from string case-insensitively, supporting space or underscore."""
        normalized = value.strip().upper().replace(" ", "_")
        try:
            return cls(normalized)
        except ValueError as exc:
            valid_roles = ", ".join(r.value for r in cls)
            raise ValueError(f"Invalid organization role '{value}'. Must be one of: {valid_roles}") from exc


class MembershipStatus(StrEnum):
    """Lifecycle state for a user's membership within an organization."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    INVITED = "INVITED"


@dataclass(frozen=True)
class Organization:
    """Domain entity representing an institutional tenant organization."""

    id: str
    name: str
    slug: str
    status: OrganizationStatus = OrganizationStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    meta_data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Organization id must not be empty.")
        if not self.name or not self.name.strip():
            raise ValueError("Organization name must not be empty.")
        if not self.slug or not self.slug.strip():
            raise ValueError("Organization slug must not be empty.")

    @property
    def is_active(self) -> bool:
        """Check if organization is active and operational."""
        return self.status == OrganizationStatus.ACTIVE


@dataclass(frozen=True)
class OrganizationMember:
    """Domain entity representing a user's membership and role in an organization."""

    id: str
    organization_id: str
    user_id: str
    role: OrganizationRole
    status: MembershipStatus = MembershipStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    meta_data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Membership id must not be empty.")
        if not self.organization_id:
            raise ValueError("Organization id must not be empty.")
        if not self.user_id:
            raise ValueError("User id must not be empty.")

    @property
    def is_active(self) -> bool:
        """Check if membership is active."""
        return self.status == MembershipStatus.ACTIVE


class InvitationStatus(StrEnum):
    """Lifecycle states for organization member invitations."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


@dataclass(frozen=True)
class OrganizationInvitation:
    """Domain entity representing a pending or processed invitation."""

    id: str
    organization_id: str
    email: str
    role: OrganizationRole
    token_hash: str
    status: InvitationStatus = InvitationStatus.PENDING
    invited_by_user_id: str | None = None
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    accepted_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Invitation id must not be empty.")
        if not self.organization_id:
            raise ValueError("Organization id must not be empty.")
        if not self.email or "@" not in self.email:
            raise ValueError("Invitation email must be valid.")
        if not self.token_hash:
            raise ValueError("Invitation token_hash must not be empty.")

    @property
    def is_pending(self) -> bool:
        """Check if invitation is still in pending state."""
        return self.status == InvitationStatus.PENDING

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if invitation can be accepted."""
        return self.is_pending and not self.is_expired

