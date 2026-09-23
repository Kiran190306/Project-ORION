# EPIC-027 PHASE 6C — IMPLEMENTATION PLAN REVIEW

**Phase:** EPIC-027 Phase 6C — Backup, Restore & Disaster Recovery Hardening  
**Repository:** `Project-ORION` (`c:\Users\Shree\CascadeProjects\forex-trading-platform-architecture\project-orion`)  
**Git Baseline:** `3ff486e` (`feat(deploy): harden cloud deployment and migration safety`)  
**Audit Reference:** [`docs/EPIC-027-PHASE-6C-AUDIT.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/EPIC-027-PHASE-6C-AUDIT.md)  
**Review Target:** [`docs/EPIC-027-PHASE-6C-IMPLEMENTATION-PLAN.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/EPIC-027-PHASE-6C-IMPLEMENTATION-PLAN.md)  
**Review Date:** 2026-09-23  
**Reviewer Role:** Principal SRE & Database Architect (Independent Review Gate)  
**Institutional Safety Invariant:** **$0.00 CAPITAL AT RISK** (Paper execution only, `broker_name="paper"`, `is_paper=True`, `ORION_WORKER_ENABLED="false"`, live broker endpoints blocked)  
**Review Verdict:** `APPROVED WITH CORRECTIONS`  

---

## 1. Executive Summary & Review Verdict

The implementation plan for **EPIC-027 Phase 6C (Backup, Restore & Disaster Recovery)** has been evaluated against the technical audit ([`docs/EPIC-027-PHASE-6C-AUDIT.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/EPIC-027-PHASE-6C-AUDIT.md)) and the repository architecture.

The plan demonstrates excellent technical understanding of managed cloud constraints, properly eliminates superuser and `DROP DATABASE` assumptions, mandates pre-restore checksum validation, and honors institutional safety invariants ($0.00 capital at risk).

However, rigorous code inspection identified ten specific areas requiring precise corrections before code execution is authorized. The implementation plan is:

### **`APPROVED WITH CORRECTIONS`**

Execution is prohibited until the ten mandatory review corrections detailed below are incorporated into the implementation scope.

---

## 2. Mandatory Review Corrections

### Correction 1: Table Inventory Derivation (Section 5.1)
- **Problem:** Section 5.1 of the plan states: *"Verify presence of all 15 core tables: users, organizations, organization_memberships, organization_invitations, accounts, orders, fills, positions, strategies, optimization_jobs, audit_logs, legal_acceptances, onboarding_progress, broker_configs, subscriptions"*.
- **Why It Matters:**  
  1. The number 15 was mistakenly conflated with the 15 Alembic migration files (`0001` to `0015`).
  2. The actual SQLAlchemy metadata in [`libraries/infrastructure/persistence/base.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/infrastructure/persistence/base.py) defines **28 application tables** registered on `Base.metadata`, plus `alembic_version` (total 29 tables).
  3. Fictional table names were hallucinated (e.g. `organization_memberships` vs actual `organization_members`, `strategies` vs actual `strategy_configs`, `broker_configs` vs actual `broker_sandbox_accounts` and `broker_reconciliation_snapshots`).
  4. Crucial production tables (such as billing models `billing_customers`, `billing_subscriptions`, `billing_invoices`, `billing_events`, `auth_tokens`, `strategy_deployments`, `risk_limits`, `risk_breaches`, `plans`) were completely omitted.
- **Required Replacement:**  
  Remove the hardcoded "15 tables" assertion. In [`scripts/deploy/verify_restore.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/scripts/deploy/verify_restore.py), dynamically import `Base.metadata.tables.keys()` from `libraries.infrastructure.persistence.base` as the single authoritative source of truth, and assert that all 28 registered tables plus `alembic_version` are present in the restored database schema.
- **Acceptance Criterion:**  
  `verify_restore.py` validates all 28 tables registered on `Base.metadata` plus `alembic_version` (total 29 tables), derived dynamically from repository models with zero hallucinated names.

---

### Correction 2: Strict Isolation & Prohibition of Automated Destructive Operations (Section 4.1, 4.2, 4.3)
- **Problem:** Section 4.2 describes Approach B (schema-level reset via `DROP SCHEMA public CASCADE`) as a fallback option, which could be inadvertently invoked or automated.
- **Why It Matters:**  
  Executing `DROP SCHEMA public CASCADE` against a live or mistakenly targeted production database causes instantaneous and irreversible data loss.
- **Required Replacement:**  
  1. **Primary & Only Automated Restore Target:** Mandate that `restore-database.sh` requires an explicitly provided, isolated destination via `--target-url <TARGET_DATABASE_URL>`.
  2. **Never Target Production by Default:** If `--target-url` is omitted, the script must abort immediately with exit code 1 and display usage instructions. The production `ORION_DATABASE_URL` must never be assumed as the default restore target.
  3. **Zero Normal Destructive Commands:** Under normal operation, the script must **never** execute `DROP DATABASE`, `CREATE DATABASE`, or `DROP SCHEMA public CASCADE`.
  4. **Emergency In-Place Reset Must Be Strictly Manual:** In-place schema reset must be completely decoupled from the automated restore path. It may only exist as an emergency manual command requiring a dedicated, multi-character confirmation flag (`--emergency-manual-in-place-schema-reset`) and a mandatory interactive prompt (`Type 'DESTROY-AND-RESTORE' to proceed`), preceded by a verified checksum check.
  5. Under no circumstances may any destructive operation be executed during implementation, testing, or demonstrations without explicit human sign-off.
- **Acceptance Criterion:**  
  `restore-database.sh` defaults to fail-safe behavior, requires explicit `--target-url`, contains zero automated `DROP DATABASE` or `DROP SCHEMA` calls, and prevents accidental production schema deletion.

---

### Correction 3: Checksum Definition & Immutability Clarification (Section 1.1, 3.2, 7.1)
- **Problem:** The plan repeatedly uses the phrase *"immutable .sha256 sidecar"* for local files.
- **Why It Matters:**  
  Local filesystem files on standard POSIX or Windows operating systems are mutable by default. Calling a local `.sha256` text file "immutable" is technically inaccurate.
- **Required Replacement:**  
  Clarify that:
  - **Local Implementation Scope:** The backup script generates a standard companion `.sha256` checksum file (`sha256sum artifact.dump > artifact.dump.sha256`) with restrictive permissions (`chmod 0600`).
  - **Restoration Verification:** Prior to any restoration or decryption, `restore-database.sh` executes `sha256sum -c artifact.dump.sha256`. If the checksum mismatches or the sidecar is missing, restoration aborts immediately with code 1.
  - **Cryptographic Immutability Scope:** True cryptographic immutability (WORM storage, S3 Object Lock, S3 bucket versioning) is classified strictly as an **`EXTERNAL PROVIDER DEPENDENCY`** requiring cloud object storage configuration.
- **Acceptance Criterion:**  
  Documentation distinguishes local `.sha256` validation from cloud object storage WORM/immutability features, and tests confirm checksum mismatch terminates restoration cleanly.

---

### Correction 4: Object Storage Boundary Separation (Section 7.1)
- **Problem:** The plan could be misinterpreted as claiming that S3 buckets, IAM roles, and lifecycle policies are already implemented in the repository.
- **Why It Matters:**  
  The repository audit confirmed that AWS CLI is not installed in the Docker image, `boto3` is not in `pyproject.toml`, no S3 bucket is provisioned, and no IAM credentials exist.
- **Required Replacement:**  
  Formally separate the architecture into three explicit tiers:
  - **Tier A (Repository-Implemented Scope):** Deterministic local dump creation (`pg_dump -Fc`), local SHA-256 sidecar generation, OpenSSL AES-256-CBC encryption via environment variables, archive TOC verification (`pg_restore -l`), and local retention pruning.
  - **Tier B (External Provider Dependency):** Remote offsite replication to AWS S3 or Cloudflare R2, bucket creation, IAM policy configuration, S3 lifecycle transition rules, and object retention policies.
  - **Tier C (Render Provider Capabilities):** Platform-managed daily snapshots on `basic-1gb` PostgreSQL tier, dashboard manual restores, and private VPC isolation.
- **Acceptance Criterion:**  
  The implementation plan explicitly states that offsite S3 upload logic is decoupled and does not block local backup, restore, and verification capabilities.

---

### Correction 5: Concrete 9-Point Restore Demonstration Protocol (Section 9)
- **Problem:** The demonstration steps must define the exact tangible artifacts and log outputs recorded at each stage.
- **Why It Matters:**  
  To satisfy the human review gate and transition from `NOT DEMONSTRATED` to `DEMONSTRATED`, every step must produce auditable evidence.
- **Required Replacement:**  
  Define the exact evidence recorded in [`docs/EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md):
  1. *Source Backup Artifact:* File path, size in bytes, creation timestamp.
  2. *SHA-256 Verification:* Exact 64-character hex hash recorded from `sha256sum`.
  3. *Archive TOC Verification:* Exit code 0 from `pg_restore -l` and line count of archive TOC entries.
  4. *Isolated Target Database:* Target connection URI (with masked credentials) confirming non-production target.
  5. *Restore Execution:* Full CLI execution log and elapsed duration in seconds ($\Delta T_{restore}$).
  6. *Alembic Verification:* Exact output of `alembic current` asserting head revision `0015_onboarding_progress`.
  7. *Semantic Data Validation:* Output of `verify_restore.py` reporting 28 tables present, non-zero user/org records, and zero null balances.
  8. *Application Connectivity:* Probing `/health/ready` and capturing JSON response `{"overall":"healthy","database":true,"redis":true}`.
  9. *Cleanup Confirmation:* Confirmation that isolated test database and decrypted scratch files were deleted.
- **Acceptance Criterion:**  
  `docs/EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md` is populated with actual, verifiable console transcripts matching all 9 evidence criteria.

---

### Correction 6: Tool-Native Secret Handling Semantics (Section 3.2, 11)
- **Problem:** The plan proposed replacing `pass:pass` with `pass:env:BACKUP_ENCRYPTION_KEY` and assumed this syntax is supported.
- **Why It Matters:**  
  If command semantics differ across versions or operating environments, scripts fail at runtime or leak secrets.
- **Required Replacement:**  
  Document the verified command syntax across all three tools:
  - **OpenSSL Encryption/Decryption:**  
    Verified on OpenSSL 3.x: `openssl enc -aes-256-cbc -salt -pbkdf2 -pass env:BACKUP_ENCRYPTION_KEY`. (Syntax is `-pass env:VAR`, **not** `pass:env:VAR`).
  - **PostgreSQL Database Password:**  
    Verified standard: `export PGPASSWORD="${DB_PASSWORD}"` within subshell or dedicated execution context. Never pass passwords on CLI flags.
  - **Redis CLI Password:**  
    Verified standard: `export REDISCLI_AUTH="${REDIS_PASSWORD}"` to eliminate `redis-cli -a` command-line warning and process table leakage.
- **Acceptance Criterion:**  
  All backup and restore scripts use verified `-pass env:VAR`, `PGPASSWORD`, and `REDISCLI_AUTH` environment mechanisms, with zero passwords appearing in `ps -ef`.

---

### Correction 7: RPO & RTO Measurement Protocol (Section 10)
- **Problem:** RTO must not be presented as achieved, and the measurement method during demonstration must be specified.
- **Why It Matters:**  
  The audit confirmed that actual RTO is currently **INDETERMINATE** because no restore has ever succeeded.
- **Required Replacement:**  
  1. Clearly state that **Target RPO < 24 Hours** and **Target RTO < 60 Minutes** are objectives, not current verified capabilities.
  2. Implement an automated timer in the restore demonstration protocol:
     - Record $T_{start}$ at the initiation of archive verification.
     - Record $T_{finish}$ upon completion of `verify_restore.py` and application `/health/ready` check.
     - Calculate $\text{Demonstrated RTO} = T_{finish} - T_{start}$.
     - Document whether the demonstrated RTO satisfies the < 60-minute objective.
- **Acceptance Criterion:**  
  The demonstration report records exact timestamps $T_{start}$, $T_{finish}$, and $\text{Demonstrated RTO}$ in seconds.

---

### Correction 8: Redis Architectural Truth & Recovery Boundaries (Section 6)
- **Problem:** Redis recovery must be framed strictly in accordance with repository evidence.
- **Why It Matters:**  
  The repository audit proved that Redis holds zero persistent financial state. All orders, fills, balances, and accounts live in PostgreSQL. Claiming Redis requires complex backup pipelines misrepresents the architecture.
- **Required Replacement:**  
  1. Document that Redis in Project ORION is strictly an ephemeral cache, pub/sub bus, and sliding-window rate limiter counter store.
  2. Mark `backup/redis-backup.sh` and `backup/restore-redis.sh` as **`DEPRECATED FOR MANAGED CLOUD PAAS`**.
  3. Document the authoritative Redis recovery runbook: In the event of Redis crash, eviction, or corruption, the operational response is a service restart (`render services restart orion-redis`), whereupon `RateLimitService` falls back gracefully to in-memory limiting and `MarketDataCache` warms automatically from incoming quote ticks.
- **Acceptance Criterion:**  
  Redis scripts are clearly documented as deprecated for cloud PaaS, and the disaster recovery runbook defines container restart and memory fallback as the primary recovery mechanism.

---

### Correction 9: Test Feasibility & Test Environment Boundaries (Section 8)
- **Problem:** Tests must not depend on unavailable production infrastructure or assume local PostgreSQL is always reachable.
- **Why It Matters:**  
  Local PostgreSQL on port 5433 was previously unreachable during verification. Tests must be feasible and fail-fast without hanging.
- **Required Replacement:**  
  Categorize the automated tests into three distinct layers:
  - **Layer 1 (Offline Static & Syntax Tests):** `test_backup_script_syntax.py` executes `bash -n` and static regex checks across all scripts in `backup/`. Requires zero external services; runs 100% offline in CI and local dev.
  - **Layer 2 (Mock / SQLite Verification Tests):** `test_verify_restore_logic.py` tests `scripts/deploy/verify_restore.py` logic, table introspection, and semantic check algorithms against in-memory SQLite or mocked databases.
  - **Layer 3 (Live PostgreSQL Restore Integration Test):** `test_postgres_restore_isolated.py` executes full `pg_dump` and `pg_restore` against an active PostgreSQL instance. If `TEST_DATABASE_URL` is unset or PostgreSQL is unreachable, the test skips gracefully with `@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Isolated PostgreSQL instance required")`.
- **Acceptance Criterion:**  
  Pytest suite executes cleanly in local offline environments (running Layer 1 and 2, skipping Layer 3 when external DB is unavailable), with zero test hangs.

---

### Correction 10: Strict File-Level Scope Enforcement (Section 13)
- **Problem:** Ensure no extraneous or scope-creeping files are included in Phase 6C.
- **Why It Matters:**  
  Phase 6C must strictly harden backup and restore scripts without triggering frontend, billing, or strategy regressions.
- **Required Replacement:**  
  Restrict the file scope strictly to:
  1. [`backup/retention-policy.sh`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/backup/retention-policy.sh) (MODIFY — fix syntax, add dry-run and traps)
  2. [`backup/database-backup.sh`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/backup/database-backup.sh) (MODIFY — valid `pg_dump -Fc`, `.sha256`, TOC check, `-pass env:VAR`)
  3. [`backup/restore-database.sh`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/backup/restore-database.sh) (MODIFY — safe isolated restore via `--target-url`, verify `.sha256` & TOC)
  4. [`scripts/deploy/verify_restore.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/scripts/deploy/verify_restore.py) (NEW — 28-table introspection, Alembic head, balance checks)
  5. [`backup/redis-backup.sh`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/backup/redis-backup.sh) (MODIFY — deprecation header for cloud PaaS)
  6. [`backup/restore-redis.sh`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/backup/restore-redis.sh) (MODIFY — deprecation header for cloud PaaS)
  7. [`docs/operations/disaster-recovery-guide.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/operations/disaster-recovery-guide.md) (MODIFY — harmonize RPO/RTO & Render cloud runbook)
  8. [`tests/unit/backup/test_backup_scripts.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/tests/unit/backup/test_backup_scripts.py) (NEW — automated pytest suite for syntax, hashing, and verification)
  9. [`docs/EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md) (NEW — 9-point restore demonstration certification artifact)
  10. [`docs/EPIC-027-PHASE-6C-IMPLEMENTATION.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/EPIC-027-PHASE-6C-IMPLEMENTATION.md) (NEW — final engineering implementation report)
- **Acceptance Criterion:**  
  Zero files outside backup, scripts/deploy, tests/unit/backup, and docs are modified during Phase 6C.

---

## 3. Institutional Safety Confirmation

The plan review re-asserts all platform guardrails:
- **Broker Name:** `"paper"`
- **Paper Flag:** `is_paper=True`
- **Autonomous Worker:** `ORION_WORKER_ENABLED="false"`
- **Endpoint Validator:** Fail-closed against all live broker URLs
- **Stripe Mode:** Test Mode only (`sk_test_*`)
- **Capital At Risk:** **$0.00** strictly preserved

---

## 4. Final Review Verdict

### **`APPROVED WITH CORRECTIONS`**

The implementation plan is architecturally approved subject to incorporating the ten corrections documented above during implementation.

---

EPIC-027 PHASE 6C — PLAN REVIEW COMPLETE — AWAITING HUMAN APPROVAL
