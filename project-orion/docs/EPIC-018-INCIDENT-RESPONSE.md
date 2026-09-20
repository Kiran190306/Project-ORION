# PROJECT ORION — EPIC-018 PHASE 7: INCIDENT RESPONSE RUNBOOK

**Project**: Project ORION — Institutional Forex Trading Platform  
**Epic**: EPIC-018 — Production Operations, Reliability, Security Hardening & Release Freeze  
**Phase**: Phase 7 — Incident Response Runbook  
**Date**: 2026-09-20  
**Target Platform**: Render Cloud Production  
**Safety Mandate**: In any trading-related anomaly, FIRST ACTION MUST BE: Verify Paper-Trading Only Mode & Worker Disabled.  

---

## 1. Incident Response Framework & Severity Levels

All operational incidents follow a standardized six-stage lifecycle:
```
  [ DETECTION ] ──► [ CONTAINMENT ] ──► [ DIAGNOSIS ]
                                             │
  [ POSTMORTEM ] ◄── [ VERIFICATION ] ◄── [ RECOVERY ]
```

### Severity Classification Matrix
| Severity | Description | Target Response SLA | Target Resolution SLA |
|---|---|:---:|:---:|
| **SEV-1 (Critical)** | Complete platform outage, database failure, worker running unauthorized, security breach, or data compromise. | < 15 minutes | < 2 hours |
| **SEV-2 (Major)** | Elevated 5xx errors (>1%), Redis outage, degraded API latency (p95 > 500ms), dashboard unreachable. | < 30 minutes | < 4 hours |
| **SEV-3 (Moderate)**| Partial feature degradation, isolated tenant authentication failure, background task failure. | < 2 hours | < 24 hours |
| **SEV-4 (Low)** | Minor cosmetic issue, non-critical log warning, non-blocking telemetry delay. | < 24 hours | Next release cycle |

---

## 2. Mandatory Trading Safety Invariant

> [!CAUTION]
> **FIRST ACTION MANDATE FOR TRADING ANOMALIES**:  
> For any incident involving unexpected orders, positions, trade fills, or market execution:  
> **1. Immediately verify that `ORION_WORKER_ENABLED=false`.**  
> **2. Confirm the platform is operating exclusively under `PaperExecutionAdapter` (`is_live=False`).**  
> **3. If any uncertainty exists, stop the trading worker and suspend the API web service.**  
> Zero real capital may ever be risked during incident diagnosis or triage.

---

## 3. Incident Procedures by Scenario

### Incident A: API Service Outage (`ApiLivenessFailed`)
1. **Detection**: Uptime monitor or `/health/live` returns non-200 or times out.
2. **Containment**: Check Render Web Console for pod crash or deployment failure.
3. **Diagnosis**: Run `render logs --service orion-api` to inspect the last 100 log lines. Look for Python uncaught exceptions, OOM (Out-of-Memory) kills (`Exit Code 137`), or port binding failures.
4. **Recovery**:
   - If transient crash: Trigger `render services restart orion-api`.
   - If corrupted release: Roll back to previous verified image/commit (`a26a168`).
5. **Verification**: Probe `GET https://orion-api-68u2.onrender.com/health/live` -> HTTP 200 (`{"status":"alive"}`).
6. **Postmortem**: Record root cause, MTTR (Mean Time to Recovery), and implement preventive monitors.

---

### Incident B: Database Outage (`PostgreSQLUnavailable`)
1. **Detection**: `/health/ready` returns HTTP 503 with `"database": false` or logs show `asyncpg.CannotConnectNowError`.
2. **Containment**: Render automatically attempts database process restarts. API returns 503 rather than serving corrupt state.
3. **Diagnosis**: Inspect Render PostgreSQL metrics (CPU, RAM, connection pool saturation). Check if max connections (typically 100) exceeded.
4. **Recovery**:
   - If connection pool exhaustion: Restart API service to flush lingering connection sockets.
   - If database instance failed: Review Render status page; initiate disaster recovery restore runbook if unrecoverable.
5. **Verification**: Verify `GET /health/ready` returns HTTP 200 with `"database": true`.
6. **Postmortem**: Analyze query execution times; optimize connection pool limits (`pool_size`, `max_overflow`).

---

### Incident C: Redis Cache Outage (`RedisUnavailable`)
1. **Detection**: `/health/ready` returns HTTP 503 with `"redis": false`.
2. **Containment**: Application cache-aside pattern prevents core transaction blocking. Verify orders and portfolio views continue operating against PostgreSQL.
3. **Diagnosis**: Inspect Redis memory utilization in Render dashboard; verify private network DNS resolution.
4. **Recovery**: Restart Redis instance via Render dashboard.
5. **Verification**: Confirm `GET /health/ready` returns HTTP 200 with `"redis": true`.
6. **Postmortem**: Check cache key TTLs to ensure memory eviction policies (`volatile-lru`) prevent Redis OOM.

---

### Incident D: Authentication / JWT Failure Spike
1. **Detection**: Sudden surge of HTTP 401 Unauthorized errors in API logs.
2. **Containment**: Verify whether the signing key `ORION_JWT_SECRET_KEY` was accidentally rotated or altered.
3. **Diagnosis**: Inspect JWT decoding errors in `libraries/observability/logging.py`. Look for `ExpiredSignatureError` vs `JWTClaimsError`.
4. **Recovery**:
   - If secret mismatch due to container restart with auto-generated secret: Set fixed 256-bit secret key in Render environment variables.
   - Advise users to re-authenticate via `POST /api/v1/auth/login`.
5. **Verification**: Execute test login and call `/auth/me` with newly minted bearer token.
6. **Postmortem**: Audit secret lifecycle and token expiration policies.

---

### Incident E: Tenant Isolation / Cross-Tenant IDOR Incident
1. **Detection**: Security alert or audit log entry indicating user in Organization A attempted access to Organization B (`HTTP 403 Forbidden`).
2. **Containment**:
   - Verify the request was blocked by the application's `@require_permission` and tenant-scoping logic.
   - If any data leaked: Immediately revoke the offending user's session token and suspend the user account:
     ```sql
     UPDATE users SET is_active = false WHERE id = 'usr_...';
     ```
3. **Diagnosis**: Audit API route parameters and database queries for missing `organization_id` WHERE clauses.
4. **Recovery**: Deploy hotfix ensuring query filter includes `organization_id = current_user.organization_id`.
5. **Verification**: Execute cross-tenant E2E tests (`test_cross_tenant_idor_blocked`).
6. **Postmortem**: Full forensic review of audit logs; notify compliance and affected tenant if required.

---

### Incident F: Unexpected Trading Behavior / Order Execution Anomaly
1. **Detection**: Trade ledger anomaly, excessive paper orders submitted, or unexpected drawdown.
2. **Containment (MANDATORY)**:
   - Verify `ORION_WORKER_ENABLED=false`.
   - Confirm paper adapter is active (`is_paper=True`).
   - Execute emergency order cancellation: cancel all open orders via `POST /api/v1/orders/{id}/cancel`.
3. **Diagnosis**: Inspect order audit trail (`audit_logs` table) to determine whether orders originated from API users or worker loop.
4. **Recovery**: Close erroneous open paper positions via `POST /api/v1/positions/{id}/close`.
5. **Verification**: Query `/api/v1/positions/` and verify open positions match expected portfolio state.
6. **Postmortem**: Review strategy parameter validations and pre-trade risk engine limits.

---

### Incident G: Autonomous Worker Unexpectedly Running
1. **Detection**: Alert 11 fires (`orion_worker_status == 1.0`).
2. **Containment**:
   - Immediately issue worker stop:
     ```bash
     curl -X POST -H "Authorization: Bearer ${TOKEN}" https://orion-api-68u2.onrender.com/api/v1/worker/stop
     ```
   - In Render dashboard, set `ORION_WORKER_ENABLED="false"`.
   - Restart `orion-api` service.
3. **Diagnosis**: Trace who or what initiated the worker startup (route call vs environment misconfiguration).
4. **Recovery**: Verify worker coordinator status is `0.0` (stopped).
5. **Verification**: Confirm `GET /metrics` shows `orion_worker_status 0.0`.
6. **Postmortem**: Audit RBAC permissions on `/api/v1/worker/start` to ensure only system owners can trigger it.

---

### Incident H: Data Corruption / Inconsistency
1. **Detection**: Foreign key constraint failures, mismatched portfolio balances, or negative margin.
2. **Containment**: Suspend API service to stop further transactional mutations.
3. **Diagnosis**: Inspect recent database transactions and Alembic migration history.
4. **Recovery**: Execute point-in-time restore or logical backup replay following `docs/EPIC-018-BACKUP-RECOVERY.md`.
5. **Verification**: Run data integrity validation queries (Section 4, Step 5 of Backup doc).
6. **Postmortem**: Add stricter database check constraints and unit-of-work transaction boundaries.

---

### Incident I: Database Migration Failure
1. **Detection**: Container fails to start on deploy with Alembic error in startup logs.
2. **Containment**: Container crashes before traffic is routed; Render keeps previous working revision active.
3. **Diagnosis**: Run `alembic current` and inspect migration error (e.g. syntax error, lock timeout, missing column).
4. **Recovery**:
   - If migration partially applied: Correct migration script locally, test against clean database, and author forward-fix.
   - Re-deploy corrected commit.
5. **Verification**: Verify container boots successfully and `GET /health/ready` returns HTTP 200.
6. **Postmortem**: Enforce local multi-database migration tests prior to git push.

---

### Incident J: Deployment Failure / Bad Release
1. **Detection**: Build error on Render, smoke tests fail post-deployment, or 5xx spike immediately after release.
2. **Containment**: Trigger immediate rollback via Render dashboard or deploy previous commit `a26a168`.
3. **Diagnosis**: Review deployment build log or diff between commits.
4. **Recovery**: Rollback to last known good deployment.
5. **Verification**: Execute 25-step cloud E2E suite against rolled-back deployment.
6. **Postmortem**: Add missing automated test to pre-deployment gate to catch regression locally.

---

### Incident K: High Request Latency (p95 > 500ms)
1. **Detection**: Alert 06 fires; users report sluggish dashboard responsiveness.
2. **Containment**: Check if cold start / spin-down occurred (Render free-tier sleeps after 15 minutes of inactivity).
3. **Diagnosis**: Profile database queries using `EXPLAIN ANALYZE`; check Redis connection latency.
4. **Recovery**: Add missing index to query filter column or scale Render service instance.
5. **Verification**: Confirm p95 latency on `/metrics` drops below 100ms.
6. **Postmortem**: Document query performance baseline in architecture records.

---

### Incident L: Credential or Secret Compromise
1. **Detection**: Secret detected in public git commit, unauthorized API access, or suspicious audit log entry.
2. **Containment**:
   - Immediately rotate `ORION_JWT_SECRET_KEY` in Render environment variables (invalidates all active sessions).
   - Rotate database password in Render PostgreSQL cluster.
   - Rotate Redis connection URL.
3. **Diagnosis**: Review git history and access logs to determine exposure scope.
4. **Recovery**: Deploy updated configuration; force all users to log in with new credentials.
5. **Verification**: Confirm old tokens fail with HTTP 401; new tokens succeed.
6. **Postmortem**: Run automated secret scanner (`git-secrets` / `trufflehog`) across entire repository history.
