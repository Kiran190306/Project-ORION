"""Member invitation application service with cryptographic token management."""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.models import (
    InvitationStatus,
    MembershipStatus,
    OrganizationInvitation,
    OrganizationMember,
    OrganizationRole,
)
from libraries.domain.organization.repository import (
    InvitationRepository,
    OrganizationRepository,
)
from libraries.infrastructure.persistence.models.audit import AuditLogModel
from libraries.infrastructure.persistence.models.user import UserModel
from libraries.infrastructure.persistence.repositories.invitation_repository import (
    SQLAlchemyInvitationRepository,
)
from libraries.infrastructure.persistence.repositories.organization_repository import (
    SQLAlchemyOrganizationRepository,
)

logger = logging.getLogger("trading_engine.services.invitation")


def _hash_token(raw_token: str) -> str:
    """Compute deterministic SHA-256 hex digest of a raw token."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class InvitationService:
    """Coordinates organization member invitations, cryptographic issuance, and acceptance."""

    def __init__(
        self,
        session: AsyncSession,
        org_repo: OrganizationRepository | None = None,
        inv_repo: InvitationRepository | None = None,
    ) -> None:
        self.session = session
        self.org_repo = org_repo or SQLAlchemyOrganizationRepository(session)
        self.inv_repo = inv_repo or SQLAlchemyInvitationRepository(session)

    async def create_invitation(
        self,
        organization_id: str,
        email: str,
        role: OrganizationRole | str,
        invited_by_user_id: str,
        expires_in_days: int = 7,
    ) -> tuple[OrganizationInvitation, str]:
        """Create a cryptographically secure member invitation and return (entity, raw_token)."""
        clean_email = email.strip().lower()
        if not clean_email or "@" not in clean_email:
            raise ValueError(f"Invalid email address '{email}'.")

        org = await self.org_repo.get_organization(organization_id)
        if org is None:
            raise ValueError(f"Organization '{organization_id}' not found.")

        resolved_role = (
            role if isinstance(role, OrganizationRole) else OrganizationRole.from_str(role)
        )

        # Check inviter authorization
        inviter_membership = await self.org_repo.get_member(organization_id, invited_by_user_id)
        if inviter_membership is None:
            raise ValueError("Inviter is not a member of the organization.")

        # Only Owner can invite Owner
        if resolved_role == OrganizationRole.OWNER and inviter_membership.role != OrganizationRole.OWNER:
            raise ValueError("Only an Owner can invite another Owner.")

        # Check if email is already an existing user and active member in this org
        user_stmt = select(UserModel).where(UserModel.email == clean_email)
        user_res = await self.session.execute(user_stmt)
        existing_user = user_res.scalar_one_or_none()
        if existing_user is not None:
            already_member = await self.org_repo.check_membership_exists(
                organization_id, existing_user.id
            )
            if already_member:
                raise ValueError(
                    f"User with email '{clean_email}' is already a member of this organization."
                )

        # Generate cryptographically secure token and its SHA-256 hash
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=expires_in_days)
        invitation = OrganizationInvitation(
            id=f"inv_{uuid.uuid4().hex[:16]}",
            organization_id=organization_id,
            email=clean_email,
            role=resolved_role,
            token_hash=token_hash,
            status=InvitationStatus.PENDING,
            invited_by_user_id=invited_by_user_id,
            expires_at=expires_at,
            accepted_at=None,
            created_at=now,
            updated_at=now,
        )

        created = await self.inv_repo.create_invitation(invitation)

        # Record audit log event
        audit = AuditLogModel(
            id=f"aud_{uuid.uuid4().hex[:16]}",
            organization_id=organization_id,
            event_type="invitation.created",
            component="invitation_service",
            actor=invited_by_user_id,
            details={
                "invitation_id": created.id,
                "email": clean_email,
                "role": resolved_role.value,
                "expires_at": expires_at.isoformat(),
            },
            timestamp=now,
        )
        self.session.add(audit)
        await self.session.flush()

        logger.info(
            "Created invitation %s for %s in org %s by user %s",
            created.id,
            clean_email,
            organization_id,
            invited_by_user_id,
        )
        return created, raw_token

    async def get_invitation_by_token(self, raw_token: str) -> OrganizationInvitation | None:
        """Fetch invitation entity using raw token."""
        token_hash = _hash_token(raw_token)
        return await self.inv_repo.get_invitation_by_token_hash(token_hash)

    async def accept_invitation(
        self,
        raw_token: str,
        user_id: str,
    ) -> OrganizationMember:
        """Validate token and transactionally accept invitation, creating active membership."""
        token_hash = _hash_token(raw_token)
        invitation = await self.inv_repo.get_invitation_by_token_hash(token_hash)
        if invitation is None:
            raise ValueError("Invalid invitation token.")

        now = datetime.now(timezone.utc)
        if invitation.status != InvitationStatus.PENDING:
            raise ValueError(f"Invitation has already been {invitation.status.value.lower()}.")

        expires_at = invitation.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if now >= expires_at:
            # Mark expired
            expired_inv = OrganizationInvitation(
                id=invitation.id,
                organization_id=invitation.organization_id,
                email=invitation.email,
                role=invitation.role,
                token_hash=invitation.token_hash,
                status=InvitationStatus.EXPIRED,
                invited_by_user_id=invitation.invited_by_user_id,
                expires_at=invitation.expires_at,
                accepted_at=None,
                created_at=invitation.created_at,
                updated_at=now,
            )
            await self.inv_repo.update_invitation(expired_inv)
            await self.session.commit()
            raise ValueError("Invitation token has expired.")

        # Verify user is not already a member
        already_member = await self.org_repo.check_membership_exists(
            invitation.organization_id, user_id
        )
        if already_member:
            raise ValueError("User is already a member of this organization.")

        # Create active organization membership
        member = OrganizationMember(
            id=f"mem_{uuid.uuid4().hex[:16]}",
            organization_id=invitation.organization_id,
            user_id=user_id,
            role=invitation.role,
            status=MembershipStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            meta_data={"invited_by": invitation.invited_by_user_id, "invitation_id": invitation.id},
        )
        created_member = await self.org_repo.create_member(member)

        # Update invitation to ACCEPTED
        accepted_inv = OrganizationInvitation(
            id=invitation.id,
            organization_id=invitation.organization_id,
            email=invitation.email,
            role=invitation.role,
            token_hash=invitation.token_hash,
            status=InvitationStatus.ACCEPTED,
            invited_by_user_id=invitation.invited_by_user_id,
            expires_at=invitation.expires_at,
            accepted_at=now,
            created_at=invitation.created_at,
            updated_at=now,
        )
        await self.inv_repo.update_invitation(accepted_inv)

        # Audit event
        audit = AuditLogModel(
            id=f"aud_{uuid.uuid4().hex[:16]}",
            organization_id=invitation.organization_id,
            event_type="invitation.accepted",
            component="invitation_service",
            actor=user_id,
            details={
                "invitation_id": invitation.id,
                "role": invitation.role.value,
                "membership_id": created_member.id,
            },
            timestamp=now,
        )
        self.session.add(audit)
        await self.session.flush()

        logger.info(
            "User %s accepted invitation %s into org %s with role %s",
            user_id,
            invitation.id,
            invitation.organization_id,
            invitation.role.value,
        )
        return created_member

    async def list_invitations(
        self,
        organization_id: str,
        status: InvitationStatus | None = None,
    ) -> list[OrganizationInvitation]:
        """List invitations for an organization."""
        return await self.inv_repo.list_invitations_by_org(organization_id, status=status)

    async def revoke_invitation(
        self,
        organization_id: str,
        invitation_id: str,
        actor_user_id: str,
    ) -> OrganizationInvitation:
        """Revoke a pending invitation."""
        invitation = await self.inv_repo.get_invitation(invitation_id)
        if invitation is None:
            raise ValueError(f"Invitation '{invitation_id}' not found.")

        if invitation.organization_id != organization_id:
            raise ValueError("Invitation does not belong to the specified organization.")

        if invitation.status != InvitationStatus.PENDING:
            raise ValueError(f"Cannot revoke invitation with status '{invitation.status.value}'.")

        now = datetime.now(timezone.utc)
        revoked_inv = OrganizationInvitation(
            id=invitation.id,
            organization_id=invitation.organization_id,
            email=invitation.email,
            role=invitation.role,
            token_hash=invitation.token_hash,
            status=InvitationStatus.REVOKED,
            invited_by_user_id=invitation.invited_by_user_id,
            expires_at=invitation.expires_at,
            accepted_at=None,
            created_at=invitation.created_at,
            updated_at=now,
        )
        updated = await self.inv_repo.update_invitation(revoked_inv)

        audit = AuditLogModel(
            id=f"aud_{uuid.uuid4().hex[:16]}",
            organization_id=organization_id,
            event_type="invitation.revoked",
            component="invitation_service",
            actor=actor_user_id,
            details={"invitation_id": invitation.id},
            timestamp=now,
        )
        self.session.add(audit)
        await self.session.flush()
        return updated
