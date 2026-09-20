"""Repository interface (Protocol) for Organization and Membership domain operations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from libraries.domain.organization.models import (
    InvitationStatus,
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    OrganizationRole,
)


@runtime_checkable
class OrganizationRepository(Protocol):
    """Protocol defining persistence operations for organizations and members."""

    async def create_organization(self, organization: Organization) -> Organization:
        """Persist a new organization."""
        ...

    async def get_organization(self, organization_id: str) -> Organization | None:
        """Fetch organization by primary ID."""
        ...

    async def get_organization_by_slug(self, slug: str) -> Organization | None:
        """Fetch organization by unique URL-safe slug."""
        ...

    async def update_organization(self, organization: Organization) -> Organization:
        """Update an existing organization's state."""
        ...

    async def create_member(self, member: OrganizationMember) -> OrganizationMember:
        """Persist a new organization membership."""
        ...

    async def get_member(self, organization_id: str, user_id: str) -> OrganizationMember | None:
        """Fetch a specific user's membership in an organization."""
        ...

    async def list_members(
        self,
        organization_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[OrganizationMember]:
        """List all members belonging to an organization with pagination."""
        ...

    async def list_user_organizations(self, user_id: str) -> list[Organization]:
        """List all organizations that a user is an active member of."""
        ...

    async def check_membership_exists(self, organization_id: str, user_id: str) -> bool:
        """Check whether a user is already a member of an organization."""
        ...

    async def update_member(self, member: OrganizationMember) -> OrganizationMember:
        """Update an existing member's role or status."""
        ...

    async def count_members_by_role(self, organization_id: str, role: OrganizationRole) -> int:
        """Count active members holding a specific role in an organization."""
        ...

    async def remove_member(self, organization_id: str, user_id: str) -> bool:
        """Remove a member from an organization."""
        ...


@runtime_checkable
class InvitationRepository(Protocol):
    """Protocol defining persistence operations for organization invitations."""

    async def create_invitation(self, invitation: OrganizationInvitation) -> OrganizationInvitation:
        """Persist a new member invitation."""
        ...

    async def get_invitation_by_token_hash(self, token_hash: str) -> OrganizationInvitation | None:
        """Fetch an invitation by token SHA-256 hash."""
        ...

    async def get_invitation(self, invitation_id: str) -> OrganizationInvitation | None:
        """Fetch an invitation by primary identifier."""
        ...

    async def list_invitations_by_org(
        self,
        organization_id: str,
        status: InvitationStatus | None = None,
    ) -> list[OrganizationInvitation]:
        """List invitations for an organization, optionally filtered by status."""
        ...

    async def update_invitation(self, invitation: OrganizationInvitation) -> OrganizationInvitation:
        """Update an invitation's status or metadata."""
        ...

