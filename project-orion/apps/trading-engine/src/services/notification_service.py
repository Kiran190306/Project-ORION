"""Notification application service orchestrating in-app notification queries and state mutations."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from libraries.infrastructure.persistence.models import NotificationRecordModel

from ..schemas import (
    MarkAllReadResponse,
    NotificationResponse,
    PaginatedResponse,
    PaginationParams,
    UnreadCountResponse,
)

logger = logging.getLogger("trading_engine.services.notification")


class NotificationService:
    """Manages in-app user and organization notifications with strict tenant isolation."""

    def __init__(
        self,
        session: AsyncSession,
        user_id: str,
        organization_id: str | None = None,
    ) -> None:
        self.session = session
        self.user_id = str(user_id)
        self.organization_id = str(organization_id) if organization_id else None

    def _build_recipient_filter(self) -> Any:
        """Construct filter expression for user and active organization scope."""
        user_identifiers = [self.user_id, f"user:{self.user_id}"]
        clauses = [NotificationRecordModel.recipient.in_(user_identifiers)]

        if self.organization_id:
            clauses.append(NotificationRecordModel.recipient == f"org:{self.organization_id}")
            clauses.append(NotificationRecordModel.recipient == self.organization_id)

        return or_(*clauses)

    def _is_notification_read(self, record: NotificationRecordModel) -> bool:
        """Check whether a notification record has been read."""
        if record.status.lower() == "read":
            return True
        meta = record.meta_data or {}
        return bool(meta.get("is_read", False) or meta.get("read_at"))

    def _to_response(self, record: NotificationRecordModel) -> NotificationResponse:
        """Map persistence model to Pydantic schema."""
        meta = dict(record.meta_data or {})
        is_read = self._is_notification_read(record)
        read_at_str = meta.get("read_at")
        read_at: datetime | None = None
        if read_at_str:
            try:
                read_at = datetime.fromisoformat(read_at_str)
            except (ValueError, TypeError):
                read_at = None

        return NotificationResponse(
            id=record.id,
            channel=record.channel or "in_app",
            severity=record.severity or "info",
            notification_type=record.notification_type,
            title=record.title,
            body=record.body,
            status="read" if is_read else "unread",
            recipient=record.recipient,
            is_read=is_read,
            read_at=read_at,
            meta_data=meta,
            created_at=record.created_at,
        )

    async def list_notifications(
        self,
        pagination: PaginationParams,
        unread_only: bool = False,
    ) -> PaginatedResponse[NotificationResponse]:
        """List notifications for the authenticated user and organization with pagination."""
        base_filter = self._build_recipient_filter()

        # Query all records for user/tenant
        query = (
            select(NotificationRecordModel)
            .where(base_filter)
            .order_by(desc(NotificationRecordModel.created_at))
        )

        res = await self.session.execute(query)
        all_records = list(res.scalars().all())

        # In-memory filter for read status to ensure cross-DB consistency
        if unread_only:
            records = [r for r in all_records if not self._is_notification_read(r)]
        else:
            records = all_records

        total = len(records)
        offset = pagination.offset
        limit = pagination.limit
        page_records = records[offset : offset + limit]

        items = [self._to_response(r) for r in page_records]
        has_more = (offset + limit) < total

        return PaginatedResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more,
        )

    async def get_unread_count(self) -> UnreadCountResponse:
        """Count unread notifications scoped to user and tenant."""
        base_filter = self._build_recipient_filter()
        query = select(NotificationRecordModel).where(base_filter)
        res = await self.session.execute(query)
        all_records = res.scalars().all()

        unread = sum(1 for r in all_records if not self._is_notification_read(r))
        return UnreadCountResponse(unread_count=unread)

    async def mark_read(self, notification_id: str) -> NotificationResponse:
        """Mark a single notification as read, enforcing strict user ownership."""
        query = select(NotificationRecordModel).where(NotificationRecordModel.id == notification_id)
        res = await self.session.execute(query)
        record = res.scalar_one_or_none()

        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notification '{notification_id}' not found",
            )

        # Enforce recipient ownership
        allowed_recipients = {self.user_id, f"user:{self.user_id}"}
        if self.organization_id:
            allowed_recipients.add(f"org:{self.organization_id}")
            allowed_recipients.add(self.organization_id)

        meta = dict(record.meta_data or {})
        recip = record.recipient or ""
        record_user = meta.get("user_id")
        record_org = meta.get("organization_id")

        is_authorized = (
            recip in allowed_recipients
            or record_user == self.user_id
            or (self.organization_id and record_org == self.organization_id)
        )

        if not is_authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cannot access another user's notifications",
            )

        now = datetime.now(timezone.utc)
        record.status = "read"
        meta["is_read"] = True
        meta["read_at"] = now.isoformat()
        record.meta_data = meta
        flag_modified(record, "meta_data")
        await self.session.commit()
        await self.session.refresh(record)

        return self._to_response(record)

    async def mark_all_read(self) -> MarkAllReadResponse:
        """Mark all unread notifications for current user/tenant as read."""
        base_filter = self._build_recipient_filter()
        query = select(NotificationRecordModel).where(base_filter)
        res = await self.session.execute(query)
        records = list(res.scalars().all())

        now = datetime.now(timezone.utc)
        marked_count = 0
        for r in records:
            if not self._is_notification_read(r):
                r.status = "read"
                meta = dict(r.meta_data or {})
                meta["is_read"] = True
                meta["read_at"] = now.isoformat()
                r.meta_data = meta
                flag_modified(r, "meta_data")
                marked_count += 1

        if marked_count > 0:
            await self.session.commit()

        return MarkAllReadResponse(
            marked_count=marked_count,
            message=f"Marked {marked_count} notifications as read",
        )

    async def create_notification(
        self,
        notification_type: str,
        title: str,
        body: str,
        severity: str = "info",
        channel: str = "in_app",
        metadata: dict[str, Any] | None = None,
    ) -> NotificationRecordModel:
        """Record and dispatch an authentic in-app notification event."""
        now = datetime.now(timezone.utc)
        record_meta = {
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "is_read": False,
            "read_at": None,
            **(metadata or {}),
        }

        record = NotificationRecordModel(
            id=f"notif_{uuid.uuid4().hex[:12]}",
            channel=channel,
            severity=severity,
            notification_type=notification_type,
            title=title,
            body=body,
            status="unread",
            recipient=self.user_id,
            error_message=None,
            delivered_at=now,
            meta_data=record_meta,
        )

        self.session.add(record)
        await self.session.flush()
        return record
