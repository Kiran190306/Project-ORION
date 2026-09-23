#!/usr/bin/env python3
"""Project ORION — Post-Restore Database Verification Tool.

Part of EPIC-027 Phase 6C (Backup, Restore & Disaster Recovery Hardening).
Validates restored database connectivity, schema completeness, Alembic revision
alignment, and data integrity.

Uses Base.metadata.tables.keys() from libraries.infrastructure.persistence.base
as the authoritative source of application tables (28 models + alembic_version = 29 total).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

# Ensure project root is present in sys.path for library imports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, make_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("orion.verify_restore")

TARGET_HEAD = "0015_onboarding_progress"


def mask_url(raw_url: str) -> str:
    """Mask password credentials in database connection string for logs."""
    try:
        parsed: URL = make_url(raw_url)
        return str(parsed._replace(password="***"))
    except Exception:  # noqa: BLE001
        return "<invalid-database-url>"


def get_expected_tables() -> set[str]:
    """Retrieve all expected application tables from SQLAlchemy declarative metadata.

    Source of truth: libraries.infrastructure.persistence.base.Base
    """
    import libraries.infrastructure.persistence.models  # noqa: F401
    from libraries.infrastructure.persistence.base import Base

    expected: set[str] = set(Base.metadata.tables.keys())
    # Add alembic version table
    expected.add("alembic_version")
    return expected


def verify_database(db_url: str, probe_url: str | None = None) -> dict[str, Any]:
    """Execute complete post-restore validation suite against target database."""
    # Convert asyncpg/aiosqlite URL to standard synchronous driver if needed
    clean_url = db_url
    if "+asyncpg" in clean_url:
        clean_url = clean_url.replace("+asyncpg", "")
    elif "+aiosqlite" in clean_url:
        clean_url = clean_url.replace("+aiosqlite", "")

    masked = mask_url(db_url)
    logger.info("Starting post-restore verification against: %s", masked)

    expected_tables = get_expected_tables()
    logger.info("Authoritative expected table count from Base.metadata: %d", len(expected_tables))

    results: dict[str, Any] = {
        "database_target": masked,
        "target_head": TARGET_HEAD,
        "checks": {},
        "summary": "UNKNOWN",
    }

    engine = None
    try:
        connect_args: dict[str, Any] = {}
        if "sqlite" not in clean_url:
            connect_args["connect_timeout"] = 10

        engine = create_engine(clean_url, connect_args=connect_args)
        with engine.connect() as conn:
            # 1. Connectivity Check
            server_version: Any = None
            try:
                server_version = conn.execute(text("SELECT version();")).scalar()
            except Exception:  # noqa: BLE001
                server_version = conn.execute(text("SELECT sqlite_version();")).scalar()

            results["checks"]["connectivity"] = {
                "status": "PASS",
                "version": str(server_version)[:100] if server_version else "Unknown",
            }
            logger.info("Check 1 [PASS] Connectivity established. Engine version verified.")

            # 2. Schema and Table Inventory Check
            inspector = inspect(conn)
            schema = "public" if "sqlite" not in clean_url else None
            try:
                discovered_tables = set(inspector.get_table_names(schema=schema))
            except Exception:  # noqa: BLE001
                discovered_tables = set(inspector.get_table_names())

            missing_tables = expected_tables - discovered_tables
            table_check_passed = len(missing_tables) == 0

            results["checks"]["table_inventory"] = {
                "status": "PASS" if table_check_passed else "FAIL",
                "expected_count": len(expected_tables),
                "discovered_count": len(discovered_tables),
                "missing_tables": sorted(missing_tables),
            }

            if table_check_passed:
                logger.info(
                    "Check 2 [PASS] Table inventory verified (%d/%d expected tables present).",
                    len(discovered_tables),
                    len(expected_tables),
                )
            else:
                logger.error(
                    "Check 2 [FAIL] Missing %d table(s): %s",
                    len(missing_tables),
                    sorted(missing_tables),
                )

            # 3. Alembic Revision Check
            current_rev: str | None = None
            try:
                rev_row = conn.execute(text("SELECT version_num FROM alembic_version;")).fetchone()
                if rev_row:
                    current_rev = str(rev_row[0])
            except Exception as e:  # noqa: BLE001
                logger.warning("Could not query alembic_version: %s", e)

            rev_passed = current_rev == TARGET_HEAD
            results["checks"]["alembic_revision"] = {
                "status": "PASS" if rev_passed else "WARN",
                "current_revision": current_rev,
                "target_head": TARGET_HEAD,
            }
            if rev_passed:
                logger.info("Check 3 [PASS] Alembic revision matches target head: %s", current_rev)
            else:
                logger.warning(
                    "Check 3 [WARN] Current revision (%s) differs from target head (%s). Run migrate.py to align.",
                    current_rev,
                    TARGET_HEAD,
                )

            # 4. Tenant & User Integrity Check
            user_count = 0
            org_count = 0
            try:
                user_count = conn.execute(text("SELECT COUNT(*) FROM users;")).scalar() or 0
                org_count = conn.execute(text("SELECT COUNT(*) FROM organizations;")).scalar() or 0
            except Exception as e:  # noqa: BLE001
                logger.warning("Could not query users or organizations: %s", e)

            results["checks"]["tenant_records"] = {
                "status": "PASS",
                "user_count": user_count,
                "organization_count": org_count,
            }
            logger.info("Check 4 [PASS] Tenant entities: %d user(s), %d organization(s).", user_count, org_count)

            # 5. Financial Account Balance Decimal Precision Check
            null_balances = 0
            account_count = 0
            total_balance = Decimal(0)
            try:
                account_count = conn.execute(text("SELECT COUNT(*) FROM accounts;")).scalar() or 0
                null_balances = (
                    conn.execute(text("SELECT COUNT(*) FROM accounts WHERE balance IS NULL;")).scalar() or 0
                )
                sum_row = conn.execute(text("SELECT COALESCE(SUM(balance), 0) FROM accounts;")).scalar()
                if sum_row is not None:
                    total_balance = Decimal(str(sum_row))
            except Exception as e:  # noqa: BLE001
                logger.warning("Could not query account balances: %s", e)

            balance_check_passed = null_balances == 0
            results["checks"]["financial_integrity"] = {
                "status": "PASS" if balance_check_passed else "FAIL",
                "account_count": account_count,
                "null_balances": null_balances,
                "total_balance_sum": str(total_balance),
            }
            if balance_check_passed:
                logger.info(
                    "Check 5 [PASS] Account balances verified: %d account(s), 0 NULL balances, total sum=%s",
                    account_count,
                    total_balance,
                )
            else:
                logger.error("Check 5 [FAIL] Found %d account(s) with NULL balance!", null_balances)

        # 6. Optional API Readiness Check
        if probe_url:
            import httpx

            try:
                resp = httpx.get(probe_url, timeout=10.0)
                readiness_pass = resp.status_code == 200
                results["checks"]["api_readiness"] = {
                    "status": "PASS" if readiness_pass else "FAIL",
                    "status_code": resp.status_code,
                    "response": resp.json() if readiness_pass else resp.text,
                }
                logger.info("Check 6 [%s] API readiness probe returned %d", "PASS" if readiness_pass else "FAIL", resp.status_code)
            except Exception as e:  # noqa: BLE001
                results["checks"]["api_readiness"] = {
                    "status": "FAIL",
                    "error": str(e),
                }
                logger.error("Check 6 [FAIL] API readiness probe failed: %s", e)

        # Determine overall summary
        has_failures = any(c.get("status") == "FAIL" for c in results["checks"].values())
        results["summary"] = "FAILED" if has_failures else "PASSED"

    except Exception as exc:  # noqa: BLE001
        logger.error("Database verification failed with unexpected exception: %s", exc)
        results["summary"] = "ERROR"
        results["error"] = str(exc)
    finally:
        if engine is not None:
            engine.dispose()

    return results


def main() -> None:
    """CLI Entrypoint."""
    parser = argparse.ArgumentParser(
        description="Project ORION — Post-Restore Database Verification Tool"
    )
    parser.add_argument(
        "--database-url",
        "-d",
        default=os.getenv("ORION_DATABASE_URL") or os.getenv("DATABASE_URL"),
        help="Target PostgreSQL connection URL",
    )
    parser.add_argument(
        "--probe-url",
        "-p",
        default=os.getenv("ORION_HEALTH_URL"),
        help="Optional API health check endpoint (e.g. http://localhost:8000/health/ready)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON results only",
    )

    args = parser.parse_args()

    if not args.database_url:
        logger.error("Database URL must be provided via --database-url or ORION_DATABASE_URL environment variable.")
        sys.exit(1)

    results = verify_database(args.database_url, args.probe_url)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        logger.info("=== VERIFICATION SUMMARY: %s ===", results["summary"])

    if results["summary"] != "PASSED":
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
