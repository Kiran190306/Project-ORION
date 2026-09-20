# EPIC-017 Phase 1: Organizations, Members & Database Foundation

**Project**: Project ORION — Institutional Forex Trading Platform  
**Epic**: EPIC-017 (Phase 1)  
**Status**: ✅ **PHASE 1 COMPLETE**  
**Trading Engine Safety**: **STRICT PAPER TRADING ONLY** (Zero real funds / Zero live broker execution)  

---

## 1. Architectural Overview

EPIC-017 Phase 1 introduces the foundational multi-tenant data model and domain abstractions for Project ORION without altering the validated execution pipeline or disrupting pre-existing single-user paper trading workflows.

The commercial multi-tenancy hierarchy is established as:
$$\text{User} \longrightarrow \text{OrganizationMember} \longrightarrow \text{Organization} \longrightarrow \text{Tenant-Scoped Resources}$$

This architecture separates:
1. **Platform-level governance**: Governed by `UserModel.is_superuser`.
2. **Tenant-level governance**: Governed by `OrganizationMemberModel.role` across the 7 institutional roles.

---

## 2. Domain Entities & Value Objects

The domain layer is established under [`libraries/domain/organization/`](file:///C:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/domain/organization/):

### 2.1 Organization (`libraries/domain/organization/models.py`)
Immutable domain entity (`@dataclass(frozen=True)`):
- `id: str`: Unique tenant identifier prefixed with `org_`
- `name: str`: Display name of the institutional trading desk
- `slug: str`: URL-safe, unique organization identifier
- `status: OrganizationStatus`: Lifecycle status (`ACTIVE` or `SUSPENDED`)
- `created_at: datetime`: Timezone-aware UTC timestamp
- `updated_at: datetime`: Timezone-aware UTC timestamp
- `meta_data: dict[str, Any]`: Extensible JSON metadata

### 2.2 OrganizationMember (`libraries/domain/organization/models.py`)
Immutable domain entity representing a user's association with an organization:
- `id: str`: Unique membership record identifier prefixed with `mem_`
- `organization_id: str`: Target organization ID
- `user_id: str`: User ID
- `role: OrganizationRole`: Institutional role
- `status: MembershipStatus`: Lifecycle status (`ACTIVE`, `SUSPENDED`, `INVITED`)
- `created_at: datetime`: Timezone-aware UTC timestamp
- `updated_at: datetime`: Timezone-aware UTC timestamp
- `meta_data: dict[str, Any]`: Extensible JSON metadata

---

## 3. The Seven Institutional Roles

Defined as a native Python 3.11 `StrEnum` (`OrganizationRole`):

| Role | Target Scope | Core Responsibility |
|---|---|---|
| `OWNER` | Organization | Full organizational control, billing, member provisioning, account lifecycle. |
| `ADMINISTRATOR` | Organization | Operational administration, integrations, audit log inspection. |
| `PORTFOLIO_MANAGER` | Multi-Account | Capital allocation, strategy parameters, consolidated performance. |
| `RISK_OFFICER` | Organization | Risk limits (drawdown, leverage caps), breach reviews, circuit breakers. |
| `TRADER` | Accounts | Manual order creation, position closures, trade history review. |
| `AUDITOR` | Organization | Read-only compliance, trade journals, immutable audit inspection. |
| `VIEWER` | Accounts | Read-only telemetry, live charts, dashboard monitoring. |

> [!IMPORTANT]
> **Superuser Distinction**: `UserModel.is_superuser` is strictly a platform-level infrastructure flag and is **never** conflated with `OWNER`. An `OWNER` has full rights within their tenant organization, while a `superuser` has cross-tenant diagnostic and maintenance access without trading backdoors.

---

## 4. Persistence Models & Schema

Defined in [`libraries/infrastructure/persistence/models/organization.py`](file:///C:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/infrastructure/persistence/models/organization.py):

### 4.1 Table: `organizations`
```sql
CREATE TABLE organizations (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    slug VARCHAR(128) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    meta_data JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE UNIQUE INDEX ix_organizations_slug ON organizations (slug);
CREATE INDEX ix_organizations_status ON organizations (status);
```

### 4.2 Table: `organization_members`
```sql
CREATE TABLE organization_members (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'VIEWER',
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    meta_data JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_organization_members PRIMARY KEY (id),
    CONSTRAINT fk_organization_members_organization_id_organizations FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    CONSTRAINT fk_organization_members_user_id_users FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_organization_members_org_user UNIQUE (organization_id, user_id)
);
CREATE INDEX ix_organization_members_organization_id ON organization_members (organization_id);
CREATE INDEX ix_organization_members_user_id ON organization_members (user_id);
```

---

## 5. Migration Strategy & Database Compatibility

### 5.1 Alembic Migration `0004_add_saas_multi_tenancy`
- **Revision**: `0004_add_saas_multi_tenancy`
- **Down Revision**: `0003_add_user_id_to_accounts`
- **Chain**: `0001_initial_schema` $\to$ `0002_add_users_table` $\to$ `0003_add_user_id_to_accounts` $\to$ `0004_add_saas_multi_tenancy`

### 5.2 SQLite Compatibility
Tested via fresh migration and upgrade from 0003:
- Fully supports Alembic standard table creation and index generation.
- Unique constraints (`uq_organization_members_org_user`) and indexes work identically to PostgreSQL.
- Downgrades cleanly drop tables and indexes without orphan artifacts.

### 5.3 PostgreSQL Compatibility
Verified against the live PostgreSQL 15 container (`postgresql+asyncpg://orion:orion@localhost:5433/orion_prod`):
- Migration 0004 applied cleanly using transactional DDL.
- Both tables (`organizations`, `organization_members`) verified via `information_schema.tables`.

---

## 6. Legacy Data & Backward Compatibility Strategy

1. **Zero Data Loss**: Existing records in `users`, `accounts`, `orders`, `positions`, `fills`, `trades`, `risk_limits`, and `strategy_configs` remain untouched.
2. **Account Ownership**: Existing accounts retain `user_id` linkage. Phase 1 does **not** force existing single-user accounts into artificial organizations or alter balances.
3. **Authentication Untouched**: `/api/v1/auth/login` and `/api/v1/auth/me` operate with zero changes.
4. **Deliberate Foreign Key Delete Behavior**:
   - `organization_members` cascades on deletion of `organization` or `user` to maintain referential hygiene.
   - Financial ledgers (`orders`, `positions`, `trades`) are **never** subjected to cascade deletion.

---

## 7. Repository & Service Architecture

### 7.1 Domain Protocol (`libraries/domain/organization/repository.py`)
`OrganizationRepository` protocol specifies:
- `create_organization(organization: Organization) -> Organization`
- `get_organization(organization_id: str) -> Organization | None`
- `get_organization_by_slug(slug: str) -> Organization | None`
- `update_organization(organization: Organization) -> Organization`
- `create_member(member: OrganizationMember) -> OrganizationMember`
- `get_member(organization_id: str, user_id: str) -> OrganizationMember | None`
- `list_members(organization_id: str, limit: int, offset: int) -> list[OrganizationMember]`
- `list_user_organizations(user_id: str) -> list[Organization]`
- `check_membership_exists(organization_id: str, user_id: str) -> bool`
- `update_member(member: OrganizationMember) -> OrganizationMember`
- `remove_member(organization_id: str, user_id: str) -> bool`

### 7.2 Implementation (`libraries/infrastructure/persistence/repositories/organization_repository.py`)
`SQLAlchemyOrganizationRepository` maps between pure domain entities and SQLAlchemy ORM models, enforcing async query semantics and proper transaction flushing.

### 7.3 Application Service (`apps/trading-engine/src/services/organization_service.py`)
`OrganizationService` provides:
- Organization creation with automated or explicit slug generation and uniqueness validation.
- Membership provisioning with duplicate prevention and role normalization.
- Member role updates and member removals.
- Cross-tenant organization listing.

---

## 8. Verification & Quality Gates

| Verification Suite | Tests Executed | Passed | Failed | Errors |
|---|---|---|---|---|
| **Domain Organization Models** | 14 | **14** | 0 | 0 |
| **OrganizationService & Repo** | 13 | **13** | 0 | 0 |
| **Migration 0004 (SQLite & PG)**| 3 | **3** | 0 | 0 |
| **Apps Unit & Integration Regression** | 204 | **204** | 0 | 0 |
| **Live Container 23-Step E2E** | 23 | **23** | 0 | 0 |
| **Ruff Linter** | Target Paths | **PASS** | 0 | 0 |
| **mypy Strict** | 16 source files | **PASS** | 0 | 0 |

---

## 9. Deferred Work (Subsequent EPIC-017 Phases)

The following capabilities are deliberately excluded from Phase 1 and will be introduced in subsequent phases:
- **Phase 2 / 3**: Resource-level `organization_id` tenancy propagation on `accounts`, `orders`, and `positions`.
- **Phase 4**: Declarative RBAC permission middleware and endpoint guards.
- **Phase 5**: Multi-tenant cross-organization IDOR verification suite.
- **Phase 6 / 7**: Subscription, Plan tiers (`FREE`, `PRO`, `BUSINESS`, `ENTERPRISE`), and entitlement quota enforcement.
- **Phase 8**: 6-step public onboarding API.
- **Phase 9 / 10**: Superuser admin endpoints and structured audit service.
- **Phase 11-14**: Production cloud deployment.
