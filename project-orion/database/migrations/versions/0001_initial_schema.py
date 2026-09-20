"""Initial schema migration for Project ORION.

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-09-13 00:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Accounts Table ───────────────────────────────────────────────────
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("broker_name", sa.String(length=32), nullable=False),
        sa.Column("account_number", sa.String(length=64), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("balance", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("equity", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("margin", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("margin_free", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("margin_level", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("leverage", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_live", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("meta_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accounts")),
        sa.UniqueConstraint("account_number", name=op.f("uq_accounts_account_number")),
    )
    op.create_index(op.f("ix_accounts_account_number"), "accounts", ["account_number"], unique=False)
    op.create_index(op.f("ix_accounts_broker_name"), "accounts", ["broker_name"], unique=False)

    # ── 2. Orders Table ─────────────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("broker_order_id", sa.String(length=64), nullable=True),
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("order_type", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("price", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("stop_price", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("stop_loss", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("take_profit", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("filled_quantity", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("average_fill_price", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name=op.f("fk_orders_account_id_accounts"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
    )
    op.create_index(op.f("ix_orders_account_id"), "orders", ["account_id"], unique=False)
    op.create_index(op.f("ix_orders_broker_order_id"), "orders", ["broker_order_id"], unique=False)
    op.create_index(op.f("ix_orders_status"), "orders", ["status"], unique=False)
    op.create_index(op.f("ix_orders_strategy_id"), "orders", ["strategy_id"], unique=False)
    op.create_index(op.f("ix_orders_symbol"), "orders", ["symbol"], unique=False)

    # ── 3. Fills Table ──────────────────────────────────────────────────────
    op.create_table(
        "fills",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("order_id", sa.String(length=64), nullable=False),
        sa.Column("broker_fill_id", sa.String(length=64), nullable=True),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("price", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("commission", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name=op.f("fk_fills_order_id_orders"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fills")),
    )
    op.create_index(op.f("ix_fills_order_id"), "fills", ["order_id"], unique=False)
    op.create_index(op.f("ix_fills_symbol"), "fills", ["symbol"], unique=False)

    # ── 4. Execution Reports Table ──────────────────────────────────────────
    op.create_table(
        "execution_reports",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("order_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("slippage_pips", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("rejection_reason", sa.String(length=255), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name=op.f("fk_execution_reports_order_id_orders"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_execution_reports")),
    )
    op.create_index(op.f("ix_execution_reports_order_id"), "execution_reports", ["order_id"], unique=False)

    # ── 5. Positions Table ──────────────────────────────────────────────────
    op.create_table(
        "positions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("open_price", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("current_price", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("stop_loss", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("take_profit", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("unrealized_pnl", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("commission", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("swap", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name=op.f("fk_positions_account_id_accounts"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_positions")),
    )
    op.create_index(op.f("ix_positions_account_id"), "positions", ["account_id"], unique=False)
    op.create_index(op.f("ix_positions_is_open"), "positions", ["is_open"], unique=False)
    op.create_index(op.f("ix_positions_symbol"), "positions", ["symbol"], unique=False)

    # ── 6. Strategy Configs Table ───────────────────────────────────────────
    op.create_table(
        "strategy_configs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=24), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("symbols", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("parameters", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_strategy_configs")),
    )
    op.create_index(op.f("ix_strategy_configs_name"), "strategy_configs", ["name"], unique=False)

    # ── 7. Risk Limits Table ────────────────────────────────────────────────
    op.create_table(
        "risk_limits",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("limit_type", sa.String(length=32), nullable=False),
        sa.Column("threshold", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("is_hard_limit", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risk_limits")),
        sa.UniqueConstraint("name", name=op.f("uq_risk_limits_name")),
    )
    op.create_index(op.f("ix_risk_limits_limit_type"), "risk_limits", ["limit_type"], unique=False)

    # ── 8. Risk Breaches Table ──────────────────────────────────────────────
    op.create_table(
        "risk_breaches",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("limit_id", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("breach_value", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("threshold_value", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("action_taken", sa.String(length=64), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["limit_id"], ["risk_limits.id"], name=op.f("fk_risk_breaches_limit_id_risk_limits"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risk_breaches")),
    )
    op.create_index(op.f("ix_risk_breaches_limit_id"), "risk_breaches", ["limit_id"], unique=False)
    op.create_index(op.f("ix_risk_breaches_severity"), "risk_breaches", ["severity"], unique=False)

    # ── 9. Notification Records Table ───────────────────────────────────────
    op.create_table(
        "notification_records",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=24), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("notification_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("recipient", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_records")),
    )
    op.create_index(op.f("ix_notification_records_channel"), "notification_records", ["channel"], unique=False)
    op.create_index(op.f("ix_notification_records_notification_type"), "notification_records", ["notification_type"], unique=False)
    op.create_index(op.f("ix_notification_records_severity"), "notification_records", ["severity"], unique=False)
    op.create_index(op.f("ix_notification_records_status"), "notification_records", ["status"], unique=False)

    # ── 10. Audit Logs Table ────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("component", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(op.f("ix_audit_logs_component"), "audit_logs", ["component"], unique=False)
    op.create_index(op.f("ix_audit_logs_event_type"), "audit_logs", ["event_type"], unique=False)
    op.create_index(op.f("ix_audit_logs_timestamp"), "audit_logs", ["timestamp"], unique=False)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("notification_records")
    op.drop_table("risk_breaches")
    op.drop_table("risk_limits")
    op.drop_table("strategy_configs")
    op.drop_table("positions")
    op.drop_table("execution_reports")
    op.drop_table("fills")
    op.drop_table("orders")
    op.drop_table("accounts")
