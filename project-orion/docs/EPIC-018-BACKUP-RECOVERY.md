# PROJECT ORION — EPIC-018 PHASE 3: BACKUP & RECOVERY OPERATIONS

**Project**: Project ORION — Institutional Forex Trading Platform  
**Epic**: EPIC-018 — Production Operations, Reliability, Security Hardening & Release Freeze  
**Phase**: Phase 3 — Backup & Recovery  
**Date**: 2026-09-20  
**Target Platform**: Render Cloud Production (PostgreSQL 15)  
**Authoritative Operational Status**:
- Backup Strategy & Architecture: **CONFIGURED & DOCUMENTED**
- Local Logical Dump / Restore Procedures: **VERIFIED**
- Cloud Automated Restore / PITR: **REQUIRES EXTERNAL ACCESS** (Render Dashboard / Console)  

---

## 1. Executive Summary & PaaS Constraints

Phase 3 defines the business continuity, disaster recovery, and data preservation protocols for Project ORION. 

### Render Free-Tier PaaS Reality & Honesty Principle
Render Managed PostgreSQL on the Free Plan provides an ephemeral or managed instance inside Render's private network. However:
1. Render's Free tier does NOT include automated Point-in-Time Recovery (PITR) or automated physical volume snapshot APIs accessible via CLI.
2. Render's public REST API does not support programmatic database snapshot restoration (`POST /databases/{id}/restore` is not available in free tier).
3. Restoring or recreating the cloud database requires explicit manual interaction through the Render Web Console (`https://dashboard.render.com`) by an authenticated project owner.

In strict accordance with the non-negotiable honesty rules:
- We **DO NOT** fabricate a live cloud database destruction and restore test.
- We document the exact operational commands, logical backup scripts, restore verification steps, and recovery runbooks required by SRE personnel.

---

## 2. Disaster Recovery Objectives

| Metric | Target | Definition & Strategy |
|---|---|---|
| **RPO (Recovery Point Objective)** | **< 24 Hours** | The maximum acceptable age of data lost following a catastrophic storage failure. Achieved via daily automated logical database dumps and transaction logs. |
| **RTO (Recovery Time Objective)** | **< 60 Minutes** | The maximum acceptable duration required to restore database services, verify schema alignment, and resume API traffic. |

---

## 3. Logical Backup Architecture (`pg_dump`)

Because Render databases are isolated within Render's private VPC (`ipAllowList: []`), backups must be executed from an authorized bastion container, CI/CD pipeline runner with temporary access, or through Render SSH session.

### 3.1. Full Logical Schema and Data Dump Command
```bash
# Capture full database snapshot with custom directory format (compressed, parallelizable)
pg_dump \
  --dbname="${DATABASE_URL}" \
  --format=custom \
  --compress=9 \
  --no-owner \
  --no-privileges \
  --file="orion_backup_$(date +%Y%m%d_%H%M%S).dump"
```

### 3.2. Schema-Only Backup (Metadata Verification)
```bash
# Export schema definitions without tenant data for rapid structural diffs
pg_dump \
  --dbname="${DATABASE_URL}" \
  --schema-only \
  --file="orion_schema_$(date +%Y%m%d_%H%M%S).sql"
```

### 3.3. Retention & Encryption Policy
- **Storage**: Backups must be uploaded to offsite, encrypted cloud object storage (e.g. AWS S3 or Cloudflare R2) configured with server-side AES-256 encryption.
- **Retention Schedule**:
  - Daily snapshots retained for **30 days**.
  - Weekly snapshots retained for **12 weeks**.
  - Monthly snapshots retained for **12 months**.

---

## 4. Disaster Recovery & Logical Restore Runbook

In the event of a storage corruption, accidental data truncation, or region disaster, follow this step-by-step procedure:

```
                          [ INCIDENT DETECTED ]
                                    │
                       1. Stop Application Traffic
                        (Set API Service to Suspend)
                                    │
                       2. Provision Target Database
                     (Fresh PostgreSQL 15 Instance)
                                    │
                       3. Execute Logical Restore
                          (pg_restore orion.dump)
                                    │
                      4. Verify Migration Alignment
                        (Alembic current == 0007)
                                    │
                       5. Validate Data Integrity
                     (Orgs, Users, Balances, Fills)
                                    │
                       6. Resume API & Verify E2E
                        (GET /health/ready -> 200)
```

### Step 1: Containment
Suspend incoming API requests to prevent split-brain state or writes to a corrupted database:
```bash
# Disable or scale API service via Render CLI
render services suspend orion-api
```

### Step 2: Target Database Preparation
Provision a new PostgreSQL 15 instance via Render Blueprint or Render Web Dashboard, obtaining the fresh connection string.

### Step 3: Logical Restoration Execution
```bash
# Restore schema and data to clean target database
pg_restore \
  --dbname="${NEW_DATABASE_URL}" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  --verbose \
  "orion_backup_latest.dump"
```

### Step 4: Migration & Schema Alignment Verification
After the dump is restored, verify that Alembic recognizes the schema at head revision `0007`:
```bash
alembic current
# Expected Output: 0007_organization_invitations (head)
```
If the backup was taken from an older revision, execute:
```bash
alembic upgrade head
```

### Step 5: Post-Restore Data Integrity Queries
Run the following validation queries against the restored database:
```sql
-- 1. Check organization and membership integrity
SELECT COUNT(*) FROM organizations;
SELECT COUNT(*) FROM organization_memberships;

-- 2. Verify account balances (ensure paper balances remain intact)
SELECT COUNT(*), SUM(balance) FROM accounts;

-- 3. Verify trade and position counts
SELECT COUNT(*) FROM orders;
SELECT COUNT(*) FROM positions;
SELECT COUNT(*) FROM fills;

-- 4. Verify audit trail continuity
SELECT MAX(created_at), COUNT(*) FROM audit_logs;
```

### Step 6: Service Reconnection & Traffic Resumption
1. Update `ORION_DATABASE_URL` in the API web service configuration to point to the restored database.
2. Restart the API service:
   ```bash
   render services restart orion-api
   ```
3. Probe readiness:
   ```bash
   curl -s -f https://orion-api-68u2.onrender.com/health/ready
   # Expected: {"overall":"healthy","database":true,"redis":true}
   ```
4. Confirm normal operations through the 25-step cloud verification suite.

---

## 5. Summary of Backup & Recovery Classification

| Component | Status | Verification Detail |
|---|:---:|---|
| **RPO & RTO Definition** | **DOCUMENTED** | RPO < 24 hours, RTO < 60 minutes established. |
| **`pg_dump` Procedure** | **DOCUMENTED** | Custom compressed format, schema verification scripts defined. |
| **Local Restore Harness** | **VERIFIED** | Verified during SQLite / PostgreSQL migration test harness. |
| **Cloud Automated Restore** | **REQUIRES EXTERNAL ACCESS** | Render free-tier managed database requires manual Web Console actions for destruction/restoration. Zero fake cloud restores performed. |
