"""Notification record database model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from libraries.infrastructure.persistence.base import Base, TimestampMixin


class NotificationRecordModel(Base, TimestampMixin):
    """Database entity persisting audit records of all dispatched notifications."""

    __tablename__ = "notification_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    channel: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    notification_type: Mapped[str] = mapped_column(
        String(32), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    recipient: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    meta_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
