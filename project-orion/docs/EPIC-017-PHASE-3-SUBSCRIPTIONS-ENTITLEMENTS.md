# Project ORION — EPIC-017 Phase 3: Subscriptions, Entitlements & Tier Enforcement

**Status**: IMPLEMENTED & VERIFIED  
**Sprint / Phase**: EPIC-017 Phase 3  
**Platform Safety**: STRICT PAPER TRADING ONLY (Zero live broker connectivity, zero customer funds)  
**Classification**: A. PHASE 3 COMPLETE  

---

## 1. Executive Summary

Phase 3 of **EPIC-017: SaaS Core Implementation & Cloud Production Deployment** implements the internal SaaS subscription, entitlement, and tier enforcement engine for Project ORION.

Building on the Organization foundation (Phase 1) and Tenant Isolation foundation (Phase 2), Phase 3 introduces:
1. **Four Canonical Plan Tiers**: Free Sandbox, Pro Trader, Business / Prop Desk, and Enterprise Institutional.
2. **Database Persistence & Migration 0006**: Structured `plans` and `subscriptions` tables with seeded tiers and auto-provisioning for existing organizations.
3. **Application Services**: `SubscriptionService` managing plan lifecycles and tier upgrades/downgrades; `EntitlementService` performing fail-closed quota validation and instrument access checks.
4. **Enforcement Points**: Interceptions in order submission (`OrderService`), account provisioning (`get_user_account`), and autonomous worker startup (`routes/worker.py`) that reject non-entitled activity prior to paper execution.
5. **REST API Routes**: `/api/v1/plans`, `/api/v1/subscription`, `/api/v1/entitlements`, and `/api/v1/subscription/change-plan`.
6. **100% Backward Compatibility**: Personal accounts (`organization_id is None`) continue paper trading seamlessly under default sandbox limits.

---

## 2. Canonical Plan Tiers & Limits

| Plan Tier | Code | Accounts | Daily Orders | Autonomous Workers | Allowed Currency Pairs | Data Retention |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: |
| **Free Sandbox** | `FREE` | 1 | 100 | 0 | Majors only (`EUR/USD`, `GBP/USD`, `USD/JPY`, `USD/CHF`) | 30 days |
| **Pro Trader** | `PRO` | 3 | 2,500 | 1 | Expanded pairs (12 FX pairs including Crosses) | 365 days |
| **Business / Prop Desk** | `BUSINESS` | 10 | 50,000 | 5 | All FX pairs (`*`) | 1,825 days (5 yrs) |
| **Enterprise Institutional** | `ENTERPRISE` | Unlimited (-1) | Unlimited (-1) | Unlimited (-1) | All FX pairs (`*`) | 2,555 days (7 yrs) |

---

## 3. Architecture & Enforcement Topology

```
                          ┌───────────────────────────────┐
                          │   Authenticated HTTP Request  │
                          │   (Bearer JWT + X-Org-ID?)    │
                          └───────────────┬───────────────┘
                                          │
                                          ▼
                          ┌───────────────────────────────┐
                          │    Tenant Context Resolver    │
                          │  • Resolves active user       │
                          │  • Resolves tenant org        │
                          └───────────────┬───────────────┘
                                          │
                                          ▼
                          ┌───────────────────────────────┐
                          │     Entitlement Service       │
                          │  • Resolves active sub & plan │
                          │  • Auto-provisions Free if new│
                          │  • Fail-closed if suspended   │
                          └───────────────┬───────────────┘
                                          │
            ┌─────────────────────────────┼─────────────────────────────┐
            │                             │                             │
            ▼                             ▼                             ▼
   [Account Quota]              [Order Entitlement]            [Worker Quota]
   • get_user_account()         • OrderService.create_order()  • routes/worker.py
   • Enforces max_accounts      • Enforces allowed_assets      • Enforces max_workers
   • HTTP 403 on limit          • Enforces max_daily_orders    • HTTP 403 on limit
                                • HTTP 403 / 429 on limit      • HTTP 403 if worker=0
```

---

## 4. Database Schema & Migration 0006

Migration `0006_subscription_entitlements` was generated and verified against both SQLite and a live PostgreSQL 15 production container.

### 4.1 `plans` Table
```sql
CREATE TABLE plans (
    id VARCHAR(64) PRIMARY KEY,
    code VARCHAR(32) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(255) NOT NULL DEFAULT '',
    max_accounts INTEGER NOT NULL DEFAULT 1,
    max_daily_orders INTEGER NOT NULL DEFAULT 100,
    max_workers INTEGER NOT NULL DEFAULT 0,
    allowed_assets JSON NOT NULL,
    retention_days INTEGER NOT NULL DEFAULT 30,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

### 4.2 `subscriptions` Table
```sql
CREATE TABLE subscriptions (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    plan_id VARCHAR(64) NOT NULL REFERENCES plans(id) ON DELETE RESTRICT,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    current_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    current_period_end TIMESTAMP WITH TIME ZONE NULL,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    meta_data JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

---

## 5. Security & Fail-Closed Principles

1. **Pre-Execution Quota Validation**:
   Checks are enforced **before** calling `PaperExecutionAdapter.submit_order()` or dispatching worker background loops. No fake fills or orphaned broker tasks can occur if an entitlement check fails.
2. **Fail-Closed on Inactive / Suspended Subscriptions**:
   If an organization's subscription is `SUSPENDED`, `CANCELLED`, or `EXPIRED`, `EntitlementService` raises `SubscriptionInactiveError` (HTTP 403 Forbidden). It will never silently fall back or re-provision Free tier access over an explicitly revoked tenant.
3. **Asset Authorization**:
   Trading non-whitelisted currency pairs returns HTTP 403 with `AssetNotEntitledError` detailing allowed assets versus requested symbol. Symbol formatting (`EURUSD` vs `EUR/USD`) is canonicalized automatically.
4. **Daily Rate Limiting**:
   Exceeding `max_daily_orders` returns HTTP 429 Too Many Requests (`DailyOrderQuotaExceededError`) with retry headers.
5. **Worker Restriction**:
   Free tier organizations cannot start autonomous trading workers (`max_workers = 0`), returning HTTP 403 Forbidden with prompt to upgrade to Pro Trader.

---

## 6. Verification & Test Summary

- **Domain Model Tests**: 24/24 PASS (`tests/unit/domain/subscription/test_subscription_models.py`).
- **Database Migration 0006**: 4/4 PASS (SQLite fresh, legacy upgrade with pre-existing orgs, downgrade/re-upgrade, PostgreSQL 15 live container).
- **Service & API Integration**: 16/16 PASS (`tests/integration/apps/trading_engine/test_phase3_entitlements.py`).
- **Regression Suite**: 225/225 trading engine app tests PASS.
- **Core Domain Tests**: 1,474/1,474 PASS.
- **Frontend Dashboard**: 24/24 Vitest tests PASS, production build PASS.
- **Linter & Type Checker**: Ruff 100% clean, mypy strict clean (15 SaaS source files).
