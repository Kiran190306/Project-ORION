"""Integration tests for Alembic migration 0006_add_subscription_entitlements.

Verifies:
1. Fresh migration from empty database up to 0006 (head).
2. Canonical plan tiers seeded (FREE, PRO, BUSINESS, ENTERPRISE) with correct limits.
3. Upgrades from 0005 containing pre-existing organizations: auto-provisions Free subscription.
4. Downgrade and re-upgrade reversibility between 0005 and 0006.
5. PostgreSQL compatibility against live PostgreSQL container (if available).
"""

from __future__ import annotations

import os
import pathlib
import uuid

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


class TestMigration0006SQLite:
    """Validate migration 0006 on SQLite (fresh, legacy upgrade, and downgrade)."""

    def test_fresh_migration_to_0006(self, tmp_path: pathlib.Path) -> None:
        """Verify clean migration from scratch up to head (0006)."""
        db_file = tmp_path / f"fresh_{uuid.uuid4().hex[:8]}.db"
        db_url = f"sqlite:///{db_file.as_posix()}"
        alembic_cfg = _get_alembic_config(db_url)

        # Run migration from empty to head
        command.upgrade(alembic_cfg, "head")

        engine = create_engine(db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)

            # 1. Verify tables exist
            tables = set(inspector.get_table_names())
            assert "plans" in tables, "plans table not created"
            assert "subscriptions" in tables, "subscriptions table not created"

            # 2. Verify plans columns
            plan_cols = {col["name"] for col in inspector.get_columns("plans")}
            assert "code" in plan_cols
            assert "max_accounts" in plan_cols
            assert "max_daily_orders" in plan_cols
            assert "max_workers" in plan_cols
            assert "allowed_assets" in plan_cols
            assert "retention_days" in plan_cols

            # 3. Verify canonical plans seeded
            rows = conn.execute(text("SELECT id, code, max_accounts, max_daily_orders, max_workers FROM plans ORDER BY max_accounts")).fetchall()
            codes = {r[1] for r in rows}
            assert codes == {"FREE", "PRO", "BUSINESS", "ENTERPRISE"}

            # Verify free plan
            free_row = next(r for r in rows if r[1] == "FREE")
            assert free_row[0] == "plan-free"
            assert free_row[2] == 1  # max_accounts
            assert free_row[3] == 100  # max_daily_orders
            assert free_row[4] == 0  # max_workers

            # Verify enterprise plan
            ent_row = next(r for r in rows if r[1] == "ENTERPRISE")
            assert ent_row[0] == "plan-enterprise"
            assert ent_row[2] == -1  # unlimited accounts
            assert ent_row[3] == -1  # unlimited orders
            assert ent_row[4] == -1  # unlimited workers

        engine.dispose()

    def test_upgrade_from_0005_with_pre_existing_organization(self, tmp_path: pathlib.Path) -> None:
        """Test upgrading from 0005 to 0006 with pre-existing organizations.

        Ensures pre-existing organizations receive a default Free subscription.
        """
        db_file = tmp_path / f"legacy_{uuid.uuid4().hex[:8]}.db"
        db_url = f"sqlite:///{db_file.as_posix()}"
        alembic_cfg = _get_alembic_config(db_url)

        # 1. Upgrade to 0005 first
        command.upgrade(alembic_cfg, "0005_add_organization_ownership")

        # 2. Seed pre-existing organization in 0005 schema
        org_id = f"org_{uuid.uuid4().hex[:12]}"
        engine = create_engine(db_url)
        with engine.begin() as conn:
            conn.execute(
                text("""
                INSERT INTO organizations (id, name, slug, status, meta_data, created_at, updated_at)
                VALUES (:org_id, 'Legacy Prop Desk', 'legacy-prop-desk', 'ACTIVE', '{}', '2026-09-19 10:00:00', '2026-09-19 10:00:00')
                """),
                {"org_id": org_id},
            )
        engine.dispose()

        # 3. Upgrade to 0006
        command.upgrade(alembic_cfg, "0006_subscription_entitlements")

        # 4. Verify organization was provisioned a default Free subscription
        engine = create_engine(db_url)
        with engine.connect() as conn:
            sub_rows = conn.execute(
                text("SELECT id, organization_id, plan_id, status FROM subscriptions WHERE organization_id = :org_id"),
                {"org_id": org_id},
            ).fetchall()
            assert len(sub_rows) == 1
            assert sub_rows[0][1] == org_id
            assert sub_rows[0][2] == "plan-free"
            assert sub_rows[0][3] == "ACTIVE"

        engine.dispose()

    def test_downgrade_and_reupgrade_reversibility(self, tmp_path: pathlib.Path) -> None:
        """Verify clean rollback to 0005 and re-upgrade to 0006."""
        db_file = tmp_path / f"reversibility_{uuid.uuid4().hex[:8]}.db"
        db_url = f"sqlite:///{db_file.as_posix()}"
        alembic_cfg = _get_alembic_config(db_url)

        # 1. Upgrade to head
        command.upgrade(alembic_cfg, "0006_subscription_entitlements")

        # 2. Downgrade to 0005
        command.downgrade(alembic_cfg, "0005_add_organization_ownership")

        engine = create_engine(db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            tables = set(inspector.get_table_names())
            assert "plans" not in tables
            assert "subscriptions" not in tables

        engine.dispose()

        # 3. Re-upgrade to 0006
        command.upgrade(alembic_cfg, "0006_subscription_entitlements")

        engine = create_engine(db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            tables = set(inspector.get_table_names())
            assert "plans" in tables
            assert "subscriptions" in tables

        engine.dispose()


class TestMigration0006PostgreSQL:
    """Validate migration 0006 against live containerized PostgreSQL when available."""

    @pytest.mark.asyncio
    async def test_postgresql_migration_0006(self) -> None:
        import asyncio

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
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name IN ('plans', 'subscriptions')
                    """
                )
            )
            found_tables = {row[0] for row in result.fetchall()}
            assert found_tables == {"plans", "subscriptions"}

            # Verify canonical plan tiers present
            plan_result = await conn.execute(text("SELECT count(*) FROM plans"))
            assert (plan_result.scalar() or 0) >= 4

        await engine.dispose()
