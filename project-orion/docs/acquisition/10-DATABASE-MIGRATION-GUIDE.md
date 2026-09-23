# Project ORION — Database Migration Guide & Schema Architecture

**Document Version:** 1.0.0
**Target Milestone:** EPIC-027 Phase 7B Acquisition Due Diligence
**Repository Working Copy:** `project-orion/`
**Classification:** Confidential — Due Diligence Technical Data Room (Tier 2 / NDA)
**Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Capital at Risk — Zero Live Broker Endpoints)

---

## 1. Executive Summary & Migration Architecture

Project ORION uses **Alembic** alongside **SQLAlchemy 2.0 (asyncio + asyncpg)** to manage its relational database schema across PostgreSQL (production/staging) and SQLite (in-memory unit testing).

All schema evolutions are managed as **linear, additive, version-controlled migration scripts** located in `database/migrations/versions/`. As of the current production release, the schema comprises **15 linear revisions** extending from initial account models up to onboarding state persistence.

### Key Architectural Invariants
1. **Single Linear Branch:** There are zero branched or diamond migration histories. Every revision has exactly one `down_revision`.
2. **Transactional DDL Execution:** PostgreSQL supports transactional DDL. Migrations run within a single transaction (`with context.begin_transaction():`). If any migration statement fails, the transaction rolls back completely, preventing half-applied schema drift.
3. **Decoupled Pre-Deployment Execution:** In cloud production (Render), migrations are decoupled from application process startup. Render executes `python scripts/deploy/migrate.py` via `preDeployCommand` in an ephemeral container prior to spinning up API containers.
4. **Additive Non-Destructive Policy:** Backward-incompatible table drops, column drops, or destructive type changes are strictly forbidden in production migrations.

---

## 2. Alembic Configuration & Directory Structure

```
project-orion/
├── alembic.ini                                # Central Alembic configuration file
├── scripts/
│   └── deploy/
│       └── migrate.py                         # Production CLI migration runner (EPIC-027 Phase 6B)
└── database/
    └── migrations/
        ├── env.py                             # Async engine configuration & metadata binding
        ├── script.py.mako                     # Migration file template
        └── versions/                          # Linear revision chain (0001 - 0015)
            ├── 0001_initial_schema.py
            ├── 0002_add_users_table.py
            ├── 0003_add_user_id_to_accounts.py
            ├── 0004_add_saas_multi_tenancy.py
            ├── 0005_add_organization_ownership.py
            ├── 0006_add_subscription_entitlements.py
            ├── 0007_organization_invitations.py
            ├── 0008_billing_foundation.py
            ├── 0009_research_experiments.py
            ├── 0010_optimization_jobs.py
            ├── 0011_deployment_pipeline.py
            ├── 0012_broker_sandbox_integration.py
            ├── 0013_auth_and_account_hardening.py
            ├── 0014_legal_acceptance.py
            └── 0015_onboarding_progress.py   # Canonical HEAD
```

---

## 3. Complete Revisions Catalog (0001 through 0015)

The table below catalogs the complete linear migration history from base to head:

| Rev ID | Revision Identifier | Down Revision | Milestone | Tables / Changes Introduced |
|:---:|---|---|---|---|
| **0001** | `0001_initial_schema` | *None (Base)* | Foundation | `accounts`, `orders`, `positions`, `trades`, `fills`, `candles`, `audit_logs` |
| **0002** | `0002_add_users_table` | `0001_initial_schema` | Auth Foundation | `users` table (username, email, hashed_password, is_active, is_superuser) |
| **0003** | `0003_add_user_id_to_accounts` | `0002_add_users_table` | Account Association | Adds foreign key `user_id` on `accounts` referencing `users.id` |
| **0004** | `0004_add_saas_multi_tenancy` | `0003_add_user_id_to_accounts` | EPIC-016 | `organizations`, `organization_members` tables; tenant scoping foundation |
| **0005** | `0005_add_organization_ownership`| `0004_add_saas_multi_tenancy` | EPIC-017 Phase 1 | Foreign key `organization_id` added across `accounts`, `orders`, `positions` |
| **0006** | `0006_subscription_entitlements`<br>*(File: `0006_add_subscription_entitlements.py`)* | `0005_add_organization_ownership`| EPIC-017 Phase 3 | `subscriptions`, `plans` tables; quota constraints (accounts, workers) |
| **0007** | `0007_organization_invitations` | `0006_add_subscription_entitlements`| EPIC-017 Phase 4 | `organization_invitations` table (invitation token, email, role, expiry) |
| **0008** | `0008_billing_foundation` | `0007_organization_invitations` | EPIC-019 | `billing_customers`, `billing_subscriptions`, `billing_invoices`, `billing_events` |
| **0009** | `0009_research_experiments` | `0008_billing_foundation` | EPIC-023 | `research_experiments` (backtest parameter storage, metrics, tear sheets) |
| **0010** | `0010_optimization_jobs` | `0009_research_experiments` | EPIC-024 | `optimization_jobs` (grid/random search, walk-forward windows, candidate rankings) |
| **0011** | `0011_deployment_pipeline` | `0010_optimization_jobs` | EPIC-025 | `strategy_deployments` (incubator paper deployment tracking, runtime health) |
| **0012** | `0012_broker_sandbox_integration`| `0011_deployment_pipeline` | EPIC-026 | `broker_sandbox_accounts`, `broker_reconciliation_snapshots` (OANDA v20 practice) |
| **0013** | `0013_auth_and_account_hardening`| `0012_broker_sandbox_integration`| EPIC-027 Phase 1 | `auth_tokens` table; `status`, `email_verified`, `password_changed_at` on `users` |
| **0014** | `0014_legal_acceptance` | `0013_auth_and_account_hardening`| EPIC-027 Phase 3 | `legal_acceptances` table (consent audit trail for Terms, Privacy, Risk disclosures) |
| **0015** | `0015_onboarding_progress` | `0014_legal_acceptance` | EPIC-027 Phase 5A | `onboarding_progress` table (**Current Head** — multi-step onboarding state machine) |

---

## 4. Upgrade Workflows

### 4.1 Local Development & CI
Developers run migrations using the Poetry CLI:
```bash
# Apply all pending migrations to head
poetry run alembic upgrade head

# Inspect current database revision
poetry run alembic current

# Inspect migration history
poetry run alembic history --verbose
```

### 4.2 Production Cloud Deployment (`scripts/deploy/migrate.py`)
In cloud environments, migrations are executed deterministically using the standalone runner:
```bash
# Check migration validity without executing (dry-run inspection)
python scripts/deploy/migrate.py --check-only

# Apply migrations to head with fail-fast exit
python scripts/deploy/migrate.py
```
If `migrate.py` encounters any error (e.g. database unreachable, schema lock timeout), it logs structured diagnostics and exits with code `1`. Render catches this non-zero exit code and immediately cancels the deploy, leaving existing live containers running safely on the previous version.

---

## 5. Migration Safety, Locking & Race Prevention

1. **Advisory Locking / Exclusive Transaction:** Alembic acquires PostgreSQL table-level locks when executing DDL (`ALTER TABLE`). Because all migrations execute within a single transaction block, concurrent application instances cannot read a partial schema state.
2. **Decoupled Architecture (Render `preDeployCommand`):** By executing `migrate.py` as a single-instance job before newly built application containers are launched, concurrent container startup races (multiple containers attempting `alembic upgrade` simultaneously) are eliminated.
3. **Zero Downtime Considerations:** Because all 15 migrations are strictly additive (adding new tables, adding nullable columns or columns with safe server defaults), existing application code can run concurrently against the database while migrations execute. However, heavy table alters on large production datasets may acquire exclusive locks; zero-downtime execution should be scheduled during low-traffic windows.

---

## 6. Backup Requirements & Disaster Recovery Relationship

A database backup must precede every production migration deployment.

### Pre-Deployment Backup Protocol
1. **Automated Render Snapshots:** Render Managed PostgreSQL performs daily automated snapshots.
2. **Explicit Logical Backup:** Run the verified backup script before triggering manual migrations:
   ```bash
   bash backup/database-backup.sh
   ```
3. **Restore Verification & Disaster Recovery Certification (EPIC-027 Phase 6C):**
   - The end-to-end physical restore procedure was executed and certified against an isolated PostgreSQL environment (`orion_dr_isolated`) on 2026-09-23 (see `docs/EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md`).
   - **Measured Physical Restore Duration:** **7 seconds** ($T_{start} = \text{2026-09-23T18:41:01+05:30}$, $T_{finish} = \text{2026-09-23T18:41:08+05:30}$).
   - **Operational RTO Target (SLA):** RTO < 60 minutes (SLA fully satisfied by the 7-second demonstrated execution).
   - **Operational RPO Target:** RPO < 24 hours (daily automated and pre-migration logical dumps).
   - If a migration fails irrecoverably, execute `backup/restore-database.sh <backup_file>` into a fresh staging database to verify data integrity before promoting to production.

---

## 7. Rollback Limitations

While all migration scripts include a `downgrade()` function, **downgrading in production is strongly discouraged**:
- Downgrades involving `op.drop_table()` or `op.drop_column()` cause permanent data loss for all records created while the new schema was active.
- Project ORION operates on a **"Forward-Fix"** policy: if a schema bug is discovered post-deployment, an additive patch migration (`0016_...`) is developed, reviewed, and deployed rather than executing a destructive downgrade.
