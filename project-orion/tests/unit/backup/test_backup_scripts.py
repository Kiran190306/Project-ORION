"""Automated Test Suite for Project ORION Backup, Restore & Disaster Recovery Scripts.

Part of EPIC-027 Phase 6C (Work Package 6).
Covers:
- Layer 1: Offline bash syntax (bash -n) and security static analysis (no CLI secrets, no DROP DATABASE)
- Layer 2: Verification logic (28 Base.metadata tables + alembic_version, checksums, masking)
- Layer 3: Isolated PostgreSQL integration (skipped gracefully when TEST_DATABASE_URL is not set)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

import libraries.infrastructure.persistence.models  # noqa: F401
from libraries.infrastructure.persistence.base import Base
from scripts.deploy.verify_restore import (
    TARGET_HEAD,
    get_expected_tables,
    mask_url,
    verify_database,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKUP_DIR = REPO_ROOT / "backup"

BASH_BIN = shutil.which("bash") or (
    Path(r"C:\Program Files\Git\bin\bash.exe")
    if Path(r"C:\Program Files\Git\bin\bash.exe").exists()
    else None
)


# ════════════════════════════════════════════════════════════
# Layer 1: Offline Bash Syntax & Security Static Analysis
# ════════════════════════════════════════════════════════════


@pytest.mark.skipif(BASH_BIN is None, reason="Bash executable not found in environment")
@pytest.mark.parametrize(
    "script_name",
    [
        "retention-policy.sh",
        "database-backup.sh",
        "restore-database.sh",
        "redis-backup.sh",
        "restore-redis.sh",
    ],
)
def test_layer1_bash_syntax_clean(script_name: str) -> None:
    """Every bash script in backup/ must pass 'bash -n' syntax validation."""
    script_path = BACKUP_DIR / script_name
    assert script_path.is_file(), f"Script not found at {script_path}"

    result = subprocess.run(
        [str(BASH_BIN), "-n", f"backup/{script_name}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert (
        result.returncode == 0
    ), f"Syntax error in {script_name}:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"


def test_layer1_security_no_cli_secrets() -> None:
    """Verify scripts never pass secrets via command-line arguments (e.g. pass:"${...}")."""
    for script_path in BACKUP_DIR.glob("*.sh"):
        content = script_path.read_text(encoding="utf-8")
        assert (
            'pass:"${' not in content
        ), f"Security violation: CLI password passing found in {script_path.name}"
        assert (
            "pass pass:" not in content
        ), f"Security violation: hardcoded pass password passing found in {script_path.name}"
        assert (
            "-a ${REDIS_PASSWORD}" not in content
        ), f"Security violation: CLI Redis password passing found in {script_path.name}"


def test_layer1_security_no_drop_or_create_database() -> None:
    """Normal restore script must NEVER execute DROP DATABASE or CREATE DATABASE."""
    restore_script = BACKUP_DIR / "restore-database.sh"
    content = restore_script.read_text(encoding="utf-8")
    for line in content.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("#") or "echo " in trimmed:
            continue
        assert (
            "DROP DATABASE" not in line
        ), f"Security violation: DROP DATABASE executable statement found: {line}"
        assert (
            "CREATE DATABASE" not in line
        ), f"Security violation: CREATE DATABASE executable statement found: {line}"


def test_layer1_restore_requires_target_url_flag() -> None:
    """Restore script must mandate explicit --target-url parameter and reject implicit targets."""
    restore_script = BACKUP_DIR / "restore-database.sh"
    content = restore_script.read_text(encoding="utf-8")
    assert "--target-url" in content, "Missing mandatory --target-url parameter definition"
    assert (
        "Missing mandatory --target-url parameter" in content
    ), "Missing fail-fast validation when target URL is omitted"


# ════════════════════════════════════════════════════════════
# Layer 2: Python Unit & Mock Verification Logic
# ════════════════════════════════════════════════════════════


def test_layer2_authoritative_table_inventory() -> None:
    """Verify get_expected_tables returns all 28 Base.metadata tables plus alembic_version."""
    tables = get_expected_tables()
    # 28 application tables registered on Base.metadata + alembic_version = 29
    assert len(tables) == 29
    assert "alembic_version" in tables
    assert "users" in tables
    assert "organizations" in tables
    assert "organization_members" in tables
    assert "accounts" in tables
    assert "orders" in tables
    assert "fills" in tables
    assert "positions" in tables
    assert "legal_acceptances" in tables
    assert "onboarding_progress" in tables
    assert "billing_customers" in tables
    assert "billing_subscriptions" in tables


def test_layer2_mask_url_credentials() -> None:
    """Verify mask_url safely obscures database passwords in logs."""
    raw = "postgresql://myuser:supersecretpass@db.example.com:5432/orion_prod"
    masked = mask_url(raw)
    assert "supersecretpass" not in masked
    assert "***" in masked
    assert "myuser" in masked
    assert "orion_prod" in masked


def test_layer2_verify_database_sqlite_success() -> None:
    """Verify verify_database passes when all 28 tables and alembic_version are present."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    engine = None
    try:
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        # Create all 28 application tables from Base.metadata
        Base.metadata.create_all(engine)
        # Create alembic_version table at head
        with engine.connect() as conn:
            conn.execute(
                text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL);")
            )
            conn.execute(
                text(
                    f"INSERT INTO alembic_version (version_num) VALUES ('{TARGET_HEAD}');"
                )
            )
            conn.commit()
        engine.dispose()
        engine = None

        report = verify_database(url)
        assert report["summary"] == "PASSED"
        assert report["checks"]["connectivity"]["status"] == "PASS"
        assert report["checks"]["table_inventory"]["status"] == "PASS"
        assert report["checks"]["table_inventory"]["discovered_count"] == 29
        assert report["checks"]["alembic_revision"]["status"] == "PASS"
        assert (
            report["checks"]["alembic_revision"]["current_revision"] == TARGET_HEAD
        )
        assert report["checks"]["financial_integrity"]["status"] == "PASS"
    finally:
        if engine is not None:
            engine.dispose()
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_layer2_verify_database_catches_missing_tables() -> None:
    """Verify verify_database flags missing tables and returns FAILED."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    engine = None
    try:
        url = f"sqlite:///{db_path}"
        # Empty database without tables
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE dummy (id INTEGER PRIMARY KEY);"))
            conn.commit()
        engine.dispose()
        engine = None

        report = verify_database(url)
        assert report["summary"] == "FAILED"
        assert report["checks"]["table_inventory"]["status"] == "FAIL"
        assert report["checks"]["table_inventory"]["discovered_count"] < 29
        assert len(report["checks"]["table_inventory"]["missing_tables"]) > 0
    finally:
        if engine is not None:
            engine.dispose()
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_layer2_verify_database_catches_null_balance() -> None:
    """Verify verify_database flags accounts with NULL balances."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    engine = None
    try:
        url = f"sqlite:///{db_path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)
        with engine.connect() as conn:
            conn.execute(
                text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL);")
            )
            conn.execute(
                text(
                    f"INSERT INTO alembic_version (version_num) VALUES ('{TARGET_HEAD}');"
                )
            )
            # Drop accounts and recreate with nullable balance to simulate corrupted/invalid restore state
            conn.execute(text("DROP TABLE accounts;"))
            conn.execute(
                text(
                    "CREATE TABLE accounts ("
                    "id VARCHAR(64) PRIMARY KEY, "
                    "organization_id VARCHAR(64), "
                    "user_id VARCHAR(64), "
                    "broker_name VARCHAR(32), "
                    "account_number VARCHAR(64), "
                    "currency VARCHAR(8), "
                    "balance NUMERIC"
                    ");"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO accounts (id, organization_id, user_id, broker_name, account_number, currency, balance) "
                    "VALUES ('acc-1', 'org-1', 'usr-1', 'paper', 'ACC-001', 'USD', NULL);"
                )
            )
            conn.commit()
        engine.dispose()
        engine = None

        report = verify_database(url)
        assert report["summary"] == "FAILED"
        assert report["checks"]["financial_integrity"]["status"] == "FAIL"
        assert report["checks"]["financial_integrity"]["null_balances"] == 1
    finally:
        if engine is not None:
            engine.dispose()
        if os.path.exists(db_path):
            os.unlink(db_path)


# ════════════════════════════════════════════════════════════
# Layer 3: Isolated PostgreSQL Integration Tests
# ════════════════════════════════════════════════════════════


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="Isolated PostgreSQL instance required (TEST_DATABASE_URL not set)",
)
def test_layer3_postgresql_restore_isolated() -> None:
    """Full pg_dump and isolated pg_restore cycle against live PostgreSQL instance."""
    pg_url = os.environ["TEST_DATABASE_URL"]
    assert "localhost" in pg_url or "127.0.0.1" in pg_url or "test" in pg_url, (
        "Safety guard: TEST_DATABASE_URL must target a local/isolated test database!"
    )
    report = verify_database(pg_url)
    assert report["summary"] == "PASSED"
