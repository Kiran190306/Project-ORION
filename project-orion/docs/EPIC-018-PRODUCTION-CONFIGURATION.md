# PROJECT ORION — EPIC-018 PHASE 1: PRODUCTION CONFIGURATION FREEZE

**Project**: Project ORION — Institutional Forex Trading Platform  
**Epic**: EPIC-018 — Production Operations, Reliability, Security Hardening & Release Freeze  
**Phase**: Phase 1 — Production Configuration Freeze  
**Date**: 2026-09-20  
**Target Platform**: Render Cloud Production  
**Deployed Commit**: `a26a168` on `main`  
**Security Classification**: CONFIDENTIAL — Zero Plaintext Secrets Embedded  

---

## 1. Executive Summary

Phase 1 establishes the **Production Configuration Freeze** for Project ORION. All configuration across the FastAPI backend, Nginx frontend reverse proxy, PostgreSQL database, and Redis cache is strictly externalized into environment variables managed securely through Render Cloud. 

Zero plaintext credentials, database passwords, or JWT signing keys are stored in source code, Docker images, or git repositories. All configuration follows secure defaults that "fail closed" if values are absent or malformed.

---

## 2. Production Configuration Matrix

The following table documents every operational configuration setting, its source, required status, secure default, and live production status. Sensitive values are strictly redacted.

| Setting Name | Source | Required | Secure Default | Production Status |
|---|---|:---:|---|---|
| `ORION_ENVIRONMENT` | Environment | No | `development` | `production` (Verified) |
| `ORION_LOG_LEVEL` | Environment | No | `INFO` | `INFO` (Verified) |
| `PORT` / `ORION_SERVER_PORT` | Render Dynamic Env | Yes | `8000` | Dynamic `$PORT` (`10000` on Render) |
| `ORION_SERVER_HOST` | Environment | No | `0.0.0.0` | `0.0.0.0` (Binds all container interfaces) |
| `ORION_DATABASE_URL` | Render Managed PG | Yes | *None (Fails closed)* | `postgresql+asyncpg://...` (Private VPC URL) |
| `ORION_DB_POOL_SIZE` | Environment | No | `10` | `10` (Max 10 persistent connections per pod) |
| `ORION_DB_MAX_OVERFLOW` | Environment | No | `20` | `20` (Surge capacity up to 30 total connections) |
| `ORION_DB_POOL_TIMEOUT` | Environment | No | `30.0` | `30.0s` (Prevents indefinite pool starvation) |
| `ORION_DB_POOL_RECYCLE` | Environment | No | `1800` | `1800s` (Recycles connections every 30 mins) |
| `ORION_REDIS_URL` | Render Managed Redis | No | `redis://localhost:6379/0` | `rediss://...` or `redis://...` (Private VPC URL) |
| `ORION_REDIS_MAX_CONNECTIONS` | Environment | No | `20` | `20` (Pool size) |
| `ORION_REDIS_SOCKET_TIMEOUT` | Environment | No | `5.0` | `5.0s` (Prevents thread/async worker lockup) |
| `ORION_REDIS_CONNECT_TIMEOUT`| Environment | No | `5.0` | `5.0s` |
| `ORION_REDIS_RETRY_TIMEOUT` | Environment | No | `true` | `true` |
| `ORION_REDIS_HEALTH_CHECK_INTERVAL` | Environment | No | `30` | `30s` (TCP keepalive verification) |
| `ORION_RUN_MIGRATIONS` | Environment | No | `false` | `true` (Runs Alembic `upgrade head` at startup) |
| `ORION_JWT_SECRET_KEY` | Render Auto-Generated| Yes | *None (Fails closed)* | 256-bit cryptographically secure secret (Redacted) |
| `ORION_JWT_ALGORITHM` | Environment | No | `HS256` | `HS256` (HMAC-SHA256) |
| `ORION_JWT_EXPIRE_MINUTES` | Environment | No | `30` | `30` (Strict 30-minute access token lifespan) |
| `ORION_CORS_ORIGINS` | Environment | No | `http://localhost:5173,...` | `https://orion-dashboard-6d3z.onrender.com` |
| `ORION_PAPER_BALANCE` | Environment | No | `100000` | `100000.00` (Starting paper balance: \$100,000) |
| `ORION_WORKER_ENABLED` | Environment | No | `false` | **`false`** (Autonomous trading worker DISABLED) |
| `ORION_WORKER_SYMBOLS` | Environment | No | `EUR/USD,GBP/USD,USD/JPY`| `EUR/USD,GBP/USD,USD/JPY` (Inactive) |
| `ORION_MARKET_DATA_POLL_INTERVAL` | Environment | No | `5.0` | `5.0s` (Inactive) |
| `ORION_TRADING_CYCLE_INTERVAL` | Environment | No | `10.0` | `10.0s` (Inactive) |
| `ORION_WORKER_TIMEOUT` | Environment | No | `30.0` | `30.0s` (Inactive) |
| `ORION_WORKER_STALE_THRESHOLD` | Environment | No | `30.0` | `30.0s` (Inactive) |
| `VITE_API_URL` | Frontend Build Arg | Yes | `/api` | `https://orion-api-68u2.onrender.com` |

---

## 3. Critical Security & Operational Invariants

### 3.1. Strict Paper-Trading Invariant
- **Policy**: Real-money broker connectivity is completely prohibited in code and configuration.
- **Enforcement**:
  - `ORION_WORKER_ENABLED` is hard-pinned to `"false"`.
  - The application instantiates only `PaperExecutionAdapter`.
  - Zero live broker API keys (e.g. OANDA, Interactive Brokers, FXCM) exist in environment variables.
  - The platform baseline account balance is \$100,000.00 virtual paper currency with `capital_at_risk = $0.00`.

### 3.2. Dynamic Port Handling & Binding
- Render dynamically assigns an unprivileged port via the `$PORT` environment variable (typically 10000).
- `AppSettings.from_env()` evaluates `ORION_SERVER_PORT` falling back to `PORT` and then `8000`.
- Docker containers run as unprivileged non-root users (`uid=999` for backend, `uid=101` for dashboard) and successfully bind to `$PORT`.

### 3.3. Dynamic CORS & Host Whitelisting
- CORS origins are parsed via `parse_cors_origins()`.
- Wildcard `*` origins are strictly prohibited in production when credentials (`allow_credentials=True`) are permitted.
- The production deployment explicitly configures `ORION_CORS_ORIGINS` to match the exact Dashboard origin:
  `https://orion-dashboard-6d3z.onrender.com`

### 3.4. HTTP Security Headers
All responses emitted by the FastAPI backend and Nginx reverse proxy include institutional-grade HTTP security headers:
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` (Enforces HTTPS)
- `X-Frame-Options: DENY` (Prevents clickjacking)
- `X-Content-Type-Options: nosniff` (Prevents MIME-type sniffing)
- `Cache-Control: no-store, no-cache, must-revalidate` (Prevents caching sensitive financial data)
- `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' http: https: ws: wss:; font-src 'self'; frame-ancestors 'none';`

---

## 4. Configuration Freeze Verification Procedure

Before any code update or deployment is initiated, the following checks must be satisfied:
1. `ORION_WORKER_ENABLED` must remain `false`.
2. `ORION_RUN_MIGRATIONS` must remain `true` to ensure schema alignment upon rollout.
3. No `.env` files or plaintext credentials may be present in the working tree.
4. Render `render.yaml` must validate cleanly via `render blueprints validate render.yaml`.
