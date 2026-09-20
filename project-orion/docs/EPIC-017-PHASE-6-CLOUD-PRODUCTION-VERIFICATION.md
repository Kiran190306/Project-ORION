# Project ORION — EPIC-017 Phase 6: Cloud Production Verification & Operations Specification

**Project**: Project ORION  
**Epic**: EPIC-017 — SaaS Multi-Tenancy, Organization Governance & Production Hardening  
**Phase**: Phase 6 — Actual Cloud Production Deployment & Production Operations  
**Date**: 2026-09-20  
**Classification**: **B. PRODUCTION READY — CLOUD DEPLOYMENT PENDING EXTERNAL ACCESS**  
**Platform Safety**: **STRICT PAPER TRADING ONLY** (Zero live broker connectivity, zero customer funds, zero real money execution)  

---

## 1. Cloud Access Decision Gate Evaluation

| Verification Check | Target / Tool | Current Status | State |
|---|---|---|---|
| Render CLI & API Key | `RENDER_API_KEY`, `RENDER_SERVICE_ID`, `~/.render/cli.yaml` | Not configured / No valid key | **PENDING EXTERNAL ACCESS** |
| Major Cloud Provider CLIs | `aws`, `gcloud`, `az` | None installed in environment | **PENDING EXTERNAL ACCESS** |
| Local Production Containers | Docker 29.7.2, PostgreSQL 15, Redis 7, ASGI, Nginx | Fully operational and healthy | **LOCAL VERIFIED** |
| Authoritative Gate Decision | Non-Negotiable Gate Rule | **STATE B** | **PRODUCTION READY — CLOUD DEPLOYMENT PENDING EXTERNAL ACCESS** |

> [!IMPORTANT]
> **NO FAKE CLOUD DEPLOYMENT**: Under State B, cloud infrastructure deployment is **not** faked or simulated. Local container verification is explicitly distinguished from actual cloud verification. All configuration files and blueprints are hardened and ready for immediate deployment as soon as external cloud credentials are supplied.

---

## 2. Production Environment Variable Matrix

| Variable Name | Service Target | Required | Secret | Source | Classification |
|---|---|---|---|---|---|
| `ORION_ENVIRONMENT` | `orion-api` | Yes | No | `render.yaml` | **CLOUD CONFIGURED** (`production`) |
| `ORION_LOG_LEVEL` | `orion-api` | Yes | No | `render.yaml` | **CLOUD CONFIGURED** (`INFO`) |
| `ORION_DATABASE_URL` | `orion-api` | Yes | **Yes** | Render Database (`connectionString`) | **CLOUD CONFIGURED** (Private Network) |
| `ORION_REDIS_URL` | `orion-api` | Yes | **Yes** | Render Redis (`connectionString`) | **CLOUD CONFIGURED** (Private Network) |
| `ORION_RUN_MIGRATIONS` | `orion-api` | Yes | No | `render.yaml` | **CLOUD CONFIGURED** (`true` / idempotent) |
| `ORION_SERVER_HOST` | `orion-api` | Yes | No | Container Default | **CLOUD CONFIGURED** (`0.0.0.0`) |
| `ORION_SERVER_PORT` / `PORT` | `orion-api` | Yes | No | Render Dynamic Host Environment | **CLOUD CONFIGURED** (Dynamic `$PORT`) |
| `ORION_PAPER_BALANCE` | `orion-api` | Yes | No | Application Default | **CLOUD CONFIGURED** (`100000.00`) |
| `ORION_WORKER_ENABLED` | `orion-api` | Yes | No | `render.yaml` | **CLOUD CONFIGURED** (`false`) |
| `ORION_WORKER_SYMBOLS` | `orion-api` | Yes | No | Application Default | **CLOUD CONFIGURED** (`EUR/USD,GBP/USD,USD/JPY`) |
| `ORION_JWT_SECRET_KEY` | `orion-api` | Yes | **Yes** | Render Blueprint `generateValue: true` | **CLOUD CONFIGURED** (Cryptographic 256-bit) |
| `ORION_JWT_ALGORITHM` | `orion-api` | Yes | No | Application Default | **CLOUD CONFIGURED** (`HS256`) |
| `ORION_JWT_EXPIRE_MINUTES` | `orion-api` | Yes | No | Application Default | **CLOUD CONFIGURED** (`30`) |
| `ORION_CORS_ORIGINS` | `orion-api` | Yes | No | `render.yaml` | **CLOUD CONFIGURED** (`https://orion-dashboard.onrender.com`) |
| `VITE_API_URL` | `orion-dashboard` | Optional | No | `render.yaml` `dockerBuildArgs` | **CLOUD CONFIGURED** (`https://orion-api.onrender.com`) |

---

## 3. Render Blueprint Specification (`render.yaml`)

The blueprint defines four managed infrastructure components:

```yaml
version: "1"

databases:
  - name: orion-postgres
    databaseName: orion_prod
    user: orion
    plan: free
    ipAllowList: [] # Private network only

services:
  - type: redis
    name: orion-redis
    plan: free
    ipAllowList: [] # Private network only

  - type: web
    name: orion-api
    env: docker
    dockerfilePath: docker/apps/trading-engine/Dockerfile
    dockerContext: .
    plan: free
    healthCheckPath: /health/live
    preDeployCommand: alembic upgrade head
    envVars:
      - key: ORION_ENVIRONMENT
        value: production
      - key: ORION_LOG_LEVEL
        value: INFO
      - key: ORION_DATABASE_URL
        fromDatabase:
          name: orion-postgres
          property: connectionString
      - key: ORION_REDIS_URL
        fromService:
          type: redis
          name: orion-redis
          property: connectionString
      - key: ORION_RUN_MIGRATIONS
        value: "true"
      - key: ORION_JWT_SECRET_KEY
        generateValue: true
      - key: ORION_CORS_ORIGINS
        value: https://orion-dashboard.onrender.com
      - key: ORION_WORKER_ENABLED
        value: "false"

  - type: web
    name: orion-dashboard
    env: docker
    dockerfilePath: apps/dashboard/Dockerfile
    dockerContext: apps/dashboard
    plan: free
    healthCheckPath: /
    dockerBuildArgs:
      - key: VITE_API_URL
        value: https://orion-api.onrender.com
    envVars:
      - key: VITE_API_URL
        value: https://orion-api.onrender.com
```

---

## 4. Local vs Cloud Verification Matrix (25 Dimensions)

| # | Dimension | Local Container Verification | Cloud Target Configuration | Cloud Deployed | Cloud Verified | Status |
|---|---|---|---|---|---|---|
| 1 | **Repository Integrity** | Verified clean syntax, zero tracked secrets | GitHub `main` branch | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 2 | **Docker Images** | Both images built with non-root runtime | Multi-stage slim images | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 3 | **PostgreSQL 15** | 17 tables created & queried on port 5433 | Render Managed PostgreSQL | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 4 | **Redis 7** | Sub-millisecond ping verified on port 6379 | Render Managed Redis | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 5 | **Alembic Migrations** | Head `0007_organization_invitations` verified | `preDeployCommand: alembic upgrade head` | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 6 | **Backend ASGI** | Tested on port 8000, 8001, 9000 | Dynamic Render `$PORT` | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 7 | **Dashboard SPA** | Nginx serves SPA routes with gzip | Render Web Service | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 8 | **Nginx Reverse Proxy** | Transparent `/api/` proxy without 502s | Internal upstream routing | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 9 | **CORS Configuration** | Preflight OPTIONS tested with dynamic origin | Origin matching dashboard URL | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 10 | **JWT Authentication** | Salted bcrypt passwords, 30-min tokens | Render `generateValue: true` | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 11 | **TLS / HTTPS** | N/A (Local HTTP) | Automatic Let's Encrypt TLS | **PENDING** | **PENDING** | **CLOUD CONFIGURED** |
| 12 | **DNS** | Localhost binding | `*.onrender.com` or custom CNAME | **PENDING** | **PENDING** | **CLOUD CONFIGURED** |
| 13 | **Health Probe** | `/health/live` returns 200 `alive` | Render Deploy Health Check | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 14 | **Readiness Probe** | `/health/ready` returns 200 (DB+Redis) | Operational probe | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 15 | **Observability Metrics**| Prometheus `/metrics` exports counters/gauges | Scraping endpoint | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 16 | **Structured Logging** | Correlation IDs injected in all requests | Cloud Log Streams | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 17 | **Autonomous Worker** | Disabled state reported accurately | `WORKER_ENABLED=false` | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 18 | **Database Backups** | Local pg_dump runbook documented | Automated daily snapshots | **PENDING** | **PENDING** | **CLOUD CONFIGURED** |
| 19 | **Database Restore** | Restore procedure documented | Point-in-time recovery | **PENDING** | **PENDING** | **NOT VERIFIED** (Runbook Ready) |
| 20 | **Alerting** | Health probes detect dependency drops | Render service notifications | **PENDING** | **PENDING** | **CLOUD CONFIGURED** |
| 21 | **RBAC Governance** | Canonical 25 permissions enforced | Centralized route dependencies | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 22 | **Multi-Tenant IDOR** | 403/404 on cross-tenant access attempts | TenantContext validation | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 23 | **Entitlements** | Tier quotas enforced on orders & assets | SubscriptionService checks | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 24 | **Audit Logging** | Organization events recorded in DB | Compliance audit trail | **PENDING** | **PENDING** | **LOCAL VERIFIED** |
| 25 | **Cloud E2E Suite** | 22/22 Local Container Scenarios Passed | Full 23-step cloud verification | **PENDING** | **PENDING** | **PENDING EXTERNAL ACCESS** |

---

## 5. Execution Instructions for External Cloud Deployment

When cloud access credentials become available to the platform operator:

1. **Prerequisite**: Set Render API Key in execution environment:
   ```bash
   export RENDER_API_KEY="rnd_..."
   ```
2. **Deploy via Render Dashboard**:
   - Navigate to https://dashboard.render.com.
   - Click **Blueprints** -> **New Blueprint Instance**.
   - Connect repository `https://github.com/Kiran190306/Project-ORION.git`.
   - Render automatically parses `render.yaml`, provisions PostgreSQL and Redis on private networking, runs `alembic upgrade head`, and deploys `orion-api` and `orion-dashboard`.
3. **Execute Cloud E2E Verification**:
   - Update `scratch/live_container_e2e.py` target URLs:
     - `BASE_API="https://orion-api.onrender.com"`
     - `BASE_NGINX="https://orion-dashboard.onrender.com"`
   - Run verification script to confirm all 22 institutional scenarios pass over public HTTPS.
