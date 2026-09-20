"""Add organization_id to tenant-owned financial and configuration tables.

Revision ID: 0005_add_organization_ownership
Revises: 0004_add_saas_multi_tenancy
Create Date: 2026-09-19 23:05:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_add_organization_ownership"
down_revision: str | None = "0004_add_saas_multi_tenancy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Accounts
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.add_column(
            sa.Column("organization_id", sa.String(length=64), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_accounts_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_accounts_organization_id",
            ["organization_id"],
            unique=False,
        )

    # 2. Orders
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(
            sa.Column("organization_id", sa.String(length=64), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_orders_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_orders_organization_id",
            ["organization_id"],
            unique=False,
        )

    # 3. Fills
    with op.batch_alter_table("fills") as batch_op:
        batch_op.add_column(
            sa.Column("organization_id", sa.String(length=64), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_fills_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_fills_organization_id",
            ["organization_id"],
            unique=False,
        )

    # 4. Positions
    with op.batch_alter_table("positions") as batch_op:
        batch_op.add_column(
            sa.Column("organization_id", sa.String(length=64), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_positions_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_positions_organization_id",
            ["organization_id"],
            unique=False,
        )

    # 5. Strategy Configs
    with op.batch_alter_table("strategy_configs") as batch_op:
        batch_op.add_column(
            sa.Column("organization_id", sa.String(length=64), nullable=True),
        )
        batch_op.add_column(
            sa.Column("account_id", sa.String(length=64), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_strategy_configs_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_strategy_configs_account_id_accounts",
            "accounts",
            ["account_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_strategy_configs_organization_id",
            ["organization_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_strategy_configs_account_id",
            ["account_id"],
            unique=False,
        )

    # 6. Risk Limits
    with op.batch_alter_table("risk_limits") as batch_op:
        batch_op.add_column(
            sa.Column("organization_id", sa.String(length=64), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_risk_limits_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_risk_limits_organization_id",
            ["organization_id"],
            unique=False,
        )

    # 7. Audit Logs
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.add_column(
            sa.Column("organization_id", sa.String(length=64), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_audit_logs_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_audit_logs_organization_id",
            ["organization_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.drop_index("ix_audit_logs_organization_id")
        batch_op.drop_constraint("fk_audit_logs_organization_id_organizations", type_="foreignkey")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("risk_limits") as batch_op:
        batch_op.drop_index("ix_risk_limits_organization_id")
        batch_op.drop_constraint("fk_risk_limits_organization_id_organizations", type_="foreignkey")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("strategy_configs") as batch_op:
        batch_op.drop_index("ix_strategy_configs_account_id")
        batch_op.drop_index("ix_strategy_configs_organization_id")
        batch_op.drop_constraint("fk_strategy_configs_account_id_accounts", type_="foreignkey")
        batch_op.drop_constraint("fk_strategy_configs_organization_id_organizations", type_="foreignkey")
        batch_op.drop_column("account_id")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("positions") as batch_op:
        batch_op.drop_index("ix_positions_organization_id")
        batch_op.drop_constraint("fk_positions_organization_id_organizations", type_="foreignkey")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("fills") as batch_op:
        batch_op.drop_index("ix_fills_organization_id")
        batch_op.drop_constraint("fk_fills_organization_id_organizations", type_="foreignkey")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_index("ix_orders_organization_id")
        batch_op.drop_constraint("fk_orders_organization_id_organizations", type_="foreignkey")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("accounts") as batch_op:
        batch_op.drop_index("ix_accounts_organization_id")
        batch_op.drop_constraint("fk_accounts_organization_id_organizations", type_="foreignkey")
        batch_op.drop_column("organization_id")
