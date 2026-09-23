# Project ORION — Infrastructure Topology & Cloud Deployment Map

**Document Version:** 1.0.0<br>
**Target Milestone:** EPIC-027 Phase 7B Acquisition Due Diligence<br>
**Repository Working Copy:** `project-orion/`<br>
**Classification:** Confidential — Due Diligence Technical Data Room (Tier 2 / NDA)<br>
**Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Capital at Risk — Zero Live Broker Endpoints)

---

## 1. Executive Topology Summary

Project ORION's primary cloud deployment model is specified declaratively as an **Infrastructure-as-Code (IaC) Blueprint (`render.yaml`)** hosted on the **Render Platform-as-a-Service (PaaS)**. A companion local development topology is orchestrated using **Docker Compose**.

### Key Infrastructure Characteristics
- **4-Tier PaaS Blueprint:** Deploys exactly four managed resources: an ASGI Python API container, an Nginx static dashboard container, a managed PostgreSQL 15 database, and a managed Redis 7 instance.
- **Isolated Private Network:** Database and cache instances are completely closed to the public internet (`ipAllowList: []`) and accessible solely over Render's internal service mesh.
- **Decoupled Pre-Deployment Migration:** Database migrations execute in an isolated container job prior to web container boot (`preDeployCommand`).
- **Safety Status:** The autonomous trading loop is disabled by default (`ORION_WORKER_ENABLED=false`). Broker connections are structurally restricted to practice sandboxes.

---

## 2. Render PaaS Resource Topology

The authoritative production infrastructure is defined in `project-orion/render.yaml`:

| Resource Name | Service Type | Runtime Environment | Render Plan | Network Visibility | Health Endpoint |
|---|---|---|---|---|---|
| `orion-api` | Web Service | Docker (`trading-engine/Dockerfile`) | `starter`* | Public HTTPS | `GET /health/live` |
| `orion-dashboard` | Web Service | Docker (`dashboard/Dockerfile`) | `free` | Public HTTPS | `GET /` (HTTP 200) |
| `orion-postgres` | Managed Relational DB | PostgreSQL 15 | `basic-1gb`* | Internal Private Network | Internal TCP Port 5432 |
| `orion-redis` | Managed Key-Value Store| Redis 7 | `free` | Internal Private Network | Internal TCP Port 6379 |

*\*Note on Paid Plan Dependencies: The `starter` web service plan is required by Render to support the `preDeployCommand` migration hook. The `basic-1gb` database plan provides persistent SSD storage, automated daily snapshots, and eliminates the 30-day expiration of Render's free tier. Provisioning these plans requires an active payment method on the deploying Render account.*

---

## 3. API Service (`orion-api`)

- **Container Image:** Built from `docker/apps/trading-engine/Dockerfile` (Debian 11 / Python 3.11-slim base).
- **Process Entrypoint:** `exec uvicorn apps.trading_engine.src.main:app --host 0.0.0.0 --port ${PORT:-8000}`
- **Dynamic Port Binding:** The container runtime reads Render's assigned `$PORT` environment variable (typically port `10000` or `8000`).
- **Process Privilege:** Runs as unprivileged non-root user `orion` (`uid=999`).
- **Pre-Deploy Execution:** Render runs `python scripts/deploy/migrate.py` in an ephemeral container prior to routing traffic to new container builds. If migrations fail, the deployment aborts with zero impact on running traffic.

---

## 4. Dashboard Service (`orion-dashboard`)

- **Container Image:** Multi-stage build from `apps/dashboard/Dockerfile` (Node 20 Alpine builder compiling Vite bundle -> Nginx 1.27 Alpine runtime).
- **Web Server:** Unprivileged Nginx instance serving pre-compiled static HTML, JavaScript, and CSS assets.
- **SPA Routing:** Configured with fallback routing (`try_files $uri $uri/ /index.html`) to support client-side React Router navigation.
- **Reverse Proxy:** Proxies API requests to the backend trading engine using internal DNS resolution.

---

## 5. Relational Storage (`orion-postgres`)

- **Engine:** PostgreSQL 15 managed by Render.
- **Database Name:** `orion_prod` (User: `orion`).
- **Network Ingress:** Strict zero-trust allowlist (`ipAllowList: []`). The database cannot be reached from the public internet.
- **Connection Mechanics:** The backend connects asynchronously via `asyncpg` (`postgresql+asyncpg://...`). Render injects the private connection string dynamically via `fromDatabase.property: connectionString`.
- **Storage Lifecycle:** Persistent SSD backing with automated daily platform-level snapshots.

---

## 6. In-Memory Cache & Distributed Lock (`orion-redis`)

- **Engine:** Redis 7 managed by Render.
- **Network Ingress:** Private network only (`ipAllowList: []`).
- **Connection Mechanics:** Connected via `redis.asyncio` client using Render's internal private connection string (`fromService.property: connectionString`).
- **Workload:** Sliding-window rate limiting (token bucket Lua scripts), market quote caching, and distributed synchronization locks.

---

## 7. Background Worker State (`ORION_WORKER_ENABLED`)

- **Process Model:** The autonomous trading worker is implemented as an asynchronous task loop (`AutonomousWorkerCoordinator`) embedded within the `orion-api` process.
- **Current Operational Invariant:** The worker is **disabled by default** in configuration (`ORION_WORKER_ENABLED=false`).
- **Safety State:** When disabled, health check probes confirm: `"Autonomous worker is disabled (ORION_WORKER_ENABLED=false)"`. Prometheus metrics export `orion_worker_status 0.0`.
- **Execution Invariant:** When enabled by risk committee authorization, the worker operates strictly against simulated paper balances ($0.00 capital at risk).

---

## 8. Private Networking & Service Isolation

```
Render Cloud Platform Boundary
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   Public Internet                                                           │
│         │                                                                   │
│         ▼ (HTTPS:443)                                                       │
│   ┌───────────────┐               (Internal API Calls)                      │
│   │orion-dashboard│ ─────────────────────────────────┐                      │
│   └───────────────┘                                  │                      │
│                                                      ▼                      │
│   ┌───────────────┐ (HTTPS:443)              ┌───────────────┐              │
│   │ Public Client │ ────────────────────────▶ │   orion-api   │              │
│   └───────────────┘                          └───────┬───────┘              │
│                                                      │                      │
│ ═════════════════════════════════════════════════════╪════════════════════  │
│ Render Private Service Mesh (ipAllowList: [])        │                      │
│                                                      │                      │
│                   ┌──────────────────────────────────┴───────────────┐      │
│                   ▼                                                  ▼      │
│          ┌─────────────────┐                                ┌─────────────┐ │
│          │ orion-postgres  │                                │ orion-redis │ │
│          │ (PostgreSQL 15) │                                │  (Redis 7)  │ │
│          └─────────────────┘                                └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Local Development Infrastructure (Docker Compose)

For local development and testing, two Compose definitions are provided:

### 9.1 Full Application Stack (`docker-compose.yml`)
Orchestrates all four application tiers locally:
- `orion-postgres`: `postgres:15-alpine` mapped to host port `5433:5432`.
- `orion-redis`: `redis:7-alpine` mapped to host port `6379:6379`.
- `orion-trading-engine`: Built from Dockerfile, mapped to host port `8000:8000`.
- `orion-dashboard`: Built from Dockerfile, mapped to host port `3000:80`.

### 9.2 Bare-Metal Dependency Stack (`docker-compose.dev.yml`)
Provisions only storage dependencies for developers running Python and Node directly on their workstations:
- `postgres:15-alpine` on host port `5433:5432`.
- `redis:7-alpine` on host port `6379:6379`.

---

## 10. Health, Readiness & Metrics Telemetry

The platform provides standard HTTP health and monitoring probes:

| Probe Path | Probe Type | Checked Dependencies | Expected Healthy Response |
|---|---|---|---|
| `/health/live` | Process Liveness | ASGI Event Loop | HTTP 200 `{"status": "ok"}` |
| `/health/ready` | Service Readiness | PostgreSQL (`SELECT 1`) & Redis (`PING`) | HTTP 200 `{"status": "ready"}` (HTTP 503 on failure) |
| `/metrics` | Prometheus Telemetry | In-memory Metrics Registry | HTTP 200 (Prometheus text exposition format) |

---

## 11. Database Migration Execution Model

- **Decoupled Pre-Deploy Hook:** Executed via Render's `preDeployCommand: python scripts/deploy/migrate.py`.
- **Process Isolation:** Runs inside a dedicated container instance before traffic routing shifts.
- **Fail-Fast Safety:** If database locks or schema errors occur, the script logs structured diagnostics and exits with code `1`. Render immediately cancels deployment, providing migration failure isolation before application deployment.

---

## 12. Backup & Disaster Recovery Architecture

- **Logical Backup Generation:** `backup/database-backup.sh` extracts PostgreSQL custom-format (`.dump`) archives.
- **Integrity Sidecars:** Generates SHA-256 checksum files verified prior to any restoration attempt.
- **Encryption:** Supports optional OpenSSL AES-256-CBC encryption (`BACKUP_ENCRYPTION_KEY`).
- **Physical Restore Demonstration (EPIC-027 Phase 6C):**
  - **Demonstrated Physical Restore Duration:** **7 seconds** ($T_{start} = \text{2026-09-23T18:41:01+05:30}$, $T_{finish} = \text{2026-09-23T18:41:08+05:30}$).
  - **RTO / RPO Assessment:** The demonstrated restore completed in 7 seconds, within the <60-minute operational RTO target. The documented operational RPO target is <24 hours. (The physical restore demonstration verified the restore mechanism and duration; operational RPO relies on daily snapshot scheduling).

---

## 13. External Service Boundaries

| Service Provider | Integration Interface | Invariant / Boundary Constraint |
|---|---|---|
| **Stripe** | REST API (`api.stripe.com`) | Test Mode only (test-mode secret keys). Live production keys are rejected. |
| **OANDA** | REST API (`api-fxpractice.oanda.com`)| Practice sandbox only. Live endpoints structurally forbidden. |
| **TwelveData** | REST API (`api.twelvedata.com`) | Historical & simulated candle ingestion. |
| **SMTP Provider** | SMTP (Port 587/465) | Transactional notifications containing mandatory paper trading disclosures. |

---

## 14. Deployment Dependencies & Billing Prerequisites

To reproduce the cloud deployment on Render, the buyer must satisfy these operational prerequisites:
1. **Render Account & Workspace:** An active Render user account with an associated workspace.
2. **Payment Method:** Render requires a valid credit card on file to provision paid service plans (`starter` for web service, `basic-1gb` for PostgreSQL).
3. **Repository Connection:** Render requires connecting the GitHub repository via the Render Web Dashboard (Render does not allow programmatic blueprint creation via REST API).

---

## 15. Current Verified State

- **Render Live URLs (Certified in EPIC-018):**
  - Production API: `https://orion-api-68u2.onrender.com`
  - Production Dashboard: `https://orion-dashboard-6d3z.onrender.com`
- **Blueprint Local Validation:** Validated via Render CLI (`render blueprints validate render.yaml` -> Valid: true, 0 errors, 4 resources).
- **Physical Restore:** Certified in isolated Docker container (7 seconds duration; demonstrated restore verification of 29 tables derived from SQLAlchemy declarative models and alembic_version).

---

## 16. External Verification Required

1. **Custom Domain Status:** The repository uses `https://app.oriontrading.io` and `https://oriontrading.io` as default template strings in emails and configuration. Production deployments currently operate on `*.onrender.com`. DNS domain registration and registrar transfer must be verified directly with the seller.
2. **Third-Party Credentials:** Stripe developer keys, OANDA practice tokens, and SMTP relay credentials must be provisioned by the operator.
3. **Helm / Kubernetes Status:** Kubernetes manifests and Helm charts exist in `deployment/helm/orion/` as architectural reference designs; they are **not** active production infrastructure.
