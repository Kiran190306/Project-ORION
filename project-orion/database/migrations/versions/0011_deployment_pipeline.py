"""Add strategy_deployments table for institutional deployment pipeline and paper incubator.

Revision ID: 0011_deployment_pipeline
Revises: 0010_optimization_jobs
Create Date: 2026-09-21 21:40:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011_deployment_pipeline"
down_revision: str | None = "0010_optimization_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "strategy_deployments",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=16), server_default="1.0.0", nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING_GATES", nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("source_optimization_id", sa.String(length=64), nullable=True),
        sa.Column("source_experiment_id", sa.String(length=64), nullable=True),
        sa.Column("evidence_chain", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("quality_gate_policy", sa.JSON(), nullable=True),
        sa.Column("quality_gate_results", sa.JSON(), nullable=True),
        sa.Column("initial_capital", sa.Numeric(precision=18, scale=4), nullable=False, server_default="10000.00"),
        sa.Column("incubation_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("incubation_metrics", sa.JSON(), nullable=True),
        sa.Column("benchmark_comparison", sa.JSON(), nullable=True),
        sa.Column("backtest_benchmark", sa.JSON(), nullable=True),
        sa.Column("promotion_verdict", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("transition_history", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_strategy_deployments_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_strategy_deployments_created_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_optimization_id"],
            ["optimization_jobs.id"],
            name="fk_strategy_deployments_source_opt_id_optimization_jobs",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_experiment_id"],
            ["research_experiments.id"],
            name="fk_strategy_deployments_source_exp_id_research_experiments",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_strategy_deployments"),
    )
    op.create_index(
        "ix_strategy_deployments_organization_id",
        "strategy_deployments",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_strategy_deployments_created_by",
        "strategy_deployments",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        "ix_strategy_deployments_strategy_id",
        "strategy_deployments",
        ["strategy_id"],
        unique=False,
    )
    op.create_index(
        "ix_strategy_deployments_symbol",
        "strategy_deployments",
        ["symbol"],
        unique=False,
    )
    op.create_index(
        "ix_strategy_deployments_status",
        "strategy_deployments",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_strategy_deployments_created_at",
        "strategy_deployments",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_strategy_deployments_org_created",
        "strategy_deployments",
        ["organization_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_strategy_deployments_org_status",
        "strategy_deployments",
        ["organization_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_strategy_deployments_org_strategy",
        "strategy_deployments",
        ["organization_id", "strategy_id"],
        unique=False,
    )
    op.create_index(
        "ix_strategy_deployments_source_opt",
        "strategy_deployments",
        ["organization_id", "source_optimization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_strategy_deployments_source_opt", table_name="strategy_deployments")
    op.drop_index("ix_strategy_deployments_org_strategy", table_name="strategy_deployments")
    op.drop_index("ix_strategy_deployments_org_status", table_name="strategy_deployments")
    op.drop_index("ix_strategy_deployments_org_created", table_name="strategy_deployments")
    op.drop_index("ix_strategy_deployments_created_at", table_name="strategy_deployments")
    op.drop_index("ix_strategy_deployments_status", table_name="strategy_deployments")
    op.drop_index("ix_strategy_deployments_symbol", table_name="strategy_deployments")
    op.drop_index("ix_strategy_deployments_strategy_id", table_name="strategy_deployments")
    op.drop_index("ix_strategy_deployments_created_by", table_name="strategy_deployments")
    op.drop_index("ix_strategy_deployments_organization_id", table_name="strategy_deployments")
    op.drop_table("strategy_deployments")
