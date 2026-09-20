"""SQLAlchemy implementation of the OrganizationRepository protocol."""

from __future__ import annotations

import logging

from sqlalchemy import delete, func, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.models import (
    MembershipStatus,
    Organization,
    OrganizationMember,
    OrganizationRole,
    OrganizationStatus,
)
from libraries.domain.organization.repository import OrganizationRepository
from libraries.infrastructure.persistence.models.organization import (
    OrganizationMemberModel,
    OrganizationModel,
)

logger = logging.getLogger("infrastructure.persistence.repositories.organization")


def _to_domain_organization(model: OrganizationModel) -> Organization:
    """Map SQLAlchemy OrganizationModel to pure domain Organization entity."""
    return Organization(
        id=model.id,
        name=model.name,
        slug=model.slug,
        status=OrganizationStatus(model.status),
        created_at=model.created_at,
        updated_at=model.updated_at,
        meta_data=dict(model.meta_data or {}),
    )


def _to_domain_member(model: OrganizationMemberModel) -> OrganizationMember:
    """Map SQLAlchemy OrganizationMemberModel to pure domain OrganizationMember entity."""
    return OrganizationMember(
        id=model.id,
        organization_id=model.organization_id,
        user_id=model.user_id,
        role=OrganizationRole(model.role),
        status=MembershipStatus(model.status),
        created_at=model.created_at,
        updated_at=model.updated_at,
        meta_data=dict(model.meta_data or {}),
    )


class SQLAlchemyOrganizationRepository(OrganizationRepository):
    """Async SQLAlchemy persistence repository for organizations and tenant memberships."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_organization(self, organization: Organization) -> Organization:
        """Persist a new organization."""
        model = OrganizationModel(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            status=organization.status.value,
            created_at=organization.created_at,
            updated_at=organization.updated_at,
            meta_data=organization.meta_data,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_domain_organization(model)

    async def get_organization(self, organization_id: str) -> Organization | None:
        """Fetch organization by primary ID."""
        stmt = select(OrganizationModel).where(OrganizationModel.id == organization_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_domain_organization(model) if model else None

    async def get_organization_by_slug(self, slug: str) -> Organization | None:
        """Fetch organization by unique URL-safe slug."""
        stmt = select(OrganizationModel).where(OrganizationModel.slug == slug)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_domain_organization(model) if model else None

    async def update_organization(self, organization: Organization) -> Organization:
        """Update an existing organization's state."""
        stmt = select(OrganizationModel).where(OrganizationModel.id == organization.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Organization '{organization.id}' does not exist.")

        model.name = organization.name
        model.status = organization.status.value
        model.updated_at = organization.updated_at
        model.meta_data = dict(organization.meta_data)

        await self._session.flush()
        return _to_domain_organization(model)

    async def create_member(self, member: OrganizationMember) -> OrganizationMember:
        """Persist a new organization membership."""
        model = OrganizationMemberModel(
            id=member.id,
            organization_id=member.organization_id,
            user_id=member.user_id,
            role=member.role.value,
            status=member.status.value,
            created_at=member.created_at,
            updated_at=member.updated_at,
            meta_data=member.meta_data,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_domain_member(model)

    async def get_member(self, organization_id: str, user_id: str) -> OrganizationMember | None:
        """Fetch a specific user's membership in an organization."""
        stmt = select(OrganizationMemberModel).where(
            OrganizationMemberModel.organization_id == organization_id,
            OrganizationMemberModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_domain_member(model) if model else None

    async def list_members(
        self,
        organization_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[OrganizationMember]:
        """List all members belonging to an organization with pagination."""
        stmt = (
            select(OrganizationMemberModel)
            .where(OrganizationMemberModel.organization_id == organization_id)
            .order_by(OrganizationMemberModel.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [_to_domain_member(m) for m in models]

    async def list_user_organizations(self, user_id: str) -> list[Organization]:
        """List all organizations that a user is a member of."""
        stmt = (
            select(OrganizationModel)
            .join(
                OrganizationMemberModel,
                OrganizationMemberModel.organization_id == OrganizationModel.id,
            )
            .where(
                OrganizationMemberModel.user_id == user_id,
                OrganizationMemberModel.status == MembershipStatus.ACTIVE.value,
            )
            .order_by(OrganizationModel.name.asc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [_to_domain_organization(m) for m in models]

    async def check_membership_exists(self, organization_id: str, user_id: str) -> bool:
        """Check whether a user is already a member of an organization."""
        stmt = (
            select(func.count())
            .select_from(OrganizationMemberModel)
            .where(
                OrganizationMemberModel.organization_id == organization_id,
                OrganizationMemberModel.user_id == user_id,
            )
        )
        result = await self._session.execute(stmt)
        count = result.scalar_one()
        return count > 0

    async def update_member(self, member: OrganizationMember) -> OrganizationMember:
        """Update an existing member's role or status."""
        stmt = select(OrganizationMemberModel).where(
            OrganizationMemberModel.organization_id == member.organization_id,
            OrganizationMemberModel.user_id == member.user_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Membership for user '{member.user_id}' in org '{member.organization_id}' not found.")

        model.role = member.role.value
        model.status = member.status.value
        model.updated_at = member.updated_at
        model.meta_data = dict(member.meta_data)

        await self._session.flush()
        return _to_domain_member(model)

    async def count_members_by_role(self, organization_id: str, role: OrganizationRole) -> int:
        """Count active members holding a specific role in an organization."""
        role_val = role.value if isinstance(role, OrganizationRole) else str(role)
        stmt = (
            select(func.count())
            .select_from(OrganizationMemberModel)
            .where(
                OrganizationMemberModel.organization_id == organization_id,
                OrganizationMemberModel.role == role_val,
                OrganizationMemberModel.status == MembershipStatus.ACTIVE.value,
            )
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def remove_member(self, organization_id: str, user_id: str) -> bool:
        """Remove a member from an organization."""
        stmt = delete(OrganizationMemberModel).where(
            OrganizationMemberModel.organization_id == organization_id,
            OrganizationMemberModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        if isinstance(result, CursorResult):
            return int(result.rowcount) > 0
        return False
