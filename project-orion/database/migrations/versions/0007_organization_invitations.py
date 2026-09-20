"""Add organization_invitations table for secure member onboarding.

Revision ID: 0007_organization_invitations
Revises: 0006_subscription_entitlements
Create Date: 2026-09-20 09:30:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_organization_invitations"
down_revision: str | None = "0006_subscription_entitlements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization_invitations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="VIEWER"),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("invited_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_invitations_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by_user_id"],
            ["users.id"],
            name="fk_invitations_invited_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_invitations"),
    )
    op.create_index("ix_invitations_token_hash", "organization_invitations", ["token_hash"], unique=True)
    op.create_index("ix_invitations_organization_id", "organization_invitations", ["organization_id"], unique=False)
    op.create_index("ix_invitations_email", "organization_invitations", ["email"], unique=False)
    op.create_index("ix_invitations_status", "organization_invitations", ["status"], unique=False)
    op.create_index("ix_invitations_invited_by_user_id", "organization_invitations", ["invited_by_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_invitations_invited_by_user_id", table_name="organization_invitations")
    op.drop_index("ix_invitations_status", table_name="organization_invitations")
    op.drop_index("ix_invitations_email", table_name="organization_invitations")
    op.drop_index("ix_invitations_organization_id", table_name="organization_invitations")
    op.drop_index("ix_invitations_token_hash", table_name="organization_invitations")
    op.drop_table("organization_invitations")
