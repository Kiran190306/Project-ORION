"""Quantitative research experiment database model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from libraries.infrastructure.persistence.base import Base, TimestampMixin


class ResearchExperimentModel(Base, TimestampMixin):
    """Database entity representing a backtest research experiment and its outputs."""

    __tablename__ = "research_experiments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_by: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    strategy_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("10000.00"),
        nullable=False,
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    simulation_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="CREATED", index=True, nullable=False)
    execution_time_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    equity_curve: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    trades: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    warnings: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_research_experiments_org_created", "organization_id", "created_at"),
        Index("ix_research_experiments_org_status", "organization_id", "status"),
    )
