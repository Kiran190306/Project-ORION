"""Create legal_acceptances table for EPIC-027 Phase 3.

Revision ID: 0014_legal_acceptance
Revises: 0013_auth_and_account_hardening
Create Date: 2026-09-22 12:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0014_legal_acceptance"
down_revision: str | None = "0013_auth_and_account_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "legal_acceptances",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=True),
        sa.Column("document_type", sa.String(length=64), nullable=False),
        sa.Column("document_version", sa.String(length=32), nullable=False),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("acceptance_method", sa.String(length=32), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_legal_acceptances_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_legal_acceptances_organization_id_organizations",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_legal_acceptances"),
        sa.UniqueConstraint(
            "user_id",
            "document_type",
            "document_version",
            name="uq_legal_acceptance_user_doc_ver",
        ),
    )
    op.create_index(
        "ix_legal_acceptances_user_id",
        "legal_acceptances",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_legal_acceptances_organization_id",
        "legal_acceptances",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_legal_acceptances_document_type",
        "legal_acceptances",
        ["document_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_legal_acceptances_document_type", table_name="legal_acceptances")
    op.drop_index("ix_legal_acceptances_organization_id", table_name="legal_acceptances")
    op.drop_index("ix_legal_acceptances_user_id", table_name="legal_acceptances")
    op.drop_table("legal_acceptances")
