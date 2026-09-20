"""Add commercial billing tables for Stripe test-mode integration.

Revision ID: 0008_billing_foundation
Revises: 0007_organization_invitations
Create Date: 2026-09-20 20:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_billing_foundation"
down_revision: str | None = "0007_organization_invitations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create billing_customers table
    op.create_table(
        "billing_customers",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("provider_customer_id", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("meta_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_billing_customers_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_billing_customers"),
    )
    op.create_index(
        "ix_billing_customers_organization_id",
        "billing_customers",
        ["organization_id"],
        unique=True,
    )
    op.create_index(
        "ix_billing_customers_provider_customer_id",
        "billing_customers",
        ["provider_customer_id"],
        unique=True,
    )

    # 2. Create billing_subscriptions table
    op.create_table(
        "billing_subscriptions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("provider_subscription_id", sa.String(length=128), nullable=False),
        sa.Column("provider_customer_id", sa.String(length=128), nullable=False),
        sa.Column("plan_code", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("latest_invoice_id", sa.String(length=128), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_billing_subscriptions_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_billing_subscriptions"),
    )
    op.create_index(
        "ix_billing_subscriptions_organization_id",
        "billing_subscriptions",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_billing_subscriptions_provider_subscription_id",
        "billing_subscriptions",
        ["provider_subscription_id"],
        unique=True,
    )
    op.create_index(
        "ix_billing_subscriptions_provider_customer_id",
        "billing_subscriptions",
        ["provider_customer_id"],
        unique=False,
    )
    op.create_index(
        "ix_billing_subscriptions_plan_code",
        "billing_subscriptions",
        ["plan_code"],
        unique=False,
    )
    op.create_index(
        "ix_billing_subscriptions_status",
        "billing_subscriptions",
        ["status"],
        unique=False,
    )

    # 3. Create billing_invoices table
    op.create_table(
        "billing_invoices",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("provider_invoice_id", sa.String(length=128), nullable=False),
        sa.Column("provider_customer_id", sa.String(length=128), nullable=False),
        sa.Column("provider_subscription_id", sa.String(length=128), nullable=True),
        sa.Column("amount_due", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("amount_paid", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="usd"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="paid"),
        sa.Column("hosted_invoice_url", sa.String(length=512), nullable=True),
        sa.Column("invoice_pdf", sa.String(length=512), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_billing_invoices_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_billing_invoices"),
    )
    op.create_index(
        "ix_billing_invoices_organization_id",
        "billing_invoices",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_billing_invoices_provider_invoice_id",
        "billing_invoices",
        ["provider_invoice_id"],
        unique=True,
    )
    op.create_index(
        "ix_billing_invoices_provider_customer_id",
        "billing_invoices",
        ["provider_customer_id"],
        unique=False,
    )
    op.create_index(
        "ix_billing_invoices_provider_subscription_id",
        "billing_invoices",
        ["provider_subscription_id"],
        unique=False,
    )
    op.create_index(
        "ix_billing_invoices_status",
        "billing_invoices",
        ["status"],
        unique=False,
    )

    # 4. Create billing_events table
    op.create_table(
        "billing_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("provider_event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PROCESSED"),
        sa.Column("meta_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("id", name="pk_billing_events"),
    )
    op.create_index(
        "ix_billing_events_provider_event_id",
        "billing_events",
        ["provider_event_id"],
        unique=True,
    )
    op.create_index(
        "ix_billing_events_event_type",
        "billing_events",
        ["event_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("billing_events")
    op.drop_table("billing_invoices")
    op.drop_table("billing_subscriptions")
    op.drop_table("billing_customers")
