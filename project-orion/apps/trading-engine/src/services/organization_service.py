"""Organization application service managing tenants and institutional memberships."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.models import (
    MembershipStatus,
    Organization,
    OrganizationMember,
    OrganizationRole,
    OrganizationStatus,
)
from libraries.domain.organization.repository import OrganizationRepository
from libraries.infrastructure.persistence.repositories.organization_repository import (
    SQLAlchemyOrganizationRepository,
)

logger = logging.getLogger("trading_engine.services.organization")


def slugify(text: str) -> str:
    """Generate a clean, URL-safe slug from a string."""
    cleaned = re.sub(r"[^\w\s-]", "", text.strip().lower())
    slug = re.sub(r"[-\s]+", "-", cleaned).strip("-")
    return slug or f"org-{uuid.uuid4().hex[:8]}"


class OrganizationService:
    """Application service coordinating organization tenant operations."""

    def __init__(
        self,
        session: AsyncSession,
        repository: OrganizationRepository | None = None,
    ) -> None:
        self.session = session
        self.repository = repository or SQLAlchemyOrganizationRepository(session)

    async def create_organization(
        self,
        name: str,
        slug: str | None = None,
        meta_data: dict[str, Any] | None = None,
    ) -> Organization:
        """Create and persist a new organization tenant."""
        if not name or not name.strip():
            raise ValueError("Organization name cannot be blank.")

        final_slug = slug.strip().lower() if slug else slugify(name)
        if not final_slug:
            raise ValueError("Organization slug cannot be blank.")

        # Check for slug uniqueness
        existing = await self.repository.get_organization_by_slug(final_slug)
        if existing is not None:
            raise ValueError(f"Organization slug '{final_slug}' is already in use.")

        org_id = f"org_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        organization = Organization(
            id=org_id,
            name=name.strip(),
            slug=final_slug,
            status=OrganizationStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            meta_data=meta_data or {},
        )

        created = await self.repository.create_organization(organization)
        logger.info("Created organization: id=%s slug=%s", created.id, created.slug)
        return created

    async def get_organization(self, organization_id: str) -> Organization | None:
        """Fetch organization by primary identifier."""
        return await self.repository.get_organization(organization_id)

    async def get_organization_by_slug(self, slug: str) -> Organization | None:
        """Fetch organization by URL slug."""
        return await self.repository.get_organization_by_slug(slug)

    async def add_member(
        self,
        organization_id: str,
        user_id: str,
        role: OrganizationRole | str,
        status: MembershipStatus = MembershipStatus.ACTIVE,
        meta_data: dict[str, Any] | None = None,
    ) -> OrganizationMember:
        """Add a user as a member to an organization."""
        org = await self.repository.get_organization(organization_id)
        if org is None:
            raise ValueError(f"Organization '{organization_id}' does not exist.")

        already_member = await self.repository.check_membership_exists(organization_id, user_id)
        if already_member:
            raise ValueError(
                f"User '{user_id}' is already a member of organization '{organization_id}'."
            )

        resolved_role = (
            role if isinstance(role, OrganizationRole) else OrganizationRole.from_str(role)
        )

        member_id = f"mem_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        member = OrganizationMember(
            id=member_id,
            organization_id=organization_id,
            user_id=user_id,
            role=resolved_role,
            status=status,
            created_at=now,
            updated_at=now,
            meta_data=meta_data or {},
        )

        created = await self.repository.create_member(member)
        logger.info(
            "Added member: id=%s org=%s user=%s role=%s",
            created.id,
            organization_id,
            user_id,
            resolved_role.value,
        )
        return created

    async def get_membership(
        self,
        organization_id: str,
        user_id: str,
    ) -> OrganizationMember | None:
        """Fetch user's membership details in an organization."""
        return await self.repository.get_member(organization_id, user_id)

    async def list_members(
        self,
        organization_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[OrganizationMember]:
        """List all members belonging to an organization."""
        return await self.repository.list_members(organization_id, limit=limit, offset=offset)

    async def list_user_organizations(self, user_id: str) -> list[Organization]:
        """List all organizations that a user has active membership in."""
        return await self.repository.list_user_organizations(user_id)

    async def update_organization(
        self,
        organization_id: str,
        name: str | None = None,
        meta_data: dict[str, Any] | None = None,
    ) -> Organization:
        """Update organization name and/or metadata."""
        org = await self.repository.get_organization(organization_id)
        if org is None:
            raise ValueError(f"Organization '{organization_id}' does not exist.")

        now = datetime.now(timezone.utc)
        updated_org = Organization(
            id=org.id,
            name=name.strip() if name and name.strip() else org.name,
            slug=org.slug,
            status=org.status,
            created_at=org.created_at,
            updated_at=now,
            meta_data={**org.meta_data, **(meta_data or {})},
        )
        return await self.repository.update_organization(updated_org)

    async def update_member_role(
        self,
        organization_id: str,
        user_id: str,
        new_role: OrganizationRole | str,
        actor_user_id: str | None = None,
    ) -> OrganizationMember:
        """Update an existing member's role with last-owner and escalation protection."""
        membership = await self.repository.get_member(organization_id, user_id)
        if membership is None:
            raise ValueError(f"Membership for user '{user_id}' in org '{organization_id}' not found.")

        resolved_role = (
            new_role
            if isinstance(new_role, OrganizationRole)
            else OrganizationRole.from_str(new_role)
        )

        # Self-escalation prevention
        if actor_user_id and actor_user_id == user_id:
            raise ValueError("Members cannot modify their own role.")

        # Actor permission check
        if actor_user_id:
            actor_member = await self.repository.get_member(organization_id, actor_user_id)
            if actor_member is None:
                raise ValueError("Actor is not a member of the organization.")
            if resolved_role == OrganizationRole.OWNER and actor_member.role != OrganizationRole.OWNER:
                raise ValueError("Only an Owner can assign the Owner role.")
            if membership.role == OrganizationRole.OWNER and actor_member.role != OrganizationRole.OWNER:
                raise ValueError("Only an Owner can change an Owner's role.")

        # Last-owner protection
        if membership.role == OrganizationRole.OWNER and resolved_role != OrganizationRole.OWNER:
            owner_count = await self.repository.count_members_by_role(organization_id, OrganizationRole.OWNER)
            if owner_count <= 1:
                raise ValueError("Cannot demote the last owner of the organization.")

        now = datetime.now(timezone.utc)
        updated_member = OrganizationMember(
            id=membership.id,
            organization_id=membership.organization_id,
            user_id=membership.user_id,
            role=resolved_role,
            status=membership.status,
            created_at=membership.created_at,
            updated_at=now,
            meta_data=membership.meta_data,
        )
        return await self.repository.update_member(updated_member)

    async def update_member_status(
        self,
        organization_id: str,
        user_id: str,
        new_status: MembershipStatus | str,
        actor_user_id: str | None = None,
    ) -> OrganizationMember:
        """Update an existing member's status (e.g. SUSPENDED or ACTIVE)."""
        membership = await self.repository.get_member(organization_id, user_id)
        if membership is None:
            raise ValueError(f"Membership for user '{user_id}' in org '{organization_id}' not found.")

        resolved_status = (
            new_status
            if isinstance(new_status, MembershipStatus)
            else MembershipStatus(new_status)
        )

        if actor_user_id and actor_user_id == user_id and resolved_status == MembershipStatus.SUSPENDED:
            raise ValueError("Members cannot suspend themselves.")

        if membership.role == OrganizationRole.OWNER and resolved_status == MembershipStatus.SUSPENDED:
            owner_count = await self.repository.count_members_by_role(organization_id, OrganizationRole.OWNER)
            if owner_count <= 1:
                raise ValueError("Cannot suspend the last active owner of the organization.")

        now = datetime.now(timezone.utc)
        updated_member = OrganizationMember(
            id=membership.id,
            organization_id=membership.organization_id,
            user_id=membership.user_id,
            role=membership.role,
            status=resolved_status,
            created_at=membership.created_at,
            updated_at=now,
            meta_data=membership.meta_data,
        )
        return await self.repository.update_member(updated_member)

    async def remove_member(
        self,
        organization_id: str,
        user_id: str,
        actor_user_id: str | None = None,
    ) -> bool:
        """Remove a member from an organization with last-owner protection."""
        membership = await self.repository.get_member(organization_id, user_id)
        if membership is None:
            return False

        if actor_user_id and actor_user_id == user_id:
            raise ValueError("Members cannot remove themselves.")

        if actor_user_id:
            actor_member = await self.repository.get_member(organization_id, actor_user_id)
            if actor_member is None:
                raise ValueError("Actor is not a member of the organization.")
            if membership.role == OrganizationRole.OWNER and actor_member.role != OrganizationRole.OWNER:
                raise ValueError("Only an Owner can remove an Owner.")

        if membership.role == OrganizationRole.OWNER:
            owner_count = await self.repository.count_members_by_role(organization_id, OrganizationRole.OWNER)
            if owner_count <= 1:
                raise ValueError("Cannot remove the last owner of the organization.")

        return await self.repository.remove_member(organization_id, user_id)
