# EPIC-027 PHASE 6C — BACKUP, RESTORE & DISASTER RECOVERY AUDIT

**Phase:** EPIC-027 Phase 6C — Backup, Restore & Disaster Recovery Hardening  
**Repository:** `Project-ORION` (`c:\Users\Shree\CascadeProjects\forex-trading-platform-architecture\project-orion`)  
**Git Baseline:** `3ff486e` (`feat(deploy): harden cloud deployment and migration safety`)  
**Audit Execution Date:** 2026-09-23  
**Auditor Role:** Principal Site Reliability Engineer (SRE), Cloud Infrastructure Architect & Database Administrator  
**Operational Safety Invariant:** **$0.00 CAPITAL AT RISK** (Paper trading execution only, autonomous worker disabled, live broker connections blocked)  
**Final Audit Classification:** `C — IMPLEMENTATION PLAN REQUIRES DESIGN CORRECTIONS`  

---

## 1. Executive Summary

This repository-wide technical audit evaluates the data protection, backup automation, restoration safety, and disaster recovery capabilities of Project ORION for **EPIC-027 Phase 6C**.

While Phase 6A/6B successfully decoupled database migrations and hardened the Render Infrastructure-as-Code blueprint (`render.yaml`) to persistent paid tiers (`basic-1gb` PostgreSQL and `starter` API), **Phase 6C data protection assets currently exhibit multiple critical architectural, syntactical, and security defects**:

1. **Syntax Corruption in `backup/retention-policy.sh`:** Lines 33–56 contain accidental LLM tool prompt text pasted directly into the script. The script cannot be parsed by bash and crashes immediately.
2. **Managed Cloud Incompatibility & Destructive Restore (`backup/restore-database.sh`):** The restore script attempts to connect to the maintenance database `postgres`, issue `pg_terminate_backend()`, and execute `DROP DATABASE IF EXISTS ${DB_NAME}` followed by `CREATE DATABASE ${DB_NAME}`. On managed PostgreSQL providers (such as Render PostgreSQL or AWS RDS), the unprivileged application user `orion` lacks superuser privileges and is denied access to the maintenance database. Furthermore, this approach is destructive to production data and provides zero isolation.
3. **Invalid `pg_dump` Parameters in `backup/database-backup.sh`:** Line 43 executes `pg_dump -Fc -j 4`. In PostgreSQL, parallel job execution (`-j`) is strictly supported only with directory format (`-F d`), not with custom single-file archive format (`-Fc`). This command fails immediately upon execution.
4. **Architectural Misalignment with Redis Ephemerality (`backup/redis-backup.sh` & `restore-redis.sh`):** Both scripts assume local filesystem access to the Redis server (`CONFIG GET dir` and `cp` on `/var/lib/redis`), as well as daemon control (`SHUTDOWN NOSAVE`). In managed cloud Redis (Render Redis), client containers have TCP-only connectivity and lack server filesystem and administrative privileges.
5. **Zero Backup/Restore Test Coverage:** There are zero unit, integration, or CI/CD tests for any script in `backup/`.
6. **Restore Demonstration Status:** **`NOT DEMONSTRATED`**. No isolated end-to-end restore has ever been executed, recorded, or verified in the repository.
7. **Process-List Secret Exposure:** Encryption keys (`pass:"${ENCRYPTION_KEY}"`) and Redis passwords (`-a "${REDIS_PASSWORD}"`) are passed as command-line arguments, making them visible to any local user via process table inspection (`ps -ef`).

Phase 6C must not proceed directly to code execution without an approved implementation plan addressing these foundational architectural flaws.

---

## 2. Current Backup Architecture

Project ORION's backup strategy is defined across three layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        BACKUP ARCHITECTURE OVERVIEW                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 1: Provider Managed Snapshots (Render basic-1gb)                     │
│  ├─ Automated daily physical/filesystem snapshots                          │
│  ├─ 7-day retention on paid tiers                                          │
│  ├─ Managed by Render Cloud Platform (requires active payment method)      │
│  └─ Restoration managed via Render Dashboard UI                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 2: Application Logical Dumps (`backup/database-backup.sh`)            │
│  ├─ Invokes `pg_dump` against PostgreSQL (`orion-postgres`)                │
│  ├─ Intended custom format with compression                                 │
│  ├─ Optional AES-256-CBC encryption via OpenSSL                             │
│  └─ Optional upload to S3-compatible object storage via AWS CLI             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 3: Cache Snapshots (`backup/redis-backup.sh`)                        │
│  ├─ Intended RDB snapshots via Redis `BGSAVE`                               │
│  └─ Host filesystem copy (architecturally invalid on cloud PaaS)           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Architectural Realities:
- **Relational Data (PostgreSQL):** Stores authoritative tenant organizations, users, accounts, balances, orders, fills, positions, legal acceptances, and onboarding wizard progress.
- **Cache Data (Redis):** Operates strictly as an ephemeral cache, rate-limiting counter store, and pub/sub message bus. Redis carries zero authoritative financial state; loss of Redis results in transient cache invalidation, not financial loss.
- **Scheduling Reality:** `render.yaml` contains **no scheduled Cron Jobs** (`type: cron`). Currently, logical dumps must be triggered manually via terminal.

---

## 3. Current Restore Architecture

The restoration architecture is conceptually described in [`docs/EPIC-018-BACKUP-RECOVERY.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/EPIC-018-BACKUP-RECOVERY.md) and implemented in [`backup/restore-database.sh`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/backup/restore-database.sh):

```
                        [ RESTORE WORKFLOW ATTEMPTED ]
                                      │
                         1. Decrypt Archive (.enc)
                                      │
                        2. Decompress Archive (.gz)
                                      │
              3. Connect to 'postgres' DB & Terminate Backends
                 [FAILS ON MANAGED POSTGRES - LACKS PRIVILEGES]
                                      │
               4. DROP DATABASE ${DB_NAME} & CREATE DATABASE
                 [FAILS ON MANAGED POSTGRES - NOT PERMITTED]
                                      │
                           5. Execute pg_restore
                                      │
                         6. Verify: SELECT COUNT(*)
                            FROM information_schema.tables
```

### Critical Flaws in Restore Architecture:
1. **Destructive Execution Without Validation:** Drops the live database before verifying the integrity of the backup file.
2. **Privilege Escalation Assumption:** Assumes the application user has superuser privileges to access the `postgres` database.
3. **No Target Isolation:** Lacks any capability to restore into an isolated sandbox database, temporary verification schema, or secondary staging environment.
4. **No Schema/Migration Verification:** Does not check Alembic revision heads (`alembic_version`) or run database migrations post-restore.
5. **No Data Integrity Verification:** Does not check row counts, financial account balance sums, or tenant isolation integrity.

---

## 4. Repository Evidence

| Component | File Path | Current Status | Key Repository Evidence |
|---|---|---|---|
| Retention Policy | [`backup/retention-policy.sh`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/backup/retention-policy.sh) | **CORRUPTED** | Lines 33–56 contain pasted prompt text (`local removedNow creating...`). Syntax error on line 33. |
| DB Restore | [`backup/restore-database.sh`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/backup/restore-database.sh) | **DEFECTIVE** | Lines 60–68: `psql ... -d postgres -c "DROP DATABASE..."`. Incompatible with managed cloud DB. |
| DB Backup | [`backup/database-backup.sh`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/backup/database-backup.sh) | **DEFECTIVE** | Line 43: `pg_dump -Fc -j 4` is invalid PostgreSQL CLI syntax. Line 50: key passed on CLI. |
| Redis Backup | [`backup/redis-backup.sh`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/backup/redis-backup.sh) | **INCOMPATIBLE** | Lines 56–61: `CONFIG GET dir` and host `cp`. Fails on managed Redis. |
| Redis Restore | [`backup/restore-redis.sh`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/backup/restore-redis.sh) | **INCOMPATIBLE** | Lines 61–65: `SHUTDOWN NOSAVE` and host `cp`. Fails on managed Redis. |
| Configuration | [`backup/backup-config.yml`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/backup/backup-config.yml) | **UNREFERENCED** | Unused passive configuration; scripts do not parse or load this YAML. |
| Cloud Blueprint | [`render.yaml`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/render.yaml) | **HARDENED** | `orion-postgres` on `plan: basic-1gb` (automated daily snapshots enabled). No cron job defined. |
| Docker Image | [`docker/apps/trading-engine/Dockerfile`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docker/apps/trading-engine/Dockerfile) | **TOOLING MISSING** | `backup/` not copied to container. `postgresql-client`, `awscli`, `openssl` CLI missing in runtime. |
| Operations Docs | [`docs/operations/backup-guide.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/operations/backup-guide.md) | **OUTDATED** | References nonexistent port 9121 Prometheus metrics. |
| DR Guide | [`docs/operations/disaster-recovery-guide.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/operations/disaster-recovery-guide.md) | **OUTDATED** | References Kubernetes, `kubectl`, Helm, and StatefulSets; disconnected from Render PaaS. |
| DR Runbook | [`docs/EPIC-018-BACKUP-RECOVERY.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/EPIC-018-BACKUP-RECOVERY.md) | **ACCURATE** | Correctly documents Render PaaS constraints and logical restore procedures. |

---

## 5. Backup Script Findings (`backup/database-backup.sh`)

1. **Invalid PostgreSQL Syntax (`pg_dump -Fc -j 4`):**  
   PostgreSQL `pg_dump` documentation specifically restricts the parallel jobs flag (`-j`) to the directory format (`-F d`). Executing `pg_dump -Fc -j 4` emits:
   ```text
   pg_dump: error: parallel backup only supported by directory format
   ```
   and immediately terminates with code 1.
2. **Redundant Double Compression:**  
   Custom format (`-Fc`) is internally compressed using zlib. Applying `gzip -9` to an already-compressed binary archive yields minimal space savings while doubling CPU overhead.
3. **Incremental Backup False Advertisement:**  
   The script header claims "Supports: Full and Incremental backups", but lines 73–74 explicitly reject incremental backups:
   ```bash
   if [ "${BACKUP_TYPE}" = "full" ]; then do_full_backup
   else error_exit "Unknown type: ${BACKUP_TYPE}"; fi
   ```
4. **No Checksum Generation:**  
   No SHA-256 hash or sidecar file is produced to verify data integrity before transmission or storage.
5. **No Archive Table-of-Contents Verification:**  
   The script does not verify the created dump with `pg_restore -l` prior to declaring success or uploading to remote storage.
6. **Missing AWS CLI in Runtime:**  
   Line 53 invokes `aws s3 cp`. The production container image does not install `awscli`.

---

## 6. Restore Script Findings (`backup/restore-database.sh`)

1. **Destructive Before Validated:**  
   The script executes destructive operations (`pg_terminate_backend`, `DROP DATABASE`) **before** verifying whether `pg_restore` can read the archive file or whether the target database is healthy.
2. **Permission Failure on Managed Cloud:**  
   Connecting to database `postgres` and dropping `orion_prod` fails with:
   ```text
   FATAL: permission denied for database "postgres"
   ERROR: must be owner of database orion_prod
   ```
   Render PostgreSQL provides a single tenant database (`orion_prod`) owned by `orion`, without access to cluster maintenance databases.
3. **Superuser Requirement:**  
   Terminating existing connections via `pg_terminate_backend()` requires superuser or membership in `pg_signal_backend`.
4. **Superficial Verification:**  
   The verification step executes:
   ```sql
   SELECT count(*) FROM information_schema.tables WHERE table_schema='public';
   ```
   This only checks if tables exist. It does not check row counts, financial balances, tenant isolation, or Alembic revision heads.
5. **Alembic Disconnection:**  
   Restoring an older backup leaves the schema at an older migration revision (e.g., `0012`). The restore script does not inspect `alembic_version` or trigger `migrate.py` to upgrade the schema to `0015_onboarding_progress`.

---

## 7. Render / PostgreSQL Findings

1. **Provider Plan Capabilities (`plan: basic-1gb`):**
   - **Persistent Storage:** Guaranteed persistent SSD (eliminates 30-day free tier wipe).
   - **Automated Snapshots:** Render performs automated daily database snapshots on all paid plans.
   - **Retention:** Render retains daily snapshots for **7 days**.
   - **PITR (Point-in-Time Recovery):** **NOT SUPPORTED** on `basic-1gb`. Render requires higher-tier Pro plans ($35+/mo) for continuous WAL archiving and minute-by-minute point-in-time recovery.
2. **Private Network Isolation (`ipAllowList: []`):**
   - `orion-postgres` is strictly private within the Render VPC.
   - External clients (e.g. developer laptops or external cron services) cannot connect over public internet to run `pg_dump`.
   - Backups must execute from within the Render private network (via a Render Cron Job container, or a pre-deploy hook).
3. **External Dependency / Provider Verification:**
   - *Status:* `EXTERNAL DEPENDENCY / REQUIRES CURRENT PROVIDER VERIFICATION`.
   - Automated cloud snapshot restores must be initiated through the Render Dashboard UI by an account administrator. Render does not expose a public REST API for free/basic tier programmatic snapshot restore.

---

## 8. Object Storage Findings

1. **S3 Configuration in Repository:**  
   `backup-config.yml` references S3 bucket `${BACKUP_S3_BUCKET:-orion-backups}` with region `us-east-1`.
2. **Bucket Provisioning Status:**  
   No S3 bucket has been provisioned, configured, or integrated into Render environment variables.
3. **Tooling & SDK Absence:**  
   - AWS CLI (`aws`) is not installed in `docker/apps/trading-engine/Dockerfile`.
   - `boto3` is not listed in `pyproject.toml` or `poetry.lock`.
4. **Authentication & Secret Management:**  
   No IAM role, AWS Access Key (`AWS_ACCESS_KEY_ID`), or Secret Access Key (`AWS_SECRET_ACCESS_KEY`) is configured in `render.yaml`.
5. **S3 Lifecycle Management:**  
   No bucket lifecycle configuration exists to enforce the documented 30-day daily, 12-week weekly, and 12-month monthly retention policy.

---

## 9. Security Findings

1. **Process Table Secret Leakage:**  
   In `backup/database-backup.sh`:
   ```bash
   openssl enc ... -pass pass:"${ENCRYPTION_KEY}"
   ```
   In `backup/redis-backup.sh`:
   ```bash
   redis-cli ... -a "${REDIS_PASSWORD}"
   ```
   Arguments passed on the command line are visible to all users on the host via `ps -ef` or `/proc/<pid>/cmdline`.
   *Remediation:* Use standard file descriptors, stdin, or environment variable references (`pass:env:BACKUP_ENCRYPTION_KEY`).
2. **Artifact Content Classification:**  
   Logical PostgreSQL dumps contain sensitive customer and operational data:
   - Tenant organizational structures and invitations
   - User account records, email addresses, and bcrypt password hashes
   - Stripe customer identifiers (`stripe_customer_id`, `stripe_subscription_id`)
   - Paper trading order history, execution fills, and account balances
   - User onboarding state and legal acceptance timestamps
   *Requirement:* Backup artifacts must be encrypted at rest with AES-256 before uploading to remote object storage, and S3 bucket access must enforce least-privilege IAM policies.
3. **Database Secrets in Dump Files:**  
   Application API keys and JWT secret keys are stored exclusively in environment variables and are **not** present in database tables. However, database passwords and connection URLs must be masked in all backup logs.

---

## 10. Integrity Verification Findings

1. **Archive Header Verification:**  
   Neither `database-backup.sh` nor `restore-database.sh` verifies archive integrity using `pg_restore --list`. Corrupted or truncated dumps would fail halfway through execution.
2. **Checksum Verification:**  
   SHA-256 checksum generation is completely absent. Best practice requires generating an immutable `.sha256` sidecar file during backup creation and validating it with `sha256sum -c` prior to decompression/decryption during restoration.
3. **Scheduled Verification Engine:**  
   `backup-config.yml` defines `verification.schedule: "0 6 * * *"` and `restore_path: /var/backups/orion/verify`. However, **no verification script exists** in the repository to execute this scheduled integrity test.

---

## 11. Restore Demonstration Status

Per audit instructions, restore capability must be classified based strictly on concrete repository evidence across 9 criteria:

| Criterion | Requirement | Repository Evidence | Status |
|---|---|---|---|
| 1. Backup Artifact | Valid logical dump exists | No dump artifact committed | `NOT MET` |
| 2. Integrity Verification | Archive validated with checksum & TOC | No checksum or TOC verification | `NOT MET` |
| 3. Isolated Target Database | Non-production target environment | Script targets live `DB_NAME` | `NOT MET` |
| 4. Restore Execution | Clean execution without errors | Script fails on `DROP DATABASE` | `NOT MET` |
| 5. Migration/Schema Alignment | Alembic head verified (`0015`) | No Alembic check in script | `NOT MET` |
| 6. Row/Count/Integrity Checks | Semantic checks across key tables | Only checks table count | `NOT MET` |
| 7. Application Connectivity | `/health/ready` verified | Not probed in restore script | `NOT MET` |
| 8. Successful Completion | Exit code 0 with operational certification | Never executed or logged | `NOT MET` |
| 9. Cleanup | Temporary files wiped | Decrypted files deleted on exit | `PARTIALLY MET` |

### **Overall Demonstration Status: `NOT DEMONSTRATED`**

No isolated end-to-end restore demonstration has ever been completed in Project ORION.

---

## 12. RPO & RTO Status

A thorough search across the repository revealed two conflicting disaster recovery objective definitions:

### 1. Authoritative Production Definition:
In [`docs/EPIC-018-BACKUP-RECOVERY.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/EPIC-018-BACKUP-RECOVERY.md) (Lines 34–36):
- **RPO (Recovery Point Objective):** **`< 24 Hours`**  
  > *"The maximum acceptable age of data lost following a catastrophic storage failure. Achieved via daily automated logical database dumps and transaction logs."*
- **RTO (Recovery Time Objective):** **`< 60 Minutes`**  
  > *"The maximum acceptable duration required to restore database services, verify schema alignment, and resume API traffic."*

### 2. Conflicting Legacy Kubernetes Definition:
In [`docs/operations/disaster-recovery-guide.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/operations/disaster-recovery-guide.md) (Lines 9–10):
- PostgreSQL: RTO 30 min | RPO 5 min
- Redis: RTO 15 min | RPO 1 min

### Audit Determination:
The 5-minute RPO in `disaster-recovery-guide.md` is **unrealistic** under Render PostgreSQL `plan: basic-1gb` because continuous WAL streaming and Point-in-Time Recovery (PITR) are unavailable on that tier. The honest and authoritative standard for Project ORION is:
- **Production Target RPO:** **`< 24 Hours`** (governed by daily automated snapshots and logical dumps).
- **Production Target RTO:** **`< 60 Minutes`** (governed by logical dump restoration and schema verification).
- **Current Actual RTO:** **`INDETERMINATE`** (due to broken restore scripts).

---

## 13. Failure Handling

| Failure Scenario | Current System Behavior | Operational Risk | Severity |
|---|---|---|---|
| **Backup Fails (Disk Full / Crash)** | `set -e` aborts; leaves partial file; zero alert emitted | Silent failure; stale backups | `HIGH` |
| **Object Storage Unavailable** | Script aborts on `aws s3 cp`; local file retained | Backup not offloaded offsite | `MEDIUM` |
| **Invalid Credentials** | `pg_isready` fails; script aborts immediately | Immediate detection, but no alert | `MEDIUM` |
| **Corrupted Backup Artifact** | `restore-database.sh` drops database **before** restore attempt | **Catastrophic data loss** | `CRITICAL` |
| **Restore Fails Halfway** | Target database left in half-restored inconsistent state | Application crash loop | `CRITICAL` |
| **Migration Differs After Restore** | Application boots into newer code with older DB schema; crashes | Extended service downtime | `HIGH` |
| **Process Crash During Dump** | Temp files left in `/var/backups/orion` without trap cleanup | Disk exhaustion | `MEDIUM` |

---

## 14. Monitoring & Alerting

1. **Prometheus Metrics:**  
   `docs/operations/backup-guide.md` claims the following metrics are exposed on port 9121:
   - `orion_backup_database_last_success_timestamp`
   - `orion_backup_database_duration_seconds`
   - `orion_backup_redis_last_success_timestamp`
   - `orion_backup_errors_total`  
   *Reality:* **No metrics exporter exists in the repository.** Port 9121 was copied from a Redis exporter Helm template.
2. **Failure Alerting:**  
   Zero webhook, email, PagerDuty, or Slack notifications are configured for backup execution failures.
3. **Dead Man's Snitch / Heartbeat:**  
   No passive heartbeat monitoring (e.g. Healthchecks.io) exists to alert when a scheduled backup fails to execute.

---

## 15. Existing Test Coverage

A comprehensive search of `tests/` confirmed:
- **Unit Tests:** `0` tests covering backup, restore, or retention scripts.
- **Integration Tests:** `0` tests covering database backup/restore workflows.
- **E2E Tests:** `0` tests covering disaster recovery failover or restore validation.
- **Validation Script:** [`scripts/validate/validate-all.sh`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/scripts/validate/validate-all.sh) only tests file existence (`[ -f "$b/$f" ]`), never testing syntax or execution.

---

## 16. Missing Test Coverage

To achieve production readiness, the following test suites must be implemented in Phase 6C:
1. **Script Syntax & Static Analysis Test:** Automated `bash -n` and `shellcheck` verification of all bash scripts in CI.
2. **Deterministic SQLite/PostgreSQL Logical Dump & Restore Test:** A test that:
   - Populates a database with sample multi-tenant data, accounts, orders, and onboarding records.
   - Executes the backup logic to generate a dump archive and SHA-256 checksum.
   - Validates the checksum and archive TOC (`pg_restore -l`).
   - Restores the archive into an isolated test database.
   - Asserts record counts and checksums match identically.
3. **Migration Fast-Forward Restore Test:** A test verifying that an older schema dump (e.g. revision `0012`) restored into a clean database is cleanly brought to head revision `0015` via `scripts/deploy/migrate.py`.

---

## 17. Disaster Recovery Gaps

1. **Managed Database Privileges Mismatch:** Restore script assumes root/superuser privileges not granted by cloud PaaS providers.
2. **Lack of Automated Scheduling in IaC:** `render.yaml` has no cron service configured to execute recurring backups.
3. **Kubernetes vs Render Documentation Mismatch:** `docs/operations/disaster-recovery-guide.md` instructs operators to run `kubectl` commands that do not apply to Render.
4. **No Disaster Recovery Runbook for Render Cloud:** No verified runbook exists detailing how to spin up a replacement PostgreSQL instance on Render, shift environment variables, and resume API traffic.

---

## 18. Phase 6C Blockers

The following items are hard blockers for Phase 6C implementation:

| Blocker ID | Description | Impact | Resolution Required |
|---|---|---|---|
| **BLK-6C-01** | `retention-policy.sh` syntax corruption | Script unexecutable | Remove pasted LLM text; implement clean retention logic |
| **BLK-6C-02** | `restore-database.sh` destructive `DROP DATABASE` | Incompatible with cloud PaaS | Refactor to restore into isolated target or clean schema |
| **BLK-6C-03** | `database-backup.sh` invalid `pg_dump -Fc -j 4` | Dump fails immediately | Remove `-j 4` or switch to directory format |
| **BLK-6C-04** | Missing checksum verification | Corrupted dumps undetected | Add SHA-256 sidecar generation and validation |
| **BLK-6C-05** | Restore never demonstrated | Unproven recovery capability | Execute and log verified isolated restore demonstration |
| **BLK-6C-06** | Redis backup scripts host-dependent | Incompatible with cloud Redis | Deprecate host `cp` scripts; document Redis cache ephemerality |

---

## 19. External Dependencies

1. **Render Account Billing Method:**  
   Required to maintain `orion-postgres` on `plan: basic-1gb` ($7/mo) for automated provider snapshots and persistent storage.
2. **Object Storage Provider (AWS S3 or Cloudflare R2):**  
   Required for offsite logical dump replication. Requires bucket creation, IAM access keys, and bucket lifecycle configuration.
3. **Render Cron Service:**  
   Scheduling recurring backups requires adding a `type: cron` service to `render.yaml`, which incurs additional compute usage on Render.

---

## 20. Recommended Phase 6C Work Packages

### Work Package 1: Script Remediation & Modernization
- Fix syntax corruption in `backup/retention-policy.sh`.
- Fix invalid `pg_dump -Fc -j 4` in `backup/database-backup.sh`.
- Remove command-line key passing; use `pass:env:BACKUP_ENCRYPTION_KEY`.
- Add SHA-256 checksum generation (`sha256sum`) and sidecar `.sha256` output.
- Add archive TOC validation (`pg_restore -l`).

### Work Package 2: Safe Managed Database Restore Pipeline
- Refactor `backup/restore-database.sh` to remove `DROP DATABASE` / `CREATE DATABASE` and superuser connection attempts.
- Implement isolated target restoration:
  - Support restoring into a temporary database URL (`RESTORE_DATABASE_URL`).
  - Or support schema-level restoration (`DROP SCHEMA public CASCADE; CREATE SCHEMA public;`).
- Integrate post-restore Alembic schema verification (`scripts/deploy/migrate.py`).
- Implement post-restore data validation query suite (table counts, balance sums, audit integrity).

### Work Package 3: Redis Architecture Alignment
- Update `backup/redis-backup.sh` and `restore-redis.sh` to document Redis ephemerality in Project ORION.
- Clarify that Redis holds zero persistent financial state, and that recovery from Redis failure consists of container restart and cache warm-up, not physical disk RDB copying.

### Work Package 4: Automated Testing & Restore Demonstration
- Implement automated test suite covering backup archive creation, checksum validation, and test database restoration.
- Execute and document an isolated restore demonstration certifying the 9 required criteria.

### Work Package 5: Disaster Recovery Runbook Harmonization
- Replace outdated Kubernetes references in `docs/operations/disaster-recovery-guide.md` with accurate Render Cloud procedures.
- Establish authoritative RPO (< 24 Hours) and RTO (< 60 Minutes) standards.

---

## 21. Acceptance Criteria for Phase 6C

1. `backup/retention-policy.sh` passes `bash -n` syntax check with zero errors.
2. `backup/database-backup.sh` generates a valid custom-format dump archive without syntax errors.
3. Every backup generates a verified `.sha256` checksum sidecar file.
4. `backup/restore-database.sh` can successfully restore a dump into an isolated database without requiring superuser privileges or `DROP DATABASE`.
5. Post-restore verification validates table counts, tenant records, and brings the database to Alembic head `0015_onboarding_progress`.
6. An isolated restore demonstration is executed, verified, and logged in documentation.
7. Zero secrets are passed via command-line arguments.
8. Safety invariants ($0.00 Capital at Risk, Paper Only, Worker Disabled) remain 100% intact.

---

## 22. Risk Matrix

| Risk Event | Likelihood | Impact | Severity | Mitigation Strategy |
|---|---|---|---|---|
| Broken restore script leaves team unable to recover from database corruption | High | Critical | **CRITICAL** | Refactor restore script to support managed PostgreSQL schema resets |
| Accidental execution of `DROP DATABASE` on live database | Medium | Critical | **CRITICAL** | Remove `DROP DATABASE` from script; require explicit confirmation flag |
| Corrupted backup passes undetected into storage | High | High | **HIGH** | Mandate SHA-256 checksum and `pg_restore -l` TOC verification |
| Silent backup failure due to lack of alerting | High | High | **HIGH** | Implement exit traps and dead-man's snitch monitoring |
| Encryption key exposed in process table | Medium | Medium | **MEDIUM** | Pass keys via standard file descriptors or environment variables |
| Free-tier database expiration destroys production state | Low | Critical | **HIGH** | Upgrade to `basic-1gb` persistent plan in `render.yaml` (Completed in Phase 6A) |

---

## 23. Final Classification

In accordance with strict repository evidence and the presence of critical syntactical errors, destructive commands, and missing isolated restore verification:

### **`C — IMPLEMENTATION PLAN REQUIRES DESIGN CORRECTIONS`**

**Justification:**  
The repository contains non-negotiable architectural defects:
1. `backup/retention-policy.sh` is syntactically corrupted and unexecutable.
2. `backup/restore-database.sh` is destructive, requires superuser privileges, and is completely incompatible with managed cloud databases.
3. `backup/database-backup.sh` uses invalid `pg_dump` arguments.
4. Restore capability has **never been demonstrated**.

An implementation plan detailing the exact architectural redesign of these scripts must be prepared and approved prior to code execution.

---

EPIC-027 PHASE 6C — AUDIT COMPLETE — AWAITING HUMAN REVIEW
