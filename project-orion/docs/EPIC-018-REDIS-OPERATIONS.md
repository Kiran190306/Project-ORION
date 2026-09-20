# PROJECT ORION — EPIC-018 PHASE 4: REDIS RELIABILITY & OPERATIONS

**Project**: Project ORION — Institutional Forex Trading Platform  
**Epic**: EPIC-018 — Production Operations, Reliability, Security Hardening & Release Freeze  
**Phase**: Phase 4 — Redis Reliability & Operations  
**Date**: 2026-09-20  
**Target Platform**: Render Managed Redis 7 (`orion-redis`)  
**Client**: `redis.asyncio` via `RedisClient` (`libraries/infrastructure/caching/client.py`)  

---

## 1. Executive Summary

Phase 4 audits and documents the operational characteristics of the **Render Managed Redis 7** cluster supporting Project ORION. 

In Project ORION's multi-tenant architecture, Redis functions as a **high-throughput ephemeral cache, distributed session token validator, and rate-limiting coordinator**. Redis is deliberately decoupled from core transactional accounting: all balance updates, trade fills, positions, and audit records persist in PostgreSQL. 

This architectural separation guarantees that if Redis degrades or experiences a network partition, the application degrades gracefully under a **non-blocking cache-aside fallback**, preventing cascading outages or trading paralysis.

---

## 2. Redis Connection Pool & Architecture

The Redis client wrapper is implemented in `libraries/infrastructure/caching/client.py` using `redis.asyncio.ConnectionPool`.

### 2.1. Operational Parameters
| Parameter | Value | Description / Operational Role |
|---|---|---|
| `max_connections` | `20` | Bounds the maximum open TCP sockets per pod to prevent socket exhaustion on Render's free tier. |
| `socket_timeout` | `5.0s` | Maximum time allowed for read/write operations before raising `RedisTimeoutError`. |
| `socket_connect_timeout` | `5.0s` | Maximum time allowed to establish initial TCP handshake and TLS negotiation. |
| `retry_on_timeout` | `True` | Automatically re-attempts transient socket timeouts once before bubbling up an error. |
| `health_check_interval` | `30s` | Periodically emits internal PINGs on idle connections to prune silent dead sockets. |
| `decode_responses` | `True` | Automatically decodes incoming Redis byte strings to UTF-8 strings. |

### 2.2. Connection Establishment & Concurrency Guard
Connection pool instantiation is thread-safe and protected by an `asyncio.Lock()` to prevent double initialization race conditions:
```python
async with self._lock:
    if self._connected and self._client is not None:
        return
    self._pool = aioredis.ConnectionPool.from_url(
        self._config.url,
        max_connections=self._config.max_connections,
        socket_timeout=self._config.socket_timeout,
        socket_connect_timeout=self._config.socket_connect_timeout,
        retry_on_timeout=self._config.retry_on_timeout,
        health_check_interval=self._config.health_check_interval,
        decode_responses=self._config.decode_responses,
    )
    self._client = aioredis.Redis(connection_pool=self._pool)
    await self._client.ping()
    self._connected = True
```

---

## 3. Failure Handling & Non-Blocking Degradation

### 3.1. Absence of Dangerous Infinite Reconnect Loops
The client wrapper strictly avoids unbounded `while True: reconnect()` loops that could block Python's asyncio event loop.
- Connection failures raise typed exceptions: `RedisConnectionError`, `RedisTimeoutError`, or `RedisError`.
- If an operation fails, the error is caught, logged with correlation context, and fallback logic executes.

### 3.2. Cache-Aside Degradation Pattern
- **Market Data & Tick Caching**: When market data is requested, the system attempts to read the latest tick from Redis. If Redis is unavailable, the system falls back to querying recent ticks from PostgreSQL or the paper adapter without throwing an HTTP 500 to the user.
- **Session Tokens**: JWT authentication validates cryptographic signatures in-memory using public/symmetric HMAC keys. Redis is consulted only for token revocation / denylist checks. If Redis fails, tokens remain verifiable via cryptographic signature checks.

### 3.3. Readiness Probe Behavior
The `/health/ready` endpoint interrogates both PostgreSQL and Redis:
```python
is_healthy = await self._redis_client.health_check()
```
- If Redis is down, `/health/ready` reports:
  ```json
  {
    "overall": "unhealthy",
    "database": true,
    "redis": false
  }
  ```
  with HTTP status `503 Service Unavailable`. This immediately notifies monitoring infrastructure and prevents traffic routing to a pod with broken caching.

---

## 4. Operational Maintenance & Triage

### 4.1. Verifying Redis Connectivity via CLI / Python
```python
import asyncio
from libraries.infrastructure.caching.client import RedisClient

async def test_redis():
    client = RedisClient()
    await client.connect()
    pong = await client.ping()
    print("Redis PING:", pong)
    await client.disconnect()

asyncio.run(test_redis())
```

### 4.2. Safe Cache Invalidation / Flush
If corrupted data is suspected in the cache, flush only the current database partition:
```bash
# Executed via Redis CLI on the private network
redis-cli -u "${REDIS_URL}" FLUSHDB
```
*Never execute `FLUSHALL` as it impacts multi-tenant partitions across other possible services.*

---

## 5. Summary of Redis Operational Status

| Check | Production Target | Verified State |
|---|---|:---:|
| **Redis Server Version** | Redis 7 | **VERIFIED** (Render Managed) |
| **Network Security** | Private VPC only (`ipAllowList: []`) | **VERIFIED** |
| **Connection Timeout** | 5.0 seconds | **VERIFIED** |
| **Readiness Integration** | Included in `/health/ready` check | **VERIFIED** |
| **Worker Independence** | Decoupled from core order execution | **VERIFIED** |
