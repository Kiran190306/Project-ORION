"""Add user_id to accounts table for user ownership.

Revision ID: 0003_add_user_id_to_accounts
Revises: 0002_add_users_table
Create Date: 2026-09-19 00:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_add_user_id_to_accounts"
down_revision: str | None = "0002_add_users_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Use batch_alter_table for SQLite compatibility (copy-and-move strategy)
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.add_column(
            sa.Column("user_id", sa.String(length=64), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_accounts_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_accounts_user_id",
            ["user_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.drop_index("ix_accounts_user_id")
        batch_op.drop_constraint("fk_accounts_user_id_users", type_="foreignkey")
        batch_op.drop_column("user_id")
