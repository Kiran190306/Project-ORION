# Project ORION — Deployment & Runbook Handover

**Document Version:** 1.0.0<br>
**Target Milestone:** EPIC-027 Phase 7B Acquisition Due Diligence<br>
**Repository Working Copy:** `project-orion/`<br>
**Classification:** Confidential — Due Diligence Technical Data Room (Tier 2 / NDA)<br>
**Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Capital at Risk — Zero Live Broker Endpoints)

---

## 1. Executive Summary & Operational Invariants

This document serves as the authoritative operational deployment and runbook handover guide for **Project ORION**, prepared for technical due diligence and operational transfer.

Project ORION is a multi-tenant algorithmic Forex trading platform designed around Domain-Driven Design (DDD) and Hexagonal Architecture principles. The production deployment model is declaratively specified as an Infrastructure-as-Code (IaC) Blueprint for the **Render Platform-as-a-Service (PaaS)**, backed by a companion local **Docker Compose** development stack.

### Key Operational Invariants
1. **Paper Trading Safety Mandate:** All trade execution in Project ORION is strictly restricted to paper trading simulations and sandbox accounts. The platform contains zero live brokerage execution endpoints and zero real-money trading adapters ($0.00 capital at risk).
2. **Decoupled Pre-Deployment Migrations:** Database schema migrations are executed via `scripts/deploy/migrate.py` inside an ephemeral container (`preDeployCommand`) prior to routing HTTP traffic to new application instances. Migration failure immediately aborts the deployment without impacting running services.
3. **Fail-Closed Container Security:** Application containers run as unprivileged non-root users (`orion`, `uid=999`). Relational databases and Redis caches are strictly isolated inside private networks with public internet access disabled (`ipAllowList: []`).
4. **Autonomous Strategy Loop Gate:** The autonomous market data polling and strategy execution loop is disabled by default (`ORION_WORKER_ENABLED: "false"`), preventing accidental execution upon initial deployment.
5. **Measured Disaster Recovery:** The disaster recovery suite (`backup/restore-database.sh`) has demonstrated a physical restore duration of **7 seconds** in an isolated target environment, within the <60-minute operational RTO target (documented operational RPO target is <24 hours). The demonstration verified a restored schema of 29 tables derived from SQLAlchemy declarative models and `alembic_version`.

---

## 2. Operational Components Classification Matrix

To ensure absolute transparency during buyer due diligence, all operational components and subsystems are classified according to their current readiness and verification status:

| Subsystem / Component | Technical Artifact | Classification | Operational Notes |
|---|---|---|---|
| **Local Development Stack** | `docker-compose.yml`, `pyproject.toml` | **CURRENTLY VERIFIED** | Verified local startup with PostgreSQL 15 and Redis 7 backing services. |
| **Alembic Database Migrations** | `database/migrations/` (15 revisions) | **CURRENTLY VERIFIED** | Reversible, forward-only migrations up to head `0015_onboarding_progress`. |
| **Pre-Deploy Migration Hook** | `scripts/deploy/migrate.py` | **CURRENTLY VERIFIED** | Fail-fast CLI migration runner verified for Render PaaS `preDeployCommand`. |
| **API Container Packaging** | `docker/apps/trading-engine/Dockerfile` | **CURRENTLY VERIFIED** | Multi-stage Python 3.11-slim container running as non-root user `orion` (`uid=999`). |
| **Dashboard Container Packaging**| `apps/dashboard/Dockerfile` | **CURRENTLY VERIFIED** | Multi-stage Node 20 / Nginx 1.27 Alpine container running as non-root user. |
| **Health & Readiness Probes** | `/health/live`, `/health/ready` | **CURRENTLY VERIFIED** | Process liveness and dependency connectivity checks (PostgreSQL + Redis). |
| **Prometheus Metrics** | `/metrics` | **CURRENTLY VERIFIED** | Standard metrics exposition protected by optional Bearer token authentication. |
| **Database Backup Suite** | `backup/database-backup.sh` | **CURRENTLY VERIFIED** | PostgreSQL custom format dump (`pg_dump -Fc`), SHA-256 sidecar, and TOC verification. |
| **Disaster Recovery Restore** | `backup/restore-database.sh` | **CURRENTLY VERIFIED** | Demonstrated in Phase 6C: 7s restore duration verifying 29 tables derived from declarative models and alembic_version. |
| **Authentication & RBAC** | `libraries/domain/organization/` | **CURRENTLY VERIFIED** | Bcrypt password hashing, JWT revocation, and 41 granular permissions defined by the current RBAC permission model. |
| **Sliding-Window Rate Limiting** | `apps/trading-engine/src/middleware/` | **CURRENTLY VERIFIED** | Redis-backed sliding-window rate limiting with trusted proxy support. |
| **Paper Execution Adapter** | `paper_execution.py` | **CURRENTLY VERIFIED** | Virtual fill simulation with adverse slippage model and equity tracking. |
| **Mock Market Data Provider** | `mock_provider.py` | **CURRENTLY VERIFIED** | Deterministic synthetic candle and tick generation for local testing. |
| **Transactional Email Adapter** | `email_service.py` (`SMTPEmailAdapter`)| **CURRENTLY VERIFIED** | Phase 7A SMTP adapter with thread offloading and anti-enumeration safeguards. |
| **TwelveData Market Data** | `twelvedata_provider.py` | **CONFIGURED BUT NOT CURRENTLY VERIFIED** | Code complete; requires active third-party API subscription key. |
| **OANDA Practice Sandbox** | `oanda_adapter.py` | **CONFIGURED BUT NOT CURRENTLY VERIFIED** | Code complete; restricted to v20 practice endpoints; requires sandbox credentials. |
| **Autonomous Strategy Worker** | `apps/trading-engine/src/worker.py` | **CONFIGURED BUT NOT CURRENTLY VERIFIED** | Background execution loop disabled by default (`ORION_WORKER_ENABLED: "false"`). |
| **AES-256 Backup Encryption** | `backup/database-backup.sh` | **CONFIGURED BUT NOT CURRENTLY VERIFIED** | OpenSSL symmetric encryption pipeline implemented; key management externalized. |
| **Redis Snapshotting** | `backup/redis-backup.sh` | **CONFIGURED BUT NOT CURRENTLY VERIFIED** | Redis `BGSAVE` snapshot script available; Render manages Redis backups. |
| **Render Cloud PaaS Deployment**| `render.yaml` | **REQUIRES EXTERNAL ACCOUNT / BILLING / DNS** | Requires Render account with payment method for `starter` and `basic-1gb` plans. |
| **Custom Domain & TLS** | Render DNS Settings | **REQUIRES EXTERNAL ACCOUNT / BILLING / DNS** | Requires DNS CNAME records pointing to Render; automated Let's Encrypt TLS. |
| **Stripe Test Billing** | `stripe_adapter.py` | **REQUIRES EXTERNAL ACCOUNT / BILLING / DNS** | Code complete; requires buyer's Stripe account in Test Mode. |
| **Production SMTP Gateway** | `email_service.py` | **REQUIRES EXTERNAL ACCOUNT / BILLING / DNS** | Requires transactional email relay (SendGrid, Postmark, AWS SES, etc.). |
| **Live Broker Real Money Trading**| N/A | **NOT IMPLEMENTED** | Structurally prohibited by architectural design ($0.00 capital at risk). |
| **Multi-Region Active Clustering**| N/A | **NOT IMPLEMENTED** | Single-region cloud PaaS deployment model. |
| **SOC 2 / ISO 27001 Audit** | N/A | **NOT IMPLEMENTED** | Formal compliance attestations have not been conducted. |

---

## 3. Prerequisites & Toolchain Specifications

To operate, develop, and deploy Project ORION, the operator workstation and CI/CD runners require the following toolchains:

### Required Toolchains
- **Python:** Version `3.11.x` (strictly required; 3.12+ not yet validated for all C-extensions).
- **Poetry:** Version `>= 1.7.0` (Python dependency and packaging manager).
- **Node.js:** Version `20.x LTS` (Iron) & **npm** `>= 10.x` (for building the dashboard SPA).
- **Docker:** Version `>= 24.0.0` & **Docker Compose** `>= 2.20.0`.
- **Git:** Version `>= 2.40.0`.
- **PostgreSQL Client Utilities:** Version `15.x` (`pg_dump`, `pg_restore`, `psql`) for executing operational backup and restore runbooks.
- **OpenSSL:** Version `3.x` for optional backup artifact encryption and token generation.

---

## 4. Local Development Environment Spin-Up

The local development workflow enables complete full-stack execution using local containers for PostgreSQL and Redis alongside hot-reloading development servers for the backend engine and frontend dashboard.

### Step 1: Clone and Inspect Working Repository
```bash
git clone https://github.com/Kiran190306/Project-ORION.git project-orion
cd project-orion
git checkout main
```

### Step 2: Spin Up Backing Infrastructure
Launch isolated local PostgreSQL 15 and Redis 7 containers via Docker Compose:
```bash
docker compose up -d postgres redis
```
Verify that containers are healthy and ports `5432` and `6379` are bound locally:
```bash
docker compose ps
```

### Step 3: Install Backend Dependencies
Initialize the Poetry virtual environment and install all core, development, and test dependencies:
```bash
poetry install
```

### Step 4: Execute Database Schema Migrations
Apply all Alembic forward migrations up to the canonical head (`0015_onboarding_progress`):
```bash
poetry run alembic upgrade head
```

### Step 5: Start Backend ASGI Trading Engine
Launch the Uvicorn ASGI server with hot-reload enabled:
```bash
poetry run uvicorn apps.trading_engine.src.main:app --host 0.0.0.0 --port 8000 --reload
```
Verify backend service health:
```bash
curl -s http://localhost:8000/health/live
# Expected response: {"status":"live"}

curl -s http://localhost:8000/health/ready
# Expected response: {"status":"ready","database":"connected","redis":"connected"}
```

### Step 6: Start Frontend Dashboard Development Server
In a separate terminal, install Node.js dependencies and launch the Vite development server:
```bash
cd apps/dashboard
npm install
npm run dev
```
The trading dashboard is accessible locally at `http://localhost:5173`. API requests are automatically proxied to `http://localhost:8000`.

---

## 5. Container Build & Packaging Architecture

Project ORION uses multi-stage Docker builds to produce minimal, security-hardened production container images for both the ASGI backend and the web dashboard.

### 5.1 Trading Engine Container (`docker/apps/trading-engine/Dockerfile`)
- **Base Image:** `python:3.11-slim` (Debian 11 bullseye-slim).
- **Security Profile:**
  - Creates a dedicated unprivileged system user and group: `orion` (`uid=999`, `gid=999`).
  - All application code and installed packages are owned by `orion:orion`.
  - Process executes strictly as non-root (`USER orion`).
- **Dynamic Port Binding:** The container runtime reads the cloud platform's `$PORT` environment variable via shell parameter expansion (`${PORT:-8000}`).
- **Entrypoint:**
  ```bash
  exec uvicorn apps.trading_engine.src.main:app --host 0.0.0.0 --port ${PORT:-8000}
  ```

### 5.2 Dashboard Web Container (`apps/dashboard/Dockerfile`)
- **Stage 1 (Builder):** `node:20-alpine` installs dependencies and compiles the Vite TypeScript application into optimized static assets (`dist/`).
- **Stage 2 (Runtime):** `nginx:1.27-alpine` provides a lightweight, hardened web server.
- **Routing Configuration:** Configured with client-side SPA routing fallback (`try_files $uri $uri/ /index.html`).
- **Security Profile:** Runs as unprivileged non-root user `nginx`, with PID files and cache directories relocated to `/tmp`.

### 5.3 Local Image Build Verification
To test container packaging locally prior to cloud deployment:
```bash
# Build Trading Engine container
docker build -t orion-api:local -f docker/apps/trading-engine/Dockerfile .

# Build Dashboard container
docker build -t orion-dashboard:local -f apps/dashboard/Dockerfile apps/dashboard
```

---

## 6. Production Cloud Deployment Blueprint (Render PaaS)

The authoritative production infrastructure is defined in `render.yaml`. The blueprint orchestrates four managed cloud components:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        RENDER PLATFORM-AS-A-SERVICE                     │
│                                                                        │
│   ┌──────────────────────┐               ┌─────────────────────────┐   │
│   │   orion-dashboard    │               │        orion-api        │   │
│   │   (Nginx Web Service)│               │    (ASGI Web Service)   │   │
│   │   Plan: free         │               │    Plan: starter        │   │
│   └──────────┬───────────┘               └────────────┬────────────┘   │
│              │ (Browser HTTPS)                        │ (Internal Mesh)│
│              └────────────────────────────────────────┤                │
│                                                       │                │
│                                  ┌────────────────────┴────────────┐   │
│                                  │                                 │   │
│                    ┌─────────────▼────────────┐      ┌─────────────▼──────────┐
│                    │      orion-postgres      │      │       orion-redis      │
│                    │   (PostgreSQL 15 DB)     │      │   (Redis 7 Instance)   │
│                    │   Plan: basic-1gb        │      │   Plan: free           │
│                    │   ipAllowList: []        │      │   ipAllowList: []      │
│                    └──────────────────────────┘      └────────────────────────┘
└────────────────────────────────────────────────────────────────────────┘
```

### 6.1 Render Blueprint Resources

| Resource Name | Service Type | Runtime Environment | Render Plan | Network Isolation | Health Check |
|---|---|---|---|---|---|
| `orion-api` | Web Service | Docker (`docker/apps/trading-engine/Dockerfile`) | `starter`* | Public HTTPS | `GET /health/live` |
| `orion-dashboard` | Web Service | Docker (`apps/dashboard/Dockerfile`) | `free` | Public HTTPS | `GET /` |
| `orion-postgres` | Managed Relational DB | PostgreSQL 15 | `basic-1gb`* | Private Mesh (`ipAllowList: []`) | Internal Port 5432 |
| `orion-redis` | Managed Key-Value Store| Redis 7 | `free` | Private Mesh (`ipAllowList: []`) | Internal Port 6379 |

> [!IMPORTANT]
> **Mandatory Paid Plan Dependencies:**
> 1. **`orion-api` requires the `starter` plan:** Render's free tier web services do NOT support the `preDeployCommand` lifecycle hook. The `starter` plan is mandatory to ensure database migrations execute deterministically before traffic cutover.
> 2. **`orion-postgres` requires the `basic-1gb` plan:** Render free-tier databases expire and are automatically deleted after 30 days. The `basic-1gb` plan provides persistent SSD storage and automated daily snapshots.
> 3. Provisioning these services requires an active payment method on the deploying Render account.

### 6.2 Render Blueprint Environment Variable Mappings

The `render.yaml` specification maps configuration variables dynamically across the service mesh:

- `ORION_ENVIRONMENT`: Set to `production`.
- `ORION_LOG_LEVEL`: Set to `INFO`.
- `ORION_DATABASE_URL`: Automatically linked to `orion-postgres` connection string via Render service discovery (`fromDatabase`).
- `ORION_REDIS_URL`: Automatically linked to `orion-redis` connection string via Render service discovery (`fromService`).
- `ORION_RUN_MIGRATIONS`: Set to `"false"` (migrations are decoupled and executed strictly via `preDeployCommand`).
- `ORION_JWT_SECRET_KEY`: Set to `generateValue: true` (Render automatically provisions a secure, cryptographically random secret).
- `ORION_CORS_ORIGINS`: Set to `https://orion-dashboard.onrender.com` (or buyer's custom dashboard domain).
- `ORION_WORKER_ENABLED`: Set to `"false"` (safety invariant: autonomous trading loop disabled by default).
- `VITE_API_URL`: Configured on `orion-dashboard` pointing to `https://orion-api.onrender.com`.

---

## 7. Pre-Deployment Database Migration Hook

Database schema evolution is decoupled from the application server lifespan using the standalone migration runner `scripts/deploy/migrate.py`.

### 7.1 Migration Hook Execution Lifecycle
1. **Trigger:** Render detects a new commit on `main` or an operator initiates a manual deploy.
2. **Container Build:** Render builds the `orion-api` Docker container image.
3. **Pre-Deploy Container Execution:** Before directing traffic to the new image, Render spawns an ephemeral container running:
   ```bash
   python scripts/deploy/migrate.py
   ```
4. **Target Head Discovery & DDL Execution:** The script connects to the target PostgreSQL database using the resolved connection string, discovers expected migration heads (`0015_onboarding_progress`), and applies forward DDL changes (`alembic upgrade head`).
5. **Application Traffic Cutover & Failure Isolation:**
   - **On Success (Exit Code 0):** Render performs a rolling restart, directing incoming traffic to the newly migrated application containers.
   - **On Failure (Exit Code 1):** The pre-deploy hook fails immediately. Render cancels the deployment and aborts the rollout. The existing running containers continue serving user traffic, providing migration failure isolation before application deployment.

### 7.2 Safety Invariants in `migrate.py`
- Strictly forward-only: executes `alembic upgrade head`.
- Never performs destructive drop, table wipe, or database reset operations.
- Never performs automatic downgrades during deployment.
- Masks database connection credentials in all execution logs.

---

## 8. Autonomous Worker Process Configuration

Project ORION includes an autonomous market analysis and strategy execution loop (`apps/trading-engine/src/worker.py`).

### 8.1 Default Safety Invariant
In production deployments, the autonomous worker is **disabled by default**:
```yaml
ORION_WORKER_ENABLED: "false"
```
When disabled, the trading engine operates strictly as an ASGI API server responding to user-initiated HTTP and WebSocket requests. No background market polling, indicator calculation, or paper trade generation takes place.

### 8.2 Safe Worker Activation Runbook
Once the acquiring team has verified market data feeds and paper trading parameters:
1. Verify market data provider connectivity (e.g., TwelveData API key configured and active).
2. Configure worker instrument basket via `ORION_WORKER_SYMBOLS` (e.g., `EUR/USD,GBP/USD,USD/JPY`).
3. Set initial virtual equity via `ORION_PAPER_BALANCE` (default: `100000.00`).
4. Update environment setting in Render dashboard:
   - Key: `ORION_WORKER_ENABLED`
   - Value: `"true"`
5. Save changes and trigger a manual deployment.
6. Inspect `orion-api` logs to verify worker cycle initialization:
   ```
   [INFO] [worker] Autonomous trading worker started. Symbols: ['EUR/USD', 'GBP/USD', 'USD/JPY']
   ```

---

## 9. Health, Readiness, and Observability Probes

The backend trading engine exposes standardized health, readiness, and metrics endpoints:

### 9.1 Liveness Probe (`GET /health/live`)
- **Purpose:** Verifies that the Uvicorn ASGI process is alive and responding to HTTP requests.
- **Render Configuration:** Configured as Render's primary health check path (`healthCheckPath: /health/live`).
- **Response Format:**
  ```json
  {"status": "live"}
  ```
- **HTTP Status:** `200 OK`.

### 9.2 Readiness Probe (`GET /health/ready`)
- **Purpose:** Verifies that backing infrastructure dependencies are operational before accepting user traffic.
- **Checks Performed:**
  1. **PostgreSQL Connectivity:** Executes `SELECT 1` via SQLAlchemy asyncpg pool.
  2. **Redis Connectivity:** Executes `PING` via Redis client.
- **Response Format (Operational):**
  ```json
  {
    "status": "ready",
    "checks": {
      "database": "connected",
      "redis": "connected"
    }
  }
  ```
- **HTTP Status:** `200 OK` if all dependencies respond; `503 Service Unavailable` if database or cache is unreachable.

### 9.3 Prometheus Metrics Exposition (`GET /metrics`)
- **Purpose:** Exposes real-time operational and business telemetry formatted for Prometheus scrapers.
- **Exposed Metrics:**
  - `http_requests_total`: Total HTTP requests partitioned by method, endpoint, and status code.
  - `http_request_duration_seconds`: Request latency histogram.
  - `orion_db_pool_size`, `orion_db_pool_checked_out`: Connection pool utilization.
  - `orion_active_orders_count`, `orion_open_positions_count`: Domain paper trading metrics.
- **Access Control:** Protected by optional `ORION_METRICS_TOKEN` Bearer token. If configured, scrape requests must include `Authorization: Bearer <token>`.

---

## 10. Backup & Snapshot Procedures

Project ORION includes an operational backup and retention suite located in `project-orion/backup/`.

### 10.1 PostgreSQL Database Backups (`backup/database-backup.sh`)
The database backup script produces PostgreSQL logical dumps with integrity verification:
- **Format:** PostgreSQL Custom Format (`pg_dump -Fc`), which supports selective table restoration and parallel decompression.
- **Checksum Sidecar:** Computes a cryptographic SHA-256 sidecar file (`.dump.sha256`) immediately following dump generation.
- **TOC Verification:** Runs `pg_restore -l` against the generated dump to ensure the archive structure and Table of Contents are uncorrupted.
- **Encryption:** Optionally encrypts the dump archive using AES-256-CBC via OpenSSL when `BACKUP_ENCRYPTION_KEY` is provided in the environment.

#### Manual Backup Execution:
```bash
# Execute standard unencrypted backup
bash backup/database-backup.sh --output-dir backups/manual

# Verify generated artifacts
ls -la backups/manual/
# Output includes:
# orion-db-full-YYYYMMDD_HHMMSS.dump
# orion-db-full-YYYYMMDD_HHMMSS.dump.sha256
```

### 10.2 Redis Key-Value Store Snapshots (`backup/redis-backup.sh`)
- Triggers an asynchronous point-in-time snapshot using the Redis `BGSAVE` command.
- Polls `LASTSAVE` until the dump completes, then archives `dump.rdb` with a timestamp sidecar.

### 10.3 Backup Retention Policy (`backup/retention-policy.sh`)
- Enforces Grandfather-Father-Son rotation on local and mounted backup storage:
  - Daily backups retained for 7 days.
  - Weekly backups retained for 30 days.
  - Monthly backups retained for 90 days.
  - Prunes expired artifacts while preserving associated checksum sidecars.

### 10.4 Render Managed Automated Backups
In addition to script-based backups, the `orion-postgres` instance on Render's `basic-1gb` tier automatically performs daily system snapshots retained for 7 days, accessible directly within the Render management console.

---

## 11. Disaster Recovery & Restoration Runbook

Disaster recovery in Project ORION is governed by the principle of **Isolated Target Restoration**, codified in `backup/restore-database.sh`.

### 11.1 Primary Architecture: Isolated Target Database Restoration
To prevent catastrophic accidental overwrites, `restore-database.sh` enforces the following safety rules:
1. **Explicit Target URL Required:** The script requires an explicit `--target-url` parameter. It will NEVER default to or infer the active production database connection string.
2. **Pre-Restore Checksum Verification:** Verifies the archive SHA-256 sidecar (`sha256sum -c`) before opening any connection to the database.
3. **Pre-Restore TOC Validation:** Validates the archive Table of Contents (`pg_restore -l`) to confirm archive completeness.
4. **Prohibition of Destructive DDL:** Normal restoration strictly prohibits `DROP DATABASE` or `CREATE DATABASE`.

### 11.2 Standard Isolated Target Restoration Runbook

#### Step 1: Provision Isolated Target Database
Provision an isolated target database (e.g., `orion_recovery_test` or an ephemeral recovery instance).

#### Step 2: Validate Backup Integrity
```bash
sha256sum -c backups/orion-db-full-20260923_183834.dump.sha256
# Expected output: backups/orion-db-full-20260923_183834.dump: OK
```

#### Step 3: Execute Restoration to Target Database
```bash
bash backup/restore-database.sh \
  --target-url "postgresql://orion:REDACTED@recovery-host:5432/orion_recovery_test" \
  backups/orion-db-full-20260923_183834.dump
```

#### Step 4: Verify Schema and Domain Integrity
Run the semantic verification script against the restored target database:
```bash
poetry run python scripts/verify_restore.py \
  --target-url "postgresql+asyncpg://orion:REDACTED@recovery-host:5432/orion_recovery_test"
```
The verification script confirms:
- Target Alembic migration head matches the expected canonical revision (`0015_onboarding_progress`).
- Table count matches the dynamically derived model inventory: 29 tables demonstrated in Phase 6C restore verification (28 declarative domain models + `alembic_version`).
- Zero NULL account balances and virtual balance preservation ($0.00 capital at risk).

### 11.3 Emergency Manual In-Place Reset Procedure
If primary storage suffers irrecoverable corruption and an in-place restore against the production instance is required:
```bash
bash backup/restore-database.sh \
  --target-url "postgresql://orion:REDACTED@prod-host:5432/orion_prod" \
  --emergency-manual-in-place-schema-reset \
  backups/orion-db-full-20260923_183834.dump
```
> [!CAUTION]
> The `--emergency-manual-in-place-schema-reset` flag drops and recreates the `public` schema in the target database. To prevent accidental execution, the script prompts the operator to manually type `RESTORE_EMERGENCY_PROD` before proceeding.

### 11.4 Certified Disaster Recovery Metrics
As certified in `docs/EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md`:
- **Physical Restore Duration:** **7 seconds** (measured from $T_{start} = \text{18:41:01}$ to $T_{finish} = \text{18:41:08}$).
- **RTO / RPO Assessment:** The demonstrated restore completed in 7 seconds, within the <60-minute operational RTO target. The documented operational RPO target is <24 hours (supported by daily snapshot scheduling; not directly proved by the single-point physical restore demonstration).
- **Table Inventory Restored:** Demonstrated restore verification of 29 tables derived from SQLAlchemy declarative models and `alembic_version`.

---

## 12. Application Rollback & Schema Forward-Fix Policy

### 12.1 Web Application Rollback (Rolling Container Rollback)
Render PaaS maintains an immutable deployment history of container builds:
1. Navigate to **Render Dashboard** -> **Services** -> `orion-api` (or `orion-dashboard`).
2. Open the **Events** or **Deploys** tab.
3. Locate the previous stable deployment SHA.
4. Click **Rollback to this version**.
5. Render diverts incoming traffic to the previous container release during the rolling rollback process.

### 12.2 Database Schema Evolution: Forward-Fix Policy
> [!WARNING]
> **STRICT POLICY: NEVER EXECUTE `alembic downgrade` IN PRODUCTION.**
>
> Executing Alembic downgrades against a production relational database introduces severe risks of silent data truncation, dropped constraint anomalies, and corrupted user sessions.

Project ORION strictly enforces a **Forward-Fix Only Policy** for database schema management:
1. All database migrations are authored to be **expand-contract compatible** (e.g., adding nullable columns, adding new tables, or maintaining dual-writing during transitional phases).
2. If a deployed schema change causes application issues, the engineering team must author a new forward migration (e.g., `alembic revision -m "fix_previous_issue"`) that remedies the schema while preserving existing data.
3. The forward migration is committed, reviewed, and deployed via the standard `preDeployCommand` pipeline.

---

## 13. External Dependency Provisioning Guide

Prior to production launch, the acquiring team must configure accounts and credentials for the following external services:

### 13.1 Render Cloud PaaS Account
1. Create or log in to a team account at [render.com](https://render.com).
2. Navigate to **Account Settings** -> **Billing** and register a corporate payment method (required for `starter` and `basic-1gb` tiers).
3. Connect the GitHub organization containing the Project ORION repository.
4. Select **New Blueprint Instance** and point Render to `render.yaml` on branch `main`.

### 13.2 Custom Domain & Automated TLS Certificates
1. In the Render Dashboard under `orion-api`, navigate to **Settings** -> **Custom Domains**.
2. Add the custom API domain (e.g., `api.orion-trading.com`).
3. Add the custom Dashboard domain under `orion-dashboard` (e.g., `app.orion-trading.com`).
4. In your DNS management console (e.g., Cloudflare, Route53, Namecheap), create the corresponding CNAME records pointing to the Render service hostnames.
5. Render automatically provisions, validates, and renews Let's Encrypt TLS certificates.
6. Update `ORION_CORS_ORIGINS` on `orion-api` to include the custom dashboard domain.

### 13.3 TwelveData Market Data Feed
1. Register for an API key at [twelvedata.com](https://twelvedata.com).
2. Configure the following environment variables in Render for `orion-api`:
   - `ORION_MARKET_DATA_PROVIDER`: Set to `twelvedata`.
   - `ORION_MARKET_DATA_API_KEY`: Input TwelveData API key.
   - `ORION_MARKET_DATA_BASE_URL`: Set to `https://api.twelvedata.com`.

### 13.4 Stripe Test Mode Billing Setup
1. Log in to the [Stripe Dashboard](https://dashboard.stripe.com) and ensure the account is in **Test Mode**.
2. Retrieve the Stripe Test Secret Key and Test Publishable Key.
3. Navigate to **Developers** -> **Webhooks** and configure a webhook endpoint pointing to:
   `https://<your-api-domain>/api/v1/billing/webhook`
4. Subscribe to events: `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`.
5. Retrieve the Webhook Signing Secret.
6. Configure environment variables in Render:
   - `ORION_STRIPE_SECRET_KEY`: Input Stripe test secret key.
   - `ORION_STRIPE_WEBHOOK_SECRET`: Input Stripe webhook signing secret.

### 13.5 SMTP Transactional Email Gateway
1. Provision a transactional SMTP relay (e.g., SendGrid, Postmark, Mailgun, or AWS SES).
2. Complete domain sender verification (configure SPF, DKIM, and DMARC DNS records).
3. Configure environment variables in Render for `orion-api`:
   - `ORION_SMTP_HOST`: SMTP server hostname (e.g., `smtp.sendgrid.net`).
   - `ORION_SMTP_PORT`: SMTP port (`587` for STARTTLS, or `465` for SSL/TLS).
   - `ORION_SMTP_USER`: SMTP authentication username.
   - `ORION_SMTP_PASSWORD`: SMTP authentication password (stored securely in Render secrets).
   - `ORION_SMTP_USE_TLS`: Set to `"true"`.
   - `ORION_EMAIL_FROM`: Verified sender email address (e.g., `noreply@orion-trading.com`).
   - `ORION_APP_BASE_URL`: Public dashboard URL for verification links (e.g., `https://app.orion-trading.com`).

### 13.6 OANDA Practice Broker Sandbox
1. Register for an OANDA fxTrade practice account at [oanda.com](https://oanda.com).
2. Generate an API personal access token for the practice environment.
3. Retrieve the practice Account ID.
4. Configure environment variables in Render for `orion-api`:
   - `OANDA_ENVIRONMENT`: Set strictly to `practice`.
   - `OANDA_PRACTICE_API_KEY`: Input OANDA practice access token.
   - `OANDA_ACCOUNT_ID`: Input practice account identifier.

---

## 14. Routine Maintenance & Operational Runbooks

### 14.1 Cryptographic Secret Rotation Runbook

#### A. JWT Secret Key Rotation (`ORION_JWT_SECRET_KEY`)
- **Impact:** Rotates the HMAC-SHA256 token signing key. All existing active user JWT sessions are invalidated immediately; users must re-authenticate.
- **Procedure:**
  1. Generate a new secure 64-character hexadecimal key:
     ```bash
     openssl rand -hex 32
     ```
  2. In Render Dashboard -> `orion-api` -> **Environment**, update `ORION_JWT_SECRET_KEY`.
  3. Trigger a manual deploy.

#### B. Database Password Rotation
- **Impact:** Temporary connection disruption during restart.
- **Procedure:**
  1. In Render Dashboard -> `orion-postgres` -> **Settings**, update database password.
  2. Copy the updated internal connection string.
  3. Update `ORION_DATABASE_URL` in `orion-api`.
  4. Trigger a rolling restart of `orion-api`.

### 14.2 Relational Database Housekeeping
1. **Autovacuum Monitoring:** PostgreSQL 15 autovacuum is enabled by default. Inspect table bloat and transaction wraparound via psql:
   ```sql
   SELECT relname, n_dead_tup, last_vacuum, last_autovacuum FROM pg_stat_user_tables;
   ```
2. **Connection Pool Health:** Monitor active pool usage via the `/metrics` endpoint (`orion_db_pool_size`, `orion_db_pool_checked_out`). Ensure active connections do not exceed the PostgreSQL `max_connections` ceiling.

### 14.3 Redis Memory Management
1. Inspect memory usage:
   ```bash
   redis-cli info memory
   ```
2. Rate-limiting keys (`ratelimit:*`) and session cache keys are created with explicit TTL expiration. If memory pressure occurs, verify that Redis eviction policy is set to `volatile-lru`.

---

## 15. Production Readiness & Go-Live Checklist

Complete the following verification checklist prior to opening the platform to public beta users:

| Category | Checklist Verification Item | Command / Verification Method | Required Status | Verified? |
|---|---|---|:---:|:---:|
| **Infrastructure** | Render Blueprint deployed without error | Render Dashboard status shows all 4 services green | Active | [ ] |
| **Infrastructure** | Private network isolation verified | `orion-postgres` and `orion-redis` have `ipAllowList: []` | Enforced | [ ] |
| **Infrastructure** | Container non-root execution | Docker inspect shows user `orion` (`uid=999`) | Confirmed | [ ] |
| **Database** | Migrations at canonical head | `poetry run alembic current` -> `0015_onboarding_progress` | Synced | [ ] |
| **Database** | Decoupled pre-deploy migration | Verify `scripts/deploy/migrate.py` passes in build logs | Success | [ ] |
| **Database** | Table inventory completeness | Demonstrated restore verification of 29 tables | 29 Tables | [ ] |
| **Security** | Random JWT secret provisioned | `ORION_JWT_SECRET_KEY` length >= 32 characters | Strong | [ ] |
| **Security** | Rate limiting active | Request burst triggers HTTP 429 Too Many Requests | Verified | [ ] |
| **Security** | Anti-enumeration active | Auth routes return identical timing / responses | Verified | [ ] |
| **Security** | Metrics token configured | Unauthenticated requests to `/metrics` return 401 | Protected | [ ] |
| **Observability** | Liveness probe operational | `GET /health/live` returns HTTP 200 `{"status":"live"}` | 200 OK | [ ] |
| **Observability** | Readiness probe operational | `GET /health/ready` returns HTTP 200 with DB & Redis OK | 200 OK | [ ] |
| **Financial Safety** | Zero live brokerage connections | Confirm zero live trading endpoints in configuration | $0.00 Risk | [ ] |
| **Financial Safety** | Worker safety switch confirmed | Confirm `ORION_WORKER_ENABLED` is `"false"` initially | Gated | [ ] |
| **Billing** | Stripe Test Mode confirmed | Key verification passes; live keys structurally rejected | Test Mode | [ ] |
| **Communication**| SMTP delivery verified | Test registration email received with valid link | Delivered | [ ] |
| **Disaster Recovery**| Backup integrity demonstrated | SHA-256 sidecar passes; restore demonstrated in 7s (<60 min RTO target) | Certified | [ ] |

---

## 16. Buyer Handover & Operational Transfer Procedures

Upon execution of definitive acquisition agreements, operational control of Project ORION is transferred according to the following protocol:

### Step 1: GitHub Repository Transfer
1. Primary seller administrator navigates to **GitHub Repository Settings** -> **General** -> **Danger Zone**.
2. Select **Transfer ownership**.
3. Specify the buyer's GitHub Organization name.
4. Buyer administrator accepts the transfer invitation via GitHub notification.

### Step 2: Render PaaS Workspace & Cloud Asset Transfer
1. Primary seller administrator invites the buyer's engineering lead to the Render Team Workspace as an **Admin**.
2. Buyer configures the buyer organization billing profile under Render Billing.
3. Seller administrator transfers the **Owner** role to the buyer's lead.
4. Seller administrative accounts are removed from the workspace.

### Step 3: Domain Delegation & DNS Transfer
1. Buyer registers or provides the production apex domain.
2. Seller updates DNS zone records or transfers domain registrar management to the buyer.
3. Buyer provisions custom domains in Render, enabling automated TLS certificate renewal.

### Step 4: Third-Party Service Account Handover
1. **Stripe:** Transfer Stripe account ownership or invite buyer administrators under Stripe Team Settings.
2. **TwelveData:** Transfer account credentials or provision a new corporate API key.
3. **SMTP Gateway:** Transfer transactional email provider ownership (SendGrid, Postmark, etc.).

### Step 5: Post-Transfer Operational Verification
1. Buyer engineering team triggers a test deployment from branch `main` to verify CI/CD and pre-deploy hooks.
2. Execute the verification suite:
   ```bash
   poetry run pytest tests/unit/
   ```
3. Execute an isolated test database backup and restore using `backup/database-backup.sh` and `backup/restore-database.sh`.
4. Confirm successful receipt of transactional verification email in a staging environment.

### 16.1 Known Operational Limitations
- **Paper Trading Only:** The platform is engineered strictly for simulated paper trading and quant research. Live-money trading execution is not implemented and is structurally restricted.
- **Single-Region PaaS Architecture:** The Render blueprint operates in a single cloud region (e.g., Oregon or Frankfurt). Multi-region geographic failover requires external DNS routing and database cross-region replication not currently included in the PaaS blueprint.
- **Single-Worker Loop:** The autonomous strategy execution loop is designed to run in a single process to prevent duplicate signal generation across worker instances.
