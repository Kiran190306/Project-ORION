# PROJECT ORION — EPIC-018 PHASE 2: DATABASE OPERATIONS

**Project**: Project ORION — Institutional Forex Trading Platform  
**Epic**: EPIC-018 — Production Operations, Reliability, Security Hardening & Release Freeze  
**Phase**: Phase 2 — Database Operations  
**Date**: 2026-09-20  
**Target Platform**: Render Managed PostgreSQL 15 (`orion-postgres`)  
**Engine**: SQLAlchemy 2.0 AsyncEngine + `asyncpg` Driver  
**Migration Head**: `0007_organization_invitations`  

---

## 1. Executive Summary

Phase 2 formalizes operational engineering for Project ORION's primary persistent datastore: **Render Managed PostgreSQL 15**. 

The operational architecture combines:
- Non-blocking asynchronous connection pooling via SQLAlchemy `create_async_engine` and `asyncpg`.
- Proactive connection health verification (`pool_pre_ping=True`) to seamlessly prune stale TCP connections.
- Strict linear Alembic migrations (revisions 0001 through 0007) automatically executed during application startup.
- Tenant isolation enforced at the schema and query level via `organization_id` partitioning.
- Zero destructive database operations policy: table drops, in-place column truncations, and migration resets are strictly forbidden.

---

## 2. PostgreSQL Connection Pool Architecture

The database connection pool is managed by `DatabaseManager` (`libraries/infrastructure/persistence/config.py`).

### 2.1. Pool Configuration Parameters
| Parameter | Value | Rationale / Behavior |
|---|---|---|
| `pool_size` | `10` | Number of persistent connections kept open in the pool per container pod. |
| `max_overflow` | `20` | Maximum surge connections permitted during peak concurrent request bursts (up to 30 total connections per pod). |
| `pool_timeout` | `30.0s` | Maximum wait duration before an acquisition request raises `TimeoutError` if pool is saturated. |
| `pool_recycle` | `1800s` (30m) | Closes and recreates idle connections after 30 minutes to prevent backend server-side drops. |
| `pool_pre_ping` | `True` | Emits a lightweight `SELECT 1` ping before handing out a connection; discards dead sockets transparently. |
| `echo` | `False` | Disables verbose query printing in production logs to prevent sensitive query payload leakage. |

### 2.2. Session Lifecycle & Transaction Handling
- Sessions are instantiated via `async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)`.
- All operations adhere to standard unit-of-work patterns:
  ```python
  async with db_manager.session() as session:
      async with session.begin():
          # Transactional statements executed atomically
          ...
      # Commits on successful exit; rolls back automatically on unhandled exception
  ```
- No long-running background tasks hold transactions open; background worker loops query data in discrete short-lived read/write scopes.

---

## 3. Alembic Migration Hierarchy (0001 → 0007)

Migrations are tracked linearly in `database/migrations/versions/`. All migrations feature idempotent upgrades and tested downgrades.

```
0001_initial_schema
        │
0002_add_users_table
        │
0003_add_user_id_to_accounts
        │
0004_add_saas_multi_tenancy
        │
0005_add_organization_ownership
        │
0006_add_subscription_entitlements
        │
0007_organization_invitations [HEAD]
```

### 3.1. Revisions Summary
1. **`0001_initial_schema`**: Foundational tables (`accounts`, `orders`, `fills`, `positions`, `market_ticks`). Defines primary keys, foreign keys, numeric decimal precisions, and timestamps.
2. **`0002_add_users_table`**: Identity management (`users`). Defines password hash storage, email indexing, and active state flags.
3. **`0003_add_user_id_to_accounts`**: Links trading accounts to individual users with foreign key cascade integrity.
4. **`0004_add_saas_multi_tenancy`**: Introduces multi-tenant constructs: `organizations`, `organization_memberships`, and `audit_logs`.
5. **`0005_add_organization_ownership`**: Adds tenant partitioning (`organization_id`) to `accounts`, `orders`, `positions`, and trading configurations.
6. **`0006_add_subscription_entitlements`**: Introduces `subscriptions` and `entitlements` tables for tier management (FREE, PRO, ENTERPRISE).
7. **`0007_organization_invitations`**: Adds tokenized membership invitation workflows (`organization_invitations`) with cryptographic tokens and expiration timestamps.

### 3.2. Automated Startup Execution
In cloud production, `ORION_RUN_MIGRATIONS=true` triggers Alembic during the FastAPI lifespan startup (`lifespan.py`):
```python
if settings.run_migrations:
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
```
If an unhandled migration exception occurs, startup aborts immediately (`SystemExit(1)`), preventing the container from serving traffic against an incompatible or partially migrated database.

---

## 4. Operational Failure Handling & Recovery

### 4.1. Database Connection Drop / Network Partition
- **Symptom**: `asyncpg.exceptions.ConnectionDoesNotExistError` or TCP disconnect.
- **System Response**:
  1. `pool_pre_ping=True` detects dead socket prior to request processing.
  2. SQLAlchemy recycles the connection and transparently establishes a fresh socket to Render PostgreSQL.
  3. If PostgreSQL is completely unreachable, the `/health/ready` probe fails immediately, returning `503 Service Unavailable`:
     ```json
     {"overall": "unhealthy", "database": false, "redis": true}
     ```
  4. Render routing stops sending external user traffic to the failing pod until connectivity recovers.

### 4.2. Lock Contention & Transaction Deadlocks
- **Safeguards**:
  - Fine-grained row-level locking (`SELECT ... FOR UPDATE`) is avoided in favor of tenant-isolated optimistic state validation.
  - Transactions complete in under 50 milliseconds.
  - PostgreSQL statement timeout parameter prevents hanging transactions from consuming pool connections.

### 4.3. Migration Rollback Limitations
- **Operational Rule**: Live production databases must NEVER be rolled back via blind `alembic downgrade -1` during an active incident unless the migration was strictly additive and verified in staging.
- **Forward-Fix Strategy**: If a defective migration is applied, a new forward migration (`0008_...`) must be authored and applied to rectify schema drift without data loss.
- **Destructive Commands Prohibited**: `DROP TABLE`, `DROP COLUMN`, and `TRUNCATE` are prohibited in all operational runbooks.
