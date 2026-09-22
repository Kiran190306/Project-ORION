# EPIC-027 Phase 2 — Public API Rate Limiting Architecture & Policy Specification

**Project**: Project ORION
**Milestone**: EPIC-027 (Public Beta & Commercial Launch Readiness)
**Phase**: Phase 2 — Public API Rate Limiting & Abuse Defense
**Classification**: Production-Grade Distributed Rate Limiting with High-Resilience Fallback
**Operational Status**: ACTIVE ($0.00 Real Capital at Risk / Sandbox-Only Mode)

---

## 1. Executive Summary

Project ORION requires institutional-grade abuse defense and traffic governance before opening registration to external beta users. Rate limiting protects against:
1. Credential stuffing and brute-force authentication attempts.
2. Denial-of-Service (DoS) and computational resource starvation from heavy backtests and walk-forward optimization sweeps.
3. Rapid scraping or exfiltration of proprietary trading logs and audit datasets.
4. Tenant quota overrun while preserving strict multi-tenant isolation.

The rate limiting subsystem utilizes an **atomic sliding-window algorithm** executed directly on Redis using Lua scripting. If Redis becomes partitioned or unavailable, the system automatically degrades to a **bounded in-memory sliding-window cache** (or fails closed on critical security boundaries), ensuring the platform remains resilient without exposing sensitive endpoints to unbounded traffic.

---

## 2. Rate Limit Policy Matrix

| Policy Name | Rate Limit | Scope | Primary Backend | Outage Fallback | Target Endpoints | Description |
|---|---|---|---|---|---|---|
| `AUTH_LOGIN` | 5 req / hour | `IP` | Redis Sorted Set | `BOUNDED_FALLBACK` | `POST /api/v1/auth/login` | Brute force and credential stuffing defense |
| `AUTH_FORGOT_PASSWORD` | 3 req / hour | `IP` | Redis Sorted Set | `BOUNDED_FALLBACK` | `POST /api/v1/auth/forgot-password` | Password reset dispatch throttling |
| `AUTH_RESEND_VERIFICATION` | 3 req / hour | `IP` | Redis Sorted Set | `BOUNDED_FALLBACK` | `POST /api/v1/auth/resend-verification` | Email verification dispatch throttling |
| `ONBOARDING_REGISTER` | 5 req / hour | `IP` | Redis Sorted Set | `BOUNDED_FALLBACK` | `POST /api/v1/onboarding/register` | Sybil defense against bot registration |
| `INVITATION_ACCEPT` | 10 req / hour | `IP` | Redis Sorted Set | `BOUNDED_FALLBACK` | `POST /api/v1/invitations/{token}/accept` | Invitation token brute force protection |
| `ORDERS_CREATE` | 60 req / min | `USER_AND_ORG` | Redis Sorted Set | `BOUNDED_FALLBACK` | `POST /api/v1/orders/` | Algorithmic runaway / flood throttling |
| `RESEARCH_EXECUTE` | 10 req / min | `USER_AND_ORG` | Redis Sorted Set | `BOUNDED_FALLBACK` | `POST /api/v1/research/experiments` | High-CPU backtest execution throttling |
| `OPTIMIZATION_EXECUTE` | 5 req / min | `USER_AND_ORG` | Redis Sorted Set | `BOUNDED_FALLBACK` | `POST /api/v1/optimization/run`, `POST /walk-forward` | Heavy grid/random parameter search throttling |
| `DATA_EXPORT` | 10 req / min | `USER_AND_ORG` | Redis Sorted Set | `BOUNDED_FALLBACK` | `GET /experiments/{id}/export`, `GET /jobs/{id}/export` | CSV/JSON large dataset extraction control |
| `BILLING_CHECKOUT` | 5 req / min | `USER_AND_ORG` | Redis Sorted Set | `BOUNDED_FALLBACK` | `POST /api/v1/billing/checkout` | Stripe session generation defense |
| `AUDIT_QUERY` | 30 req / min | `USER_AND_ORG` | Redis Sorted Set | `BOUNDED_FALLBACK` | `GET /organizations/{id}/audit-logs` | Compliance log query throttling |

---

## 3. Distributed Atomic Sliding Window Algorithm

### 3.1 Lua Implementation (`libraries/infrastructure/security/rate_limiter.py`)
Sliding windows are evaluated atomically in Redis using a single Lua script, eliminating race conditions across concurrent application processes without distributed locks:

```lua
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

-- 1. Remove expired timestamps outside the sliding window
local clear_before = now - window
redis.call('ZREMRANGEBYSCORE', key, '-inf', clear_before)

-- 2. Count surviving requests within window
local current_count = redis.call('ZCARD', key)

-- 3. Check limit
if current_count < limit then
    redis.call('ZADD', key, now, member)
    redis.call('PEXPIRE', key, window)
    local remaining = limit - current_count - 1
    local reset_after = math.ceil(window / 1000)
    return {1, remaining, 0, reset_after}
else
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = 1
    if oldest and #oldest >= 2 then
        local oldest_time = tonumber(oldest[2])
        local wait_ms = (oldest_time + window) - now
        if wait_ms > 0 then
            retry_after = math.ceil(wait_ms / 1000)
        end
    end
    local reset_after = retry_after
    return {0, 0, retry_after, reset_after}
end
```

### 3.2 Computational Complexity
- **Time**: $O(\log N + M)$ where $N$ is the number of elements in the sorted set and $M$ is the number of elements removed. Given small limits (5 to 60), execution overhead is $< 0.5\text{ ms}$.
- **Space**: $O(N)$ elements per active key. Redis key TTL (`PEXPIRE`) guarantees automatic reclamation when idle.

---

## 4. High-Resilience Fallback Architecture

When Redis experiences an outage, network partition, or connection timeout:
1. `RedisRateLimiter` catches the connection error and raises `RedisError`.
2. `RateLimitService` logs a structured warning and increments `rate_limit_redis_errors_total`.
3. Depending on `policy.fallback_mode`:
   - `BOUNDED_FALLBACK`: Diverts traffic to `InMemoryRateLimiter`. Tracks timestamps using an `OrderedDict` with an `asyncio.Lock()`. Automatically evicts the least recently used keys when exceeding `max_keys=10000`, guaranteeing $O(1)$ memory usage and preventing Out-Of-Memory (OOM) exploits.
   - `FAIL_CLOSED`: Rejects requests immediately with HTTP 429 (`Retry-After: 60`), preserving strict perimeter security for ultra-sensitive endpoints.
   - `FAIL_OPEN`: Passes requests gracefully if availability overrides security.

---

## 5. HTTP Response & Header Contract

When an endpoint exceeds its policy quota, the server responds with **HTTP 429 Too Many Requests** accompanied by institutional headers conforming to RFC-6585:

### 5.1 Headers
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 3600
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1790058360
X-Correlation-ID: 776573ed3c864d7ba5d76e06c8eba56d
Content-Type: application/json
```

### 5.2 JSON Body Envelope (RFC-7807)
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Please retry after 3600 seconds.",
  "detail": "Rate limit exceeded. Please retry after 3600 seconds.",
  "correlation_id": "776573ed3c864d7ba5d76e06c8eba56d",
  "timestamp": "2026-09-22T05:30:00.123456+00:00"
}
```

---

## 6. Observability & Telemetry

Prometheus telemetry records rate limit operations in real-time:
- `rate_limit_allowed_total`: Incremented on each permitted request.
- `rate_limit_rejected_total`: Incremented on each HTTP 429 rejection.
- `rate_limit_redis_errors_total`: Incremented when Redis calls fail.
- `rate_limit_fallback_total`: Incremented when requests are serviced by the in-memory fallback cache.
