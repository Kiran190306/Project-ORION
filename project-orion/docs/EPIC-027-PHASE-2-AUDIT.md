# EPIC-027 — Phase 2: Public API Rate Limiting & Abuse Defense
**Comprehensive Architectural & Security Audit**

- **Project:** Project ORION
- **Milestone:** EPIC-027 (Public Beta & Commercial Launch Readiness)
- **Phase:** PHASE 2 ONLY
- **Date:** 2026-09-22
- **Environment Invariant:** PAPER TRADING ONLY. Live broker execution disabled. Real capital at risk: $0.00.

---

## 1. Current Architecture

Project ORION is an institutional-grade automated Forex paper-trading platform structured around Domain-Driven Design (DDD) principles:
- **`apps/trading-engine`:** FastAPI ASGI asynchronous application managing market data, paper execution, risk management, quantitative research, optimization, deployment pipelines, tenant management, and authentication.
- **`apps/dashboard`:** React 18 / TypeScript SPA communicating via strongly typed REST clients.
- **`libraries/`:** Decoupled domain, infrastructure, and observability layers:
  - `libraries/domain/`: Pure domain entities, value objects, and business rules (order validation, risk limits, subscription plans, RBAC permissions).
  - `libraries/infrastructure/`: Concrete adapters for persistence (SQLAlchemy + asyncpg/aiosqlite), caching (RedisClient), execution (PaperExecutionAdapter), and external integrations.
  - `libraries/observability/`: In-memory thread-safe `MetricsRegistry` exporting Prometheus metrics, structured contextual logging, and correlation ID tracking.

---

## 2. Existing Redis Path

- **Client Implementation:** `libraries/infrastructure/caching/client.py` (`RedisClient`).
- **Configuration:** `libraries/infrastructure/caching/config.py` (`RedisConfig`).
  - Sourced from `ORION_REDIS_URL` or `REDIS_URL` (default: `redis://localhost:6379/0`).
  - Configurable `max_connections`, `socket_timeout`, `socket_connect_timeout`, `retry_on_timeout`, `health_check_interval`.
  - Underlying driver: `redis.asyncio` (`aioredis`).
- **Lifecycle & Dependency Injection:**
  - `apps/trading-engine/src/lifespan.py`: Instantiates `RedisConfig` and `RedisClient`, stores instance on `app.state.redis_client`, registers `RedisHealthCheck`, calls `await redis_client.connect()` at startup, and `await redis_client.disconnect()` during shutdown.
  - `apps/trading-engine/src/dependencies.py`: Exposes `get_redis(request: Request) -> RedisClient`, retrieving `request.app.state.redis_client`.
- **Current Redis Usage:**
  - Market data caching (`MarketDataCache`).
  - Readiness health check (`RedisHealthCheck` ping).
- **Audit Finding:**
  `RedisClient` contains CRUD operations (`get`, `set`, `delete`, `exists`, `expire`, `hget`, `hset`, `hgetall`), but does **not** currently expose sorted set commands (`zadd`, `zremrangebyscore`, `zcard`, `zrange`) or Lua script execution (`eval` / `evalsha`).
- **Architectural Requirement:**
  We must reuse this exact `RedisClient` and connection pool without creating a secondary Redis connection pool. We should extend `RedisClient` with an atomic Lua script execution method (`eval_script` or `execute_lua`) and sorted set operations, or wrap the underlying `aioredis.Redis` client safely.

---

## 3. Existing Middleware Architecture

- Located in `apps/trading-engine/src/main.py`:
  1. `CORSMiddleware`: Handles cross-origin requests from configured origins (`ORION_CORS_ORIGINS`).
  2. `correlation_id_middleware`: Extracts `X-Correlation-ID` header or generates a new UUID4, attaches to `request.state.correlation_id`, sets context var via `set_correlation_id()`, and injects into response headers.
  3. `security_headers_middleware`: Adds `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`, `Content-Security-Policy`, and cache control headers.
- **Audit Finding:**
  There is currently no rate-limiting middleware or route-level rate-limiting dependency.

---

## 4. Existing Error Format

- Defined in `apps/trading-engine/src/schemas.py`:
  ```python
  class ErrorResponse(BaseModel):
      error: str
      message: str
      correlation_id: str = ""
      timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
  ```
- Handled in `apps/trading-engine/src/errors.py`:
  `register_exception_handlers(app)` catches:
  - `RequestValidationError` $\to$ HTTP 422
  - `StarletteHTTPException` $\to$ HTTP status code from exception
  - `ConfigurationError` $\to$ HTTP 503
  - `Exception` (catch-all) $\to$ HTTP 500
- **Critical Audit Finding:**
  In `errors.py`, `_error_response()` only sets `headers = {"x-correlation-id": correlation_id}`.
  When an endpoint raises `HTTPException(status_code=429, detail=..., headers=...)`, Starlette attaches those headers to `exc.headers`. However, `errors.py:http_exception_handler` was **ignoring** `exc.headers`!
  **Correction Required:** `http_exception_handler` must forward `exc.headers` (e.g. `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`) to `JSONResponse` so rate-limit headers reach the caller.

---

## 5. Existing Authentication Routes

- File: `apps/trading-engine/src/routes/auth.py`
  - `POST /api/v1/auth/login`: Authenticates username + password, returns JWT access token.
  - `GET /api/v1/auth/me`: Retrieves current active user profile.
  - `POST /api/v1/auth/logout`: Revokes session.
  - `POST /api/v1/auth/forgot-password`: Generates 15m password reset token, sends email, returns generic response.
  - `POST /api/v1/auth/reset-password`: Resets password using single-use token, invalidates prior sessions.
  - `POST /api/v1/auth/verify-email`: Validates email token, marks `email_verified=True`.
  - `POST /api/v1/auth/resend-verification`: Dispatches new verification token, returns generic response.
  - `POST /api/v1/auth/deactivate`: Deactivates account with sole-owner protection.
  - `POST /api/v1/auth/users/{id}/reactivate`: Superuser account reactivation.

---

## 6. Existing Public Routes

The following routes are accessible without an `Authorization: Bearer <JWT>` header:
- `GET /health/live`: Liveness probe (must NEVER be rate limited).
- `GET /health/ready`: Readiness probe (must NEVER be rate limited).
- `GET /metrics`: Prometheus scraper (must NEVER be rate limited).
- `POST /api/v1/auth/login`: Brute-force sensitive. **Needs Rate Limiting.**
- `POST /api/v1/auth/forgot-password`: Account enumeration & email flood sensitive. **Needs Rate Limiting.**
- `POST /api/v1/auth/reset-password`: Token guessing sensitive. **Needs Rate Limiting.**
- `POST /api/v1/auth/verify-email`: Token guessing sensitive. **Needs Rate Limiting.**
- `POST /api/v1/auth/resend-verification`: Email flood sensitive. **Needs Rate Limiting.**
- `POST /api/v1/onboarding/register`: Account spam sensitive. **Needs Rate Limiting.**
- `POST /api/v1/invitations/{token}/accept`: Invitation acceptance. **Needs Rate Limiting.**
- `POST /api/v1/billing/webhook`: Stripe webhook signature verified. Excluded from client rate limiting.

---

## 7. Existing Expensive & Resource-Intensive Routes

- `POST /api/v1/orders/`: Paper order creation (triggers execution simulation, position updates, audit logging).
- `POST /api/v1/research/experiments`: Backtesting simulation sweep over historic tick/bar data.
- `GET /api/v1/research/experiments/{id}/export`: CSV/JSON data serialization.
- `POST /api/v1/optimization/run`: Parameter sweep (grid/random search running multiple simulations).
- `POST /api/v1/optimization/walk-forward`: Chronological Walk-Forward Analysis (computationally intensive).
- `GET /api/v1/optimization/jobs/{job_id}/export`: Bulk optimization dataset export.
- `POST /api/v1/billing/checkout`: Calls external Stripe API to create checkout session.
- `GET /api/v1/organizations/{id}/audit`: Database queries across high-volume audit logs.
- `POST /api/v1/organizations/{id}/audit/export`: Audit log bulk export.
- `POST /api/v1/broker-sandbox/accounts/{id}/connect`: Broker sandbox credentials verification & connection handshake.
- `POST /api/v1/broker-sandbox/reconcile`: Broker position/balance reconciliation snapshot.

---

## 8. Existing Entitlement Enforcement

- Managed by `apps/trading-engine/src/services/entitlement_service.py` (`EntitlementService`).
- Checks business quotas:
  - Account count quota (`check_account_quota`).
  - Daily order limit quota (`check_daily_order_quota`).
  - Daily research backtest quota (`check_research_quota`).
  - Active optimization jobs quota (`check_optimization_quota`).
- **Invariant:** Rate limiting does **not** replace `EntitlementService`. Entitlements represent commercial subscription limits (e.g. 100 orders/day on Free tier). Rate limiting represents instantaneous denial-of-service and burst protection (e.g. 60 orders/minute). Both layers must be enforced concurrently.

---

## 9. Existing Tenant Context

- Defined in `apps/trading-engine/src/dependencies.py`:
  `TenantContext` data class:
  ```python
  class TenantContext:
      user_id: str
      organization_id: str | None = None
      role: str | None = None
      is_superuser: bool = False
  ```
  Resolved via `get_tenant_context(request, current_user, session)`.
- Validates `X-Organization-ID` header against database memberships fail-closed.
- Rate limiting keys for authenticated endpoints must isolate by `user_id` and `organization_id` to prevent one user or tenant from consuming another tenant's rate allowance.

---

## 10. Existing Audit System

- Table: `audit_logs` (`AuditLogModel`).
- Emits structured events with:
  - `id`: UUID.
  - `event_type`: String (e.g. `USER_REGISTERED`, `PASSWORD_RESET_REQUESTED`).
  - `actor_user_id`: String (nullable).
  - `organization_id`: String (nullable).
  - `resource_id`: String (nullable).
  - `component`: String (e.g. `auth_service`).
  - `action`: String.
  - `status`: String (`SUCCESS`, `FAILED`).
  - `payload`: JSON/dict (sanitized).
  - `timestamp`: UTC DateTime.
- Security requirement: When a rate limit is exceeded on sensitive routes, log a structured warning and emit a `RATE_LIMIT_EXCEEDED` audit entry where session context permits, with burst de-duplication to prevent audit log flooding.

---

## 11. Existing Proxy / Network Configuration

- Production Render topology (`render.yaml`):
  - Service `orion-api` runs inside Docker container behind Render Cloud reverse proxy.
  - Direct connection to container originates from internal proxy IP.
  - Client IP is appended to `X-Forwarded-For`.
- **Security Vulnerability If Unchecked:**
  If an application naively reads `request.headers.get("X-Forwarded-For")` without verifying the direct socket client (`request.client.host`), an attacker can send arbitrary spoofed headers (e.g. `X-Forwarded-For: 1.1.1.1`) to cycle through endless IPs and completely bypass IP-based rate limiting!
- **Mitigation Requirement:**
  Implement a `ClientIpResolver` that only trusts `X-Forwarded-For` when `request.client.host` matches a configured trusted proxy list (`AppSettings.trusted_proxies`). If the direct caller is not trusted, `request.client.host` must be used.

---

## 12. Existing Tests

- Backend Unit: `tests/unit/` (43+ test files, 1,000+ tests).
- Backend Integration: `tests/integration/` (onboarding, rbac, security, broker sandbox).
- Frontend Vitest: `apps/dashboard/tests/` (19 test files, 61 passing tests).
- Total platform regression passing: 4,308+ tests.

---

## 13. Identified Gaps

1. **No Rate Limiter Abstraction:** No domain or infrastructure rate limiter exists.
2. **Missing Sorted Set & Lua Support in RedisClient:** `RedisClient` lacks atomic `eval` and sorted set commands necessary for a race-condition-free sliding window counter.
3. **No Centralized Policy Registry:** No definition of per-route burst limits, windows, and scoping strategies.
4. **No Trusted Proxy Resolver:** No mechanism to parse `X-Forwarded-For` safely while preventing IP spoofing.
5. **No 429 Header Forwarding in Exception Handler:** `errors.py:http_exception_handler` drops `exc.headers`, preventing `Retry-After` and `X-RateLimit-*` headers from reaching the client.
6. **No In-Memory Resilient Fallback:** No bounded local sliding window cache to protect sensitive endpoints during Redis transient outages.
7. **No Observability for Rate Limiting:** No Prometheus counters for allowed/rejected/error rate limit outcomes.
8. **Frontend 429 Handling:** Dashboard `client.ts` catches 429 and shows generic message, but does not parse `Retry-After` header.

---

## 14. Proposed Architecture

```
                       Incoming HTTP Request
                                 │
                                 ▼
                     Client IP Resolver (Safe)
                 (Direct socket vs Trusted Proxies)
                                 │
                                 ▼
                    FastAPI Route / Dependency
                  Depends(rate_limit(POLICY_NAME))
                                 │
                                 ▼
                         RateLimitService
                  (Extracts Scope: IP / User / Org)
                                 │
               ┌─────────────────┴─────────────────┐
               ▼                                   ▼
      [Redis Available]                    [Redis Unavailable]
               │                                   │
      Atomic Redis Lua Script             Bounded In-Memory Cache
     (Sorted Set Sliding Window)         (Thread-Safe Local Window)
               │                                   │
               └─────────────────┬─────────────────┘
                                 │
                     RateLimitResult Check
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
          Allowed (<= Limit)             Exceeded (> Limit)
                 │                               │
       Continue Route Execution          Emit Metric & Warning Log
      (Headers: Limit, Remaining)        Raise HTTPException(429)
                                         Headers: Retry-After, Limit, Reset
                                         RFC-7807 Error JSON
```

### Key Design Principles:
1. **Atomic Sliding Window via Redis Lua:**
   All sliding window logic (`ZREMRANGEBYSCORE`, `ZCARD`, `ZADD`, `EXPIRE`) runs inside an atomic Lua script executed by Redis. Eliminates check-then-set race conditions under high concurrency.
2. **Bounded In-Memory Fallback:**
   If Redis times out or is unreachable, the system automatically falls back to an in-memory sliding window limiter bounded to 10,000 keys with background expiration. Sensitive authentication endpoints are never left unprotected.
3. **Centralized Policy Registry:**
   Policies defined in `libraries/domain/security/rate_limit.py` as immutable dataclasses specifying limit, window seconds, scope, and fallback behavior.
4. **Strict RFC-7807 & Standard Rate Limit Headers:**
   Headers `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` returned alongside `ErrorResponse`.

---

## 15. Files Expected to Change

1. `libraries/infrastructure/caching/client.py`: Add `eval_script()` / `execute_lua()` to existing `RedisClient`.
2. `apps/trading-engine/src/config.py`: Add `trusted_proxies` and `rate_limiting_enabled` to `AppSettings`.
3. `apps/trading-engine/src/errors.py`: Forward `exc.headers` to response in `http_exception_handler`.
4. `apps/trading-engine/src/dependencies.py`: Add `get_rate_limit_service` and `rate_limit` dependency factories.
5. `apps/trading-engine/src/lifespan.py`: Initialize and register rate-limiting metrics.
6. `apps/trading-engine/src/routes/auth.py`: Apply rate limits to login, forgot-password, reset-password, verify-email, resend-verification.
7. `apps/trading-engine/src/routes/onboarding.py`: Apply rate limit to register.
8. `apps/trading-engine/src/routes/organization.py`: Apply rate limit to invitation accept and invitations creation.
9. `apps/trading-engine/src/routes/orders.py`: Apply rate limit to order creation.
10. `apps/trading-engine/src/routes/research.py`: Apply rate limit to experiment execution and export.
11. `apps/trading-engine/src/routes/optimization.py`: Apply rate limit to optimization sweep, WFA, and export.
12. `apps/trading-engine/src/routes/billing.py`: Apply rate limit to checkout session creation.
13. `apps/dashboard/src/api/client.ts`: Respect `Retry-After` header and enhance user feedback.

---

## 16. Files Expected to be Created

1. `libraries/domain/security/rate_limit.py`: Domain models (`RateLimitPolicy`, `RateLimitScope`, `RateLimitResult`).
2. `libraries/infrastructure/security/ip_resolver.py`: Trusted-proxy-aware client IP resolver (`ClientIpResolver`).
3. `libraries/infrastructure/security/rate_limiter.py`: `RedisRateLimiter` (with Lua script) and `InMemoryRateLimiter` (bounded fallback).
4. `apps/trading-engine/src/services/rate_limit_service.py`: `RateLimitService` orchestrating policy, key generation, and execution.
5. `tests/unit/libraries/test_rate_limiter.py`: Unit tests for Redis Lua script, sliding window, in-memory fallback, concurrency.
6. `tests/unit/libraries/test_ip_resolver.py`: Unit tests for direct client, trusted proxy, untrusted proxy, IPv4, IPv6, spoofing.
7. `tests/unit/apps/trading_engine/test_rate_limit_service.py`: Unit tests for policy resolution, key generation, metrics.
8. `tests/integration/apps/trading_engine/test_rate_limiting.py`: End-to-end integration tests for protected endpoints, 429 status, headers, and anti-enumeration.
9. `docs/EPIC-027-PHASE-2-AUDIT.md`: (This audit document).
10. `docs/EPIC-027-PHASE-2-RATE-LIMITING.md`: Architecture & policy documentation.
11. `docs/EPIC-027-PHASE-2-SECURITY.md`: Threat model & security analysis.
12. `docs/EPIC-027-PHASE-2-VERIFICATION.md`: Final Phase 2 verification report.

---

## 17. Migration Requirement Assessment

- **Assessment:** **No database migration required.**
- **Rationale:** Rate limiting state is ephemeral burst telemetry stored exclusively in Redis (and memory fallback). No persistent schema changes or table alterations are required.

---

## 18. Dependency Change Assessment

- **Assessment:** **No new dependencies required.**
- **Rationale:** The existing `redis.asyncio` package natively supports Lua script evaluation via `client.eval()`. Python standard library `ipaddress` handles IPv4/IPv6 validation. Adding `slowapi` is unnecessary and would introduce duplicate connection pools and unneeded abstractions.

---

## 19. Security Risks & Mitigations

| Threat | Risk | Mitigation |
|---|---|---|
| **X-Forwarded-For Spoofing** | Attacker bypasses IP rate limit by forging headers | Check socket client first; only trust header if socket is in `trusted_proxies`. |
| **Redis Denial of Service / Outage** | Unprotected endpoints or application crash if Redis is down | Bounded in-memory fallback sliding window limiter with automatic recovery. |
| **Memory Exhaustion (OOM)** | Attacker floods distinct fake keys into in-memory fallback | Hard maximum key capacity (10,000 keys) with LRU eviction and active TTL sweep. |
| **Race Conditions Under Load** | Concurrency allows burst to exceed limit | Atomic Lua script executed server-side in Redis (`EVAL`). |
| **User Enumeration Channel** | Rate limit error differences reveal registered emails | Generic responses preserved; limits keyed on client IP, not existence of user. |
| **Cross-Tenant Quota Starvation** | One tenant exhausts another tenant's allowance | Authenticated endpoints strictly keyed by `user_id` and `organization_id`. |

---

## 20. Rollback Considerations

- If rate limiting causes unintended friction in testing or deployment:
  - Setting `ORION_RATE_LIMITING_ENABLED=false` immediately bypasses rate check logic.
  - No database changes means zero rollback migrations.
  - Zero disruption to existing paper trading, market data, and risk engine operations.
