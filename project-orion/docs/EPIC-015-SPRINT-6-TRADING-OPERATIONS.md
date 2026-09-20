# EPIC-015 Sprint-6: Trading Operations, Authentication & Dashboard Foundation

> **Status**: ✅ COMPLETE  
> **Sprint**: 6 of EPIC-015  
> **Branch**: main  
> **Date**: 2026-09-19

---

## Overview

Sprint-6 transforms the Project ORION trading engine foundation established in Sprint-5 into a real user-facing paper-trading application. This sprint delivers authentication, authorization, order management, position tracking, trade history, portfolio analytics, strategy control, and a consolidated dashboard API.

### Sprint-5 Baseline (Starting Point)

| Suite | Passed | Failed | Errors | Notes |
|-------|--------|--------|--------|-------|
| Application Unit | 99 | 0 | 0 | |
| Application Integration | 26 | 0 | 1 | Redis connection refused (infra) |
| Strategy | 157 | 0 | 0 | |
| Trading | 157 | 0 | 0 | |
| Risk | 288 | 0 | 0 | |
| Market Data | 173 | 0 | 0 | |
| Notification | 11 | 0 | 0 | |
| Portfolio | 491 | 9 | 0 | Pre-existing (journal ordering, dataclass immutability) |
| Execution | 104 | 52 | 21 | Pre-existing (model parameter, sync/async mismatches) |

---

## Architecture Decisions

### AD-1: Direct bcrypt (No passlib)

**Decision**: Use `bcrypt` library directly instead of `passlib`.

**Rationale**: `passlib` 1.7.4 has a known compatibility defect with `bcrypt` >= 4.0.0:
- `AttributeError: module 'bcrypt' has no attribute '__about__'`
- `ValueError: password cannot be longer than 72 bytes`

**Implementation**: `apps/trading-engine/src/services/auth.py`
- `bcrypt.hashpw()` / `bcrypt.checkpw()` with standard UTF-8 encoding
- 72-byte safe truncation to prevent boundary errors
- Standard bcrypt salting via `bcrypt.gensalt()`

### AD-2: Environment-Driven JWT Configuration

**Decision**: JWT secret key, algorithm, and expiration are sourced from environment variables.

| Variable | Default | Description |
|----------|---------|-------------|
| `ORION_JWT_SECRET_KEY` | `insecure-dev-secret-key-...` | JWT signing secret |
| `ORION_JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `ORION_JWT_EXPIRE_MINUTES` | `30` | Token expiration |

**Rationale**: Deterministic default (not random `secrets.token_urlsafe`) ensures tokens survive process restarts in development. Production deployments MUST set `ORION_JWT_SECRET_KEY`.

### AD-3: Real-Time Architecture Gap (Documented for Sprint-7)

**Decision**: No WebSocket/SSE implementation in Sprint-6.

**Rationale**:
- `RedisClient` currently wraps basic key-value operations without pub/sub
- Redis is optional in development/test setups
- WebSockets without distributed pub/sub would produce fragile in-memory implementation
- **Sprint-7 Action**: Implement Redis pub/sub event bus, then add WebSocket endpoints

### AD-4: Non-Destructive Database Migration

**Decision**: `user_id` column added to `accounts` table as nullable with `SET NULL` on delete.

**Implementation**: `database/migrations/versions/0003_add_user_id_to_accounts.py`
- Column: `user_id VARCHAR(64)` with FK to `users.id`
- Index: `ix_accounts_user_id`
- On delete: `SET NULL` (non-destructive)

---

## API Endpoints

### Authentication & Authorization

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/login` | Public | Login with username/password, returns JWT |
| POST | `/api/v1/auth/logout` | Bearer | Logout (token invalidation) |
| GET | `/api/v1/auth/me` | Bearer | Get authenticated user info |

### Account Management

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/account/` | Bearer | Get account details |
| GET | `/api/v1/account/summary` | Bearer | Get account financial summary |

### Order Management

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/orders/` | Bearer | Create a new paper trading order |
| GET | `/api/v1/orders/` | Bearer | List orders (paginated, filterable) |
| GET | `/api/v1/orders/{order_id}` | Bearer | Get order by ID |
| POST | `/api/v1/orders/{order_id}/cancel` | Bearer | Cancel a pending order |

### Position Management

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/positions/` | Bearer | List positions (paginated, filterable) |
| GET | `/api/v1/positions/{position_id}` | Bearer | Get position by ID |
| POST | `/api/v1/positions/{position_id}/close` | Bearer | Close an open position |

### Trade History

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/trades/` | Bearer | List trade fills (paginated, filterable) |
| GET | `/api/v1/trades/{trade_id}` | Bearer | Get trade by ID |

### Portfolio Analytics

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/portfolio/` | Bearer | Portfolio overview (balance, equity, margin) |
| GET | `/api/v1/portfolio/equity` | Bearer | Equity curve and drawdown metrics |
| GET | `/api/v1/portfolio/pnl` | Bearer | P&L breakdown |
| GET | `/api/v1/portfolio/exposure` | Bearer | Currency exposure analysis |

### Strategy Control

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/strategies/` | Public | List all available strategies |
| GET | `/api/v1/strategies/{id}` | Public | Get strategy details |
| GET | `/api/v1/strategies/{id}/config-schema` | Public | Get configurable parameter schema |
| GET | `/api/v1/strategies/account/config` | Bearer | Get active account strategy config |
| PUT | `/api/v1/strategies/account/config` | Bearer | Update account strategy config |

### Dashboard

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/dashboard/` | Bearer | Consolidated dashboard data |

### Worker Control

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/worker/status` | Bearer | Worker status |
| GET | `/api/v1/worker/metrics` | Bearer | Worker metrics |
| POST | `/api/v1/worker/start` | Superuser | Start worker |
| POST | `/api/v1/worker/stop` | Superuser | Stop worker |

### Infrastructure

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/health` | Public | Health check |
| GET | `/api/v1/health/live` | Public | Liveness probe |
| GET | `/api/v1/metrics` | Public | Prometheus metrics |
| GET | `/api/v1/risk/status` | Public | Risk engine status |

---

## Pagination & Filtering

All list endpoints support standardized pagination and filtering:

```
GET /api/v1/orders/?limit=20&offset=0&sort_by=created_at&order=desc&date_from=2026-01-01T00:00:00Z&date_to=2026-12-31T23:59:59Z&symbol=EUR/USD&status=FILLED
```

Response envelope:
```json
{
    "items": [...],
    "total": 100,
    "limit": 20,
    "offset": 0,
    "has_more": true
}
```

---

## Security

### Authentication
- JWT Bearer tokens via `Authorization: Bearer <token>` header
- bcrypt password hashing with 72-byte safe truncation
- Configurable token expiration (default: 30 minutes)

### Authorization
- Role-based: `get_current_active_user` for standard endpoints
- `get_current_superuser` for worker control endpoints
- Account ownership verification (IDOR prevention) on all data endpoints

### Security Headers
All responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Cache-Control: no-store, no-cache, must-revalidate`
- `X-XSS-Protection: 1; mode=block`
- `X-Correlation-ID: <uuid>` (correlation tracking)

### Paper Trading Safety
- All trading responses include `is_paper: bool = True`
- `AccountModel.is_live = False` enforced
- No live broker connections possible

---

## Database Changes

### Migration: 0003_add_user_id_to_accounts

```sql
ALTER TABLE accounts ADD COLUMN user_id VARCHAR(64);
ALTER TABLE accounts ADD CONSTRAINT fk_accounts_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
CREATE INDEX ix_accounts_user_id ON accounts (user_id);
```

---

## Application Service Layer

| Service | Responsibility |
|---------|---------------|
| `OrderService` | Order lifecycle: create, list, get, cancel |
| `PositionService` | Position queries and close operations |
| `TradeService` | Trade/fill history with pagination |
| `PortfolioService` | Portfolio overview, equity, P&L, exposure |
| `DashboardService` | Consolidated aggregation across all services |

All services are instantiated per-request via FastAPI dependency injection, receiving the `PaperExecutionAdapter`, `AsyncSession`, and `AccountModel` as constructor arguments.

---

## Files Changed

### New Files
| File | Purpose |
|------|---------|
| `apps/trading-engine/src/services/order_service.py` | Order lifecycle orchestration |
| `apps/trading-engine/src/services/position_service.py` | Position management |
| `apps/trading-engine/src/services/trade_service.py` | Trade history queries |
| `apps/trading-engine/src/services/portfolio_service.py` | Portfolio analytics |
| `apps/trading-engine/src/services/dashboard_service.py` | Dashboard aggregation |
| `apps/trading-engine/src/routes/orders.py` | Order API endpoints |
| `apps/trading-engine/src/routes/positions.py` | Position API endpoints |
| `apps/trading-engine/src/routes/trades.py` | Trade API endpoints |
| `apps/trading-engine/src/routes/portfolio.py` | Portfolio API endpoints |
| `apps/trading-engine/src/routes/dashboard.py` | Dashboard API endpoint |
| `database/migrations/versions/0003_add_user_id_to_accounts.py` | User-account migration |
| `tests/unit/apps/trading_engine/test_orders.py` | Order endpoint tests |
| `tests/unit/apps/trading_engine/test_positions.py` | Position endpoint tests |
| `tests/unit/apps/trading_engine/test_trades.py` | Trade endpoint tests |
| `tests/unit/apps/trading_engine/test_portfolio.py` | Portfolio endpoint tests |
| `tests/unit/apps/trading_engine/test_dashboard.py` | Dashboard endpoint tests |
| `tests/unit/apps/trading_engine/test_strategy_control.py` | Strategy control tests |
| `docs/EPIC-015-SPRINT-6-TRADING-OPERATIONS.md` | This document |

### Modified Files
| File | Change |
|------|--------|
| `libraries/infrastructure/persistence/models/account.py` | Added `user_id` FK + relationship |
| `apps/trading-engine/src/config.py` | Added JWT settings |
| `apps/trading-engine/src/services/auth.py` | passlib → direct bcrypt, env-driven JWT |
| `apps/trading-engine/src/workers/__init__.py` | Fixed absolute → relative imports |
| `apps/trading-engine/src/dependencies.py` | Added `get_user_account`, `get_pagination_params` |
| `apps/trading-engine/src/schemas.py` | Added Sprint-6 DTOs (~400 lines) |
| `apps/trading-engine/src/routes/auth.py` | Clean imports, typed UserResponse |
| `apps/trading-engine/src/routes/account.py` | Auth protection |
| `apps/trading-engine/src/routes/worker.py` | Auth protection (superuser for controls) |
| `apps/trading-engine/src/routes/strategies.py` | Detail, config-schema, account config endpoints |
| `apps/trading-engine/src/main.py` | Mount new routers, security headers middleware |
| `tests/unit/apps/trading_engine/test_auth.py` | Rewritten with proper mock fixtures |

---

## Pre-Existing Technical Debt (Unchanged)

These pre-existing failures are NOT Sprint-6 regressions:

- **Portfolio**: 491 passed, 9 failed (journal ordering + dataclass immutability)
- **Execution**: 104 passed, 52 failed, 21 errors (model parameter + sync/async mismatches)
- **Integration**: 1 error (Redis connection refused — no local Redis in dev)

---

## Sprint-7 Roadmap

1. **WebSocket/SSE Real-Time Updates**: Implement Redis pub/sub event bus, then WebSocket endpoints for live position/order updates
2. **Frontend Dashboard**: React/Next.js dashboard consuming the Sprint-6 API
3. **Live Broker Integration**: MT4/MT5 broker adapter alongside paper adapter
4. **Performance Optimization**: Database query optimization, connection pooling tuning
5. **Audit Logging**: Comprehensive audit trail for all trading operations
