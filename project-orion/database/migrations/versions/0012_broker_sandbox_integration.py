"""Add broker_sandbox_accounts and broker_reconciliation_snapshots tables for EPIC-026.

Revision ID: 0012_broker_sandbox_integration
Revises: 0011_deployment_pipeline
Create Date: 2026-09-21 22:50:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012_broker_sandbox_integration"
down_revision: str | None = "0011_deployment_pipeline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create broker_sandbox_accounts table
    op.create_table(
        "broker_sandbox_accounts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("environment", sa.String(length=16), server_default="SANDBOX", nullable=False),
        sa.Column("account_id_external", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="DISCONNECTED", nullable=False),
        sa.Column("last_connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("credentials_encrypted", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("config", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_broker_sandbox_accounts_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_broker_sandbox_accounts_created_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_broker_sandbox_accounts"),
    )
    op.create_index(
        "ix_broker_sandbox_accounts_organization_id",
        "broker_sandbox_accounts",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_broker_sandbox_accounts_provider",
        "broker_sandbox_accounts",
        ["provider"],
        unique=False,
    )
    op.create_index(
        "ix_broker_sandbox_accounts_status",
        "broker_sandbox_accounts",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_broker_sandbox_org_provider",
        "broker_sandbox_accounts",
        ["organization_id", "provider"],
        unique=False,
    )
    op.create_index(
        "ix_broker_sandbox_org_created",
        "broker_sandbox_accounts",
        ["organization_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_broker_sandbox_org_status",
        "broker_sandbox_accounts",
        ["organization_id", "status"],
        unique=False,
    )

    # 2. Create broker_reconciliation_snapshots table
    op.create_table(
        "broker_reconciliation_snapshots",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("broker_account_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="MATCHED", nullable=False),
        sa.Column("order_discrepancies", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("position_discrepancies", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("account_discrepancies", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("balance_delta", sa.Numeric(precision=18, scale=4), server_default="0.0000", nullable=False),
        sa.Column("equity_delta", sa.Numeric(precision=18, scale=4), server_default="0.0000", nullable=False),
        sa.Column("details", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_broker_reconciliation_snapshots_org_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["broker_account_id"],
            ["broker_sandbox_accounts.id"],
            name="fk_broker_reconciliation_snapshots_account_id_sandbox",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_broker_reconciliation_snapshots"),
    )
    op.create_index(
        "ix_broker_reconciliation_snapshots_organization_id",
        "broker_reconciliation_snapshots",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_broker_reconciliation_snapshots_broker_account_id",
        "broker_reconciliation_snapshots",
        ["broker_account_id"],
        unique=False,
    )
    op.create_index(
        "ix_broker_reconciliation_snapshots_status",
        "broker_reconciliation_snapshots",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_broker_recon_org_account",
        "broker_reconciliation_snapshots",
        ["organization_id", "broker_account_id"],
        unique=False,
    )
    op.create_index(
        "ix_broker_recon_org_created",
        "broker_reconciliation_snapshots",
        ["organization_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    # 1. Drop broker_reconciliation_snapshots
    op.drop_index("ix_broker_recon_org_created", table_name="broker_reconciliation_snapshots")
    op.drop_index("ix_broker_recon_org_account", table_name="broker_reconciliation_snapshots")
    op.drop_index("ix_broker_reconciliation_snapshots_status", table_name="broker_reconciliation_snapshots")
    op.drop_index("ix_broker_reconciliation_snapshots_broker_account_id", table_name="broker_reconciliation_snapshots")
    op.drop_index("ix_broker_reconciliation_snapshots_organization_id", table_name="broker_reconciliation_snapshots")
    op.drop_table("broker_reconciliation_snapshots")

    # 2. Drop broker_sandbox_accounts
    op.drop_index("ix_broker_sandbox_org_status", table_name="broker_sandbox_accounts")
    op.drop_index("ix_broker_sandbox_org_created", table_name="broker_sandbox_accounts")
    op.drop_index("ix_broker_sandbox_org_provider", table_name="broker_sandbox_accounts")
    op.drop_index("ix_broker_sandbox_accounts_status", table_name="broker_sandbox_accounts")
    op.drop_index("ix_broker_sandbox_accounts_provider", table_name="broker_sandbox_accounts")
    op.drop_index("ix_broker_sandbox_accounts_organization_id", table_name="broker_sandbox_accounts")
    op.drop_table("broker_sandbox_accounts")
