"""Notification endpoints for in-app alert tracking, pagination, and read status."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import (
    TenantContext,
    get_current_active_user,
    get_db_session,
    get_pagination_params,
    get_tenant_context,
)
from ..schemas import (
    MarkAllReadResponse,
    NotificationResponse,
    PaginatedResponse,
    PaginationParams,
    UnreadCountResponse,
)
from ..services.notification_service import NotificationService

logger = logging.getLogger("trading_engine.routes.notifications")

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


@router.get(
    "/",
    response_model=PaginatedResponse[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Notifications",
    description="Retrieve paginated in-app notifications for the authenticated user and active organization.",
)
async def list_notifications(
    current_user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    unread_only: bool = Query(False, description="Filter only unread notifications"),
) -> PaginatedResponse[NotificationResponse]:
    """List notifications with pagination and unread filtering."""
    service = NotificationService(
        session=session,
        user_id=str(current_user["id"]),
        organization_id=tenant_context.organization_id,
    )
    return await service.list_notifications(pagination=pagination, unread_only=unread_only)


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Unread Notification Count",
    description="Retrieve total count of unread notifications for notification bell badge rendering.",
)
async def get_unread_count(
    current_user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UnreadCountResponse:
    """Get count of unread notifications."""
    service = NotificationService(
        session=session,
        user_id=str(current_user["id"]),
        organization_id=tenant_context.organization_id,
    )
    return await service.get_unread_count()


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark Notification as Read",
    description="Mark a single notification as read on the backend.",
)
async def mark_notification_read(
    notification_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationResponse:
    """Mark a notification as read with tenant authorization check."""
    service = NotificationService(
        session=session,
        user_id=str(current_user["id"]),
        organization_id=tenant_context.organization_id,
    )
    return await service.mark_read(notification_id=notification_id)


@router.post(
    "/read-all",
    response_model=MarkAllReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark All Notifications as Read",
    description="Mark all notifications for the active user/tenant as read.",
)
async def mark_all_notifications_read(
    current_user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    tenant_context: Annotated[TenantContext, Depends(get_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MarkAllReadResponse:
    """Batch-mark all notifications as read."""
    service = NotificationService(
        session=session,
        user_id=str(current_user["id"]),
        organization_id=tenant_context.organization_id,
    )
    return await service.mark_all_read()
