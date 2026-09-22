"""Add auth_tokens table and enhance users table with status, email_verified, password_changed_at for EPIC-027.

Revision ID: 0013_auth_and_account_hardening
Revises: 0012_broker_sandbox_integration
Create Date: 2026-09-22 10:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0013_auth_and_account_hardening"
down_revision: str | None = "0012_broker_sandbox_integration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Enhance users table with status, email_verified, and password_changed_at
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False)
        )
        batch_op.add_column(
            sa.Column("email_verified", sa.Boolean(), server_default=sa.false(), nullable=False)
        )
        batch_op.add_column(
            sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_index("ix_users_status", ["status"])

    # 2. Create auth_tokens table
    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_type", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
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
            name="fk_auth_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_auth_tokens"),
    )

    # 3. Create indexes on auth_tokens
    op.create_index("ix_auth_tokens_token_hash", "auth_tokens", ["token_hash"], unique=True)
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"])
    op.create_index("ix_auth_tokens_token_type", "auth_tokens", ["token_type"])
    op.create_index("ix_auth_tokens_expires_at", "auth_tokens", ["expires_at"])
    op.create_index("ix_auth_tokens_user_type", "auth_tokens", ["user_id", "token_type"])


def downgrade() -> None:
    # 1. Drop auth_tokens indexes and table
    op.drop_index("ix_auth_tokens_user_type", table_name="auth_tokens")
    op.drop_index("ix_auth_tokens_expires_at", table_name="auth_tokens")
    op.drop_index("ix_auth_tokens_token_type", table_name="auth_tokens")
    op.drop_index("ix_auth_tokens_user_id", table_name="auth_tokens")
    op.drop_index("ix_auth_tokens_token_hash", table_name="auth_tokens")
    op.drop_table("auth_tokens")

    # 2. Remove columns from users table
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_status")
        batch_op.drop_column("password_changed_at")
        batch_op.drop_column("email_verified")
        batch_op.drop_column("status")
