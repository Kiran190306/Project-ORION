"""Quantitative strategy optimization database model."""

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
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from libraries.infrastructure.persistence.base import Base, TimestampMixin


class OptimizationJobModel(Base, TimestampMixin):
    """Database entity representing a strategy optimization or walk-forward research job."""

    __tablename__ = "optimization_jobs"

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
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("10000.00"),
        nullable=False,
    )
    optimization_type: Mapped[str] = mapped_column(String(32), nullable=False)
    fitness_objective: Mapped[str] = mapped_column(String(32), nullable=False)
    parameter_space: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    optimization_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="CREATED", index=True, nullable=False)
    total_combinations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_combinations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    execution_time_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    best_parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    best_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    top_candidates: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    walk_forward_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    regime_breakdown: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    stability_report: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    heatmap: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    warnings: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_optimization_jobs_org_created", "organization_id", "created_at"),
        Index("ix_optimization_jobs_org_status", "organization_id", "status"),
        Index("ix_optimization_jobs_org_strategy", "organization_id", "strategy_id"),
    )
