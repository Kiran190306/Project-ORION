"""Integration tests for Alembic migration 0005_add_organization_ownership.

Verifies:
1. Fresh SQLite migration from empty database up to 0005 (head).
2. Existing-data preservation: Upgrades from 0004 containing real users, accounts, orders, positions, strategies.
3. Downgrade and re-upgrade reversibility between 0004 and 0005.
4. PostgreSQL compatibility against live PostgreSQL container (if available).
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import uuid
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError


def _get_alembic_config(db_url: str) -> Config:
    """Create an isolated Alembic Config pointing to the specified database URL."""
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


class TestMigration0005SQLite:
    """Validate migration 0005 on SQLite (fresh, legacy upgrade, and downgrade)."""

    def test_fresh_migration_to_0005(self, tmp_path: pathlib.Path) -> None:
        """Verify clean migration from scratch up to head (0005)."""
        db_file = tmp_path / f"fresh_{uuid.uuid4().hex[:8]}.db"
        db_url = f"sqlite:///{db_file.as_posix()}"
        alembic_cfg = _get_alembic_config(db_url)

        # Run migration from empty to head
        command.upgrade(alembic_cfg, "head")

        engine = create_engine(db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)

            # Verify organization_id column on all target tables
            target_tables = [
                "accounts",
                "orders",
                "fills",
                "positions",
                "strategy_configs",
                "risk_limits",
                "audit_logs",
            ]
            for tbl in target_tables:
                columns = {col["name"] for col in inspector.get_columns(tbl)}
                assert "organization_id" in columns, f"{tbl} missing organization_id"

            # Verify account_id on strategy_configs
            strategy_cols = {col["name"] for col in inspector.get_columns("strategy_configs")}
            assert "account_id" in strategy_cols

        engine.dispose()

    def test_upgrade_from_0004_with_existing_data(self, tmp_path: pathlib.Path) -> None:
        """Test upgrading from 0004 to 0005 with pre-existing data.

        Guarantees zero data loss or corruption for existing legacy records.
        """
        db_file = tmp_path / f"legacy_{uuid.uuid4().hex[:8]}.db"
        db_url = f"sqlite:///{db_file.as_posix()}"
        alembic_cfg = _get_alembic_config(db_url)

        # 1. Upgrade to 0004 first
        command.upgrade(alembic_cfg, "0004_add_saas_multi_tenancy")

        # 2. Seed pre-existing legacy data into 0004 schema
        engine = create_engine(db_url)
        with engine.begin() as conn:
            conn.execute(
                text("""
                INSERT INTO users (id, username, email, hashed_password, is_active, is_superuser, meta_data, created_at, updated_at)
                VALUES ('usr_legacy_002', 'legacy_trader2', 'legacy2@orion.dev', 'hashed_pass_123', 1, 0, '{}', '2026-09-19 10:00:00', '2026-09-19 10:00:00')
                """)
            )
            conn.execute(
                text("""
                INSERT INTO accounts (id, user_id, broker_name, account_number, currency, balance, equity, margin, margin_free, margin_level, leverage, is_live, is_active, meta_data, created_at, updated_at)
                VALUES ('acc_legacy_002', 'usr_legacy_002', 'paper', 'PAPER-LEGACY-002', 'USD', 250000.0000, 250000.0000, 0.0000, 250000.0000, 0.0, 100, 0, 1, '{}', '2026-09-19 10:05:00', '2026-09-19 10:05:00')
                """)
            )
            conn.execute(
                text("""
                INSERT INTO orders (id, account_id, symbol, side, order_type, quantity, status, filled_quantity, meta_data, created_at, updated_at)
                VALUES ('ord_legacy_002', 'acc_legacy_002', 'GBP/USD', 'BUY', 'MARKET', 50000.0000, 'FILLED', 50000.0000, '{}', '2026-09-19 10:10:00', '2026-09-19 10:10:00')
                """)
            )
            conn.execute(
                text("""
                INSERT INTO fills (id, order_id, symbol, side, price, quantity, commission, timestamp)
                VALUES ('fil_legacy_002', 'ord_legacy_002', 'GBP/USD', 'BUY', 1.295000, 50000.0000, 0.0000, '2026-09-19 10:10:01')
                """)
            )
            conn.execute(
                text("""
                INSERT INTO positions (id, account_id, symbol, side, quantity, open_price, current_price, realized_pnl, unrealized_pnl, commission, swap, is_open, opened_at, meta_data, created_at, updated_at)
                VALUES ('pos_legacy_002', 'acc_legacy_002', 'GBP/USD', 'BUY', 50000.0000, 1.295000, 1.295000, 0.0000, 0.0000, 0.0000, 0.0000, 1, '2026-09-19 10:10:00', '{}', '2026-09-19 10:10:00', '2026-09-19 10:10:00')
                """)
            )
            conn.execute(
                text("""
                INSERT INTO strategy_configs (id, name, version, is_active, symbols, parameters, created_at, updated_at)
                VALUES ('strat_legacy_002', 'TrendFollower', '1.0.0', 1, '["GBP/USD"]', '{"ema_fast": 12}', '2026-09-19 10:15:00', '2026-09-19 10:15:00')
                """)
            )
            conn.execute(
                text("""
                INSERT INTO risk_limits (id, name, limit_type, threshold, is_hard_limit, is_enabled, created_at, updated_at)
                VALUES ('risk_legacy_002', 'MaxDrawdown', 'DRAWDOWN', 0.050000, 1, 1, '2026-09-19 10:20:00', '2026-09-19 10:20:00')
                """)
            )
            conn.execute(
                text("""
                INSERT INTO audit_logs (id, event_type, component, actor, details, timestamp)
                VALUES ('aud_legacy_002', 'ORDER_CREATED', 'EXECUTION', 'usr_legacy_002', '{}', '2026-09-19 10:10:00')
                """)
            )

        # 3. Apply migration 0005
        command.upgrade(alembic_cfg, "0005_add_organization_ownership")

        # 4. Verify all pre-existing rows remain completely intact with NULL organization_id
        with engine.connect() as conn:
            # Account check
            acc = conn.execute(
                text("SELECT id, user_id, organization_id, balance FROM accounts WHERE id = 'acc_legacy_002'")
            ).mappings().one()
            assert acc["user_id"] == "usr_legacy_002"
            assert acc["organization_id"] is None
            assert Decimal(str(acc["balance"])) == Decimal("250000.0000")

            # Order check
            ord_row = conn.execute(
                text("SELECT id, organization_id, symbol, status FROM orders WHERE id = 'ord_legacy_002'")
            ).mappings().one()
            assert ord_row["organization_id"] is None
            assert ord_row["symbol"] == "GBP/USD"
            assert ord_row["status"] == "FILLED"

            # Fill check
            fil_row = conn.execute(
                text("SELECT id, organization_id FROM fills WHERE id = 'fil_legacy_002'")
            ).mappings().one()
            assert fil_row["organization_id"] is None

            # Position check
            pos_row = conn.execute(
                text("SELECT id, organization_id, is_open FROM positions WHERE id = 'pos_legacy_002'")
            ).mappings().one()
            assert pos_row["organization_id"] is None
            assert pos_row["is_open"] in (1, True)

            # Strategy config check
            strat_row = conn.execute(
                text("SELECT id, organization_id, account_id FROM strategy_configs WHERE id = 'strat_legacy_002'")
            ).mappings().one()
            assert strat_row["organization_id"] is None
            assert strat_row["account_id"] is None

            # Risk limit check
            risk_row = conn.execute(
                text("SELECT id, organization_id FROM risk_limits WHERE id = 'risk_legacy_002'")
            ).mappings().one()
            assert risk_row["organization_id"] is None

            # Audit log check
            aud_row = conn.execute(
                text("SELECT id, organization_id FROM audit_logs WHERE id = 'aud_legacy_002'")
            ).mappings().one()
            assert aud_row["organization_id"] is None

        # 5. Test Downgrade to 0004 and Re-upgrade reversibility
        command.downgrade(alembic_cfg, "0004_add_saas_multi_tenancy")
        with engine.connect() as conn:
            inspector = inspect(conn)
            account_cols = {col["name"] for col in inspector.get_columns("accounts")}
            assert "organization_id" not in account_cols

            strat_cols = {col["name"] for col in inspector.get_columns("strategy_configs")}
            assert "organization_id" not in strat_cols
            assert "account_id" not in strat_cols

            # Verify existing data was untouched by downgrade
            acc_count = conn.execute(text("SELECT count(*) FROM accounts")).scalar()
            assert acc_count == 1

        # Re-upgrade to head
        command.upgrade(alembic_cfg, "head")
        with engine.connect() as conn:
            inspector = inspect(conn)
            account_cols = {col["name"] for col in inspector.get_columns("accounts")}
            assert "organization_id" in account_cols

        engine.dispose()


class TestMigration0005PostgreSQL:
    """Validate migration 0005 against live containerized PostgreSQL when available."""

    @pytest.mark.asyncio
    async def test_postgresql_migration_0005(self) -> None:
        from sqlalchemy.ext.asyncio import create_async_engine

        pg_url = os.getenv(
            "TEST_POSTGRES_URL",
            "postgresql+asyncpg://orion:orion@localhost:5433/orion_prod",
        )
        try:
            engine = create_async_engine(pg_url)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except (SQLAlchemyError, OSError):
            pytest.skip("Local PostgreSQL container not reachable on port 5433.")

        alembic_cfg = _get_alembic_config(pg_url)
        await asyncio.to_thread(command.upgrade, alembic_cfg, "head")

        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    """
                    SELECT table_name, column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND column_name = 'organization_id'
                    """
                )
            )
            tables_with_org_id = {row[0] for row in result.fetchall()}
            assert {
                "accounts",
                "orders",
                "fills",
                "positions",
                "strategy_configs",
                "risk_limits",
                "audit_logs",
            }.issubset(tables_with_org_id)

        await engine.dispose()
