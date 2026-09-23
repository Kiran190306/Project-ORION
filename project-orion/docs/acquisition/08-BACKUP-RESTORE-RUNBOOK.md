# Project ORION — Backup & Disaster Recovery Runbook

**Document Version:** 1.0.0<br>
**Target Milestone:** EPIC-027 Phase 7B Acquisition Due Diligence<br>
**Repository Working Copy:** `project-orion/`<br>
**Classification:** Confidential — Due Diligence Technical Data Room (Tier 2 / NDA)<br>
**Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Capital at Risk — Zero Live Broker Endpoints)

---

## 1. Disaster Recovery Objectives & Scope

This runbook defines the technical procedures, validation gates, and recovery workflows for **Project ORION** relational storage and key-value state.

### Operational Targets
- **Recovery Time Objective (RTO) Target:** `< 60 minutes`
- **Recovery Point Objective (RPO) Target:** `< 24 hours` (governed by daily automated snapshot schedules)
- **Demonstrated Physical Restore Duration:** **7 seconds** (measured in EPIC-027 Phase 6C isolated target restoration demonstration)

> [!IMPORTANT]
> **RTO vs RPO Demonstration Distinction:**
> The 7-second isolated restore demonstrates restore execution time for the tested artifact/environment; it does not independently prove the RPO target. RPO is supported operationally by daily automated snapshot scheduling.

### Architecture of Disaster Recovery Tiers
Data resilience in Project ORION is structured across three distinct operational layers:
1. **Repository Tooling:** Standalone, deterministic shell scripts and Python verifiers (`backup/*.sh`, `scripts/deploy/verify_restore.py`) operating on standard PostgreSQL dumps.
2. **Render-Managed Infrastructure:** Automated daily system snapshots managed by Render PaaS on the `basic-1gb` PostgreSQL tier (7-day retention).
3. **Buyer-Configured External Storage:** Offsite object storage replication (e.g. AWS S3, Cloudflare R2, Google Cloud Storage), which must be configured by the buyer.

---

## 2. Backup Tooling Architecture

The core backup tooling resides in `project-orion/backup/`:

### 2.1 Database Logical Backup (`backup/database-backup.sh`)
- **Format:** PostgreSQL Custom Format (`pg_dump -Fc`). The custom format is compressed by default, supports selective table extraction, and allows parallel restoration.
- **Cryptographic SHA-256 Sidecar:** Every dump immediately produces an accompanying `.dump.sha256` checksum sidecar file using `sha256sum`.
- **Table of Contents (TOC) Verification:** The script runs `pg_restore -l` against the newly created dump to verify that the archive header and internal table of contents are structurally sound.
- **Optional Symmetric Encryption:** Supports AES-256-CBC encryption via OpenSSL when `BACKUP_ENCRYPTION_KEY` is supplied in the execution environment.

#### Manual Backup Execution Runbook:
```bash
# Generate logical backup to specified directory
bash backup/database-backup.sh --output-dir backups/manual

# Verify generated artifacts
ls -la backups/manual/
# Output includes:
# orion-db-full-YYYYMMDD_HHMMSS.dump
# orion-db-full-YYYYMMDD_HHMMSS.dump.sha256
```

### 2.2 Backup Retention Management (`backup/retention-policy.sh`)
- Enforces Grandfather-Father-Son rotation on local and mounted backup directories:
  - Daily archives retained for 7 days.
  - Weekly archives retained for 30 days.
  - Monthly archives retained for 90 days.
  - Prunes expired `.dump` files while simultaneously purging their associated `.dump.sha256` sidecars.

### 2.3 Redis Key-Value Store Snapshots (`backup/redis-backup.sh`)
- Issues a non-blocking `BGSAVE` command to the managed Redis instance.
- Polls `LASTSAVE` until snapshot completion, then archives `dump.rdb` with a timestamp sidecar.
- **Note on Redis Data:** Redis stores sliding-window rate limit counters, user sessions, and quote caches. All data in Redis is ephemeral and reconstructable upon process restart; Redis loss does not cause financial or relational data loss.

---

## 3. Primary Disaster Recovery Architecture: Isolated Target Database Restoration

To eliminate the catastrophic risk of accidentally overwriting an active production database during recovery operations, `backup/restore-database.sh` enforces **Isolated Target Database Restoration**.

### Non-Negotiable Safety Invariants in `restore-database.sh`
1. **Mandatory Target URL (`--target-url`):** The script refuses to execute without an explicit `--target-url` argument. It will never default to, infer, or target the active production database connection string.
2. **Pre-Restore Checksum Verification:** Verifies the archive SHA-256 sidecar (`sha256sum -c`) before establishing any network connection to the target database.
3. **Pre-Restore TOC Inspection:** Runs `pg_restore -l` to ensure archive integrity before modifying database state.
4. **Prohibition of Destructive DDL:** Standard restoration strictly prohibits `DROP DATABASE` and `CREATE DATABASE` commands.

---

## 4. Standard Isolated Restoration Runbook

### Step 1: Provision Isolated Target Database
Provision an isolated recovery database (e.g. an ephemeral PostgreSQL container or a separate managed staging instance: `orion_dr_isolated`).

### Step 2: Validate Archive Integrity
```bash
sha256sum -c backups/orion-db-full-20260923_183834.dump.sha256
# Expected output: backups/orion-db-full-20260923_183834.dump: OK
```

### Step 3: Execute Restoration to Isolated Target
```bash
bash backup/restore-database.sh \
  --target-url "postgresql://orion:REDACTED@recovery-host:5432/orion_dr_isolated" \
  backups/orion-db-full-20260923_183834.dump
```

### Step 4: Execute Semantic Verification Suite (`verify_restore.py`)
Run the post-restore verification tool against the newly restored target:
```bash
poetry run python scripts/deploy/verify_restore.py \
  --target-url "postgresql+asyncpg://orion:REDACTED@recovery-host:5432/orion_dr_isolated"
```
The verification tool executes three objective integrity checks:
1. **Alembic Revision Alignment:** Checks that `alembic_version` in the database matches the canonical target head (`0015_onboarding_progress`).
2. **Schema Inventory Verification:** Dynamically inspects all application tables against SQLAlchemy declarative models (`Base.metadata.tables.keys()`) plus `alembic_version` (29 tables demonstrated in Phase 6C).
3. **Financial & Paper Trading Integrity:** Confirms zero NULL account balances, validates balance preservation ($100,000.00 virtual equity default), and verifies that `is_live=False` ($0.00 capital at risk).

---

## 5. Emergency Manual In-Place Schema Reset Runbook

If primary production storage suffers catastrophic logical corruption and an immediate in-place schema restoration against the primary instance is authorized:

```bash
bash backup/restore-database.sh \
  --target-url "postgresql://orion:REDACTED@prod-host:5432/orion_prod" \
  --emergency-manual-in-place-schema-reset \
  backups/orion-db-full-20260923_183834.dump
```

> [!CAUTION]
> **HIGH RISK OPERATIONAL PROCEDURE:**
> The `--emergency-manual-in-place-schema-reset` flag drops and recreates the `public` schema in the target database. To prevent accidental execution, the script prompts the operator to manually type `RESTORE_EMERGENCY_PROD` before proceeding with any destructive DDL.

---

## 6. Certified Demonstration Evidence (EPIC-027 Phase 6C)

As formally certified in `docs/EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md`:

| Demonstration Criterion | Verified Result | Target / SLA | Status |
|---|---|---|:---:|
| **Backup Archive Format** | PostgreSQL Custom Format (`PGDMP`, 103,588 bytes) | Custom Format with TOC | **PASS** |
| **Integrity Validation** | SHA-256 sidecar verified via `sha256sum -c` | Cryptographic match | **PASS** |
| **Archive Inspection** | `pg_restore -l` passed with exit code 0 | Valid Table of Contents | **PASS** |
| **Restoration Execution** | `backup/restore-database.sh` exited with code 0 | Clean execution | **PASS** |
| **Alembic Revision** | `0015_onboarding_progress` confirmed in database | Match canonical head | **PASS** |
| **Table Inventory** | 29 tables dynamically verified from `Base.metadata` | Complete schema restoration | **PASS** |
| **Financial Integrity** | 1 account, $100k virtual equity, 0 NULL balances | $0.00 capital at risk | **PASS** |
| **Physical Restore Duration** | **7 seconds** ($T_{start} = \text{18:41:01}$, $T_{finish} = \text{18:41:08}$) | RTO < 60 minutes | **PASS** |

---

## 7. Storage Boundaries & External Offsite Replication

1. **Local and Mounted Storage:** The backup script defaults to storing archives in `/var/backups/orion` or an operator-specified directory (`--output-dir`).
2. **Render Managed Snapshots:** When provisioned on Render's `basic-1gb` PostgreSQL plan, Render takes automated daily system-level snapshots with 7-day retention.
3. **Buyer Offsite Storage Responsibility:** Project ORION does not include hardcoded cloud bucket credentials. The acquiring team must configure an external cron job or pipeline wrapper (e.g. AWS CLI `aws s3 sync` or R2 CLI `rclone`) to synchronize local backup directories to an encrypted offsite object storage bucket.
