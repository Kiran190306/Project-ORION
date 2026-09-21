"""Add research_experiments table for institutional backtesting and strategy research.

Revision ID: 0009_research_experiments
Revises: 0008_billing_foundation
Create Date: 2026-09-21 12:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_research_experiments"
down_revision: str | None = "0008_billing_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_experiments",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), server_default="1.0.0", nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("initial_capital", sa.Numeric(precision=18, scale=4), nullable=False, server_default="10000.00"),
        sa.Column("parameters", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("simulation_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=32), server_default="CREATED", nullable=False),
        sa.Column("execution_time_seconds", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("equity_curve", sa.JSON(), nullable=True),
        sa.Column("trades", sa.JSON(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_research_experiments_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_research_experiments_created_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_research_experiments"),
    )
    op.create_index(
        "ix_research_experiments_organization_id",
        "research_experiments",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_research_experiments_created_by",
        "research_experiments",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        "ix_research_experiments_strategy_id",
        "research_experiments",
        ["strategy_id"],
        unique=False,
    )
    op.create_index(
        "ix_research_experiments_symbol",
        "research_experiments",
        ["symbol"],
        unique=False,
    )
    op.create_index(
        "ix_research_experiments_status",
        "research_experiments",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_research_experiments_created_at",
        "research_experiments",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_experiments_org_created",
        "research_experiments",
        ["organization_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_experiments_org_status",
        "research_experiments",
        ["organization_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_research_experiments_org_status", table_name="research_experiments")
    op.drop_index("ix_research_experiments_org_created", table_name="research_experiments")
    op.drop_index("ix_research_experiments_created_at", table_name="research_experiments")
    op.drop_index("ix_research_experiments_status", table_name="research_experiments")
    op.drop_index("ix_research_experiments_symbol", table_name="research_experiments")
    op.drop_index("ix_research_experiments_strategy_id", table_name="research_experiments")
    op.drop_index("ix_research_experiments_created_by", table_name="research_experiments")
    op.drop_index("ix_research_experiments_organization_id", table_name="research_experiments")
    op.drop_table("research_experiments")
