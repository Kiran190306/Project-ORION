"""Quantitative strategy deployment database model for Project ORION."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from libraries.infrastructure.persistence.base import Base, TimestampMixin


class StrategyDeploymentModel(Base, TimestampMixin):
    """Database entity representing an institutional strategy deployment pipeline instance.

    Tracks a strategy's progression from optimization through quality gating,
    paper incubation, benchmark evaluation, and promotion review.

    EPIC-025 strictly operates in Paper Trading ($0.00 Capital at risk).
    """

    __tablename__ = "strategy_deployments"

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
    strategy_version: Mapped[str] = mapped_column(String(16), default="1.0.0", nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default="PENDING_GATES",
        index=True,
        nullable=False,
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source_optimization_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("optimization_jobs.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    source_experiment_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("research_experiments.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    evidence_chain: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    quality_gate_policy: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    quality_gate_results: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    initial_capital: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("10000.00"),
        nullable=False,
    )
    incubation_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    incubation_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    benchmark_comparison: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    backtest_benchmark: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    promotion_verdict: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    transition_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_strategy_deployments_org_created", "organization_id", "created_at"),
        Index("ix_strategy_deployments_org_status", "organization_id", "status"),
        Index("ix_strategy_deployments_org_strategy", "organization_id", "strategy_id"),
        Index("ix_strategy_deployments_source_opt", "organization_id", "source_optimization_id"),
    )
