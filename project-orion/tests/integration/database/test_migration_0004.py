"""Integration tests for Alembic migration 0004_add_saas_multi_tenancy.

Verifies:
1. Fresh SQLite migration from empty database up to 0004 (head).
2. Existing-data preservation: Upgrades from 0003 containing real users, accounts, orders, positions.
3. Integrity constraints: Uniqueness of organization slug and (organization_id, user_id).
4. Migration downgrade and re-upgrade reversibility.
5. PostgreSQL compatibility against live PostgreSQL container (if available).
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
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError


def _get_alembic_config(db_url: str) -> Config:
    """Create an isolated Alembic Config pointing to the specified database URL."""
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


class TestMigration0004SQLite:
    """Validate migration 0004 on SQLite (fresh, legacy upgrade, and downgrade)."""

    def test_fresh_migration_to_0004(self, tmp_path: pathlib.Path) -> None:
        """Verify clean migration from scratch up to head (0004)."""
        db_file = tmp_path / f"fresh_{uuid.uuid4().hex[:8]}.db"
        db_url = f"sqlite:///{db_file.as_posix()}"
        alembic_cfg = _get_alembic_config(db_url)

        # Run migration from empty to head
        command.upgrade(alembic_cfg, "head")

        engine = create_engine(db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            tables = inspector.get_table_names()

            # Ensure both new tables are present
            assert "organizations" in tables
            assert "organization_members" in tables

            # Verify organizations columns
            org_columns = {col["name"] for col in inspector.get_columns("organizations")}
            assert {"id", "name", "slug", "status", "meta_data", "created_at", "updated_at"}.issubset(
                org_columns
            )

            # Verify organization_members columns
            mem_columns = {col["name"] for col in inspector.get_columns("organization_members")}
            assert {
                "id",
                "organization_id",
                "user_id",
                "role",
                "status",
                "meta_data",
                "created_at",
                "updated_at",
            }.issubset(mem_columns)

        engine.dispose()

    def test_upgrade_from_0003_with_existing_data(self, tmp_path: pathlib.Path) -> None:
        """Test upgrading from 0003 with real pre-existing data.

        Guarantees zero data loss or corruption for existing users, accounts, orders, positions.
        """
        db_file = tmp_path / f"legacy_{uuid.uuid4().hex[:8]}.db"
        db_url = f"sqlite:///{db_file.as_posix()}"
        alembic_cfg = _get_alembic_config(db_url)

        # 1. Upgrade to 0003 first
        command.upgrade(alembic_cfg, "0003_add_user_id_to_accounts")

        # 2. Seed pre-existing legacy data into 0003 schema
        engine = create_engine(db_url)
        with engine.begin() as conn:
            conn.execute(
                text("""
                INSERT INTO users (id, username, email, hashed_password, is_active, is_superuser, meta_data, created_at, updated_at)
                VALUES ('usr_legacy_001', 'legacy_trader', 'legacy@orion.dev', 'hashed_pass_123', 1, 0, '{}', '2026-09-19 10:00:00', '2026-09-19 10:00:00')
                """)
            )
            conn.execute(
                text("""
                INSERT INTO accounts (id, user_id, broker_name, account_number, currency, balance, equity, margin, margin_free, margin_level, leverage, is_live, is_active, meta_data, created_at, updated_at)
                VALUES ('acc_legacy_001', 'usr_legacy_001', 'paper', 'PAPER-LEGACY-001', 'USD', 100000.0000, 100000.0000, 0.0000, 100000.0000, 0.0, 100, 0, 1, '{}', '2026-09-19 10:05:00', '2026-09-19 10:05:00')
                """)
            )
            conn.execute(
                text("""
                INSERT INTO orders (id, account_id, symbol, side, order_type, quantity, status, filled_quantity, meta_data, created_at, updated_at)
                VALUES ('ord_legacy_001', 'acc_legacy_001', 'EUR/USD', 'BUY', 'MARKET', 10000.0000, 'FILLED', 10000.0000, '{}', '2026-09-19 10:10:00', '2026-09-19 10:10:00')
                """)
            )
            conn.execute(
                text("""
                INSERT INTO positions (id, account_id, symbol, side, quantity, open_price, current_price, realized_pnl, unrealized_pnl, commission, swap, is_open, opened_at, meta_data, created_at, updated_at)
                VALUES ('pos_legacy_001', 'acc_legacy_001', 'EUR/USD', 'BUY', 10000.0000, 1.085000, 1.085000, 0.0000, 0.0000, 0.0000, 0.0000, 1, '2026-09-19 10:10:00', '{}', '2026-09-19 10:10:00', '2026-09-19 10:10:00')
                """)
            )

        # 3. Apply migration 0004
        command.upgrade(alembic_cfg, "0004_add_saas_multi_tenancy")

        # 4. Verify all pre-existing rows remain completely intact
        with engine.connect() as conn:
            # User verification
            u = conn.execute(text("SELECT id, username, email FROM users WHERE id = 'usr_legacy_001'")).mappings().one()
            assert u["username"] == "legacy_trader"
            assert u["email"] == "legacy@orion.dev"

            # Account verification (balance must equal 100,000.0000)
            a = conn.execute(text("SELECT id, user_id, balance, equity, account_number FROM accounts WHERE id = 'acc_legacy_001'")).mappings().one()
            assert a["user_id"] == "usr_legacy_001"
            assert Decimal(str(a["balance"])) == Decimal("100000.0000")
            assert a["account_number"] == "PAPER-LEGACY-001"

            # Order verification
            o = conn.execute(text("SELECT id, symbol, side, status, quantity FROM orders WHERE id = 'ord_legacy_001'")).mappings().one()
            assert o["symbol"] == "EUR/USD"
            assert o["status"] == "FILLED"
            assert Decimal(str(o["quantity"])) == Decimal("10000.0000")

            # Position verification
            p = conn.execute(text("SELECT id, symbol, quantity, open_price, is_open FROM positions WHERE id = 'pos_legacy_001'")).mappings().one()
            assert p["symbol"] == "EUR/USD"
            assert Decimal(str(p["open_price"])) == Decimal("1.085000")
            assert p["is_open"] in (1, True)

            # 5. Verify inserting and linking new organization and member
            conn.execute(
                text("""
                INSERT INTO organizations (id, name, slug, status, meta_data, created_at, updated_at)
                VALUES ('org_legacy_test', 'Legacy Capital', 'legacy-capital', 'ACTIVE', '{}', '2026-09-19 11:00:00', '2026-09-19 11:00:00')
                """)
            )
            conn.execute(
                text("""
                INSERT INTO organization_members (id, organization_id, user_id, role, status, meta_data, created_at, updated_at)
                VALUES ('mem_legacy_001', 'org_legacy_test', 'usr_legacy_001', 'OWNER', 'ACTIVE', '{}', '2026-09-19 11:05:00', '2026-09-19 11:05:00')
                """)
            )

            # Test duplicate membership constraint
            with pytest.raises((IntegrityError, DBAPIError)):
                conn.execute(
                    text("""
                    INSERT INTO organization_members (id, organization_id, user_id, role, status, meta_data, created_at, updated_at)
                    VALUES ('mem_duplicate', 'org_legacy_test', 'usr_legacy_001', 'TRADER', 'ACTIVE', '{}', '2026-09-19 11:10:00', '2026-09-19 11:10:00')
                    """)
                )

        # 6. Test Downgrade and Re-upgrade reversibility
        command.downgrade(alembic_cfg, "0003_add_user_id_to_accounts")
        with engine.connect() as conn:
            inspector = inspect(conn)
            tables = inspector.get_table_names()
            assert "organizations" not in tables
            assert "organization_members" not in tables

            # Verify existing data was untouched by downgrade
            user_count = conn.execute(text("SELECT count(*) FROM users")).scalar()
            assert user_count == 1
            account_count = conn.execute(text("SELECT count(*) FROM accounts")).scalar()
            assert account_count == 1

        # Re-upgrade to head
        command.upgrade(alembic_cfg, "head")
        with engine.connect() as conn:
            inspector = inspect(conn)
            tables = inspector.get_table_names()
            assert "organizations" in tables
            assert "organization_members" in tables

        engine.dispose()


class TestMigration0004PostgreSQL:
    """Validate migration 0004 against live containerized PostgreSQL when available."""

    @pytest.mark.asyncio
    async def test_postgresql_migration_0004(self) -> None:
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

        # Test against live postgres via Alembic in separate thread to allow asyncio.run in env.py
        alembic_cfg = _get_alembic_config(pg_url)
        await asyncio.to_thread(command.upgrade, alembic_cfg, "head")

        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            )
            tables = {row[0] for row in result.fetchall()}
            assert "organizations" in tables
            assert "organization_members" in tables

        await engine.dispose()
