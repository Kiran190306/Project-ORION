# EPIC-027 PHASE 6 — CLOUD DEPLOYMENT, DEVOPS & BACKUP HARDENING AUDIT

**Phase:** EPIC-027 Phase 6 — Cloud Deployment, DevOps & Backup Hardening
**Repository:** `Project-ORION` (`c:\Users\Shree\CascadeProjects\forex-trading-platform-architecture\project-orion`)
**Git Baseline:** `c2e224a` (`feat(onboarding): implement first-login onboarding UX`)
**Branch:** `main` (synchronized with `origin/main`)
**Audit Execution Date:** 2026-09-23
**Auditor Role:** Principal Cloud Architect, Lead DevOps & SRE Engineer, Infrastructure Security Specialist
**Final Classification:** `B — IMPLEMENTATION READY WITH EXTERNAL DEPENDENCIES` *(with Production Go-Live `C — IMPLEMENTATION BLOCKED` pending isolated restore demonstration)*

---

## 1. Executive Summary

This comprehensive audit evaluates the cloud deployment topology, infrastructure-as-code configuration, DevOps automation, database migration safety, and disaster recovery posture of **Project ORION** following the successful implementation and verification of EPIC-027 Phase 5B (`c2e224a`).

The objective is to determine whether Project ORION is operationally primed for production cloud deployment and hardening on the Render PaaS platform, identifying architectural flaws, security gaps, operational single-points-of-failure, and external dependencies before code or infrastructure modifications occur.

### Key Audit Findings:

1. **Safety Invariants Are Exceptional (VERIFIED):**
   The platform enforces rigorous defense-in-depth safety invariants at the code level. The default execution adapter is strictly `PaperExecutionAdapter`, the autonomous trading worker is disabled by default (`ORION_WORKER_ENABLED=false`), Stripe operations reject live keys with `LiveCredentialsForbiddenError`, and `BrokerEndpointValidator` terminates and fails closed upon detecting any non-sandbox broker URL (such as OANDA live endpoints). The system guarantees **$0.00 capital at risk**.

2. **Render Free-Tier Ephemeral Risks (BLOCKER for Production Go-Live):**
   The current `render.yaml` blueprint specifies `plan: free` across all four services (`orion-postgres`, `orion-redis`, `orion-api`, `orion-dashboard`). On Render's Free tier:
   - PostgreSQL databases **expire and are permanently deleted after 30 days**.
   - Web services spin down after 15 minutes of inactivity, resulting in a **50–90 second cold-start latency**.
   - Redis is ephemeral (25MB RAM, in-memory only, no disk persistence).
   - Automated point-in-time recovery (PITR) and automated backups are completely absent.

3. **Backup Script Corruption & Managed Database Incompatibility (BLOCKER):**
   While `database-backup.sh` implements AES-256-CBC encryption and S3 upload capabilities:
   - `backup/retention-policy.sh` is syntactically broken (lines 33–56 contain accidental LLM tool prompt text), causing instant shell execution failure.
   - `backup/restore-database.sh` relies on connecting to maintenance database `postgres` and executing `DROP DATABASE ...` / `CREATE DATABASE ...`. On managed cloud databases (Render, AWS RDS), the unprivileged tenant user lacks superuser permissions, rendering the restore script non-functional.
   - **Crucially: An end-to-end isolated restore demonstration has never been executed.**

4. **Database Migration Race Condition Risk (PARTIALLY VERIFIED):**
   In `render.yaml`, `ORION_RUN_MIGRATIONS: "true"` causes the FastAPI web container lifespan to run `alembic upgrade head` upon boot. If multiple container instances start or if rolling deploys occur, concurrent DDL execution can trigger table lock deadlocks and migration corruption.

5. **External Dependencies & Missing Services:**
   - Celery is **not present** in the codebase (the platform uses an in-process `asyncio` coordinator).
   - Transactional email delivery lacks an outbound SMTP or AWS SES adapter (only `MockEmailAdapter` and `ConsoleEmailAdapter` are implemented).
   - `/metrics` exposes Prometheus telemetry to the public internet without authentication.

---

## 2. Git Baseline

Verification of the local repository against upstream `origin/main` was executed:

```
Commit:  c2e224a6955a549a177db65b41b65b4c081efe03
Message: feat(onboarding): implement first-login onboarding UX
Branch:  main
Tracking: origin/main [up to date]
```

- **Commit Cleanliness:** Commit `c2e224a` cleanly encapsulates all EPIC-027 Phase 5B frontend components (`OnboardingWizard.tsx`, step components, `useOnboarding.ts`, Vitest suite, and documentation).
- **Working Tree Notice:** Working directory contains uncommitted Phase 5A backend changes/tests from prior development; git baseline on `main` is synchronized with `origin/main`.
- **Classification:** `VERIFIED`.

---

## 3. Render Deployment Architecture

The infrastructure configuration is governed by `render.yaml` at the repository root.

```yaml
services:
  # 1. Backend API (FastAPI)
  - type: web
    name: orion-api
    env: docker
    dockerfilePath: docker/apps/trading-engine/Dockerfile
    plan: free
    healthCheckPath: /health/live
    envVars:
      - key: ORION_ENV
        value: production
      - key: ORION_LOG_LEVEL
        value: INFO
      - key: ORION_RUN_MIGRATIONS
        value: "true"
      - key: ORION_WORKER_ENABLED
        value: "false"
      - key: ORION_DATABASE_URL
        fromDatabase:
          name: orion-postgres
          property: connectionString
      - key: ORION_REDIS_URL
        fromRedis:
          name: orion-redis
          property: connectionString
      - key: ORION_JWT_SECRET_KEY
        generateValue: true
      - key: ORION_CORS_ORIGINS
        value: https://orion-dashboard.onrender.com

  # 2. Frontend Terminal (React SPA + Nginx)
  - type: web
    name: orion-dashboard
    env: docker
    dockerfilePath: apps/dashboard/Dockerfile
    plan: free
    healthCheckPath: /
    envVars:
      - key: VITE_API_URL
        value: https://orion-api.onrender.com

databases:
  # 3. Relational Storage
  - name: orion-postgres
    databaseName: orion_prod
    user: orion
    plan: free
    ipAllowList: []

  # 4. In-Memory Cache & Message Bus
  - name: orion-redis
    type: redis
    plan: free
    ipAllowList: []
```

### Architectural Analysis:

| Component | Target in `render.yaml` | Reality in Codebase | Discrepancy / Risk |
|---|---|---|---|
| **API Service** | Docker (`docker/apps/trading-engine/Dockerfile`) | Multi-stage Python 3.11-slim, non-root user `orion` | Dynamic port `${PORT:-8000}` properly handled. |
| **Dashboard Service** | Docker (`apps/dashboard/Dockerfile`) | Node 20 builder -> Nginx 1.27 alpine runtime | Security headers and SPA fallback properly configured. |
| **PostgreSQL** | Managed Render Postgres (`plan: free`) | PostgreSQL 15/16 expected | **Deleted after 30 days** on free tier. Zero PITR. |
| **Redis** | Managed Render Redis (`plan: free`) | Ephemeral cache / pub-sub | In-memory only (25MB), zero disk persistence. |
| **Worker Service** | Omitted | `AutonomousWorkerCoordinator` in API process | Celery absent; coordinator safely disabled by default. |
| **Migration Job** | Inline within API container startup | Alembic via `lifespan.py` | Race condition on rolling deployments or container scaling. |
| **CORS / Slugs** | Hardcoded `https://orion-dashboard.onrender.com` | Render assigns random suffixes (`orion-api-68u2`) | Hostname mismatch leads to CORS rejection unless manually updated. |

- **Classification:** `PARTIALLY VERIFIED`.

---

## 4. Production Environment Topology

The deployed network and application topology operates across three tiers:

```
[ Internet Traffic ]
        │ (HTTPS :443)
        ▼
[ Render Cloud Edge Load Balancer / TLS Termination ]
        ├──► / (Static Assets) ──► [ orion-dashboard (Nginx:80) ]
        │                                    │
        │                                    ▼ (Browser REST / SSE calls via HTTPS)
        └──► /api/*, /health/*, /metrics ──► [ orion-api (FastAPI/Uvicorn:8000) ]
                                                     │
                                       (Render Private SDN)
                                       ├──► [ orion-postgres:5432 ] (ipAllowList: [])
                                       └──► [ orion-redis:6379 ]    (ipAllowList: [])
```

### Topology Assessment:
1. **Public Ingress:** Only `orion-dashboard` and `orion-api` expose public HTTPS endpoints.
2. **Private Network Isolation:** Both `orion-postgres` and `orion-redis` specify `ipAllowList: []`, rendering them accessible solely from services within the same Render workspace over internal hostnames.
3. **Internal Port Mapping:** The API container listens on dynamic `$PORT` provided by Render, defaulting to 8000. Dashboard container listens on port 80.
4. **Security Header Enforcement:** Handled by Nginx in `apps/dashboard/nginx.conf` (`HSTS`, `X-Frame-Options DENY`, `X-Content-Type-Options nosniff`, `CSP`).
5. **Observability Exposure:** The `/metrics` endpoint is exposed directly to the public internet on `orion-api` without IP whitelisting or bearer authentication.

- **Classification:** `PARTIALLY VERIFIED`.

---

## 5. Environment and Secret Management

The environment variable audit assessed secret isolation, generation mechanisms, and configuration fallbacks:

### 5.1 Secret Audit Findings:
- **Zero Secrets in Git:** Forensic git history inspection confirms no API keys, private keys, database passwords, or JWT secrets are committed to the repository.
- **`.gitignore` Hygiene:** `.env`, `.env.*`, `*.pem`, `*.key`, and `var/backups` are properly excluded.
- **JWT Secret Key:** Handled via `generateValue: true` in `render.yaml`, prompting Render's secure vault to generate an unpredictable cryptographic key upon initial provisioning.
- **Database & Redis Credentials:** Injected dynamically using Render property links (`fromDatabase` / `fromRedis`), preventing cleartext password exposure in blueprint manifests.

### 5.2 Missing Production Variables in `render.yaml`:
While keeping secrets out of code is required, production deployment requires these variables to be configured in Render's environment dashboard:
- `STRIPE_SECRET_KEY` & `STRIPE_WEBHOOK_SECRET` (Stripe Test Mode keys)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` (Transactional email dispatch)
- `BACKUP_ENCRYPTION_KEY` (AES-256 backup encryption)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET` (Remote backup archive)
- `ORION_METRICS_TOKEN` (To protect `/metrics`)

- **Classification:** `PARTIALLY VERIFIED`.

---

## 6. Database Migration Safety

Project ORION uses Alembic with SQLAlchemy async models for relational schema state:

### 6.1 Migration Revision Chain:
All 15 migrations form a strict, unbroken linear sequence:
```
0001_initial_schema
  └──► 0002_add_users_table
        └──► 0003_add_user_id_to_accounts
              └──► 0004_add_saas_multi_tenancy
                    └──► 0005_add_organization_ownership
                          └──► 0006_add_subscription_entitlements
                                └──► 0007_organization_invitations
                                      └──► 0008_billing_foundation
                                            └──► 0009_research_experiments
                                                  └──► 0010_optimization_jobs
                                                        └──► 0011_deployment_pipeline
                                                              └──► 0012_broker_sandbox_integration
                                                                    └──► 0013_auth_and_account_hardening
                                                                          └──► 0014_legal_acceptance
                                                                                └──► 0015_onboarding_progress (HEAD)
```

### 6.2 Reversibility & Downgrade Safety:
- Every migration file (0001 through 0015) defines an explicit `downgrade()` implementation.
- Migration `0015_onboarding_progress` drops its indices (`ix_onboarding_progress_status`, `ix_onboarding_progress_organization_id`, `ix_onboarding_progress_user_id`) before safely dropping the `onboarding_progress` table.

### 6.3 Startup Migration Concurrency Risk:
- **Current Behavior:** In `render.yaml`, `ORION_RUN_MIGRATIONS: "true"` invokes `alembic upgrade head` inside `apps/trading-engine/src/lifespan.py` on container startup.
- **Failure Scenario:** If Render provisions a new instance during a rolling deploy while an old instance is running, or if two instances launch concurrently under autoscaling, both instances attempt schema modifications simultaneously, risking deadlocks or corrupting Alembic version tables.
- **Architectural Remedy:** Decouple migration execution from application startup. In Render, use:
  ```yaml
  preDeployCommand: poetry run alembic upgrade head
  ```
  Render executes `preDeployCommand` in an isolated ephemeral one-off container *before* traffic shifts to the new release.

- **Classification:** `PARTIALLY VERIFIED`.

---

## 7. PostgreSQL Readiness

Relational database requirements were audited against `libraries/infrastructure/persistence/`:

1. **Connection Pooling:**
   `DatabaseManager` in `libraries/infrastructure/persistence/database.py` configures:
   - `pool_size = 10`
   - `max_overflow = 20`
   - `pool_pre_ping = True` (actively eliminates stale severed connections)
   - `pool_recycle = 3600` (refreshes connections every hour)
2. **SSL Enforcement:**
   `asyncpg` connection strings automatically enforce SSL when connecting to Render's internal/external endpoints via `sslmode=require`.
3. **Row-Level Security (RLS):**
   Implemented in migration `0004_add_saas_multi_tenancy.py` with multi-tenant tenant isolation policies (`tenant_isolation_policy`).
4. **Render Free Tier Constraints (CRITICAL RISK):**
   - **30-Day Expiration:** Free PostgreSQL instances are wiped after 30 days.
   - **No Automated Backups:** Render provides zero snapshot backups on the free tier.
   - **No PITR:** Point-in-time recovery is unavailable on the free tier.
   - **RAM/CPU Throttling:** 256MB RAM limit risks out-of-memory crashes during complex multi-fold walk-forward analytics queries.

- **Classification:** `PARTIALLY VERIFIED` *(Code is ready; Cloud Free Plan is unacceptable for persistent deployment)*.

---

## 8. Redis Architecture

Redis usage in Project ORION was audited across storage, messaging, and concurrency domains:

1. **Role Separation:**
   Redis is utilized strictly as an **ephemeral cache, rate-limiting store, and pub/sub message bus**:
   - `RateLimitService` (`libraries/infrastructure/security/rate_limiter.py`): Sliding-window counter tracking with fallback to local memory.
   - `MarketDataCache`: Real-time tick caching and order book quote propagation.
   - Distributed locking for order execution safety.
2. **Persistence Philosophy:**
   Redis does **not** store authoritative financial, accounting, or user state. If Redis restarts or evicts keys, the platform experiences zero financial data loss.
3. **Resilience & Fallback:**
   The `RateLimitService` implements an automatic in-memory fallback (`InMemoryRateLimiter(max_keys=10000)`). If Redis is unreachable, the API logs a warning, falls back to memory, and keeps servicing requests.
4. **Render Free Tier Limits:**
   Render Free Redis provides 25MB RAM, in-memory only, with no disk persistence. This is adequate for paper trading development, but memory limits require aggressive key TTL policies.

- **Classification:** `VERIFIED`.

---

## 9. Celery / Worker Safety

Background processing was audited against codebase execution models:

1. **Absence of Celery:**
   Celery is **not present** anywhere in `project-orion`. No Celery worker, beat scheduler, or RabbitMQ/Redis broker queues exist.
2. **Autonomous Worker Architecture:**
   Background tasks are coordinated by `AutonomousWorkerCoordinator` (`apps/trading-engine/src/autonomous_worker.py`), an in-process `asyncio` task runner initialized in `apps/trading-engine/src/lifespan.py`.
3. **Fail-Safe Startup Guardrails:**
   - In `AppSettings`: `worker_enabled: bool = False` (default).
   - In `render.yaml`: `ORION_WORKER_ENABLED: "false"`.
   - In `lifespan.py`: When `enabled=False`, `worker.start()` emits an informational log and halts execution without spawning trading loops.
4. **Execution Safety:**
   Even if an operator sets `ORION_WORKER_ENABLED="true"`, the coordinator binds exclusively to `PaperExecutionAdapter` with mock market data. Accidental real-money execution is completely impossible.

- **Classification:** `VERIFIED`.

---

## 10. Backup Strategy

The backup subsystem in `backup/` was analyzed for automation, security, and integrity:

### 10.1 Backup Assets:
- `backup/backup-config.yml`: Retention configuration (daily 7d, weekly 4w, monthly 3m).
- `backup/database-backup.sh`: Full logical database backup using `pg_dump -Fc -j 4`, gzip compression, openssl AES-256-CBC encryption via `BACKUP_ENCRYPTION_KEY`, and SHA-256 checksum generation.
- `backup/redis-backup.sh`: Triggers `BGSAVE` and copies RDB snapshots.
- `backup/retention-policy.sh`: Automated backup pruning.

### 10.2 Critical Defects Identified:

#### 1. Syntax Corruption in `backup/retention-policy.sh`:
Lines 33–56 contain accidental LLM tool prompt text pasted into the script:
```bash
32:     count_after=$(find "${BACKUP_BASE}" -name "${pattern}" -type f 2>/dev/null | wc -l)
33:     local removedNow creating all remaining scripts and documentation files:
34:
35: <create_file>
36: <absolute_path>
37: c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/backup/database-backup.sh
...
```
Any execution of this script fails immediately with syntax errors.

#### 2. Cloud Redis Incompatibility in `backup/redis-backup.sh`:
Lines 56–61 attempt:
```bash
local rdb_path=$(redis-cli CONFIG GET dir ...)
cp "${rdb_path}/${rdb_filename}" "${filepath}"
```
On managed Redis services (such as Render Redis or AWS ElastiCache), `CONFIG` commands are disabled for security, and remote client containers have no filesystem access to the Redis server host.

#### 3. Lack of Automated Scheduling:
`render.yaml` contains no scheduled Cron Jobs or worker containers to execute `database-backup.sh`. Backups currently require manual terminal execution.

- **Classification:** `PARTIALLY VERIFIED`.

---

## 11. Restore Verification (CRITICAL BLOCKER)

The database restoration script `backup/restore-database.sh` was audited against managed cloud database permissions:

### 11.1 Structural Incompatibility:
Lines 59–68 of `backup/restore-database.sh`:
```bash
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid <> pg_backend_pid();"

psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
    -c "DROP DATABASE IF EXISTS ${DB_NAME};"

psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
    -c "CREATE DATABASE ${DB_NAME};"
```

**Why this fails on Managed Cloud (Render / RDS / Supabase):**
1. The application database user (`orion`) is **not a PostgreSQL superuser**.
2. Unprivileged users cannot connect to the system `postgres` maintenance database.
3. Managed database providers do not allow dropping the root instance database assigned to the tenant.
4. Calling `pg_terminate_backend()` requires superuser or `pg_signal_backend` privileges.
5. Executing `restore-database.sh` against Render PostgreSQL yields:
   ```
   FATAL: permission denied for database "postgres"
   FATAL: must be owner of database orion_prod
   ```

### 11.2 Required Remediation:
The restore script must be refactored to perform schema-level resets within the existing connection context:
```bash
psql "${DATABASE_URL}" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
pg_restore -d "${DATABASE_URL}" --clean --if-exists "${restore_path}"
```

### 11.3 Demonstration Status:
```
BACKUP SCRIPT EXISTS:     [YES]
BACKUP VERIFIED (S3/AES): [NO]
RESTORE VERIFIED:         [NO - NEVER DEMONSTRATED]
```
Per audit requirements, the lack of an isolated restore demonstration constitutes an **OPERATIONAL BLOCKER** for production launch.

- **Classification:** `BLOCKER`.

---

## 12. Disaster Recovery

Disaster recovery capabilities and recovery metrics were analyzed across failure modes:

| Failure Mode | Detection | Automated Recovery | Manual Intervention Required | Est. RPO | Est. RTO |
|---|---|---|---|---|---|
| **API Web Crash** | Render Health Check (`/health/live`) | Container auto-restart | None | 0 (Stateless) | < 2 min (50s on free) |
| **Redis Crash** | API Health Check (`/health/ready`) | Redis container restart | None (Rate limiter falls back to RAM) | 0 (Ephemeral) | < 3 min |
| **PostgreSQL Outage** | Health Check (`/health/ready`) | Render platform restart | None | 0 (WAL persistence) | 2–5 min |
| **PostgreSQL Corruption / Deletion** | Operator observation / 500 spike | **None on Free Tier** | Full manual restore from S3 backup | **24+ hours** (manual pg_dump) | **Indeterminate** (restore script broken) |
| **Render Region Outage** | External DNS monitor | None (Single-region PaaS) | Re-provision infrastructure in backup region | Dependent on last S3 backup | 2–4 hours |

### Target vs Current SLA:
- **Target Institutional RPO:** < 1 hour.
- **Current Actual RPO:** Up to 24 hours (due to absence of automated cron backup on Render Free tier).
- **Target Institutional RTO:** < 30 minutes.
- **Current Actual RTO:** Indeterminate (due to `restore-database.sh` superuser failures).

- **Classification:** `PARTIALLY VERIFIED`.

---

## 13. Deployment Ordering

Safe zero-downtime releases require strict operational sequencing:

```
[ Step 1: Database Health ]
   Check Postgres & Redis connectivity via Render internal DNS
            │
            ▼
[ Step 2: Schema Migration ]
   Execute 'alembic upgrade head' via isolated one-off job (preDeployCommand)
            │
            ▼
[ Step 3: Backend API Rollout ]
   Build image -> Launch container -> Await '/health/ready' passing -> Shift traffic
            │
            ▼
[ Step 4: Frontend Dashboard Rollout ]
   Build Vite bundle -> Launch Nginx container -> Await HTTP 200 on '/' -> Shift traffic
```

### Current Status in `render.yaml`:
- **Current Ordering:** Unsynchronized. Render launches builds in parallel upon git push.
- **Risk:** Dashboard may deploy and attempt API calls while the API container is still compiling Python dependencies or running startup migrations.
- **Fix:** Establish dependency ordering via Render Blueprint deployment hooks or Github Actions CD pipelines.

- **Classification:** `PARTIALLY VERIFIED`.

---

## 14. Rollback Strategy

1. **Application Code Rollback:**
   Render provides native, instant one-click rollback to previously built container image SHA digests.
2. **Database Migration Rollback:**
   All 15 migrations have valid `downgrade()` methods. However, in production relational databases, executing `downgrade()` that drops columns or tables containing user financial data causes irreversible data loss.
3. **Zero-Loss Migration Policy:**
   Project ORION must enforce an **Expand / Contract schema migration model**:
   - Phase 1 (Deploy): Add new nullable columns or tables.
   - Phase 2 (Code Release): Write to both old and new columns.
   - Phase 3 (Cleanup Release): Deprecate old columns without requiring immediate down-migrations.

- **Classification:** `PARTIALLY VERIFIED`.

---

## 15. Health, Readiness, and Observability

Endpoints implemented in `apps/trading-engine/src/routes/health.py` and `metrics.py`:

### 15.1 Health Probes:
- **Liveness Probe (`/health/live`):**
  Returns HTTP 200 `{"status": "alive"}` instantly. Used by Render load balancer to check container viability.
- **Readiness Probe (`/health/ready`):**
  Deep system probe verifying:
  - Database connectivity via `SELECT 1` ping.
  - Redis connectivity via `PING`.
  - Database migration synchronization (compares Alembic current revision against disk head).
  - Paper Execution Adapter connection state.
  - Returns HTTP 200 if healthy, HTTP 503 if any core dependency fails.

### 15.2 Metrics & Logging:
- **Structured JSON Logging:** Implemented across the backend using `structlog` (`libraries/observability/logging.py`), emitting ISO-8601 timestamps, log levels, correlation IDs, and tenant IDs.
- **Prometheus Metrics (`/metrics`):** Emits request durations, error counts, rate limit rejections, and execution latency.
- **VULNERABILITY:** `/metrics` is unauthenticated and publicly accessible to any internet user. It leaks internal operational topology, active request rates, and order counts.

- **Classification:** `PARTIALLY VERIFIED`.

---

## 16. Security Hardening

Security controls across network, application, and container boundaries were audited:

### 16.1 Transport & Container Security:
- **TLS/HTTPS:** Enforced by Render edge load balancers with TLS 1.3 and automatic certificate renewal.
- **Non-Root Execution:** Backend Dockerfile (`docker/apps/trading-engine/Dockerfile`) specifies unprivileged runtime user `orion` (UID 10001).
- **Security Headers (`apps/dashboard/nginx.conf`):**
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  - `X-Frame-Options: DENY`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; connect-src 'self' https: wss:; ...`

### 16.2 Network Vulnerabilities:
- **Unprotected Metrics:** `/metrics` requires token authentication.
- **CORS Configuration Drift:** `render.yaml` specifies `ORION_CORS_ORIGINS: https://orion-dashboard.onrender.com`. In practice, Render assigns unique service hashes (e.g. `orion-dashboard-6d3z.onrender.com`), triggering CORS failures unless wildcard regex or dashboard domain overrides are configured.

- **Classification:** `PARTIALLY VERIFIED`.

---

## 17. Email Provider Readiness

Transactional email capabilities (`libraries/infrastructure/communication/email_service.py`) were audited:

### 17.1 Codebase Reality:
Only two adapters are implemented in the entire repository:
1. `MockEmailAdapter`: Records sent emails to an in-memory list (used for CI and pytest).
2. `ConsoleEmailAdapter`: Prints verification and password reset URLs to standard output.

### 17.2 Missing Production Infrastructure:
- **No SMTP Adapter:** No `smtplib` or asynchronous SMTP client (`aiosmtplib`) is implemented.
- **No API Provider Adapter:** No AWS SES, SendGrid, Mailgun, or Postmark integration exists.
- **Operational Impact:** In a live cloud deployment on Render, verification emails and password reset links will only appear in Render container logs; **no emails will be delivered to actual users**.
- Implementation of a real `SmtpEmailAdapter` or `SesEmailAdapter` is an external dependency required for live onboarding.

- **Classification:** `EXTERNAL DEPENDENCY`.

---

## 18. Stripe / Billing Readiness

Commercial subscription handling in `libraries/infrastructure/billing/` was audited:

1. **Strict Test Mode Enforcement:**
   `BillingConfig` (`libraries/infrastructure/billing/config.py`) raises `LiveCredentialsForbiddenError` during initialization if `secret_key` starts with `sk_live_` or `publishable_key` starts with `pk_live_`.
2. **Webhook Security:**
   `StripeBillingAdapter` strictly verifies webhook signatures using `stripe.Webhook.construct_event` and `STRIPE_WEBHOOK_SECRET`.
3. **Database Billing State:**
   Migrations `0008_billing_foundation.py` and `0010_optimization_jobs.py` establish `subscriptions`, `invoices`, and `payment_methods` tables with tenant isolation.
4. **Conclusion:** Billing is fully operational and safe in Test Mode. Live billing transition requires governance approval.

- **Classification:** `VERIFIED`.

---

## 19. Broker Safety (Zero Capital at Risk)

Broker connectivity and execution safety invariants were audited against `libraries/infrastructure/security/endpoint_validator.py` and `libraries/infrastructure/execution/`:

### 19.1 Institutional Invariants:
1. **Paper Mode Default:** All user registrations and tenant organizations initialize with `broker_name="paper"` and `is_live=False`.
2. **Hard Fail-Closed Endpoint Validator:**
   `BrokerEndpointValidator` implements hardcoded static host allowlists:
   - **Allowed Sandbox Hosts:** `api-fxpractice.oanda.com`, `stream-fxpractice.oanda.com`, `paper-api.alpaca.markets`, `testnet.binance.vision`.
   - **Forbidden Production Hosts:** `api-fxtrade.oanda.com`, `stream-fxtrade.oanda.com`, `api.binance.com`, `live.alpaca.markets`.
3. **Immediate Rejection:** Any broker configuration or outbound API call attempting to reach a live trading host immediately raises `InvalidEndpointError`.
4. **Metadata SSRF Protection:** Blocks AWS/GCP link-local metadata addresses (`169.254.169.254`).
5. **Capital Exposure:** Verified **$0.00 capital at risk**.

- **Classification:** `VERIFIED`.

---

## 20. Cloud Cost and Plan Risks

A cost and operational viability analysis of Render hosting was performed:

| Service | Current Plan | Monthly Cost | Operational Limitations & Risks |
|---|---|---|---|
| **orion-postgres** | Free | $0.00 | **Database automatically deleted after 30 days.** No automated snapshots, no PITR, 256MB RAM limit. |
| **orion-redis** | Free | $0.00 | 25MB RAM, ephemeral in-memory only, no disk snapshots. |
| **orion-api** | Free | $0.00 | Sleeps after 15 min idle; **50–90s cold start**; 512MB RAM limit. |
| **orion-dashboard**| Free | $0.00 | Sleeps after 15 min idle; 512MB RAM limit. |
| **Shared Free Hours**| Free | $0.00 | 750 free instance hours shared across account per month. Exceeding limits halts all services. |

### Minimum Viable Production Upgrade:
To guarantee database persistence, zero cold starts, and reliable operation, Project ORION requires:
- **Render PostgreSQL Starter:** $7.00/month (Persistent, daily automated backups, 1GB RAM).
- **Render Web Service (API) Starter:** $7.00/month (Always-on, no cold starts, 512MB RAM).
- **Render Web Service (Dashboard) Starter:** $7.00/month (Always-on, fast global CDN).
- **Render Redis Starter:** $7.00/month (Persistent AOF/RDB storage, 256MB RAM).
- **Estimated Total:** ~$28.00/month.

- **Classification:** `BLOCKER` *(Free tier is non-viable for sustained production persistence)*.

---

## 21. Data Retention

Data lifecycle policies across relational tables were audited:

1. **Immutable Audit Trails:** `audit_logs` and `legal_acceptances` retain records permanently; no automated purge routines exist.
2. **Order & Trade History:** `orders`, `trades`, `positions`, and `fill_models` accumulate indefinitely for historical analytics and compliance reporting.
3. **Onboarding State:** `onboarding_progress` records persist permanently per `(user_id, organization_id)`.
4. **Backup Archive Retention:** `backup-config.yml` dictates 7-day daily, 28-day weekly, and 90-day monthly retention. However, automated pruning is stalled due to syntax errors in `retention-policy.sh`.

- **Classification:** `PARTIALLY VERIFIED`.

---

## 22. Monitoring and Alerting

Production observability was audited against operational alerting requirements:

| Alert Trigger | Current Detection Mechanism | Notification Dispatcher | Status |
|---|---|---|---|
| **API Outage (503 / Crash)** | Render Liveness Check (`/health/live`) | None (Render Dashboard UI only) | `MISSING` |
| **Database Connection Failure**| API Readiness Check (`/health/ready`) | None | `MISSING` |
| **High Error Rate (5xx spikes)**| None | None | `MISSING` |
| **Rate Limit / Brute Force Spike**| Counter metrics in `RateLimitService` | None | `MISSING` |
| **Backup Script Failure** | Log file output in `var/backups` | None | `MISSING` |
| **PostgreSQL Disk / RAM Full** | None | None | `MISSING` |
| **Worker Coordination Failure** | In-process log warning | None | `MISSING` |

### Required Production Alerts:
Integration with an external monitoring service (e.g. BetterStack, Datadog, Sentry, or Render Webhook Alerts) is required to notify engineers via Slack or PagerDuty upon failure.

- **Classification:** `MISSING`.

---

## 23. Deployment Runbook

Existing deployment documentation was evaluated:
- Documents evaluated: `docs/DEPLOYMENT_RUNBOOK.md`, `docs/PHASE4_DEPLOYMENT_PLAN.md`.
- **Gaps Identified:**
  - Existing runbooks focus on local Docker Compose setups.
  - Missing step-by-step procedure for deploying and linking Render Blueprints via Git.
  - Missing disaster recovery runbook for restoring PostgreSQL from an S3 archive onto a managed Render database.
  - Missing manual secret rotation procedures for JWT and Stripe credentials.

- **Classification:** `PARTIALLY VERIFIED`.

---

## 24. Production Safety Invariants

| Safety Invariant | Enforcing Mechanism | Code Location | Status |
|---|---|---|---|
| **Paper Trading by Default** | `broker_name="paper"`, `is_paper=True` | `apps/trading-engine/src/lifespan.py:236` | `VERIFIED` |
| **Autonomous Worker Disabled** | `worker_enabled=False`, `ORION_WORKER_ENABLED="false"` | `render.yaml:23`, `apps/trading-engine/src/config.py` | `VERIFIED` |
| **Live Broker Endpoints Blocked** | Hardcoded blacklist + sandbox whitelist | `libraries/infrastructure/security/endpoint_validator.py:46` | `VERIFIED` |
| **Stripe Live Keys Forbidden** | Rejection of `sk_live_*` with `LiveCredentialsForbiddenError` | `libraries/infrastructure/billing/config.py:30` | `VERIFIED` |
| **$0.00 Capital at Risk** | Zero live brokerage API integration | Platform-wide architectural invariant | `VERIFIED` |
| **Private Database & Redis** | `ipAllowList: []` on all Render databases | `render.yaml:45,51` | `VERIFIED` |
| **Container Privilege Separation**| Unprivileged user `orion` (UID 10001) | `docker/apps/trading-engine/Dockerfile:42` | `VERIFIED` |

- **Classification:** `VERIFIED`.

---

## 25. Phase 6 Gap Matrix

| Domain | Current State | Repository Evidence | Risk / Severity | Required Action | Classification |
|---|---|---|---|---|---|
| **Restore Verification** | No isolated restore test ever performed. | `backup/restore-database.sh` | Critical data loss if backup cannot be restored. | Execute isolated restore verification test against test DB. | `BLOCKER` |
| **Restore Script Privileges**| Script uses `DROP DATABASE` on `postgres` DB. | `backup/restore-database.sh:65` | Script fails immediately on managed cloud DBs. | Refactor script to use schema-level reset (`DROP SCHEMA public CASCADE`). | `BLOCKER` |
| **Render DB Retention** | Free PostgreSQL expires and deletes after 30 days. | `render.yaml:39` | Unrecoverable loss of all tenant & trading data. | Upgrade Render database to Starter tier ($7/mo). | `BLOCKER` |
| **Backup Retention Script** | Script contains accidental LLM tool prompt text. | `backup/retention-policy.sh:33` | Cron pruning fails with bash syntax errors. | Clean and repair shell script syntax. | `BLOCKER` |
| **Migration Concurrency** | Migrations run inside FastAPI app lifespan. | `apps/trading-engine/src/lifespan.py:211` | DDL deadlocks on multi-instance deploys. | Move migrations to Render `preDeployCommand`. | `PARTIALLY VERIFIED` |
| **Email Dispatcher** | Only mock and console email adapters exist. | `email_service.py:47,100` | Cloud users cannot receive verification emails. | Implement `SmtpEmailAdapter` / `SesEmailAdapter`. | `EXTERNAL DEPENDENCY` |
| **Metrics Security** | `/metrics` is unauthenticated and public. | `apps/trading-engine/src/routes/metrics.py:16` | Telemetry & business metric exposure. | Add API key / token header guard to `/metrics`. | `PARTIALLY VERIFIED` |
| **CORS / Slugs** | Hardcoded static domains in `render.yaml`. | `render.yaml:29,38` | Frontend API calls blocked by browser CORS. | Align Render domain slugs and support wildcards/env vars. | `PARTIALLY VERIFIED` |
| **Automated Backups** | No cron job defined in `render.yaml`. | `render.yaml` | Backups rely on manual execution. | Configure Render Cron Job or automated workflow. | `PARTIALLY VERIFIED` |
| **Operational Alerts** | No external webhook or paging configured. | `render.yaml`, `k8s/monitoring` | Engineers unaware of production downtime. | Configure Render or external alert webhooks. | `MISSING` |
| **Worker Safety** | Worker coordinator disabled by default. | `render.yaml:23`, `config.py` | None (Safety invariant verified). | Maintain `ORION_WORKER_ENABLED="false"`. | `VERIFIED` |
| **Broker Safety** | Live endpoints blocked by validator. | `endpoint_validator.py:46` | None (Safety invariant verified). | Maintain $0.00 capital at risk invariant. | `VERIFIED` |
| **Stripe Safety** | Live keys blocked by configuration. | `libraries/infrastructure/billing/config.py` | None (Safety invariant verified). | Maintain Test Mode invariant. | `VERIFIED` |

---

## 26. Proposed Phase 6 Implementation Plan

To remediate the identified gaps and achieve operational hardening, the following ordered work packages are proposed for EPIC-027 Phase 6 implementation:

```
[ Phase 6A: Cloud Infrastructure & Blueprint Hardening ]
  - Upgrade Render plan configurations in documentation / runbook (Starter tier)
  - Configure dynamic CORS origins and correct service URL slugs
  - Decouple migrations from API lifespan using Render 'preDeployCommand'

[ Phase 6B: Backup & Retention Script Remediation ]
  - Clean corrupted text from 'backup/retention-policy.sh'
  - Refactor 'backup/restore-database.sh' for managed cloud DBs (schema-level drop)
  - Update 'backup/redis-backup.sh' for cloud managed Redis compatibility

[ Phase 6C: Isolated Restore Demonstration (CRITICAL GATE) ]
  - Create isolated test database
  - Run full backup -> encrypt -> decrypt -> restore sequence
  - Verify row counts, table schemas, and data integrity post-restore
  - Formally document restore evidence in verification artifact

[ Phase 6D: Transactional Email Infrastructure ]
  - Implement production 'SmtpEmailAdapter' with TLS/STARTTLS support
  - Add SMTP configuration settings to 'AppSettings'
  - Verify email dispatch via sandbox SMTP server

[ Phase 6E: Observability & Endpoint Security Hardening ]
  - Secure '/metrics' with 'ORION_METRICS_TOKEN' bearer dependency
  - Validate '/health/ready' deep dependency ping accuracy
  - Document production monitoring and alerting runbook

[ Phase 6F: Final Verification & Production Runbook ]
  - Run complete end-to-end integration and smoke test suite
  - Produce 'docs/EPIC-027-PHASE-6-FINAL-VERIFICATION.md'
  - Final Quality Gate Sign-Off
```

---

## 27. External Dependencies

Implementation of Phase 6 and final production deployment require the following external resources:

1. **Render Account & Tier Upgrade:**
   - Active Render account with billing enabled for Starter PostgreSQL ($7/mo) to eliminate the 30-day database deletion limit.
2. **AWS S3 Backup Bucket & IAM Credentials:**
   - An AWS S3 bucket (e.g. `orion-production-backups`) with an IAM user provisioned with `s3:PutObject`, `s3:GetObject`, and `s3:ListBucket` permissions.
3. **Production Transactional Email Provider:**
   - SMTP credentials from AWS SES, SendGrid, Postmark, or Mailgun with verified sender domain DNS records (SPF, DKIM, DMARC).
4. **Stripe Test Mode Account:**
   - Valid Stripe Test API Keys (`sk_test_*`, `pk_test_*`) and webhook secret (`whsec_*`).

---

## 28. Final Classification

Based strictly on codebase evidence, infrastructure analysis, and verification boundaries:

### **B — IMPLEMENTATION READY WITH EXTERNAL DEPENDENCIES**

**Rationale:**
The application code, multi-stage Docker builds, database migration chain (0001–0015), and institutional safety invariants are complete, robust, and fully auditable. Implementation of Phase 6 hardening packages (script repairs, `preDeployCommand` migration decoupling, SMTP adapter implementation, and metrics protection) can commence immediately.

**Operational Condition:**
Live production deployment and commercial go-live remain **`C — IMPLEMENTATION BLOCKED`** until:
1. An isolated, automated **database restore demonstration** is successfully executed and verified (Phase 6C).
2. The Render PostgreSQL database is upgraded to a persistent paid tier to eliminate the 30-day data deletion risk.
3. External SMTP credentials are provided for transactional user verification.

---

EPIC-027 PHASE 6 — AUDIT COMPLETE — AWAITING REVIEW
