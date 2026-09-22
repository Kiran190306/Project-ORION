"""Organization, member, and invitation governance endpoints."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.permissions import Permission
from libraries.domain.security.rate_limit import RateLimitPolicies
from libraries.infrastructure.persistence.models import AuditLogModel

from ..dependencies import (
    TenantContext,
    get_current_active_user,
    get_db_session,
    get_invitation_service,
    get_organization_service,
    rate_limit,
    require_permission,
)
from ..schemas import (
    AcceptInvitationResponse,
    AuditLogResponse,
    CreateInvitationRequest,
    InvitationResponse,
    OrganizationMemberResponse,
    OrganizationResponse,
    UpdateMemberRoleRequest,
    UpdateOrganizationRequest,
)
from ..services.invitation_service import InvitationService
from ..services.organization_service import OrganizationService

logger = logging.getLogger("trading_engine.routes.organization")

router = APIRouter(prefix="/api/v1", tags=["Organization"])


def _verify_tenant_match(context_org_id: str | None, route_org_id: str) -> None:
    """Enforce strict cross-tenant boundary matching between context and route parameter."""
    if context_org_id is None or context_org_id != route_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cross-tenant operation denied",
        )


# ─── Organization Endpoints ───────────────────────────────────────────────────


@router.get(
    "/organizations",
    response_model=list[OrganizationResponse],
    status_code=status.HTTP_200_OK,
    summary="List User Organizations",
    description="Returns all organizations where the authenticated user has active membership.",
)
async def list_user_organizations(
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> list[OrganizationResponse]:
    """List organizations for the calling user."""
    orgs = await org_service.list_user_organizations(str(user["id"]))
    return [
        OrganizationResponse(
            id=o.id,
            name=o.name,
            slug=o.slug,
            status=o.status.value,
            created_at=o.created_at,
            updated_at=o.updated_at,
            meta_data=o.meta_data,
        )
        for o in orgs
    ]


@router.get(
    "/organizations/{id}",
    response_model=OrganizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Organization Details",
    description="Returns organization metadata and operational status. Requires ORGANIZATION_READ.",
)
async def get_organization(
    id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.ORGANIZATION_READ))],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> OrganizationResponse:
    """Fetch organization by identifier."""
    _verify_tenant_match(tenant_context.organization_id, id)
    org = await org_service.get_organization(id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        status=org.status.value,
        created_at=org.created_at,
        updated_at=org.updated_at,
        meta_data=org.meta_data,
    )


@router.patch(
    "/organizations/{id}",
    response_model=OrganizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Organization",
    description="Updates organization settings and profile. Requires ORGANIZATION_UPDATE.",
)
async def update_organization(
    id: str,
    request: UpdateOrganizationRequest,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.ORGANIZATION_UPDATE))],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> OrganizationResponse:
    """Update organization settings."""
    _verify_tenant_match(tenant_context.organization_id, id)
    try:
        updated = await org_service.update_organization(
            organization_id=id,
            name=request.name,
            meta_data=request.meta_data,
        )
        return OrganizationResponse(
            id=updated.id,
            name=updated.name,
            slug=updated.slug,
            status=updated.status.value,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
            meta_data=updated.meta_data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ─── Member Governance ────────────────────────────────────────────────────────


@router.get(
    "/organizations/{id}/members",
    response_model=list[OrganizationMemberResponse],
    status_code=status.HTTP_200_OK,
    summary="List Organization Members",
    description="Returns all active and suspended members within the tenant organization. Requires MEMBER_READ.",
)
async def list_organization_members(
    id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.MEMBER_READ))],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> list[OrganizationMemberResponse]:
    """List members belonging to the organization."""
    _verify_tenant_match(tenant_context.organization_id, id)
    members = await org_service.list_members(id)
    return [
        OrganizationMemberResponse(
            id=m.id,
            organization_id=m.organization_id,
            user_id=m.user_id,
            role=m.role.value,
            status=m.status.value,
            created_at=m.created_at,
            updated_at=m.updated_at,
            meta_data=m.meta_data,
        )
        for m in members
    ]


@router.post(
    "/organizations/{id}/members/invite",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite Member",
    description="Issues a cryptographically secure, single-use member invitation. Requires MEMBER_INVITE.",
)
async def invite_member(
    id: str,
    request: CreateInvitationRequest,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.MEMBER_INVITE))],
    invitation_service: Annotated[InvitationService, Depends(get_invitation_service)],
) -> InvitationResponse:
    """Create a new member invitation."""
    _verify_tenant_match(tenant_context.organization_id, id)
    try:
        invitation, raw_token = await invitation_service.create_invitation(
            organization_id=id,
            email=request.email,
            role=request.role,
            invited_by_user_id=tenant_context.user_id,
        )
        return InvitationResponse(
            id=invitation.id,
            organization_id=invitation.organization_id,
            email=invitation.email,
            role=invitation.role.value,
            status=invitation.status.value,
            invited_by_user_id=invitation.invited_by_user_id,
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
            invitation_token=raw_token,
            invitation_url=f"/api/v1/invitations/{raw_token}/accept",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/invitations/{token}/accept",
    response_model=AcceptInvitationResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept Member Invitation",
    description="Accepts an issued invitation using its raw token, granting membership to the authenticated user.",
    dependencies=[Depends(rate_limit(RateLimitPolicies.INVITATION_ACCEPT))],
)
async def accept_invitation(
    token: str,
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    invitation_service: Annotated[InvitationService, Depends(get_invitation_service)],
) -> AcceptInvitationResponse:
    """Accept invitation and become an active member."""
    try:
        member = await invitation_service.accept_invitation(
            raw_token=token,
            user_id=str(user["id"]),
        )
        return AcceptInvitationResponse(
            membership_id=member.id,
            organization_id=member.organization_id,
            user_id=member.user_id,
            role=member.role.value,
            status=member.status.value,
            accepted_at=member.created_at,
        )
    except ValueError as exc:
        msg = str(exc)
        if "expired" in msg.lower():
            raise HTTPException(status_code=status.HTTP_410_GONE, detail=msg) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from exc


@router.patch(
    "/organizations/{id}/members/{user_id}/role",
    response_model=OrganizationMemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Member Role",
    description="Updates an organization member's role. Enforces last-owner protection and self-escalation bans. Requires MEMBER_UPDATE.",
)
async def update_member_role(
    id: str,
    user_id: str,
    request: UpdateMemberRoleRequest,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.MEMBER_UPDATE))],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> OrganizationMemberResponse:
    """Update a member's role."""
    _verify_tenant_match(tenant_context.organization_id, id)
    try:
        updated = await org_service.update_member_role(
            organization_id=id,
            user_id=user_id,
            new_role=request.role,
            actor_user_id=tenant_context.user_id,
        )
        return OrganizationMemberResponse(
            id=updated.id,
            organization_id=updated.organization_id,
            user_id=updated.user_id,
            role=updated.role.value,
            status=updated.status.value,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
            meta_data=updated.meta_data,
        )
    except ValueError as exc:
        msg = str(exc)
        if "only an owner" in msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from exc


@router.post(
    "/organizations/{id}/members/{user_id}/suspend",
    response_model=OrganizationMemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Suspend Member",
    description="Suspends a member from organization operations. Enforces last-owner and self-suspension protections. Requires MEMBER_UPDATE.",
)
async def suspend_member(
    id: str,
    user_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.MEMBER_UPDATE))],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> OrganizationMemberResponse:
    """Suspend a member."""
    _verify_tenant_match(tenant_context.organization_id, id)
    try:
        updated = await org_service.update_member_status(
            organization_id=id,
            user_id=user_id,
            new_status="SUSPENDED",
            actor_user_id=tenant_context.user_id,
        )
        return OrganizationMemberResponse(
            id=updated.id,
            organization_id=updated.organization_id,
            user_id=updated.user_id,
            role=updated.role.value,
            status=updated.status.value,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
            meta_data=updated.meta_data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/organizations/{id}/members/{user_id}/reactivate",
    response_model=OrganizationMemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Reactivate Member",
    description="Restores an organization member to ACTIVE status. Requires MEMBER_UPDATE.",
)
async def reactivate_member(
    id: str,
    user_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.MEMBER_UPDATE))],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> OrganizationMemberResponse:
    """Reactivate a suspended member."""
    _verify_tenant_match(tenant_context.organization_id, id)
    try:
        updated = await org_service.update_member_status(
            organization_id=id,
            user_id=user_id,
            new_status="ACTIVE",
            actor_user_id=tenant_context.user_id,
        )
        return OrganizationMemberResponse(
            id=updated.id,
            organization_id=updated.organization_id,
            user_id=updated.user_id,
            role=updated.role.value,
            status=updated.status.value,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
            meta_data=updated.meta_data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete(
    "/organizations/{id}/members/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove Member",
    description="Removes a member from the organization. Enforces last-owner protection. Requires MEMBER_REMOVE.",
)
async def remove_member(
    id: str,
    user_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.MEMBER_REMOVE))],
    org_service: Annotated[OrganizationService, Depends(get_organization_service)],
) -> dict[str, Any]:
    """Remove member from organization."""
    _verify_tenant_match(tenant_context.organization_id, id)
    try:
        removed = await org_service.remove_member(
            organization_id=id,
            user_id=user_id,
            actor_user_id=tenant_context.user_id,
        )
        if not removed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
        return {"status": "removed", "user_id": user_id, "organization_id": id}
    except ValueError as exc:
        msg = str(exc)
        if "only an owner" in msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from exc


# ─── Invitation Management ───────────────────────────────────────────────────


@router.get(
    "/organizations/{id}/invitations",
    response_model=list[InvitationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Organization Invitations",
    description="Lists all pending invitations for the organization. Requires MEMBER_READ.",
)
async def list_organization_invitations(
    id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.MEMBER_READ))],
    invitation_service: Annotated[InvitationService, Depends(get_invitation_service)],
) -> list[InvitationResponse]:
    """List pending invitations for an organization."""
    _verify_tenant_match(tenant_context.organization_id, id)
    invitations = await invitation_service.list_invitations(id)
    return [
        InvitationResponse(
            id=inv.id,
            organization_id=inv.organization_id,
            email=inv.email,
            role=inv.role.value,
            status=inv.status.value,
            invited_by_user_id=inv.invited_by_user_id,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
            invitation_token=None,  # Hashed in DB; raw token never returned on list
            invitation_url=None,
        )
        for inv in invitations
    ]


@router.delete(
    "/organizations/{id}/invitations/{invitation_id}",
    status_code=status.HTTP_200_OK,
    summary="Revoke Invitation",
    description="Revokes a pending member invitation. Requires MEMBER_INVITE.",
)
async def revoke_invitation(
    id: str,
    invitation_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.MEMBER_INVITE))],
    invitation_service: Annotated[InvitationService, Depends(get_invitation_service)],
) -> dict[str, Any]:
    """Revoke a pending invitation."""
    _verify_tenant_match(tenant_context.organization_id, id)
    try:
        revoked = await invitation_service.revoke_invitation(
            organization_id=id,
            invitation_id=invitation_id,
            actor_user_id=tenant_context.user_id,
        )
        return {
            "status": "revoked",
            "invitation_id": revoked.id,
            "organization_id": id,
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ─── Audit Log Endpoints ───────────────────────────────────────────────────────


@router.get(
    "/organizations/{id}/audit-logs",
    response_model=list[AuditLogResponse],
    status_code=status.HTTP_200_OK,
    summary="List Organization Audit Logs",
    description="Returns compliance audit trail entries for the organization with pagination and secret redaction. Requires AUDIT_READ.",
    dependencies=[Depends(rate_limit(RateLimitPolicies.AUDIT_QUERY))],
)
async def list_organization_audit_logs(
    id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.AUDIT_READ))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    event_type: str | None = Query(None, description="Filter by event type"),
) -> list[AuditLogResponse]:
    """List compliance audit trail entries for the organization."""
    _verify_tenant_match(tenant_context.organization_id, id)

    stmt = select(AuditLogModel).where(AuditLogModel.organization_id == id)
    if event_type:
        stmt = stmt.where(AuditLogModel.event_type == event_type)
    stmt = stmt.order_by(desc(AuditLogModel.timestamp)).offset(offset).limit(limit)

    result = await session.execute(stmt)
    records = list(result.scalars().all())

    # Redact sensitive fields if any exist in details
    sensitive_keys = ("password", "token", "secret", "hashed_password", "raw_token", "api_key", "authorization")

    def _redact_details(d: Any) -> Any:
        if isinstance(d, dict):
            return {
                k: "[REDACTED]" if any(s in k.lower() for s in sensitive_keys) else _redact_details(v)
                for k, v in d.items()
            }
        if isinstance(d, list):
            return [_redact_details(x) for x in d]
        return d

    return [
        AuditLogResponse(
            id=r.id,
            organization_id=r.organization_id,
            event_type=r.event_type,
            component=r.component,
            actor=r.actor,
            details=_redact_details(r.details) if isinstance(r.details, dict) else {},
            timestamp=r.timestamp,
        )
        for r in records
    ]

