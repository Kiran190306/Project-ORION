"""User profile and personal preferences endpoints."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from libraries.infrastructure.persistence.models import AuditLogModel, UserModel

from ..dependencies import get_current_active_user, get_db_session
from ..schemas import (
    NotificationPreferences,
    UpdateNotificationPreferencesRequest,
    UpdateProfileRequest,
    UserProfileResponse,
)

logger = logging.getLogger("trading_engine.routes.users")

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


def _extract_profile(user: UserModel) -> UserProfileResponse:
    """Build UserProfileResponse from UserModel."""
    meta = dict(user.meta_data or {})
    prefs_dict = meta.get("notification_preferences", {})
    prefs = NotificationPreferences(
        trade_events=bool(prefs_dict.get("trade_events", True)),
        risk_alerts=bool(prefs_dict.get("risk_alerts", True)),
        strategy_events=bool(prefs_dict.get("strategy_events", True)),
        security_alerts=bool(prefs_dict.get("security_alerts", True)),
    )

    return UserProfileResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        status=user.status,
        email_verified=user.email_verified,
        password_changed_at=user.password_changed_at,
        timezone=str(meta.get("timezone", "UTC")),
        notification_preferences=prefs,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User Profile",
    description="Retrieve the authenticated user's profile and preferences.",
)
async def get_my_profile(
    current_user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserProfileResponse:
    """Get full profile details of authenticated user."""
    user_id = str(current_user["id"])
    res = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = res.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return _extract_profile(user)


@router.patch(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update User Profile",
    description="Update editable profile fields (full name, timezone) for authenticated user.",
)
async def update_my_profile(
    request: UpdateProfileRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserProfileResponse:
    """Update profile fields with audit trail logging."""
    try:
        user_id = str(current_user["id"])
        res = await session.execute(select(UserModel).where(UserModel.id == user_id))
        user = res.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        updated_fields: dict[str, Any] = {}
        now = datetime.now(timezone.utc)

        if request.full_name is not None:
            user.full_name = request.full_name.strip() if request.full_name else None
            updated_fields["full_name"] = user.full_name

        meta = dict(user.meta_data or {})
        if request.timezone is not None:
            clean_tz = request.timezone.strip()
            meta["timezone"] = clean_tz
            user.meta_data = meta
            flag_modified(user, "meta_data")
            updated_fields["timezone"] = clean_tz

        if updated_fields:
            audit = AuditLogModel(
                id=f"aud_{uuid.uuid4().hex[:12]}",
                event_type="USER_PROFILE_UPDATED",
                component="user",
                actor=user.id,
                details={"username": user.username, "updated_fields": list(updated_fields.keys())},
                timestamp=now,
            )
            session.add(audit)

        await session.commit()
        await session.refresh(user)

        logger.info("User profile updated for user_id=%s: %s", user.id, updated_fields)
        return _extract_profile(user)

    except HTTPException:
        raise
    except Exception as exc:
        await session.rollback()
        logger.error("Error updating user profile: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        ) from exc


@router.get(
    "/me/preferences",
    response_model=NotificationPreferences,
    status_code=status.HTTP_200_OK,
    summary="Get Notification Preferences",
    description="Retrieve notification delivery preferences for the authenticated user.",
)
async def get_notification_preferences(
    current_user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationPreferences:
    """Get user's notification preferences."""
    user_id = str(current_user["id"])
    res = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = res.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    meta = dict(user.meta_data or {})
    prefs_dict = meta.get("notification_preferences", {})
    return NotificationPreferences(
        trade_events=bool(prefs_dict.get("trade_events", True)),
        risk_alerts=bool(prefs_dict.get("risk_alerts", True)),
        strategy_events=bool(prefs_dict.get("strategy_events", True)),
        security_alerts=bool(prefs_dict.get("security_alerts", True)),
    )


@router.put(
    "/me/preferences",
    response_model=NotificationPreferences,
    status_code=status.HTTP_200_OK,
    summary="Update Notification Preferences",
    description="Update notification delivery preferences with persistent storage.",
)
async def update_notification_preferences(
    request: UpdateNotificationPreferencesRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationPreferences:
    """Update notification preferences and log audit event."""
    try:
        user_id = str(current_user["id"])
        res = await session.execute(select(UserModel).where(UserModel.id == user_id))
        user = res.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        now = datetime.now(timezone.utc)
        meta = dict(user.meta_data or {})
        prefs = dict(meta.get("notification_preferences", {}))

        if request.trade_events is not None:
            prefs["trade_events"] = request.trade_events
        if request.risk_alerts is not None:
            prefs["risk_alerts"] = request.risk_alerts
        if request.strategy_events is not None:
            prefs["strategy_events"] = request.strategy_events
        if request.security_alerts is not None:
            prefs["security_alerts"] = request.security_alerts

        meta["notification_preferences"] = prefs
        user.meta_data = meta
        flag_modified(user, "meta_data")

        audit = AuditLogModel(
            id=f"aud_{uuid.uuid4().hex[:12]}",
            event_type="NOTIFICATION_PREFERENCES_UPDATED",
            component="user",
            actor=user.id,
            details={"username": user.username, "preferences": prefs},
            timestamp=now,
        )
        session.add(audit)
        await session.commit()
        await session.refresh(user)

        logger.info("Notification preferences updated for user_id=%s", user.id)
        return NotificationPreferences(
            trade_events=bool(prefs.get("trade_events", True)),
            risk_alerts=bool(prefs.get("risk_alerts", True)),
            strategy_events=bool(prefs.get("strategy_events", True)),
            security_alerts=bool(prefs.get("security_alerts", True)),
        )

    except HTTPException:
        raise
    except Exception as exc:
        await session.rollback()
        logger.error("Error updating notification preferences: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification preferences",
        ) from exc
