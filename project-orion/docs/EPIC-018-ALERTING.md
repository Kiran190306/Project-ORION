# PROJECT ORION — EPIC-018 PHASE 6: PRODUCTION ALERTING SPECIFICATION

**Project**: Project ORION — Institutional Forex Trading Platform  
**Epic**: EPIC-018 — Production Operations, Reliability, Security Hardening & Release Freeze  
**Phase**: Phase 6 — Production Alerting Specification  
**Date**: 2026-09-20  
**Target Platform**: Render Cloud Production  
**Authoritative Operational Status**:
- Alert Rules & Thresholds: **DEFINED** (All 15 Conditions)
- Metrics & Health Check Telemetry: **CONFIGURED & VERIFIED**
- Outbound Webhook / PagerDuty Dispatch: **REQUIRES EXTERNAL ACCESS** (Third-party API credentials)  

---

## 1. Executive Summary & Alerting Philosophy

Phase 6 defines the 15 critical production alert conditions for Project ORION. 

To maintain operational integrity and prevent alert fatigue, alerts are categorized into three severity tiers:
1. **P1 — CRITICAL (Immediate Page)**: Platform outage, database unreachable, worker enabled in production, or data compromise. On-call response SLA < 15 minutes.
2. **P2 — MAJOR (High Priority Notification)**: Elevated 5xx rate, Redis partition, latency breach, or authorization spikes. On-call response SLA < 30 minutes.
3. **P3 — WARNING (Informational Ticket)**: Transient poll errors, high memory warning, or rate limit threshold approached. Addressed during business hours.

In strict compliance with the non-negotiable honesty rules:
- Telemetry sources (Prometheus metrics, health endpoints, JSON logs) are **CONFIGURED & VERIFIED**.
- Alerting rules, mathematical queries, and thresholds are **DEFINED**.
- Outbound delivery to external notification providers (PagerDuty, OpsGenie, Slack Webhooks) is classified as **REQUIRES EXTERNAL ACCESS** because external API credentials are not configured in Render. No simulated deliveries are claimed.

---

## 2. Master 15 Production Alert Definitions

| # | Alert Name | Severity | Metric / Log Source | Threshold / Condition | Classification | Routing / External Dependency |
|---|---|:---:|---|---|:---:|---|
| **01** | `ApiLivenessFailed` | **P1** | `GET /health/live` | Status != 200 for > 2 consecutive probes (60s) | **DEFINED** | PagerDuty / Render Health Probe (REQUIRES EXTERNAL ACCESS) |
| **02** | `ApiReadinessFailed` | **P1** | `GET /health/ready` | Status != 200 for > 2 consecutive probes (60s) | **DEFINED** | PagerDuty / Render Health Probe (REQUIRES EXTERNAL ACCESS) |
| **03** | `PostgreSQLUnavailable`| **P1** | `orion_database_healthy` or `/health/ready` | `database == false` for > 30s | **DEFINED** | PagerDuty / DBA Escalation (REQUIRES EXTERNAL ACCESS) |
| **04** | `RedisUnavailable` | **P2** | `orion_redis_healthy` or `/health/ready` | `redis == false` for > 60s | **DEFINED** | Slack #alerts / SRE Team (REQUIRES EXTERNAL ACCESS) |
| **05** | `HighHttp5xxRate` | **P1** | `rate(orion_http_errors_total[5m])` | 5xx error rate > 1% of total traffic over 5m | **DEFINED** | PagerDuty / SRE On-Call (REQUIRES EXTERNAL ACCESS) |
| **06** | `HighRequestLatency` | **P2** | `histogram_quantile(0.95, orion_http_request_duration_seconds)` | p95 latency > 500ms sustained over 5m | **DEFINED** | Slack #alerts / Backend Team (REQUIRES EXTERNAL ACCESS) |
| **07** | `AuthFailureSpike` | **P2** | JSON Logs (`logger="trading_engine.routes.auth"`) | > 10 failed login attempts in 5m | **DEFINED** | Security Team / SIEM (REQUIRES EXTERNAL ACCESS) |
| **08** | `AuthorizationSpike` | **P2** | HTTP 403 responses | > 5 403 Forbidden responses across tenants in 5m | **DEFINED** | Security Team / SIEM (REQUIRES EXTERNAL ACCESS) |
| **09** | `PaperExecutionError`| **P2** | `orion_paper_trades_total` vs fill errors | Unhandled exception in `PaperExecutionAdapter` | **DEFINED** | Trading Platform Team (REQUIRES EXTERNAL ACCESS) |
| **10** | `RiskEngineFailure` | **P1** | `orion_risk_rejections_total` or risk crash | Risk evaluation throws unhandled error | **DEFINED** | Risk Officer / SRE On-Call (REQUIRES EXTERNAL ACCESS) |
| **11** | `WorkerUnexpectedlyEnabled`| **P1** | `orion_worker_status` | `orion_worker_status == 1.0` in production | **DEFINED** | PagerDuty EMERGENCY (REQUIRES EXTERNAL ACCESS) |
| **12** | `WorkerCycleErrors` | **P2** | `orion_worker_cycle_errors_total` | Cycle failure rate > 0 when worker is active | **DEFINED** | Engineering On-Call (REQUIRES EXTERNAL ACCESS) |
| **13** | `MigrationFailed` | **P1** | Container exit code / Lifespan startup | Startup exit code == 1 with Alembic error | **DEFINED** | Release Manager / Deployer (REQUIRES EXTERNAL ACCESS) |
| **14** | `ResourceExhaustion` | **P2** | Render container metrics | Memory usage > 90% (460MB of 512MB free tier) | **DEFINED** | SRE Team (REQUIRES EXTERNAL ACCESS) |
| **15** | `ContainerCrashLoop` | **P1** | Render process supervisor | > 3 container restarts within 10 minutes | **DEFINED** | PagerDuty / SRE On-Call (REQUIRES EXTERNAL ACCESS) |

---

## 3. Detailed Alert Specifications & Response Runbooks

### Alert 11: `WorkerUnexpectedlyEnabled` (P1 Emergency)
- **Condition**: `orion_worker_status == 1.0` in production environment.
- **Description**: The autonomous trading worker coordinator has been started in production, violating the strict safety mandate (`ORION_WORKER_ENABLED=false`).
- **Immediate Containment**:
  1. Trigger immediate emergency shutdown:
     ```bash
     curl -X POST -H "Authorization: Bearer ${ADMIN_TOKEN}" https://orion-api-68u2.onrender.com/api/v1/worker/stop
     ```
  2. Suspend or restart the API service with `ORION_WORKER_ENABLED="false"`.
  3. Verify all paper orders: `GET /api/v1/orders/`.
  4. Escalate to Lead Architect and Compliance Officer.

### Alert 01 & 02: `ApiLivenessFailed` & `ApiReadinessFailed` (P1 Critical)
- **Condition**: HTTP probe to `/health/live` or `/health/ready` returns non-200 or times out after 5.0 seconds.
- **Immediate Containment**:
  1. Inspect Render container logs for OOM (Out-of-Memory) crash or unhandled runtime panic:
     ```bash
     render logs --service orion-api
     ```
  2. If PostgreSQL is reported down (`database: false`), check PostgreSQL status in Render dashboard.
  3. If transient lockup, trigger restart:
     ```bash
     render services restart orion-api
     ```

### Alert 05: `HighHttp5xxRate` (P1 Critical)
- **Condition**: HTTP 5xx responses exceed 1% of total throughput over a 5-minute rolling window.
- **Immediate Containment**:
  1. Filter logs for exception stack traces: `level="ERROR"`.
  2. Identify failing endpoint and correlation IDs.
  3. If tied to a recent deployment, initiate rollback runbook immediately.

---

## 4. Alerting Integration Checklist (Prerequisites for Phase Verification)

To transition Alerting status from **DEFINED** to **CONFIGURED & VERIFIED** in future epics, the following external resources must be provisioned:
1. Provision PagerDuty / OpsGenie service API key or incoming Webhook URL.
2. Configure Render environment variable: `ORION_ALERT_WEBHOOK_URL="https://events.pagerduty.com/..."`.
3. Trigger a synthetic test alert to confirm end-to-end receipt, notification routing, and on-call escalation.
