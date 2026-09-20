"""SQLAlchemy implementation of InvitationRepository protocol."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.models import (
    InvitationStatus,
    OrganizationInvitation,
    OrganizationRole,
)
from libraries.domain.organization.repository import InvitationRepository
from libraries.infrastructure.persistence.models.invitation import (
    OrganizationInvitationModel,
)

logger = logging.getLogger("infrastructure.persistence.repositories.invitation")


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _to_domain_invitation(model: OrganizationInvitationModel) -> OrganizationInvitation:
    """Map SQLAlchemy OrganizationInvitationModel to pure domain entity."""
    return OrganizationInvitation(
        id=model.id,
        organization_id=model.organization_id,
        email=model.email,
        role=OrganizationRole(model.role),
        token_hash=model.token_hash,
        status=InvitationStatus(model.status),
        invited_by_user_id=model.invited_by_user_id,
        expires_at=_ensure_utc(model.expires_at),
        accepted_at=_ensure_utc(model.accepted_at),
        created_at=_ensure_utc(model.created_at),
        updated_at=_ensure_utc(model.updated_at),
    )


class SQLAlchemyInvitationRepository(InvitationRepository):
    """Async SQLAlchemy persistence repository for organization member invitations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_invitation(
        self, invitation: OrganizationInvitation
    ) -> OrganizationInvitation:
        """Persist a new member invitation."""
        model = OrganizationInvitationModel(
            id=invitation.id,
            organization_id=invitation.organization_id,
            email=invitation.email,
            role=invitation.role.value,
            token_hash=invitation.token_hash,
            status=invitation.status.value,
            invited_by_user_id=invitation.invited_by_user_id,
            expires_at=invitation.expires_at,
            accepted_at=invitation.accepted_at,
            created_at=invitation.created_at,
            updated_at=invitation.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_domain_invitation(model)

    async def get_invitation_by_token_hash(
        self, token_hash: str
    ) -> OrganizationInvitation | None:
        """Fetch an invitation by token SHA-256 hash."""
        stmt = select(OrganizationInvitationModel).where(
            OrganizationInvitationModel.token_hash == token_hash
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_domain_invitation(model) if model else None

    async def get_invitation(self, invitation_id: str) -> OrganizationInvitation | None:
        """Fetch an invitation by primary identifier."""
        stmt = select(OrganizationInvitationModel).where(
            OrganizationInvitationModel.id == invitation_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_domain_invitation(model) if model else None

    async def list_invitations_by_org(
        self,
        organization_id: str,
        status: InvitationStatus | None = None,
    ) -> list[OrganizationInvitation]:
        """List invitations for an organization, optionally filtered by status."""
        stmt = select(OrganizationInvitationModel).where(
            OrganizationInvitationModel.organization_id == organization_id
        )
        if status is not None:
            stmt = stmt.where(OrganizationInvitationModel.status == status.value)

        stmt = stmt.order_by(OrganizationInvitationModel.created_at.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [_to_domain_invitation(m) for m in models]

    async def update_invitation(
        self, invitation: OrganizationInvitation
    ) -> OrganizationInvitation:
        """Update an invitation's status or metadata."""
        stmt = select(OrganizationInvitationModel).where(
            OrganizationInvitationModel.id == invitation.id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Invitation '{invitation.id}' not found.")

        model.status = invitation.status.value
        model.accepted_at = invitation.accepted_at
        model.updated_at = invitation.updated_at
        await self._session.flush()
        return _to_domain_invitation(model)
