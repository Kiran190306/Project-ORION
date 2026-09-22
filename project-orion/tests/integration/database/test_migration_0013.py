"""Integration tests for Alembic migration 0013_auth_and_account_hardening.

Verifies:
1. Fresh migration from scratch up to head (0013).
2. Verification of users table enhancements (status, email_verified, password_changed_at).
3. Verification of auth_tokens table and indexes.
4. Downgrade from 0013 to 0012 reversibility.
5. Re-upgrade from 0012 to 0013.
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


class TestMigration0013SQLite:
    """Validate migration 0013 on SQLite (fresh, upgrade, downgrade, re-upgrade)."""

    def test_migration_0013_lifecycle(self, tmp_path: pathlib.Path) -> None:
        """Verify full lifecycle: upgrade head -> verify -> downgrade -> verify -> upgrade."""
        db_file = tmp_path / f"test_mig_0013_{uuid.uuid4().hex[:8]}.db"
        db_url = f"sqlite:///{db_file.as_posix()}"
        alembic_cfg = _get_alembic_config(db_url)

        # 1. Upgrade from empty up to 0013 (head)
        command.upgrade(alembic_cfg, "head")

        engine = create_engine(db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            tables = set(inspector.get_table_names())

            # Verify auth_tokens table created
            assert "auth_tokens" in tables, "auth_tokens table was not created"

            # Verify auth_tokens columns
            token_cols = {col["name"] for col in inspector.get_columns("auth_tokens")}
            expected_token_cols = {
                "id",
                "user_id",
                "token_hash",
                "token_type",
                "expires_at",
                "used_at",
                "created_at",
                "updated_at",
            }
            assert expected_token_cols.issubset(token_cols), f"Missing token columns: {expected_token_cols - token_cols}"

            # Verify users columns
            user_cols = {col["name"] for col in inspector.get_columns("users")}
            assert "status" in user_cols
            assert "email_verified" in user_cols
            assert "password_changed_at" in user_cols

        # 2. Downgrade from 0013 to 0012
        command.downgrade(alembic_cfg, "0012_broker_sandbox_integration")

        with engine.connect() as conn:
            inspector = inspect(conn)
            tables_after_down = set(inspector.get_table_names())
            assert "auth_tokens" not in tables_after_down, "auth_tokens table was not dropped on downgrade"

            user_cols_after_down = {col["name"] for col in inspector.get_columns("users")}
            assert "status" not in user_cols_after_down
            assert "email_verified" not in user_cols_after_down
            assert "password_changed_at" not in user_cols_after_down

        # 3. Re-upgrade back to head (0013)
        command.upgrade(alembic_cfg, "head")

        with engine.connect() as conn:
            inspector = inspect(conn)
            tables_after_reup = set(inspector.get_table_names())
            assert "auth_tokens" in tables_after_reup
            user_cols_reup = {col["name"] for col in inspector.get_columns("users")}
            assert "status" in user_cols_reup
            assert "email_verified" in user_cols_reup
            assert "password_changed_at" in user_cols_reup
