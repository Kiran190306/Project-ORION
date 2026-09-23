"""Create onboarding_progress table for EPIC-027 Phase 5A.

Revision ID: 0015_onboarding_progress
Revises: 0014_legal_acceptance
Create Date: 2026-09-23 12:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0015_onboarding_progress"
down_revision: str | None = "0014_legal_acceptance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "onboarding_progress",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="NOT_STARTED", nullable=False),
        sa.Column("current_step", sa.String(length=32), server_default="WELCOME", nullable=False),
        sa.Column("completed_steps", sa.JSON(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_onboarding_progress_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_onboarding_progress_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_onboarding_progress"),
        sa.UniqueConstraint(
            "user_id",
            "organization_id",
            name="uq_onboarding_progress_user_org",
        ),
    )
    op.create_index(
        "ix_onboarding_progress_user_id",
        "onboarding_progress",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_onboarding_progress_organization_id",
        "onboarding_progress",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_onboarding_progress_status",
        "onboarding_progress",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_onboarding_progress_status", table_name="onboarding_progress")
    op.drop_index("ix_onboarding_progress_organization_id", table_name="onboarding_progress")
    op.drop_index("ix_onboarding_progress_user_id", table_name="onboarding_progress")
    op.drop_table("onboarding_progress")
