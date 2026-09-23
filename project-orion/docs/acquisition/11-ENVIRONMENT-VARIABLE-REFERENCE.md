# Project ORION — Environment Variable & Configuration Reference

**Document Version:** 1.0.0
**Target Milestone:** EPIC-027 Phase 7B Acquisition Due Diligence
**Repository Working Copy:** `project-orion/`
**Classification:** Confidential — Due Diligence Technical Data Room (Tier 2 / NDA)
**Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Capital at Risk — Zero Live Broker Endpoints)

---

## 1. Executive Configuration Architecture

Project ORION enforces a strict **Twelve-Factor configuration methodology**. 100% of application runtime configuration, credential references, infrastructure hostnames, and operational safety switches are externalized into environment variables.

### Key Architectural Principles
1. **Zero Hardcoded Secrets:** No secrets, signing keys, passwords, or connection strings exist within the source code or Git history.
2. **Fail-Closed Validation:** Missing required production variables or invalid types raise a strongly-typed `ConfigurationError` during ASGI lifespan startup and halt process initialization.
3. **Canonical Prefixing:** All platform variables are canonically prefixed with `ORION_`. Secondary fallback variables (such as standard cloud PaaS conventions like `DATABASE_URL` and `PORT`) are supported for cloud deployment compatibility.
4. **Paper-Only Safety Guards:** Any attempt to configure live Stripe credentials (live keys with prefix `sk` + `live`) or live broker trading endpoints raises immediate exceptions at configuration validation time.

> [!IMPORTANT]
> **SECURITY NOTICE:** This document intentionally excludes all production secret values, active API keys, database credentials, and signing secrets. Where syntax illustrations require parameter examples, inert placeholder tokens (e.g. `<CONFIGURED_IN_DASHBOARD>`, `mock`, `localhost`) are used. Real credentials must be injected solely via secure platform secrets managers (e.g., Render Environment Variables, AWS Secrets Manager, HashiCorp Vault).

---

## 2. Master Configuration Matrix

| Variable | Purpose | Type | Required? | Default (Dev/Local) | Environment | Secret? | Sourced In Code |
|---|---|---|:---:|---|---|:---:|---|
| `ORION_ENVIRONMENT` | Declares runtime stage; enforces production security rules when set to `production` | String (`development`, `staging`, `production`, `test`) | No | `development` | All | No | `apps/trading-engine/src/config.py` |
| `ORION_LOG_LEVEL` | Application logging verbosity | String (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) | No | `INFO` | All | No | `apps/trading-engine/src/config.py` |
| `ORION_SERVER_HOST` | TCP bind address for Uvicorn ASGI server | String (IP or hostname) | No | `0.0.0.0` | All | No | `apps/trading-engine/src/config.py` |
| `ORION_SERVER_PORT` | TCP port for Uvicorn ASGI server | Integer | No | `8000` | All | No | `apps/trading-engine/src/config.py` |
| `PORT` | Dynamic TCP port override provided by cloud PaaS (e.g., Render) | Integer | Cloud Only | `8000` | Production | No | `apps/trading-engine/src/config.py`, `render.yaml` |
| `ORION_DATABASE_URL` | PostgreSQL asyncpg connection string | URI String (`postgresql+asyncpg://...`) | **Yes** | Fallback to `DATABASE_URL` | All | **Yes** | `apps/trading-engine/src/config.py`, `libraries/infrastructure/persistence/config.py` |
| `DATABASE_URL` | Cloud PaaS default database URL fallback (auto-normalized to `postgresql+asyncpg://`) | URI String | Cloud Only | None | Production | **Yes** | `apps/trading-engine/src/config.py`, `render.yaml` |
| `ORION_RUN_MIGRATIONS` | Controls automated in-lifespan Alembic schema migrations on process startup | Boolean (`true`, `false`) | No | `false` | All | No | `apps/trading-engine/src/config.py`, `render.yaml` |
| `ORION_DB_POOL_SIZE` | Base connection pool size for SQLAlchemy async engine | Integer | No | `10` | All | No | `libraries/infrastructure/persistence/config.py` |
| `ORION_DB_MAX_OVERFLOW` | Maximum overflow connections above base pool size | Integer | No | `20` | All | No | `libraries/infrastructure/persistence/config.py` |
| `ORION_DB_POOL_TIMEOUT` | Seconds to wait before timing out on connection pool checkout | Float | No | `30.0` | All | No | `libraries/infrastructure/persistence/config.py` |
| `ORION_DB_POOL_RECYCLE` | Number of seconds after which pooled connections are recycled | Integer | No | `1800` | All | No | `libraries/infrastructure/persistence/config.py` |
| `ORION_DB_ECHO` | Enable SQLAlchemy statement logging / echo | Boolean (`true`, `false`) | No | `false` | Dev | No | `libraries/infrastructure/persistence/config.py` |
| `ORION_REDIS_URL` | Redis connection URI for caching, distributed locks, and rate limiting | URI String (`redis://...` or `rediss://...`) | No | `redis://localhost:6379/0` | All | **Yes** | `apps/trading-engine/src/config.py`, `libraries/infrastructure/caching/client.py` |
| `REDIS_URL` | Cloud PaaS default Redis URL fallback | URI String | Cloud Only | `redis://localhost:6379/0` | Production | **Yes** | `apps/trading-engine/src/config.py`, `render.yaml` |
| `ORION_REDIS_MAX_CONNECTIONS` | Maximum connections in Redis async connection pool | Integer | No | `20` | All | No | `libraries/infrastructure/caching/config.py` |
| `ORION_REDIS_SOCKET_TIMEOUT` | Socket read/write timeout for Redis commands in seconds | Float | No | `5.0` | All | No | `libraries/infrastructure/caching/config.py` |
| `ORION_REDIS_CONNECT_TIMEOUT` | Socket connection establishment timeout in seconds | Float | No | `5.0` | All | No | `libraries/infrastructure/caching/config.py` |
| `ORION_REDIS_RETRY_TIMEOUT` | Retry command automatically on timeout | Boolean (`true`, `false`) | No | `true` | All | No | `libraries/infrastructure/caching/config.py` |
| `ORION_REDIS_HEALTH_CHECK_INTERVAL` | Ping interval for connection pool health checks in seconds | Integer | No | `30` | All | No | `libraries/infrastructure/caching/config.py` |
| `ORION_JWT_SECRET_KEY` | HMAC-SHA256 secret key for signing auth tokens (minimum 32 characters in production) | String | **Yes (in prod)** | Dev insecure default | All | **Yes** | `apps/trading-engine/src/config.py`, `apps/trading-engine/src/routes/auth.py` |
| `ORION_JWT_ALGORITHM` | Cryptographic algorithm for JWT signature | String | No | `HS256` | All | No | `apps/trading-engine/src/config.py` |
| `ORION_JWT_EXPIRE_MINUTES` | Lifetime of issued JWT access tokens in minutes | Integer | No | `30` | All | No | `apps/trading-engine/src/config.py` |
| `ORION_METRICS_TOKEN` | Bearer token reserved for metrics scrape; **not currently consumed by application code** (`GET /metrics` has no application auth check) | String | No | Empty | External / Ops | **Yes** | Sourced in `.env.example` (Not consumed in `metrics.py`) |
| `ORION_CORS_ORIGINS` | Comma-separated list of permitted HTTP Origin headers for browser CORS | String (comma-separated URLs) | No | `http://localhost:5173,http://localhost:3000` | All | No | `apps/trading-engine/src/config.py`, `render.yaml` |
| `ORION_RATE_LIMITING_ENABLED` | Global master toggle for sliding-window rate limiters | Boolean (`true`, `false`) | No | `true` | All | No | `apps/trading-engine/src/config.py`, `apps/trading-engine/src/middleware/rate_limit.py` |
| `ORION_TRUSTED_PROXIES` | Comma-separated list of upstream proxy IP addresses for client IP resolution | String (comma-separated IPs) | No | `127.0.0.1,::1` | Production | No | `apps/trading-engine/src/config.py` |
| `ORION_ALLOW_HTTP_TESTING` | Emergency testing override permitting non-HTTPS broker sandbox endpoints during unit/integration tests; strictly fails closed in production | Boolean (`true`, `false`) | No | `false` | Test Only | No | `libraries/infrastructure/security/endpoint_validator.py` |
| `ORION_WORKER_ENABLED` | Safety switch for autonomous strategy execution loop (**Paper-only**) | Boolean (`true`, `false`) | No | `false` | All | No | `apps/trading-engine/src/config.py`, `render.yaml` |
| `ORION_WORKER_SYMBOLS` | Comma-separated list of trading instruments evaluated by worker | String (comma-separated symbols) | No | `EUR/USD,GBP/USD,USD/JPY` | All | No | `apps/trading-engine/src/config.py` |
| `ORION_PAPER_BALANCE` | Initial virtual equity allocated to new paper trading accounts | Decimal String | No | `100000.00` | All | No | `apps/trading-engine/src/config.py` |
| `ORION_WORKER_STALE_THRESHOLD` | Maximum elapsed seconds before quote feed is considered stale | Float | No | `30.0` | All | No | `apps/trading-engine/src/config.py` |
| `ORION_MARKET_DATA_POLL_INTERVAL` | Interval between market data ingest polls in seconds | Float | No | `5.0` | All | No | `apps/trading-engine/src/config.py` |
| `ORION_TRADING_CYCLE_INTERVAL` | Interval between strategy decision iterations in seconds | Float | No | `10.0` | All | No | `apps/trading-engine/src/config.py` |
| `ORION_WORKER_TIMEOUT` | Hard execution timeout for individual worker cycles in seconds | Float | No | `30.0` | All | No | `apps/trading-engine/src/config.py` |
| `ORION_MARKET_DATA_PROVIDER` | Active market data feed adapter (`mock`, `twelvedata`) | String | No | `mock` | All | No | `apps/trading-engine/src/config.py`, `libraries/infrastructure/market_data/config.py` |
| `ORION_MARKET_DATA_API_KEY` | API authentication key for TwelveData provider | String | If using TwelveData | Empty | Staging/Prod | **Yes** | `apps/trading-engine/src/config.py`, `libraries/infrastructure/market_data/config.py` |
| `ORION_MARKET_DATA_BASE_URL` | HTTP endpoint URL for TwelveData provider | String (URL) | No | `https://api.twelvedata.com` | All | No | `apps/trading-engine/src/config.py`, `libraries/infrastructure/market_data/config.py` |
| `ORION_MARKET_DATA_TIMEOUT` | HTTP request timeout for market data provider fetches in seconds | Float | No | `10.0` | All | No | `libraries/infrastructure/market_data/config.py` |
| `ORION_MARKET_DATA_RATE_LIMIT` | Provider outbound requests rate limit per minute | Integer | No | `60` | All | No | `libraries/infrastructure/market_data/config.py` |
| `ORION_MARKET_DATA_STALE_THRESHOLD` | Maximum elapsed seconds before market quote is marked stale | Float | No | `30.0` | All | No | `libraries/infrastructure/market_data/config.py` |
| `OANDA_ENVIRONMENT` | Operational template variable (sourced in `.env.example`); not loaded into `oanda_execution.py`. Broker credentials are created via API/UI and stored AES-GCM encrypted in DB | String (`practice`) | No | `practice` | Staging/Prod | No | Sourced in `.env.example` (Not in `oanda_execution.py`) |
| `OANDA_PRACTICE_API_KEY` | Operational template variable in `.env.example`; actual sandbox tokens are provisioned via `/api/v1/broker-sandbox/accounts` API and stored encrypted in DB | String | No | Empty | Staging/Prod | **Yes** | Sourced in `.env.example` (Not in `oanda_execution.py`) |
| `OANDA_ACCOUNT_ID` | Operational template variable in `.env.example`; actual sandbox account IDs are provisioned via `/api/v1/broker-sandbox/accounts` API and stored encrypted in DB | String | No | Empty | Staging/Prod | **Yes** | Sourced in `.env.example` (Not in `oanda_execution.py`) |
| `ORION_STRIPE_SECRET_KEY` | Stripe Test Mode secret API key (must begin with standard test prefix) | String | No (falls to mock) | Empty | All | **Yes** | `libraries/infrastructure/billing/config.py` |
| `ORION_STRIPE_PUBLISHABLE_KEY` | Stripe Test Mode publishable API key (must begin with standard test prefix) | String | No (falls to mock) | Empty | All | No | `libraries/infrastructure/billing/config.py` |
| `ORION_STRIPE_WEBHOOK_SECRET` | Stripe HMAC signing secret for webhook verification | String | If receiving webhooks | Empty | Staging/Prod | **Yes** | `libraries/infrastructure/billing/config.py` |
| `ORION_STRIPE_PRICE_PRO` | Stripe Price ID for Pro subscription tier | String | No | `price_test_pro_monthly` | All | No | `libraries/infrastructure/billing/config.py` |
| `ORION_STRIPE_PRICE_BUSINESS` | Stripe Price ID for Business subscription tier | String | No | `price_test_business_monthly` | All | No | `libraries/infrastructure/billing/config.py` |
| `ORION_STRIPE_PRICE_ENTERPRISE` | Stripe Price ID for Enterprise subscription tier | String | No | `price_test_enterprise_monthly` | All | No | `libraries/infrastructure/billing/config.py` |
| `ORION_BILLING_USE_MOCK` | Forces deterministic in-memory billing mock regardless of keys | Boolean (`true`, `false`) | No | `false` | All | No | `libraries/infrastructure/billing/config.py` |
| `ORION_EMAIL_BACKEND` | Active transactional email transport (`mock`, `console`, `smtp`) | String | No | `mock` | All | No | `libraries/infrastructure/communication/email_service.py` |
| `ORION_SMTP_HOST` | Hostname of outbound SMTP relay server (e.g. `smtp.sendgrid.net`) | String | If `smtp` backend | Empty | Staging/Prod | No | `libraries/infrastructure/communication/email_service.py` |
| `ORION_SMTP_PORT` | Outbound SMTP relay port (`587` for STARTTLS, `465` for SSL) | Integer | No | `587` | All | No | `libraries/infrastructure/communication/email_service.py` |
| `ORION_SMTP_USERNAME` | SMTP authentication user / API account identifier | String | No | Empty (unauthenticated relay) | Staging/Prod | **Yes** | `libraries/infrastructure/communication/email_service.py` |
| `ORION_SMTP_PASSWORD` | SMTP authentication password / API key | String | If username set | Empty | Staging/Prod | **Yes** | `libraries/infrastructure/communication/email_service.py` |
| `ORION_SMTP_USE_TLS` | Upgrade plain connection to TLS via STARTTLS command | Boolean (`true`, `false`) | No | `true` | All | No | `libraries/infrastructure/communication/email_service.py` |
| `ORION_SMTP_FROM_EMAIL` | Sender email address for outbound transactional messages | String (Email) | No | `notifications@oriontrading.io` | All | No | `libraries/infrastructure/communication/email_service.py` |
| `ORION_SMTP_FROM_NAME` | Display name for outbound transactional messages | String | No | `Project ORION` | All | No | `libraries/infrastructure/communication/email_service.py` |
| `ORION_SMTP_TIMEOUT_SECONDS` | Socket timeout for SMTP connection, greeting, and delivery | Float | No | `10.0` | All | No | `libraries/infrastructure/communication/email_service.py` |
| `ORION_FRONTEND_URL` | Base URL used to construct single-use verification & reset links | String (URL) | No | `https://orion-dashboard.onrender.com` | All | No | `libraries/infrastructure/communication/email_service.py` |
| `BACKUP_ENCRYPTION_KEY` | 32-byte hexadecimal key for OpenSSL AES-256-CBC backup encryption | String (64 hex characters) | Required for encrypted dumps | None | Production | **Yes** | `backup/database-backup.sh` |
| `AWS_ACCESS_KEY_ID` | External operational variable; not consumed by current repository backup tooling (`backup/database-backup.sh`) | String | Not consumed in repo | None | Production | **Yes** | Sourced in `.env.example` (external script) |
| `AWS_SECRET_ACCESS_KEY` | External operational variable; not consumed by current repository backup tooling (`backup/database-backup.sh`) | String | Not consumed in repo | None | Production | **Yes** | Sourced in `.env.example` (external script) |
| `AWS_S3_BUCKET` | External operational variable; not consumed by current repository backup tooling (`backup/database-backup.sh`) | String | Not consumed in repo | None | Production | No | Sourced in `.env.example` (external script) |
| `AWS_REGION` | External operational variable; not consumed by current repository backup tooling (`backup/database-backup.sh`) | String | Not consumed in repo | `us-east-1` | Production | No | Sourced in `.env.example` (external script) |
| `VITE_API_URL` | Frontend client base URL for API communication (empty string uses relative reverse proxy) | String (URL) | No | `""` (Empty string) | Frontend All | No | `apps/dashboard/src/api/client.ts`, `render.yaml` |

---

## 3. Production Deployment Profiles

### 3.1 Cloud Production Profile (Render PaaS)
As defined in `render.yaml`, Render automatically resolves and provisions:
- `ORION_DATABASE_URL`: Injected dynamically from `orion-postgres` (`basic-1gb` managed database).
- `ORION_REDIS_URL`: Injected dynamically from `orion-redis` (`free` managed key-value store).
- `ORION_JWT_SECRET_KEY`: Automatically generated with a cryptographically secure 256-bit random string via `generateValue: true`.
- `PORT`: Automatically assigned by Render container runtime (`10000`).
- `ORION_RUN_MIGRATIONS`: Fixed to `"false"`. Migrations are decoupled from service startup and executed via Render's `preDeployCommand: python scripts/deploy/migrate.py`.

### 3.2 Local Development Profile
Developers execute with SQLite or local Docker containers:
- `ORION_ENVIRONMENT` configured as `development`
- `ORION_DATABASE_URL` configured with local SQLite or local PostgreSQL
- `ORION_REDIS_URL` configured with local Redis instance
- `ORION_EMAIL_BACKEND` configured as `console` (or `mock`)
- `ORION_BILLING_USE_MOCK` configured as `true`

---

## 4. Inviolable Safety Guard Verifications

The configuration loader enforces three strict hard-failure guards to preserve system safety:
1. **Live Stripe Key Prohibition (`LiveCredentialsForbiddenError`):**
   ```python
   # Rejects any live Stripe key prefix
   if self.secret_key.strip().startswith("sk" + "_live"):
       raise LiveCredentialsForbiddenError("Live Stripe secret key detected. Project ORION operates strictly in Stripe TEST MODE only.")
   ```
2. **Production JWT Weak Key Rejection (`ConfigurationError`):**
   When `ORION_ENVIRONMENT=production`, if `ORION_JWT_SECRET_KEY` is missing, matches the default development string, or is shorter than 32 characters, the system fails closed immediately.
3. **Broker Live Endpoint Prohibition:**
   The broker adapter factory strictly forbids `LIVE` environments, failing closed if production broker URLs (e.g. `api-fxtrade.oanda.com`) are supplied.

---

## 5. Configuration-Template Drift (.env.example vs Application Code)

A buyer due-diligence review should note the following configuration-template drift between the legacy `.env.example` file and the authoritative Python application code:

1. **Environment Flag (`ORION_ENV` vs `ORION_ENVIRONMENT`):**
   - `.env.example` defines `ORION_ENV=production`.
   - The application configuration loader (`apps/trading-engine/src/config.py`) exclusively reads `ORION_ENVIRONMENT` (default: `development`). `ORION_ENV` is ignored by the settings parser.
2. **JWT Expiration Setting (`ORION_JWT_EXPIRATION_MINUTES` vs `ORION_JWT_EXPIRE_MINUTES`):**
   - `.env.example` specifies `ORION_JWT_EXPIRATION_MINUTES=60`.
   - The application configuration loader (`config.py`) exclusively reads `ORION_JWT_EXPIRE_MINUTES` (default: `30`).
3. **SMTP Relay Settings (`SMTP_*` vs `ORION_SMTP_*`):**
   - `.env.example` specifies un-prefixed names: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `SMTP_FROM_EMAIL`.
   - The application email dispatcher (`libraries/infrastructure/communication/email_service.py`) exclusively parses canonical prefixed variables: `ORION_SMTP_HOST`, `ORION_SMTP_PORT`, `ORION_SMTP_USERNAME`, `ORION_SMTP_PASSWORD`, `ORION_SMTP_USE_TLS`, `ORION_SMTP_FROM_EMAIL`. Un-prefixed variables are not evaluated.
4. **Metrics Scrape Protection Token (`ORION_METRICS_TOKEN`):**
   - `.env.example` documents `ORION_METRICS_TOKEN` for protecting `GET /metrics`.
   - The active endpoint implementation (`apps/trading-engine/src/routes/metrics.py`) contains no application-level authentication dependency and exposes metrics openly; this token is not evaluated by Python application code.
5. **Broker Sandbox Credentials (`OANDA_*`):**
   - `.env.example` contains placeholders for `OANDA_ENVIRONMENT`, `OANDA_PRACTICE_API_KEY`, `OANDA_ACCOUNT_ID`.
   - The active application architecture provisions broker connections dynamically via the `/api/v1/broker-sandbox/accounts` API and stores encrypted credentials in the database rather than consuming them from process environment variables.
