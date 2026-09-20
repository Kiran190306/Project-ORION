# PROJECT ORION — EPIC-018 PHASE 12: PRODUCTION OPERATOR RUNBOOK

**Project**: Project ORION — Institutional Forex Trading Platform  
**Epic**: EPIC-018 — Production Operations, Reliability, Security Hardening & Release Freeze  
**Phase**: Phase 12 — Central Production Runbook  
**Date**: 2026-09-20  
**Target Platform**: Render Cloud Production  
**Primary API**: `https://orion-api-68u2.onrender.com`  
**Primary Dashboard**: `https://orion-dashboard-6d3z.onrender.com`  
**Standard**: Comprehensive Standalone On-Call Operator Manual  

---

## 1. Quick Operational Health Checks

Execute these commands immediately when triaging any platform alert or system anomaly:

### 1.1. Process Liveness Check
```bash
curl -s -f https://orion-api-68u2.onrender.com/health/live
```
- **Expected Output**: `{"status":"alive"}`
- **Expected Status**: `HTTP 200 OK`
- **Triage**: If non-200 or timeout, container process is crashed or spinning up. Check Render logs.

### 1.2. Dependency Readiness Check (PostgreSQL & Redis)
```bash
curl -s -f https://orion-api-68u2.onrender.com/health/ready
```
- **Expected Output**: `{"overall":"healthy","database":true,"redis":true}`
- **Expected Status**: `HTTP 200 OK`
- **Triage**:
  - If `"database": false` -> PostgreSQL unreachable or pool saturated.
  - If `"redis": false` -> Redis unreachable. Check Render private network.

### 1.3. Observability & Prometheus Metrics
```bash
curl -s -f https://orion-api-68u2.onrender.com/metrics | head -n 30
```
- **Expected Output**: Standard Prometheus metrics text exposition containing `orion_http_requests_total`, `orion_paper_account_balance`, and `orion_worker_status 0.0`.

### 1.4. Dashboard & Security Headers Check
```bash
curl -s -I https://orion-dashboard-6d3z.onrender.com
```
- **Expected Output**: `HTTP/2 200` with headers:
  - `x-frame-options: DENY`
  - `x-content-type-options: nosniff`
  - `content-security-policy: default-src 'self' ...`

---

## 2. Invariant Paper Trading Safety Verification

Before performing any operational task, confirm that the system is strictly in paper trading mode:
```bash
curl -s https://orion-api-68u2.onrender.com/api/v1/account/
```
- **Required Invariants**:
  - `is_live`: must be `false`
  - `broker_name`: must be `"paper"`
  - `capital_at_risk`: must be `0.00`
  - `live_broker_connectivity`: must be `"NONE"`

---

## 3. Daily Operational Commands & Triage

### 3.1. Viewing Live Cloud Application Logs
```bash
# Using Render CLI (authenticated)
render logs --service orion-api --tail 100

# To filter for runtime errors
render logs --service orion-api | grep -i "error"
```

### 3.2. Database Health & Active Connection Inspection
```sql
-- Connect via psql using DATABASE_URL
SELECT count(*) FROM pg_stat_activity WHERE datname = 'orion_prod';
SELECT pid, query_start, state, query FROM pg_stat_activity WHERE state != 'idle';
```

### 3.3. Restarting Services via CLI
```bash
# Restart API service gracefully
render services restart orion-api

# Restart Dashboard service
render services restart orion-dashboard
```

---

## 4. Standard Operating Procedures (SOP)

### SOP-01: Standard Code Deployment
1. Verify all tests pass locally: `python -m pytest tests/unit/ -q`.
2. Commit changes cleanly: `git commit -m "feat/fix: description"`.
3. Push to main: `git push origin main`.
4. Monitor Render dashboard until both `orion-api` and `orion-dashboard` show `Live`.
5. Execute Quick Health Checks (Section 1.1 through 1.4).

### SOP-02: Rapid Production Rollback
1. Open Render Dashboard: `https://dashboard.render.com`.
2. Select `orion-api` -> **Deploys** tab.
3. Click `...` next to the last known good deploy (`a26a168`) -> **Rollback to this deploy**.
4. Repeat for `orion-dashboard` if frontend was changed.
5. Re-run Quick Health Checks.

### SOP-03: Disaster Recovery Restore
1. Follow `docs/EPIC-018-BACKUP-RECOVERY.md`.
2. Restore clean database: `pg_restore --dbname="${DATABASE_URL}" --clean orion_backup_latest.dump`.
3. Run `alembic upgrade head`.
4. Verify readiness: `curl https://orion-api-68u2.onrender.com/health/ready`.

---

## 5. Escalation & Contact Directory

| Role | Responsibility | Escalation Trigger |
|---|---|---|
| **Primary SRE On-Call** | Initial triage, service restart, rollback | SEV-1 or SEV-2 alert firing |
| **Lead Backend Architect** | Database deadlocks, Alembic migration failure | Unresolved database outage > 15m |
| **Lead Security Officer** | Token compromise, IDOR breach, unauthorized access | Security alert or suspicious tenant logs |
| **Trading Risk Officer** | Order anomalies, risk engine discrepancies | Any trading discrepancy or position error |
