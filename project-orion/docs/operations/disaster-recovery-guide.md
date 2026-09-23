# Project ORION — Cloud Disaster Recovery Guide

**Architecture:** Render Cloud PaaS (Docker, Managed PostgreSQL 15, Managed Redis)
**Version:** v1.0.0 (EPIC-027 Phase 6C Hardened)
**Institutional Safety Invariant:** **$0.00 CAPITAL AT RISK** (Paper trading only, autonomous worker disabled by default, live broker endpoints permanently blocked)

---

## 1. Disaster Recovery Objectives

Recovery objectives reflect the realities of managed cloud infrastructure on Render:

| Component | Architecture Role | Target RTO | Target RPO | Recovery Mechanism |
|---|---|---|---|---|
| **API Web Service (`orion-api`)** | Stateless ASGI App Container | < 5 min | N/A (Stateless) | Container auto-restart / Image rollback |
| **Dashboard UI (`orion-dashboard`)** | Stateless Nginx SPA Container | < 5 min | N/A (Stateless) | Static container restart / Rollback |
| **Relational DB (`orion-postgres`)** | Authoritative Multi-Tenant State | < 60 min | < 24 Hours | Isolated logical restore via `restore-database.sh` OR Render daily snapshot |
| **Cache & Bus (`orion-redis`)** | Ephemeral Cache & Rate Limiting | < 5 min | N/A ($0.00 State) | Container restart (`render services restart orion-redis`) |
| **Autonomous Worker** | In-Process Task Coordinator | N/A | N/A (Stateless) | Kept disabled (`ORION_WORKER_ENABLED="false"`) |

> [!NOTE]
> **Authoritative RPO & RTO Framing:**
> - **Documented Target RPO:** **`< 24 Hours`** (governed by daily automated snapshots on `plan: basic-1gb` and daily logical database dumps).
> - **Documented Target RTO:** **`< 60 Minutes`** (governed by target database preparation, archive checksum verification, logical restore, and post-restore semantic verification).
> - **Actual Demonstrated RTO:** Measured dynamically during isolated restore drills ($\Delta T = T_{finish} - T_{start}$).

---

## 2. Failure Scenarios & Operational Runbooks

### Scenario 1: API Container Crash or Unhealthy Deployment
- **Detection:** Render Health Check failure on `/health/live`, HTTP 502/503 spikes.
- **Automated Response:** Render platform automatically restarts the container.
- **Manual Runbook:**
  ```bash
  # Check service status and recent logs
  render logs --service orion-api --tail 100

  # Trigger manual restart if stuck
  render services restart orion-api

  # If recent deploy was bad, rollback via Render Dashboard (one-click instant image rollback)
  ```

---

### Scenario 2: Redis Cache Failure or Memory Eviction
- **Architectural Reality:** Redis contains **zero persistent financial state**. All accounts, balances, orders, and tenant models live in PostgreSQL. Loss of Redis resets sliding-window rate limit counters to local memory and temporarily clears market tick caches.
- **Detection:** API logs warn `Redis connection failed; falling back to InMemoryRateLimiter`.
- **Manual Runbook:**
  ```bash
  # Restart managed Redis service
  render services restart orion-redis

  # Verify API reconnection via readiness probe
  curl -s -f https://orion-api.onrender.com/health/ready
  # Expected: {"overall":"healthy","database":true,"redis":true}
  ```

---

### Scenario 3: Database Data Corruption or Unintended Modification
- **Detection:** Integrity anomalies, unhandled database errors, or operator incident report.
- **Strategy:** **Isolated Target Restoration (Approach A)**. Never drop or overwrite active databases without prior verification.
- **Step-by-Step Procedure:**

```
                        [ INCIDENT DETECTED ]
                                  │
                     1. Suspend Live Traffic
                        render services suspend orion-api
                                  │
                     2. Provision Target Database
                        Provision `orion-postgres-dr` on Render
                        Obtain target connection URI
                                  │
                     3. Pre-Restore Checksum Verification
                        Verify SHA-256 sidecar of backup dump
                                  │
                     4. Execute Safe Restore
                        ./backup/restore-database.sh \
                          --target-url "${TARGET_DATABASE_URL}" \
                          /var/backups/orion/database/latest.dump
                                  │
                     5. Post-Restore Verification
                        python scripts/deploy/verify_restore.py \
                          --database-url "${TARGET_DATABASE_URL}"
                                  │
                     6. Shift Traffic & Resume Service
                        Update ORION_DATABASE_URL on orion-api
                        render services resume orion-api
```

#### Detailed Commands:
1. **Traffic Suspension:**
   ```bash
   render services suspend orion-api
   ```
2. **Execute Safe Restore to Target Database:**
   ```bash
   ./backup/restore-database.sh \
     --target-url "${NEW_TARGET_DATABASE_URL}" \
     /var/backups/orion/database/2026-09-23/orion-db-full-20260923_120000.dump
   ```
   *(Note: The script automatically checks `.sha256` integrity and `pg_restore -l` TOC before touching the target database).*

3. **Verify Restored Database Integrity:**
   ```bash
   python scripts/deploy/verify_restore.py --database-url "${NEW_TARGET_DATABASE_URL}"
   ```
   *(Asserts connectivity, all 28 `Base.metadata` tables + `alembic_version` = 29 tables, Alembic head `0015_onboarding_progress`, non-empty tenant counts, and zero NULL balances).*

4. **Fast-Forward Migrations (If Restoring Older Backup):**
   If restored revision is older than current application codebase:
   ```bash
   python scripts/deploy/migrate.py --database-url "${NEW_TARGET_DATABASE_URL}"
   ```

5. **Shift Application Traffic:**
   Update `ORION_DATABASE_URL` in the `orion-api` service configuration to point to the restored database, then resume traffic:
   ```bash
   render services resume orion-api
   ```

6. **Validate Production Readiness:**
   ```bash
   curl -s -f https://orion-api.onrender.com/health/ready
   ```

---

### Scenario 4: Cloud Provider Regional Outage
- **Detection:** Complete unreachability of Render region (e.g. `us-east`).
- **Response:**
  1. Retrieve offsite encrypted backup archive and companion `.sha256` checksum from remote object storage.
  2. Spin up standby infrastructure in secondary cloud region (or secondary PaaS provider) using repository blueprint `render.yaml`.
  3. Execute `restore-database.sh` against secondary database.
  4. Point DNS CNAME to secondary endpoint.

---

## 3. Post-Recovery Validation Checklist

After any disaster recovery restoration, verify:
- [ ] Database connectivity verified via `pg_isready`
- [ ] All 28 application tables present + `alembic_version` (29 total)
- [ ] Schema aligned with Alembic head `0015_onboarding_progress`
- [ ] Tenant records and user accounts verified non-empty
- [ ] Financial account balances verified: zero NULL values, valid Decimal sums
- [ ] API readiness probe (`/health/ready`) returns HTTP 200 with `database: true`
- [ ] Rate limiting service healthy with Redis connection active
- [ ] Safety invariants active: **$0.00 Capital at Risk**, paper trading default
