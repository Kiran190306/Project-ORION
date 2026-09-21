"""Add optimization_jobs table for quantitative strategy optimization and walk-forward research.

Revision ID: 0010_optimization_jobs
Revises: 0009_research_experiments
Create Date: 2026-09-21 16:30:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010_optimization_jobs"
down_revision: str | None = "0009_research_experiments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "optimization_jobs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("initial_capital", sa.Numeric(precision=18, scale=4), nullable=False, server_default="10000.00"),
        sa.Column("optimization_type", sa.String(length=32), nullable=False),
        sa.Column("fitness_objective", sa.String(length=32), nullable=False),
        sa.Column("parameter_space", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("optimization_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=32), server_default="CREATED", nullable=False),
        sa.Column("total_combinations", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completed_combinations", sa.Integer(), server_default="0", nullable=False),
        sa.Column("execution_time_seconds", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("best_parameters", sa.JSON(), nullable=True),
        sa.Column("best_metrics", sa.JSON(), nullable=True),
        sa.Column("top_candidates", sa.JSON(), nullable=True),
        sa.Column("walk_forward_result", sa.JSON(), nullable=True),
        sa.Column("regime_breakdown", sa.JSON(), nullable=True),
        sa.Column("stability_report", sa.JSON(), nullable=True),
        sa.Column("heatmap", sa.JSON(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_optimization_jobs_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_optimization_jobs_created_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_optimization_jobs"),
    )
    op.create_index(
        "ix_optimization_jobs_organization_id",
        "optimization_jobs",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_optimization_jobs_created_by",
        "optimization_jobs",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        "ix_optimization_jobs_strategy_id",
        "optimization_jobs",
        ["strategy_id"],
        unique=False,
    )
    op.create_index(
        "ix_optimization_jobs_symbol",
        "optimization_jobs",
        ["symbol"],
        unique=False,
    )
    op.create_index(
        "ix_optimization_jobs_status",
        "optimization_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_optimization_jobs_created_at",
        "optimization_jobs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_optimization_jobs_org_created",
        "optimization_jobs",
        ["organization_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_optimization_jobs_org_status",
        "optimization_jobs",
        ["organization_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_optimization_jobs_org_strategy",
        "optimization_jobs",
        ["organization_id", "strategy_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_optimization_jobs_org_strategy", table_name="optimization_jobs")
    op.drop_index("ix_optimization_jobs_org_status", table_name="optimization_jobs")
    op.drop_index("ix_optimization_jobs_org_created", table_name="optimization_jobs")
    op.drop_index("ix_optimization_jobs_created_at", table_name="optimization_jobs")
    op.drop_index("ix_optimization_jobs_status", table_name="optimization_jobs")
    op.drop_index("ix_optimization_jobs_symbol", table_name="optimization_jobs")
    op.drop_index("ix_optimization_jobs_strategy_id", table_name="optimization_jobs")
    op.drop_index("ix_optimization_jobs_created_by", table_name="optimization_jobs")
    op.drop_index("ix_optimization_jobs_organization_id", table_name="optimization_jobs")
    op.drop_table("optimization_jobs")
