# EPIC-015 Sprint-2: Application Assembly & Runtime Wiring

**Status:** ✅ COMPLETE  
**Date:** 2026-09-13  
**Repository:** `project-orion` on `main` branch (uncommitted)  
**Author:** Project ORION Engineering

---

## 1. Executive Summary

Sprint-2 successfully assembled Project ORION's mature domain modules into the platform's first **real, runnable FastAPI ASGI application runtime** (`apps/trading-engine`).

All Sprint-1 foundational layers (SQLAlchemy 2.x async persistence, Alembic migrations, Redis async pooling) were connected to the application runtime via clean dependency injection and async lifespan management. A safe, deterministic paper-trading flow was wired end-to-end through domain interfaces without duplicating any domain logic or requiring live broker credentials.

All quality gates pass:
- **Ruff check:** 0 errors
- **mypy --strict (`apps/trading-engine`):** 0 errors across 11 source files
- **Unit test suite (`tests/unit/apps/trading_engine`):** 22/22 passed
- **Integration test suite (`tests/integration/apps/trading_engine`):** 6/6 passed
- **Sprint-1 Foundation regression:** 22/22 passed
- **Domain regression (Strategies, Risk, Market Data):** 584/584 passed

---

## 2. Application Architecture

The Trading Engine application strictly observes Clean/Hexagonal Architecture and Domain-Driven Design (DDD):

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application Layer                       │
│                     (apps/trading-engine/src/main.py)                  │
├───────────────────┬───────────────────────────┬────────────────────────┤
│  Health Endpoints │     Metrics Endpoint      │     Trading Routes     │
│  /health/live     │     /metrics              │     /api/v1/paper-trade│
│  /health/ready    │     (Prometheus text)     │     (DTO in/out)       │
└─────────┬─────────┴─────────────┬─────────────┴────────────┬───────────┘
          │                       │                          │
          ▼                       ▼                          ▼
┌──────────────────┐    ┌──────────────────┐    ┌────────────────────────┐
│ Health Registry  │    │ Metrics Registry │    │  Paper Trading Service │
│ (Infra Adapter)  │    │  (Observability) │    │  (Application Service) │
└─────────┬────────┘    └──────────────────┘    └────────────┬───────────┘
          │                                                  │
          ├────────────────────────┐                         │
          ▼                        ▼                         ▼
┌──────────────────┐    ┌──────────────────┐    ┌────────────────────────┐
│ DatabaseManager  │    │   RedisClient    │    │      OrderBuilder      │
│ (PostgreSQL/SQL) │    │ (Connection Pool)│    │     (Domain Pure)      │
└──────────────────┘    └──────────────────┘    └────────────┬───────────┘
                                                             │
                                                             ▼
                                                ┌────────────────────────┐
                                                │  PaperExecutionAdapter │
                                                │ (Infra Broker Adapter) │
                                                └────────────────────────┘
```

### Architectural Principles Preserved:
1. **Domain Purity:** Zero framework imports (`fastapi`, `sqlalchemy`, `redis`) inside `libraries/domain/`.
2. **Dependency Inversion:** Applications depend on domain interfaces (`OrderBuilder`, `TradeDecision`, `BrokerAdapter`).
3. **No Service-Locator Anti-Patterns:** All dependencies (`AsyncSession`, `RedisClient`, `PaperTradingService`, `AppSettings`) are injected via FastAPI `Depends()`.
4. **No Global Mutable State:** Runtime dependencies are bound to `app.state` within the async lifespan context manager.

---

## 3. Endpoints Implemented

| Method | Path | Purpose | Status Code | Description |
|---|---|---|---|---|
| `GET` | `/health/live` | Process Liveness Probe | `200 OK` | Process/container liveness probe only. |
| `GET` | `/health/ready` | Infrastructure Readiness Probe | `200 OK` / `503 Service Unavailable` | Actively tests PostgreSQL connectivity via `SELECT 1` and Redis connectivity via `PING`. Returns 503 if any required dependency is unavailable. |
| `GET` | `/metrics` | Prometheus Metrics | `200 OK` | Exposes application counters and gauges in Prometheus text exposition format (version 0.0.4). |
| `POST` | `/api/v1/paper-trade` | Paper Trade Execution | `200 OK` / `400 Bad Request` / `503 Service Unavailable` | Submits an order through the paper execution pipeline. Validated via `PaperTradeRequest` DTO and returns `PaperTradeResponse` DTO. |

---

## 4. Infrastructure Wiring

### 4.1 Database Wiring (SQLAlchemy 2.x Async)
- Managed via `DatabaseManager` in `libraries/infrastructure/persistence/config.py`.
- Application startup instantiates an `AsyncEngine` with connection pooling (`pool_size`, `max_overflow`, `pool_recycle`, `pool_pre_ping=True`).
- `get_db_session` dependency yields an `AsyncSession` that commits on success, rolls back on error, and always closes on exit to eliminate connection leaks.
- On shutdown, `DatabaseManager.close()` disposes the underlying engine and connection pool cleanly.

### 4.2 Redis Wiring (redis-py 8.x Async)
- Managed via `RedisClient` in `libraries/infrastructure/caching/client.py`.
- Connects using `ConnectionPool.from_url` with timeout and retry configuration.
- Startup validates connectivity via `ping()`. If unavailable in dev/test, non-fatal warning is logged and `/health/ready` truthfully reports 503.
- On shutdown, `RedisClient.disconnect()` gracefully disconnects the connection pool.

### 4.3 Alembic Migrations
- Executed on startup only if `ORION_RUN_MIGRATIONS=true`.
- Invokes `alembic.command.upgrade(config, "head")` against authoritative migration scripts in `database/migrations/`.
- No migrations executed per request; no cron jobs created.

---

## 5. Domain Orchestration & Paper Trading Flow

The paper-trading pipeline executes deterministically without live broker credentials:

1. **Client Request:** `POST /api/v1/paper-trade` receives `PaperTradeRequest` DTO.
2. **Decision Construction:** `PaperTradingService.create_decision` creates an immutable `TradeDecision` with `outcome=EXECUTE`.
3. **Broker Neutrality:** Domain `OrderBuilder.build` translates the `TradeDecision` into a broker-neutral `Order` with rounding, tick size, and lot size precision.
4. **Paper Execution:** `PaperExecutionAdapter.submit_order` processes the order through simulated spread, slippage, and latency models.
5. **Metric Recording:** Application emits `orion_paper_trades_total` metric increment.
6. **Response:** Sanitized execution result returned as `PaperTradeResponse` DTO with correlation ID.

---

## 6. Error Handling & Observability

- **Centralized Handlers:** Registered in `apps/trading-engine/src/errors.py`.
- **Validation Errors (`RequestValidationError`):** Returns 422 with structured `ErrorResponse`.
- **HTTP Exceptions (`StarletteHTTPException`):** Returns appropriate status code with structured JSON.
- **Unhandled Exceptions (`Exception`):** Returns safe 500 without leaking stack traces or sensitive credentials. Server logs capture full trace with correlation ID.
- **Correlation ID:** Propagated across every request via HTTP middleware (`X-Correlation-ID`).

---

## 7. Quality Gate Verification

```bash
# 1. Ruff check apps/trading-engine
poetry run python -m ruff check apps/trading-engine
# Output: All checks passed!

# 2. mypy --strict apps/trading-engine
poetry run python -m mypy --strict apps/trading-engine
# Output: Success: no issues found in 11 source files

# 3. Unit tests
poetry run pytest tests/unit/apps/trading_engine -v
# Output: 22 passed in 3.99s

# 4. Integration tests
poetry run pytest tests/integration/apps/trading_engine -v
# Output: 6 passed in 2.95s

# 5. Sprint-1 Regression suite
poetry run pytest tests/unit/domain/notification tests/unit/infrastructure/persistence tests/unit/infrastructure/caching -v
# Output: 22 passed in 2.09s

# 6. Domain Regression suites
poetry run pytest tests/unit/domain/strategies tests/unit/domain/risk tests/unit/domain/market_data -q
# Output: 584 passed in 2.54s
```

---

## 8. File Inventory

### Files Created:
1. `apps/__init__.py`
2. `apps/trading-engine/src/__init__.py`
3. `apps/trading-engine/src/config.py`
4. `apps/trading-engine/src/schemas.py`
5. `apps/trading-engine/src/errors.py`
6. `apps/trading-engine/src/dependencies.py`
7. `apps/trading-engine/src/lifespan.py`
8. `apps/trading-engine/src/main.py`
9. `apps/trading-engine/src/routes/__init__.py`
10. `apps/trading-engine/src/routes/health.py`
11. `apps/trading-engine/src/routes/metrics.py`
12. `apps/trading-engine/src/routes/trading.py`
13. `apps/trading-engine/src/services/__init__.py`
14. `apps/trading-engine/src/services/paper_trading.py`
15. `tests/conftest.py`
16. `tests/unit/apps/__init__.py`
17. `tests/unit/apps/trading_engine/__init__.py`
18. `tests/unit/apps/trading_engine/test_config.py`
19. `tests/unit/apps/trading_engine/test_health.py`
20. `tests/unit/apps/trading_engine/test_errors.py`
21. `tests/unit/apps/trading_engine/test_metrics.py`
22. `tests/unit/apps/trading_engine/test_paper_trading_service.py`
23. `tests/integration/__init__.py`
24. `tests/integration/apps/__init__.py`
25. `tests/integration/apps/trading_engine/__init__.py`
26. `tests/integration/apps/trading_engine/test_app_startup.py`
27. `docs/EPIC-015-SPRINT-2-APPLICATION-ASSEMBLY.md`

### Files Modified:
1. `pyproject.toml` — Added dependencies for `fastapi`, `uvicorn`, `httpx`, `anyio` and package inclusion for `apps`.
