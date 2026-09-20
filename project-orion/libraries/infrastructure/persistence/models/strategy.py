"""Strategy configuration database model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from libraries.infrastructure.persistence.base import Base, TimestampMixin


class StrategyConfigModel(Base, TimestampMixin):
    """Database entity representing a trading strategy configuration and status."""

    __tablename__ = "strategy_configs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    account_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(24), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    symbols: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
