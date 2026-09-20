"""Integration tests for Alembic migration 0007_organization_invitations.

Verifies:
1. Fresh migration from empty database up to 0007 (head).
2. Upgrades from 0006 containing pre-existing subscriptions/organizations.
3. Downgrade and re-upgrade reversibility between 0006 and 0007.
4. PostgreSQL compatibility against live PostgreSQL container (if available).
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


class TestMigration0007SQLite:
    """Validate migration 0007 on SQLite (fresh, legacy upgrade, and downgrade)."""

    def test_fresh_migration_to_0007(self, tmp_path: pathlib.Path) -> None:
        """Verify clean migration from scratch up to head (0007)."""
        db_file = tmp_path / f"fresh_{uuid.uuid4().hex[:8]}.db"
        db_url = f"sqlite:///{db_file.as_posix()}"
        alembic_cfg = _get_alembic_config(db_url)

        # Run migration from empty to head
        command.upgrade(alembic_cfg, "head")

        engine = create_engine(db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)

            # 1. Verify organization_invitations table exists
            tables = set(inspector.get_table_names())
            assert "organization_invitations" in tables, "organization_invitations table not created"

            # 2. Verify columns
            cols = {col["name"] for col in inspector.get_columns("organization_invitations")}
            expected_cols = {
                "id",
                "organization_id",
                "email",
                "role",
                "token_hash",
                "status",
                "invited_by_user_id",
                "expires_at",
                "accepted_at",
                "created_at",
                "updated_at",
            }
            assert expected_cols.issubset(cols), f"Missing columns in organization_invitations: {expected_cols - cols}"

    def test_upgrade_from_0006_with_data(self, tmp_path: pathlib.Path) -> None:
        """Verify upgrade from 0006 to 0007 preserves existing data."""
        db_file = tmp_path / f"upgrade_{uuid.uuid4().hex[:8]}.db"
        db_url = f"sqlite:///{db_file.as_posix()}"
        alembic_cfg = _get_alembic_config(db_url)

        # Step 1: Migrate to 0006
        command.upgrade(alembic_cfg, "0006_subscription_entitlements")

        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Seed organization and user
            conn.execute(
                text("INSERT INTO organizations (id, name, slug, status, meta_data, created_at, updated_at) "
                     "VALUES ('org-test-1', 'Test Desk', 'test-desk', 'ACTIVE', '{}', '2026-09-20 00:00:00', '2026-09-20 00:00:00')")
            )
            conn.execute(
                text("INSERT INTO users (id, username, email, hashed_password, is_active, is_superuser, meta_data, created_at, updated_at) "
                     "VALUES ('user-inviter', 'inviter', 'inviter@desk.com', 'hash', 1, 0, '{}', '2026-09-20 00:00:00', '2026-09-20 00:00:00')")
            )
            conn.commit()

        # Step 2: Migrate to 0007
        command.upgrade(alembic_cfg, "head")

        with engine.connect() as conn:
            # Verify we can insert and query an invitation
            conn.execute(
                text("INSERT INTO organization_invitations (id, organization_id, email, role, token_hash, status, invited_by_user_id, expires_at, created_at, updated_at) "
                     "VALUES ('inv-1', 'org-test-1', 'new@desk.com', 'TRADER', 'hash123', 'PENDING', 'user-inviter', '2026-09-27 00:00:00', '2026-09-20 00:00:00', '2026-09-20 00:00:00')")
            )
            conn.commit()

            row = conn.execute(text("SELECT email, role, status FROM organization_invitations WHERE id = 'inv-1'")).fetchone()
            assert row is not None
            assert row[0] == "new@desk.com"
            assert row[1] == "TRADER"
            assert row[2] == "PENDING"

    def test_downgrade_reversibility(self, tmp_path: pathlib.Path) -> None:
        """Verify downgrade from 0007 back to 0006 and re-upgrade."""
        db_file = tmp_path / f"reversibility_{uuid.uuid4().hex[:8]}.db"
        db_url = f"sqlite:///{db_file.as_posix()}"
        alembic_cfg = _get_alembic_config(db_url)

        # Upgrade to head (0007)
        command.upgrade(alembic_cfg, "head")

        engine = create_engine(db_url)
        with engine.connect() as conn:
            assert "organization_invitations" in inspect(conn).get_table_names()

        # Downgrade back to 0006
        command.downgrade(alembic_cfg, "0006_subscription_entitlements")
        with engine.connect() as conn:
            assert "organization_invitations" not in inspect(conn).get_table_names()
            assert "plans" in inspect(conn).get_table_names()

        # Re-upgrade to head (0007)
        command.upgrade(alembic_cfg, "head")
        with engine.connect() as conn:
            assert "organization_invitations" in inspect(conn).get_table_names()


class TestMigration0007PostgreSQL:
    """Validate migration 0007 against live containerized PostgreSQL when available."""

    @pytest.mark.asyncio
    async def test_postgresql_migration_0007(self) -> None:
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
                      AND table_name = 'organization_invitations'
                    """
                )
            )
            found_tables = {row[0] for row in result.fetchall()}
            assert found_tables == {"organization_invitations"}

        await engine.dispose()
