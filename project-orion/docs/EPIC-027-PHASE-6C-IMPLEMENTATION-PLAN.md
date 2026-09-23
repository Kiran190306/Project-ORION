# EPIC-027 PHASE 6C — BACKUP, RESTORE & DISASTER RECOVERY IMPLEMENTATION PLAN

**Phase:** EPIC-027 Phase 6C — Backup, Restore & Disaster Recovery Hardening  
**Repository:** `Project-ORION` (`c:\Users\Shree\CascadeProjects\forex-trading-platform-architecture\project-orion`)  
**Git Baseline:** `3ff486e` (`feat(deploy): harden cloud deployment and migration safety`)  
**Audit Reference:** [`docs/EPIC-027-PHASE-6C-AUDIT.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture\project-orion\docs\EPIC-027-PHASE-6C-AUDIT.md)  
**Plan Date:** 2026-09-23  
**Plan Author:** Principal Site Reliability Engineer (SRE) & Lead Database Solutions Architect  
**Safety Invariant:** **$0.00 CAPITAL AT RISK** (Paper execution only, `broker_name="paper"`, `is_paper=True`, `ORION_WORKER_ENABLED="false"`, live trading endpoints blocked)  
**Plan Classification:** `B — IMPLEMENTATION READY WITH EXTERNAL DEPENDENCIES`  

---

## 1. Executive Summary & Design Principles

This implementation plan establishes the architectural corrections and technical work packages required to resolve all blockers identified in [`docs/EPIC-027-PHASE-6C-AUDIT.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture\project-orion\docs\EPIC-027-PHASE-6C-AUDIT.md).

### Core Design Principles:
1. **Managed Cloud PaaS Alignment:** All database backup and restoration workflows must operate cleanly under unprivileged user contexts (`user: orion`) on managed cloud databases (such as Render PostgreSQL), without assuming superuser rights, access to maintenance databases (`postgres`), or destructive `DROP DATABASE` / `CREATE DATABASE` commands.
2. **Zero-Destruction Restore Isolation:** Restorations must never drop or overwrite an active database without prior validation in an isolated target environment.
3. **Cryptographic & Archive Integrity:** Every backup artifact must generate an immutable SHA-256 checksum sidecar (`.sha256`) and pass Table-of-Contents archive verification (`pg_restore --list`) before upload or storage.
4. **Zero Process-Table Secret Exposure:** Passwords and encryption keys must never appear in command-line arguments or process listings (`ps -ef`). Tool-native secure mechanisms (`PGPASSWORD`, `pass:env:VAR`, stdin) must be used exclusively.
5. **Architectural Truthfulness Regarding Redis:** Acknowledge repository evidence that Redis is strictly an ephemeral cache and message bus carrying $0.00 persistent financial state. Host-dependent filesystem copying is formally deprecated in favor of fast container restart and cache re-population.
6. **Strict Preservation of Institutional Safety Invariants:** All operations must preserve paper-only execution, zero capital at risk, disabled autonomous worker loops, and fail-closed endpoint validations.

---

## 2. Source-of-Truth & Audit Alignment

This plan derives strictly from [`docs/EPIC-027-PHASE-6C-AUDIT.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture\project-orion\docs\EPIC-027-PHASE-6C-AUDIT.md). The six mandatory audit blockers are mapped directly to implementation work packages:

| Audit Blocker ID | Description | Impact | Target Work Package |
|---|---|---|---|
| **BLK-6C-01** | `retention-policy.sh` syntax corruption | Unexecutable script | **Work Package 1** (Script Remediation) |
| **BLK-6C-02** | Destructive / incompatible `restore-database.sh` | Incompatible with cloud PaaS; destructive | **Work Package 2** (Safe Restore Architecture) |
| **BLK-6C-03** | Invalid `pg_dump -Fc -j 4` | Dump fails immediately | **Work Package 1** (Script Remediation) |
| **BLK-6C-04** | Missing checksum verification | Corrupted archives undetected | **Work Package 1 & 2** (Integrity & Validation) |
| **BLK-6C-05** | Restore never demonstrated | Unproven recovery capability | **Work Package 7** (Isolated Demonstration) |
| **BLK-6C-06** | Redis host-filesystem backup architecture | Fails on managed cloud Redis | **Work Package 4** (Redis Architecture) |

---

## 3. Work Package 1: Script Remediation & Modernization

### 3.1 `backup/retention-policy.sh` Remediation (Resolves BLK-6C-01)
- **Problem:** Lines 33–56 contain accidental LLM tool prompt text (`local removedNow creating all remaining scripts and documentation files: \n <create_file> ...`).
- **Design Correction:**
  1. Purge all corrupted tool text and invalid tokens.
  2. Implement strict shell header: `#!/usr/bin/env bash`, `set -euo pipefail`.
  3. Define error trap handler (`trap 'cleanup_on_error' ERR`) to report failure and exit cleanly.
  4. Implement deterministic local pruning logic:
     - Match `orion-db-full-*.dump*` files.
     - Respect `RETENTION_DAYS_FULL` (default: 7 days).
     - Prune empty directories safely.
     - Log count of files examined, deleted, and retained with timestamps.
  5. Provide explicit dry-run mode (`--dry-run` or `-n`) so operators can inspect candidates before deletion.

### 3.2 `backup/database-backup.sh` Remediation (Resolves BLK-6C-03, BLK-6C-04)
- **Problem 1 (Invalid CLI Combination):** Line 43 specifies `pg_dump -Fc -j 4`. In PostgreSQL, parallel jobs (`-j`) require directory format (`-F d`).
- **Correction 1:** Remove `-j 4`. Use standard custom single-file archive format:
  ```bash
  pg_dump -Fc -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    --no-owner --no-privileges -f "${filepath}"
  ```
  *(Custom single-file format `-Fc` is portable, internally zlib-compressed, supports table-level selective restoration, and requires no parallel multi-file directory handling).*
- **Problem 2 (Redundant Compression):** Line 45 runs `gzip -9` on an already-compressed `-Fc` dump.
- **Correction 2:** Eliminate redundant `gzip` step. The `.dump` file produced by `pg_dump -Fc` is already compressed.
- **Problem 3 (Process-Table Secret Exposure):** Line 50 passes `pass:"${ENCRYPTION_KEY}"` on the command line.
- **Correction 3:** Use OpenSSL environment variable source:
  ```bash
  openssl enc -aes-256-cbc -salt -pbkdf2 -in "${filepath}" \
    -out "${filepath}.enc" -pass env:BACKUP_ENCRYPTION_KEY
  ```
- **Problem 4 (Missing Checksums):** No hash is produced.
- **Correction 4:** Generate an immutable SHA-256 checksum sidecar immediately after dump creation:
  ```bash
  sha256sum "${artifact_file}" > "${artifact_file}.sha256"
  ```
- **Problem 5 (Missing Archive TOC Verification):**
  Validate archive table of contents before certifying success:
  ```bash
  pg_restore -l "${filepath}" > /dev/null
  ```
- **Problem 6 (Incremental False Claim):** Remove unsupported incremental claims; explicitly document that full logical dumps are generated.

---

## 4. Work Package 2: Safe Database Restore Architecture (Resolves BLK-6C-02)

### 4.1 Comparative Evaluation of Restore Architectures

To eliminate destructive operations (`DROP DATABASE` / `CREATE DATABASE`) and avoid superuser requirements, two restore paradigms are compared:

| Architectural Metric | Approach A: Isolated Target Database (`RESTORE_DATABASE_URL`) | Approach B: Schema-Level Reset (`DROP SCHEMA public CASCADE`) |
|---|---|---|
| **Privileges Required** | Standard DB owner on target instance (Zero superuser) | Standard DB owner on existing database |
| **Blast Radius** | **ZERO to Production** (Operates in isolated target) | **CRITICAL to Production** (Destroys active schema immediately) |
| **Isolation Level** | **Complete** (Separate database instance or port) | None (Modifies live production database) |
| **Destructive Behavior** | Non-destructive to live data | Highly destructive (Drops all live tables and constraints) |
| **Compatibility with Managed PaaS** | **100% Compatible** (Standard connection string to new DB) | **Compatible with caveats** (Must own `public` schema) |
| **Operational Complexity** | Medium (Requires provisioning target DB or test container) | Low (Single command against current DB) |
| **Testability in Staging/CI** | **High** (Easily spun up in CI or local Docker) | Low (Risks accidental wipe of staging state) |
| **Rollback Characteristics** | **Instantaneous** (Active DB remains untouched; traffic not shifted if restore fails) | **Zero Rollback** (If restore fails, active schema is already dropped) |
| **Suitability for Production DR** | **HIGHLY RECOMMENDED** (Primary Disaster Recovery Strategy) | **EMERGENCY LAST-RESORT ONLY** (Not default path) |

### 4.2 Selected Primary Architecture: Isolated Target Restoration (Approach A)

In strict accordance with cloud PaaS constraints and non-negotiable safety:
1. **Primary Production DR Workflow:** **Approach A (Isolated Target Database)**.
   - The operator provisions a fresh PostgreSQL instance (e.g. via Render Blueprint or Web Console).
   - The restore script accepts `TARGET_DATABASE_URL` (or `RESTORE_DATABASE_URL`).
   - The restore script verifies that `TARGET_DATABASE_URL` is healthy.
   - The restore executes cleanly into the target database without dropping databases or touching active traffic.
   - Once validated (Work Package 3), the operator shifts application traffic by updating `ORION_DATABASE_URL` and restarting `orion-api`.
2. **Controlled In-Place Restoration (Approach B) — Emergency Only:**
   - If an operator explicitly mandates in-place restoration against an existing database, the script must require an explicit confirmation flag (`--force-in-place-schema-reset`).
   - Instead of `DROP DATABASE`, the script executes schema-level reset:
     ```sql
     DROP SCHEMA public CASCADE;
     CREATE SCHEMA public;
     GRANT ALL ON SCHEMA public TO orion;
     ```
   - Before executing the drop, the script **must verify** the backup archive's SHA-256 checksum and TOC readability (`pg_restore -l`). If validation fails, the script aborts immediately with zero modifications to the schema.

### 4.3 Script Redesign: `backup/restore-database.sh`
- Accepts arguments: `<backup-artifact> [--target-url <url>] [--force-in-place]`
- Validates SHA-256 checksum against `.sha256` sidecar file before touching any database.
- Decrypts via `pass env:BACKUP_ENCRYPTION_KEY` (no CLI key exposure).
- Verifies archive table of contents (`pg_restore -l`).
- Restores cleanly using:
  ```bash
  pg_restore -d "${TARGET_URL}" --clean --if-exists --no-owner --no-privileges "${restore_path}"
  ```
- Executes post-restore schema alignment and semantic integrity checks (Work Package 3).

---

## 5. Work Package 3: Post-Restore Validation Pipeline

Restoration is not complete until the restored schema and data are deterministically verified.

### 5.1 Deterministic Validation Pipeline
```
[ RESTORE EXECUTION FINISHED ]
              │
              ▼
1. Connectivity & Engine Probe
   ├─► Verify TCP connection and PostgreSQL version
   └─► Assert `pg_isready` returns 0
              │
              ▼
2. Alembic Migration Head Alignment
   ├─► Query `SELECT version_num FROM alembic_version;`
   ├─► Compare restored version to codebase target head (`0015_onboarding_progress`)
   └─► If restored version < 0015: Execute `python scripts/deploy/migrate.py`
              │
              ▼
3. Table Inventory Verification
   ├─► Verify presence of all 15 core tables:
   │   `users`, `organizations`, `organization_memberships`, `organization_invitations`,
   │   `accounts`, `orders`, `fills`, `positions`, `strategies`, `optimization_jobs`,
   │   `audit_logs`, `legal_acceptances`, `onboarding_progress`, `broker_configs`, `subscriptions`
              │
              ▼
4. Semantic Data Integrity Checks
   ├─► User & Org Integrity: `SELECT COUNT(*) FROM users;` (Assert count > 0)
   ├─► Balance Decimal Precision: `SELECT COUNT(*) FROM accounts WHERE balance IS NULL;` (Assert 0)
   ├─► Tenant Isolation Sanity: Verify foreign keys connect valid users to organizations
   ├─► Audit Trail Continuity: Verify `MAX(created_at)` from `audit_logs`
   └─► Onboarding State: Verify `onboarding_progress` records exist and are intact
              │
              ▼
5. Application API Readiness Probe
   ├─► Test application connectivity via `/health/ready`
   └─► Assert `{"overall":"healthy","database":true,"redis":true}`
```

### 5.2 Implementation Deliverable
Create a standalone verification tool [`scripts/deploy/verify_restore.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture\project-orion\scripts\deploy\verify_restore.py) that implements these exact checks with structured JSON logging and clear pass/fail exit codes.

---

## 6. Work Package 4: Redis Architecture Realignment (Resolves BLK-6C-06)

### 6.1 Repository Evidence & Architectural Truth
1. Redis is configured in `render.yaml` as `plan: free` (in-memory only, 25MB RAM, private network).
2. Codebase analysis confirms Redis is utilized exclusively for:
   - Rate limiting sliding-window counters (`RateLimitService` with fallback to `InMemoryRateLimiter`).
   - Real-time tick caching and quote distribution (`MarketDataCache`).
   - Order execution distributed mutual exclusion locks.
3. Redis stores **zero persistent financial state**. All balances, accounts, orders, trades, and tenant models are stored in PostgreSQL.
4. Loss or flush of Redis results in momentary rate-limiter reset and cache warming, with **zero capital at risk and zero financial data loss**.

### 6.2 Treatment of Redis Backup Scripts
- `backup/redis-backup.sh` and `backup/restore-redis.sh` rely on `CONFIG GET dir`, host `cp` on `/var/lib/redis`, and `SHUTDOWN NOSAVE`. These commands are fundamentally invalid on cloud PaaS / managed Redis.
- **Action:**
  1. Formally **deprecate** host-filesystem copying in `backup/redis-backup.sh` and `backup/restore-redis.sh`.
  2. Retain them with clear header documentation: `DEPRECATED FOR MANAGED CLOUD — LOCAL STANDALONE DOCKER ONLY`.
  3. Document the cloud Redis disaster recovery procedure:
     - On Redis failure or corruption, restart the Redis container via Render Web Console or CLI (`render services restart orion-redis`).
     - Project ORION's API services automatically reconnect and re-warm caches.

---

## 7. Work Package 5: Object Storage & Remote Backup Destination

### 7.1 Separation of Concerns: Local vs Cloud

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 REPOSITORY-VERIFIED vs EXTERNAL DEPENDENCY                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  REPOSITORY-VERIFIED (In Scope for Local Testing & CI):                     │
│  ├─ Deterministic dump creation in local staging directory                 │
│  ├─ Local SHA-256 sidecar generation and verification                      │
│  ├─ OpenSSL AES-256-CBC encryption using `pass:env:KEY`                    │
│  └─ Archive Table-of-Contents validation via `pg_restore -l`               │
├─────────────────────────────────────────────────────────────────────────────┤
│  EXTERNAL PROVIDER DEPENDENCY (Requires Cloud Infrastructure):              │
│  ├─ AWS S3 or Cloudflare R2 bucket provisioning (`orion-backups`)          │
│  ├─ IAM least-privilege credentials (`PutObject`, `GetObject`, `ListBucket`)│
│  ├─ Server-side encryption (`--sse AES256`)                                │
│  └─ S3 Lifecycle Rules (Prune daily > 30d, weekly > 90d, monthly > 365d)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Offsite Replication Protocol
1. **Remote Destination CLI Independence:** To avoid bundling heavy AWS CLI tooling into the production Docker runtime, offsite replication should support either:
   - Python-based upload script using standard HTTP / lightweight S3 SDK (`boto3` or `httpx` S3 presigned URLs).
   - Or execution via a dedicated Render Cron Job container configured with `awscli`.
2. **Object Key Hierarchy:**
   ```text
   s3://${BACKUP_S3_BUCKET}/database/YYYY-MM-DD/orion-db-full-YYYYMMDD_HHMMSS.dump.enc
   s3://${BACKUP_S3_BUCKET}/database/YYYY-MM-DD/orion-db-full-YYYYMMDD_HHMMSS.dump.enc.sha256
   ```
3. **Upload Integrity:** The SHA-256 checksum sidecar must be uploaded alongside the archive.

---

## 8. Work Package 6: Automated Testing Suite

To eliminate the "Zero Test Coverage" audit finding, a dedicated test suite must be implemented:

### 8.1 Automated Test Specifications
1. **`test_backup_script_syntax.py`:**
   - Executes `bash -n` on all scripts in `backup/`.
   - Asserts exit code 0 and zero syntax errors across all scripts.
2. **`test_backup_creation_and_integrity.py`:**
   - Mocks/provisions a temporary test PostgreSQL or SQLite database.
   - Executes backup script logic.
   - Asserts valid dump artifact is created.
   - Asserts `.sha256` sidecar exists and matches `sha256sum`.
   - Asserts `pg_restore -l` validates archive table of contents.
3. **`test_restore_isolated_pipeline.py`:**
   - Generates test backup artifact.
   - Executes restore logic against isolated target.
   - Asserts database schema matches Alembic head `0015_onboarding_progress`.
   - Asserts test tenant and user records are fully restored.
4. **`test_security_secret_exposure.py`:**
   - Runs mock backup/restore commands.
   - Inspects `/proc` or mocked argument strings to ensure zero passwords or encryption keys were passed via CLI flags.

---

## 9. Work Package 7: Isolated Restore Demonstration Protocol (Resolves BLK-6C-05)

To transition restore capability from **`NOT DEMONSTRATED`** to **`DEMONSTRATED`**, an evidence-producing restore protocol must be executed:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 ISOLATED RESTORE DEMONSTRATION WORKFLOW                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  Step 1: Source Database Seeding                                            │
│  ├─ Seed temporary database with users, orgs, accounts, and onboarding data │
│  └─ Capture baseline row counts and table inventory                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  Step 2: Backup Creation & Cryptographic Sealing                            │
│  ├─ Execute `backup/database-backup.sh`                                     │
│  ├─ Generate `orion-db-full-<TIMESTAMP>.dump`                               │
│  ├─ Compute SHA-256 checksum: `orion-db-full-<TIMESTAMP>.dump.sha256`      │
│  └─ Verify archive TOC: `pg_restore -l` -> 0                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Step 3: Isolated Target Preparation                                        │
│  ├─ Target clean database instance (isolated port / container / URL)       │
│  └─ Confirm live source database is disconnected / protected                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Step 4: Restore Execution                                                  │
│  ├─ Validate SHA-256 checksum prior to restoration                          │
│  ├─ Execute `backup/restore-database.sh --target-url <ISOLATED_URL>`         │
│  └─ Assert restore exits with code 0                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Step 5: Schema & Semantic Validation                                       │
│  ├─ Execute `verify_restore.py`                                             │
│  ├─ Assert `alembic_version` == `0015_onboarding_progress`                  │
│  ├─ Assert row counts match Step 1 baseline exactly                         │
│  └─ Probe `/health/ready` -> 200 OK                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  Step 6: Evidence Recording & Cleanup                                       │
│  ├─ Record command outputs, SHA-256 hashes, and execution logs              │
│  ├─ Publish report: `docs/EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md`       │
│  └─ Teardown temporary isolated database and scratch files                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Work Package 8: RPO & RTO Realism & Harmonization

### 10.1 Authoritative Standard Definition
- **Production Target RPO:** **`< 24 Hours`**  
  *(Governed by daily automated Render snapshots and daily logical dumps).*
- **Production Target RTO:** **`< 60 Minutes`**  
  *(Governed by target database provisioning, logical restore execution, and schema verification).*
- **Current Actual RTO:** **`INDETERMINATE`** until the isolated restore demonstration (Work Package 7) is executed and timed.

### 10.2 Documentation Harmonization Plan
- Update [`docs/operations/disaster-recovery-guide.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture\project-orion\docs\operations\disaster-recovery-guide.md) to:
  1. Remove fictional 5-minute RPO claims that assume continuous WAL archiving.
  2. Replace legacy Kubernetes (`kubectl`, Helm) commands with accurate Render Cloud procedures.
  3. Align with [`docs/EPIC-018-BACKUP-RECOVERY.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture\project-orion\docs\EPIC-018-BACKUP-RECOVERY.md).

---

## 11. Work Package 9: Security & Secret Hardening

1. **Eliminate Command-Line Secrets:**
   - Prohibit `-pass pass:"${SECRET}"`. Use `pass:env:BACKUP_ENCRYPTION_KEY`.
   - Prohibit `redis-cli -a "${REDIS_PASSWORD}"`. Use `REDISCLI_AUTH="${REDIS_PASSWORD}"` environment variable.
   - Use `PGPASSWORD` exported inside subshell or standard `.pgpass` file.
2. **File Permissions:**
   - Ensure all dump artifacts in `/var/backups/orion` or temporary folders are created with restrictive permissions (`chmod 0600`).
   - Ensure backup logs do not log decrypted database connection URLs or authorization headers.
3. **Least Privilege:**
   - Database restore operations must require only standard object privileges on the target schema, with zero superuser access.

---

## 12. Work Package 10: Operational Runbooks

The operational documentation will be organized into two distinct, step-by-step procedures:

### Runbook A: Routine Scheduled Backup Operations
- Triggering manual on-demand logical dumps.
- Validating backup directory size and SHA-256 sidecars.
- Applying retention policy pruning (`retention-policy.sh`).
- Verifying Render daily snapshot status via Render Web Console.

### Runbook B: Disaster Recovery & Emergency Restore
1. **Incident Declaration & Traffic Containment:** Suspend API traffic via Render Dashboard or CLI (`render services suspend orion-api`).
2. **Target Database Provisioning:** Provision replacement PostgreSQL instance on Render (`orion-postgres-dr`).
3. **Archive Retrieval & Integrity Verification:** Fetch latest backup dump and verify SHA-256 checksum.
4. **Execution:** Run `restore-database.sh` pointing to the new database URL.
5. **Schema Alignment:** Run `python scripts/deploy/migrate.py` to ensure schema is at `0015_onboarding_progress`.
6. **Data Validation:** Execute `verify_restore.py` and confirm zero anomalies.
7. **Traffic Resumption:** Update `ORION_DATABASE_URL` on `orion-api` and restart the service.
8. **Post-Recovery Verification:** Probe `/health/ready` and confirm normal dashboard operation.

---

## 13. File-Level Implementation Plan

| Target File | Proposed Modification | Justification | Risk | Test Strategy | Acceptance Criterion |
|---|---|---|---|---|---|
| [`backup/retention-policy.sh`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture\project-orion\backup\retention-policy.sh) | Remove corrupted prompt text; implement clean retention logic with dry-run support | Fixes BLK-6C-01 | Low | `bash -n` & dry-run test | Script parses with exit code 0; safely prunes files older than retention |
| [`backup/database-backup.sh`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture\project-orion\backup\database-backup.sh) | Remove `-j 4`, remove redundant gzip, use `pass:env`, generate `.sha256`, add `pg_restore -l` | Fixes BLK-6C-03, BLK-6C-04 | Medium | Mock execution against local PostgreSQL | Generates valid `.dump` and `.sha256`; TOC check passes; no CLI secrets |
| [`backup/restore-database.sh`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture\project-orion\backup\restore-database.sh) | Remove `DROP DATABASE` / `CREATE DATABASE`; support `--target-url`; verify checksum; invoke validation | Fixes BLK-6C-02 | Medium | Restoration into isolated target DB | Restores without superuser; verifies checksum & Alembic head; non-destructive |
| [`scripts/deploy/verify_restore.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture\project-orion\scripts\deploy\verify_restore.py) | **[NEW]** Standalone Python validation tool for restored databases | Implements Work Package 3 | Low | Unit tests with mock DB | Emits structured JSON; validates tables, counts, balances, and Alembic head |
| [`backup/redis-backup.sh`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture\project-orion\backup\redis-backup.sh) | Deprecate host filesystem copy; document Redis ephemerality | Fixes BLK-6C-06 | Low | Review docs | Clear deprecation notice for cloud PaaS |
| [`backup/restore-redis.sh`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture\project-orion\backup\restore-redis.sh) | Deprecate host filesystem copy; document Redis recovery procedure | Fixes BLK-6C-06 | Low | Review docs | Clear recovery runbook via container restart |
| [`docs/operations/disaster-recovery-guide.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture\project-orion\docs\operations\disaster-recovery-guide.md) | Harmonize RPO/RTO standards; replace K8s references with Render Cloud runbooks | Implements Work Package 8 | Low | Markdown lint | RPO < 24h, RTO < 60m; accurate Render procedures |
| [`tests/unit/backup/test_backup_scripts.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture\project-orion\tests\unit\backup\test_backup_scripts.py) | **[NEW]** Automated pytest suite for script syntax, checksums, and validation | Implements Work Package 6 | Low | `poetry run pytest` | 100% tests pass; covers syntax, checksum, and verification |
| [`docs/EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture\project-orion\docs\EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md) | **[NEW]** Formal certification report of isolated restore demonstration | Fixes BLK-6C-05 | Low | Review evidence | Documents all 9 criteria with complete execution transcripts |

---

## 14. Phase Boundary & Invariant Protections

The execution of Phase 6C is strictly scoped to backup scripts, restoration safety, test suites, and disaster recovery documentation.

### Explicitly Excluded from Phase 6C:
- **Zero Live Trading Functionality:** No live brokerage integrations or live trading endpoints.
- **Zero Broker Activation:** Default broker remains `"paper"` with `is_paper=True`.
- **Zero Autonomous Execution:** `ORION_WORKER_ENABLED="false"` preserved in all configurations.
- **Zero Architectural Redesign:** No modifications to billing, authentication, onboarding, frontend, or trading engines.
- **Capital At Risk:** **$0.00** strictly preserved.

---

## 15. Acceptance Criteria

1. **Syntax Integrity:** All bash scripts in `backup/` pass `bash -n` syntax validation with zero warnings or errors.
2. **Deterministic Dump Creation:** `database-backup.sh` creates a valid custom-format PostgreSQL dump archive using valid `pg_dump -Fc` syntax without parallel format conflicts.
3. **Cryptographic Checksumming:** Every backup run outputs a companion `.sha256` sidecar file containing the SHA-256 hash of the archive.
4. **Pre-Restore Validation:** `restore-database.sh` verifies the SHA-256 hash and archive Table of Contents (`pg_restore -l`) before modifying any database state.
5. **Managed Cloud Compatibility:** `restore-database.sh` restores successfully into an isolated target database without requiring `postgres` maintenance database access, superuser privileges, or `DROP DATABASE` / `CREATE DATABASE` commands.
6. **Schema & Migration Alignment:** Restored databases are deterministically aligned with Alembic revision head `0015_onboarding_progress`.
7. **Semantic Integrity Verification:** Post-restore validation confirms table inventories, non-empty tenant/user tables, and valid account balance Decimal precision.
8. **Secret Hygiene:** Zero passwords or encryption keys appear in process listings (`ps -ef`), command-line arguments, or log files.
9. **Redis Architecture Realignment:** Redis backup scripts document the ephemerality of Redis cache state and define container restart recovery procedures.
10. **RPO / RTO Documentation Harmonization:** Documentation reflects realistic Render PaaS standards (RPO < 24 Hours, RTO < 60 Minutes).
11. **Isolated Restore Demonstration Certified:** A complete 9-point isolated restore demonstration is executed, verified, and documented in `docs/EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md`.

---

## 16. Risk Matrix

| Risk ID | Description | Likelihood | Impact | Mitigation Strategy | Verification Method |
|---|---|---|---|---|---|
| **RSK-01** | Corrupted backup artifact restored over production | Medium | Critical | Mandate SHA-256 verification and TOC check prior to schema alteration | Test corrupted file rejection in automated suite |
| **RSK-02** | Inadvertent drop of live database during restore | Low | Catastrophic | Eliminate `DROP DATABASE`; enforce `--target-url` isolation | Code review & isolation validation in test |
| **RSK-03** | Restored database schema lags behind application code | High | High | Run `scripts/deploy/migrate.py` post-restore to fast-forward to head `0015` | Automated migration head assertion in `verify_restore.py` |
| **RSK-04** | Process-table snooping exposes encryption keys | Medium | High | Replace `pass:pass` with `pass:env:VAR` and secure file descriptors | Inspect `/proc/<pid>/cmdline` during execution |
| **RSK-05** | Managed database rejects superuser commands | High | High | Restrict all SQL operations to tenant schema ownership scope | Execute test restore under unprivileged user role |
| **RSK-06** | Redis outage causes application failure | Medium | Low | Confirm rate limiter memory fallback; document container restart | Verify `/health/ready` behavior during Redis restart |
| **RSK-07** | Actual recovery time exceeds 60-minute RTO | Medium | Medium | Benchmark isolated restore execution duration during demonstration | Record exact elapsed timings in demonstration log |

---

## 17. Final Plan Classification

### **`B — IMPLEMENTATION READY WITH EXTERNAL DEPENDENCIES`**

**Technical Justification:**  
The implementation design is technically complete, fully specified, and rigorously eliminates all architectural defects identified in the audit (BLK-6C-01 through BLK-6C-06). Execution is ready to proceed upon human authorization, with the following documented external dependencies:
1. **Accessible PostgreSQL Instance for Restore Demonstration:** Executing the physical restore demonstration requires an active local PostgreSQL container or isolated staging database.
2. **Render Account Billing Method:** Required in cloud staging to activate persistent `basic-1gb` PostgreSQL snapshots ($7/mo).
3. **Object Storage Bucket Provisioning:** Offsite S3 replication requires an active S3/R2 bucket and IAM credentials.

---

EPIC-027 PHASE 6C — IMPLEMENTATION PLAN COMPLETE — AWAITING HUMAN REVIEW
