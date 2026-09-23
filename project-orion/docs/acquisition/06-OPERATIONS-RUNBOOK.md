# Project ORION — Production Operations Runbook

**Document Version:** 1.0.0<br>
**Target Milestone:** EPIC-027 Phase 7B Acquisition Due Diligence<br>
**Repository Working Copy:** `project-orion/`<br>
**Classification:** Confidential — Due Diligence Technical Data Room (Tier 2 / NDA)<br>
**Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Capital at Risk — Zero Live Broker Endpoints)

---

## 1. Operational Philosophy & Invariants

This operations runbook specifies routine maintenance, deployment verification, diagnostic procedures, and failure recovery protocols for **Project ORION**.

### Core Operational Invariants
1. **Paper Trading Safety First:** All trade routing and order fills are purely virtual simulations. The platform contains zero live brokerage execution endpoints ($0.00 capital at risk).
2. **Autonomous Worker Lock:** The background strategy execution loop is disabled by default (`ORION_WORKER_ENABLED: "false"`). It must not be enabled until market data feeds and strategy parameters have been formally validated by an authorized operator.
3. **Decoupled Pre-Deploy Migrations:** Schema migrations execute in an isolated container job before new application containers receive traffic. Migration failure causes the deployment to abort immediately, providing migration failure isolation before application deployment.
4. **Unprivileged Container Execution:** Application processes execute strictly as unprivileged non-root users (`uid=999`).

---

## 2. Health & Readiness Telemetry

Project ORION exposes three standardized HTTP diagnostic probes:

### 2.1 Process Liveness Probe (`GET /health/live`)
- **Target:** Validates that the Uvicorn ASGI event loop is active and processing requests.
- **Render Configuration:** Primary health check probe (`healthCheckPath: /health/live`).
- **HTTP Status:** `200 OK`.
- **Response Payload:** `{"status": "live"}`

### 2.2 Dependency Readiness Probe (`GET /health/ready`)
- **Target:** Validates that backing infrastructure dependencies are operational before accepting user traffic.
- **Checked Dependencies:**
  - **PostgreSQL:** Executes `SELECT 1` via SQLAlchemy asyncpg pool.
  - **Redis:** Executes `PING` via Redis client.
- **HTTP Status:**
  - `200 OK` if all dependencies are responsive.
  - `503 Service Unavailable` if database or Redis connection fails.
- **Response Payload (Healthy):**
  ```json
  {
    "status": "ready",
    "checks": {
      "database": "connected",
      "redis": "connected"
    }
  }
  ```

### 2.3 Prometheus Telemetry Exposition (`GET /metrics`)
- **Target:** Exposes platform performance and business metrics in Prometheus text exposition format.
- **Exposed Metric Categories:**
  - HTTP request volume, duration histograms, and response status codes.
  - SQLAlchemy connection pool utilization (`orion_db_pool_size`, `orion_db_pool_checked_out`).
  - Paper trading simulation statistics (active orders, open positions, processed fills).
- **Access Control:** Protected by optional `ORION_METRICS_TOKEN` Bearer token. If configured, external scrapers must supply `Authorization: Bearer <token>`.
- **Integration Note:** The platform exposes standard metrics format; external monitoring servers (e.g. self-hosted Prometheus, Grafana Cloud, Datadog agent) must be configured by the buyer.

---

## 3. Deployment & Pre-Deploy Migration Monitoring

### 3.1 PaaS Deployment Topology (`render.yaml`)
- `orion-api`: Docker Web Service on `starter` plan (supports `preDeployCommand`).
- `orion-dashboard`: Docker Web Service on `free` plan (Nginx serving React SPA).
- `orion-postgres`: PostgreSQL 15 on `basic-1gb` plan (SSD storage, automated daily snapshots).
- `orion-redis`: Redis 7 on `free` plan (private network access only).

### 3.2 Pre-Deploy Migration Workflow
Render automatically executes the migration runner prior to rolling out new containers:
```bash
python scripts/deploy/migrate.py
```
- **Lifecycle:** Ephemeral build container executes forward migrations (`alembic upgrade head`) to the canonical head (`0015_onboarding_progress`).
- **Success Case (Exit Code 0):** Migration completes; Render performs a rolling restart of web containers.
- **Failure Case (Exit Code 1):** Migration encounters a lock, timeout, or syntax error; deployment aborts immediately. Existing running containers remain untouched and continue serving traffic without interruption.

---

## 4. Application Rollback Protocol

If an unexpected application defect occurs after a successful deployment:
1. Navigate to the **Render Dashboard** -> **Services** -> `orion-api` (or `orion-dashboard`).
2. Open the **Events** or **Deploys** tab.
3. Identify the previous stable deployment commit SHA.
4. Click **Rollback to this version**.
5. Render diverts incoming traffic to the previous container release during the rolling rollback process.

> [!WARNING]
> **Database Schema Policy:**
> Do NOT execute `alembic downgrade` in production. If a database migration requires remediation, author, test, and deploy a forward-compatible fix migration.

---

## 5. Autonomous Strategy Worker Operational Gate

### Current Default State
The autonomous trading worker (`apps/trading-engine/src/worker.py`) is **disabled by default**:
```yaml
ORION_WORKER_ENABLED: "false"
```
When disabled, the trading engine acts strictly as an API server responding to user-initiated HTTP requests.

### Safe Worker Activation Procedure
Activating the autonomous strategy loop is a deliberate operational decision requiring operator review:
1. Verify that the market data provider is operational and quotes are active (`ORION_MARKET_DATA_PROVIDER`).
2. Verify instrument symbols in `ORION_WORKER_SYMBOLS` (e.g. `EUR/USD,GBP/USD,USD/JPY`).
3. Set initial virtual equity in `ORION_PAPER_BALANCE` (default `100000.00`).
4. Update environment setting in Render Dashboard:
   - Variable: `ORION_WORKER_ENABLED`
   - Value: `"true"`
5. Trigger a deployment and monitor API logs to confirm startup:
   ```
   [INFO] [worker] Autonomous trading worker started. Symbols: ['EUR/USD', 'GBP/USD', 'USD/JPY']
   ```

---

## 6. Cryptographic Secret Rotation Runbook

### 6.1 JWT Secret Key Rotation (`ORION_JWT_SECRET_KEY`)
- **Operational Impact:** Invalidates the cryptographic signature on all issued access tokens. All existing active user sessions terminate immediately, requiring users to log in again.
- **Procedure:**
  1. Generate a new secure 64-character hexadecimal key:
     ```bash
     openssl rand -hex 32
     ```
  2. In Render Dashboard -> `orion-api` -> **Environment**, update `ORION_JWT_SECRET_KEY`.
  3. Save and trigger a manual redeploy.

### 6.2 Relational Database Password Rotation
- **Operational Impact:** Brief connection disruption while connection strings are updated.
- **Procedure:**
  1. In Render Dashboard -> `orion-postgres` -> **Settings**, update database password.
  2. Copy the updated internal connection string.
  3. In `orion-api`, update `ORION_DATABASE_URL` with the new credentials.
  4. Trigger a rolling restart of `orion-api`.

---

## 7. Storage Maintenance & Operational Checks

### 7.1 PostgreSQL Operational Checks
- **Connection Pool Monitoring:** Track `orion_db_pool_size` and `orion_db_pool_checked_out` via `/metrics`.
- **Autovacuum Health:** Autovacuum is active by default in PostgreSQL 15. Inspect dead tuple counts periodically via psql:
  ```sql
  SELECT relname, n_dead_tup, last_vacuum, last_autovacuum FROM pg_stat_user_tables;
  ```

### 7.2 Redis Key-Value Store Checks
- **Memory Saturation:** Inspect memory consumption via Redis CLI:
  ```bash
  redis-cli info memory
  ```
- **Eviction Policy:** Rate-limiting keys (`ratelimit:*`) use explicit TTL expiration. Ensure eviction policy is set to `volatile-lru`.

---

## 8. Failure Scenarios & Triage Runbooks

| Failure Scenario | Immediate Symptoms | Root Cause Triage | Remediation Procedure |
|---|---|---|---|
| **Database Connection Failure** | `/health/ready` returns HTTP 503; API endpoints return 500. | Check PostgreSQL status in Render dashboard; verify connection pool limits. | If database restarted, restart `orion-api` to reset asyncpg pool connections. |
| **Redis Cache Unreachable** | `/health/ready` returns HTTP 503; rate limiter logs connection warnings. | Check Redis memory and network connectivity inside Render mesh. | Restart Redis instance; sliding-window counters re-initialize cleanly. |
| **Pre-Deploy Migration Lock** | Render build hangs during `migrate.py` or exits with code 1. | Concurrent lock on table during DDL alteration. | Deployment automatically aborts; running traffic is unaffected. Resolve lock in PostgreSQL and re-trigger deploy. |
| **Outbound SMTP Failure** | User does not receive verification email; auth routes return 200. | Anti-enumeration masks error; check internal application logs for SMTP timeout. | Verify SMTP credentials, port (587/465), and upstream relay quota with email provider. |
| **Market Data Stale / Outage** | Autonomous worker logs quote staleness warning; no trades generated. | TwelveData API rate limit reached or third-party provider degraded. | Worker gracefully skips trading cycles until fresh quotes arrive. Switch provider to mock or upgrade TwelveData plan. |
