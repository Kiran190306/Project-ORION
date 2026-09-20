# PROJECT ORION — EPIC-019: PHASE 0 BASELINE AUDIT

**Epic**: EPIC-019 — Commercial Billing & Stripe Test-Mode Implementation  
**Phase**: Phase 0 — Existing Architecture Baseline Audit  
**Date**: 2026-09-20  
**Target Repository**: `project-orion/`  
**Git Baseline**: Commit `a0e18aa986e4fcbbb3395ea6e47cd1d9a7e2f33e` on `origin/main`  

---

## 1. Overview & Objective

Phase 0 establishes the empirical baseline of the Project ORION codebase prior to implementing commercial billing capabilities. The audit inspects all relevant existing modules across domain, persistence, application service, API route, and security layers to ensure complete compatibility and prevent duplication of existing concepts.

---

## 2. Existing Modules & Architecture Inspection

### 2.1. Domain Layer (`libraries/domain/subscription/`)
- **File**: `libraries/domain/subscription/models.py`
  - `PlanCode(StrEnum)`: Canonical tiers `FREE`, `PRO`, `BUSINESS`, `ENTERPRISE`.
  - `SubscriptionStatus(StrEnum)`: Lifecycle states `ACTIVE`, `TRIALING`, `SUSPENDED`, `CANCELLED`, `EXPIRED`.
  - `PlanLimits`: Immutable dataclass specifying quotas:
    - `max_accounts`: int
    - `max_daily_orders`: int
    - `max_workers`: int
    - `allowed_assets`: tuple[str, ...]
    - `retention_days`: int
  - `Plan`: Domain entity with `id`, `code`, `name`, `description`, `limits`, `is_active`.
  - `Subscription`: Domain entity with `id`, `organization_id`, `plan_id`, `status`, `current_period_start`, `current_period_end`, `cancel_at_period_end`, `meta_data`.
  - `Entitlement`: Aggregate value object combining organization, plan, and active limits.

### 2.2. Persistence Layer (`libraries/infrastructure/persistence/`)
- **File**: `libraries/infrastructure/persistence/models/subscription.py`
  - `PlanModel`: Table `plans` with columns for all plan attributes and quota thresholds.
  - `SubscriptionModel`: Table `subscriptions` linking `organization_id` (FK to `organizations.id`) to `plan_id` (FK to `plans.id`).
- **File**: `libraries/infrastructure/persistence/models/audit.py`
  - `AuditLogModel`: Table `audit_logs` storing `organization_id`, `event_type`, `component`, `actor`, `details` (JSON), and `timestamp`.

### 2.3. Database Migrations (`database/migrations/versions/`)
- Revisions 0001 through 0007 form a linear unbroken chain:
  - `0001_initial_schema`
  - `0002_add_users_table`
  - `0003_add_user_id_to_accounts`
  - `0004_add_saas_multi_tenancy`
  - `0005_add_organization_ownership`
  - `0006_subscription_entitlements` (created `plans` and `subscriptions`, seeded canonical plans)
  - `0007_organization_invitations` (current HEAD revision)
- **EPIC-019 Integration**: Migration `0008_billing_foundation.py` will have `down_revision = "0007_organization_invitations"`.

### 2.4. Application Services (`apps/trading-engine/src/services/`)
- **File**: `subscription_service.py`
  - Contains `CANONICAL_PLANS` definitions and default assignment logic.
  - Implements `get_plan`, `get_plan_by_code`, `get_active_subscription`, `assign_default_subscription`, and `change_plan`.
- **File**: `entitlement_service.py`
  - Implements fail-closed quota validation:
    - `check_account_quota(organization_id)`
    - `check_daily_order_quota(organization_id)`
    - `check_worker_quota(organization_id)`
    - `check_asset_access(organization_id, symbol)`
    - `get_usage_summary(organization_id)`

### 2.5. RBAC & Security (`libraries/domain/organization/permissions.py`)
- Fine-grained permissions already defined:
  - `Permission.SUBSCRIPTION_READ`: Read subscription and quota details. (Roles: `OWNER`, `ADMINISTRATOR`, `PORTFOLIO_MANAGER`, `RISK_OFFICER`).
  - `Permission.SUBSCRIPTION_MANAGE`: Initiate upgrades, downgrades, and cancellations. (Roles: `OWNER`, `ADMINISTRATOR`).

### 2.6. API Routes (`apps/trading-engine/src/routes/subscription.py`)
- Existing endpoints:
  - `GET /api/v1/plans`: Returns active tiers and quotas.
  - `GET /api/v1/subscription`: Returns active subscription for current tenant organization.
  - `GET /api/v1/entitlements`: Returns quota limits and real-time utilization.
  - `POST /api/v1/subscription/change-plan`: Internal/administrative tier switch.
- **EPIC-019 Integration**: New billing routes will be housed in `apps/trading-engine/src/routes/billing.py` under prefix `/api/v1/billing`, providing commercial checkout, webhook handling, and invoice access.

---

## 3. Baseline Audit Confirmation

1. **No Redundancy**: EPIC-019 will strictly extend existing models by adding billing-specific tables rather than replacing `plans` or `subscriptions`.
2. **Deterministic Test Readiness**: The test suite currently has 412 passing Python tests and 24 passing Vitest tests.
3. **Safety Status**: Strict paper-trading mode (`is_paper=True`) and disabled worker (`ORION_WORKER_ENABLED=false`) are firmly established in production and testing baselines.
