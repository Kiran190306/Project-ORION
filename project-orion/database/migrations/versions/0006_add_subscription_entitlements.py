"""Add plans and subscriptions tables with seeded tiers.

Revision ID: 0006_add_subscription_entitlements
Revises: 0005_add_organization_ownership
Create Date: 2026-09-19 23:20:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
import uuid

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_subscription_entitlements"
down_revision: str | None = "0005_add_organization_ownership"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create plans table
    op.create_table(
        "plans",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("max_accounts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_daily_orders", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("max_workers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("allowed_assets", sa.JSON(), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_plans"),
    )
    op.create_index("ix_plans_code", "plans", ["code"], unique=True)
    op.create_index("ix_plans_is_active", "plans", ["is_active"], unique=False)

    # 2. Create subscriptions table
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("meta_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_subscriptions_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["plans.id"],
            name="fk_subscriptions_plan_id_plans",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_subscriptions"),
    )
    op.create_index("ix_subscriptions_organization_id", "subscriptions", ["organization_id"], unique=False)
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"], unique=False)
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"], unique=False)

    # 3. Seed canonical plans
    plans_table = sa.table(
        "plans",
        sa.column("id", sa.String),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("max_accounts", sa.Integer),
        sa.column("max_daily_orders", sa.Integer),
        sa.column("max_workers", sa.Integer),
        sa.column("allowed_assets", sa.JSON),
        sa.column("retention_days", sa.Integer),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    now = datetime.now(timezone.utc)
    seed_plans = [
        {
            "id": "plan-free",
            "code": "FREE",
            "name": "Free Sandbox",
            "description": "Free Sandbox tier with basic paper trading capabilities",
            "max_accounts": 1,
            "max_daily_orders": 100,
            "max_workers": 0,
            "allowed_assets": ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF"],
            "retention_days": 30,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "plan-pro",
            "code": "PRO",
            "name": "Pro Trader",
            "description": "Professional paper trading with expanded assets and autonomous worker",
            "max_accounts": 3,
            "max_daily_orders": 2500,
            "max_workers": 1,
            "allowed_assets": [
                "EUR/USD",
                "GBP/USD",
                "USD/JPY",
                "USD/CHF",
                "AUD/USD",
                "USD/CAD",
                "NZD/USD",
                "EUR/GBP",
                "EUR/JPY",
                "GBP/JPY",
                "AUD/JPY",
                "EUR/CHF",
            ],
            "retention_days": 365,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "plan-business",
            "code": "BUSINESS",
            "name": "Business / Prop Desk",
            "description": "Multi-account prop desk tier with all currency pairs and 5 workers",
            "max_accounts": 10,
            "max_daily_orders": 50000,
            "max_workers": 5,
            "allowed_assets": ["*"],
            "retention_days": 1825,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "plan-enterprise",
            "code": "ENTERPRISE",
            "name": "Enterprise Institutional",
            "description": "Unlimited enterprise capacity with maximum data retention and support",
            "max_accounts": -1,
            "max_daily_orders": -1,
            "max_workers": -1,
            "allowed_assets": ["*"],
            "retention_days": 2555,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
    ]
    op.bulk_insert(plans_table, seed_plans)

    # 4. Seed default Free subscription for any existing organizations
    conn = op.get_bind()
    org_rows = conn.execute(sa.text("SELECT id FROM organizations")).fetchall()
    if org_rows:
        subscriptions_table = sa.table(
            "subscriptions",
            sa.column("id", sa.String),
            sa.column("organization_id", sa.String),
            sa.column("plan_id", sa.String),
            sa.column("status", sa.String),
            sa.column("current_period_start", sa.DateTime(timezone=True)),
            sa.column("current_period_end", sa.DateTime(timezone=True)),
            sa.column("cancel_at_period_end", sa.Boolean),
            sa.column("meta_data", sa.JSON),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        )
        for org in org_rows:
            op.bulk_insert(
                subscriptions_table,
                [
                    {
                        "id": f"sub-{uuid.uuid4().hex[:12]}",
                        "organization_id": org[0],
                        "plan_id": "plan-free",
                        "status": "ACTIVE",
                        "current_period_start": now,
                        "current_period_end": None,
                        "cancel_at_period_end": False,
                        "meta_data": {},
                        "created_at": now,
                        "updated_at": now,
                    }
                ],
            )


def downgrade() -> None:
    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_plan_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_organization_id", table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index("ix_plans_is_active", table_name="plans")
    op.drop_index("ix_plans_code", table_name="plans")
    op.drop_table("plans")
