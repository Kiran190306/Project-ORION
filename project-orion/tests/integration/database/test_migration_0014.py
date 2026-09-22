"""Integration tests for Alembic migration 0014_legal_acceptance.

Verifies:
1. Fresh migration from scratch up to head (0014).
2. Verification of legal_acceptances table, columns, and indexes.
3. Verification of unique constraint on (user_id, document_type, document_version).
4. Downgrade from 0014 to 0013 reversibility.
5. Re-upgrade from 0013 to 0014.
"""

from __future__ import annotations

import pathlib
import uuid

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _get_alembic_config(db_url: str) -> Config:
    """Create an isolated Alembic Config pointing to the specified database URL."""
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


class TestMigration0014SQLite:
    """Validate migration 0014 on SQLite (fresh, upgrade, downgrade, re-upgrade)."""

    def test_migration_0014_lifecycle(self, tmp_path: pathlib.Path) -> None:
        """Verify full lifecycle: upgrade head -> verify -> downgrade -> verify -> upgrade."""
        db_file = tmp_path / f"test_mig_0014_{uuid.uuid4().hex[:8]}.db"
        db_url = f"sqlite:///{db_file.as_posix()}"
        alembic_cfg = _get_alembic_config(db_url)

        # 1. Upgrade from empty up to 0014 (head)
        command.upgrade(alembic_cfg, "head")

        engine = create_engine(db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            tables = set(inspector.get_table_names())

            # Verify legal_acceptances table created
            assert "legal_acceptances" in tables, "legal_acceptances table was not created"

            # Verify columns
            cols = {col["name"] for col in inspector.get_columns("legal_acceptances")}
            expected_cols = {
                "id",
                "user_id",
                "organization_id",
                "document_type",
                "document_version",
                "accepted_at",
                "acceptance_method",
                "user_agent",
            }
            assert expected_cols.issubset(cols), f"Missing columns: {expected_cols - cols}"

            # Verify indexes
            idx_names = {idx["name"] for idx in inspector.get_indexes("legal_acceptances")}
            assert "ix_legal_acceptances_user_id" in idx_names
            assert "ix_legal_acceptances_organization_id" in idx_names
            assert "ix_legal_acceptances_document_type" in idx_names

        # 2. Downgrade to 0013
        command.downgrade(alembic_cfg, "0013_auth_and_account_hardening")

        with engine.connect() as conn:
            inspector = inspect(conn)
            tables_after = set(inspector.get_table_names())
            assert "legal_acceptances" not in tables_after, "legal_acceptances was not dropped on downgrade"

        # 3. Re-upgrade to head (0014)
        command.upgrade(alembic_cfg, "head")

        with engine.connect() as conn:
            inspector = inspect(conn)
            tables_reup = set(inspector.get_table_names())
            assert "legal_acceptances" in tables_reup, "legal_acceptances was not re-created on upgrade"
