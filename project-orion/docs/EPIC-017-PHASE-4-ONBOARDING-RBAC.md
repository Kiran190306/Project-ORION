# Project ORION — EPIC-017 Phase 4: Organization Onboarding, Member Invitations & RBAC Route Governance

**Status**: IMPLEMENTED & VERIFIED  
**Sprint / Phase**: EPIC-017 Phase 4  
**Platform Safety**: STRICT PAPER TRADING ONLY (Zero live broker connectivity, zero customer funds)  
**Classification**: A. PHASE 4 COMPLETE  

---

## 1. Executive Summary

Phase 4 of **EPIC-017: SaaS Core Implementation & Cloud Production Deployment** elevates Project ORION from an internal multi-tenant prototype to a commercially ready institutional SaaS platform.

Phase 4 delivers three core pillars:
1. **Atomic Organization Onboarding**: A single transactional API (`POST /api/v1/onboarding/register`) that atomically provisions a tenant user, institutional organization, `OWNER` membership, default `FREE` subscription, and a $100,000.00 paper trading account under strict rollback-all guarantees.
2. **Cryptographic Member Invitations**: Secure out-of-band invitation system using high-entropy tokens (`secrets.token_urlsafe(32)`), SHA-256 DB token hashing, 7-day expiration, single-use enforcement, and tenant-scoped revocation.
3. **Institutional 7-Role RBAC & Centralized Route Governance**: 25 granular permissions strictly enforced across all operational endpoints (`orders`, `positions`, `trades`, `risk`, `workers`, `organizations`, `members`, `subscriptions`) via a declarative FastAPI dependency `require_permission`.
4. **Governance Invariants**: Last-owner protection (cannot demote, remove, or suspend the sole owner), self-escalation bans, superuser tenant separation, and seamless personal sandbox backward compatibility.

---

## 2. Canonical 7-Role RBAC Matrix

The platform enforces 25 granular operational permissions partitioned across 7 canonical roles. Superuser status (`is_superuser=True`) is a platform administrative flag and confers zero automatic permissions within a tenant organization.

| Permission Code | Category | OWNER | ADMINISTRATOR | PORTFOLIO_MANAGER | RISK_OFFICER | TRADER | AUDITOR | VIEWER |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `ORGANIZATION_READ` | Org Governance | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ORGANIZATION_UPDATE` | Org Governance | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `MEMBER_READ` | Membership | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `MEMBER_INVITE` | Membership | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `MEMBER_UPDATE` | Membership | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `MEMBER_REMOVE` | Membership | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `ACCOUNT_READ` | Account Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ACCOUNT_CREATE` | Account Admin | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `ACCOUNT_UPDATE` | Account Admin | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `ORDER_READ` | Orders | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ORDER_CREATE` | Orders | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| `ORDER_CANCEL` | Orders | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| `POSITION_READ` | Positions | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POSITION_CLOSE` | Positions | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| `TRADE_READ` | Trades | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `STRATEGY_READ` | Strategy | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `STRATEGY_CONFIGURE` | Strategy | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| `RISK_READ` | Risk Controls | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `RISK_CONFIGURE` | Risk Controls | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `WORKER_READ` | Autonomous Worker | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `WORKER_START` | Autonomous Worker | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `WORKER_STOP` | Autonomous Worker | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `SUBSCRIPTION_READ` | Subscriptions | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `SUBSCRIPTION_MANAGE`| Subscriptions | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `AUDIT_READ` | Compliance Audit | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| **Total Permissions** | | **25** | **21** | **19** | **12** | **14** | **11** | **10** |

---

## 3. Architecture & Transaction Flows

### 3.1 Transactional Onboarding Architecture
```
  POST /api/v1/onboarding/register
  ┌─────────────────────────────────────────────────────────────┐
  │ 1. Validate Uniqueness: Username, Email, Org Slug           │
  │ 2. Create UserModel (hashed password, is_active=True)        │
  │ 3. Create OrganizationModel (status=ACTIVE)                 │
  │ 4. Create OrganizationMemberModel (role=OWNER, status=ACTIVE)│
  │ 5. Assign Default FREE Subscription (PlanModel bootstrap)   │
  │ 6. Provision AccountModel ($100,000.00 Paper Balance)       │
  │ 7. Record Immutable AuditLogModel entry                     │
  │ 8. Commit Session (Rollback all on any exception)           │
  └─────────────────────────────────────────────────────────────┘
                                │
               Success: Return JWT + Tenant Context
```

### 3.2 Cryptographic Invitation Lifecycle
```
  [Org Owner / Admin]
           │
           │ POST /api/v1/organizations/{id}/members/invite
           ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ • Generate raw token: secrets.token_urlsafe(32)             │
  │ • Compute SHA-256 hash of token                             │
  │ • Persist OrganizationInvitationModel(token_hash, 7d expiry)│
  │ • Return raw token in response (NOT stored in plaintext)    │
  └─────────────────────────────────────────────────────────────┘
           │
  [Out-of-band delivery to Invitee]
           │
           │ POST /api/v1/invitations/{token}/accept
           ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ • Hash provided token with SHA-256                          │
  │ • Lookup invitation by token_hash                           │
  │ • Validate: status == PENDING, now < expires_at             │
  │ • If expired: mark EXPIRED, commit, return 410 Gone         │
  │ • Create OrganizationMemberModel(status=ACTIVE, role=inv)   │
  │ • Mark invitation ACCEPTED                                  │
  │ • Record AuditLogModel event                                │
  └─────────────────────────────────────────────────────────────┘
```

---

## 4. Database Schema & Migration 0007

Database migration `0007_organization_invitations` adds the cryptographic invitation model.

### 4.1 Schema Definition
```sql
CREATE TABLE organization_invitations (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL,
    token_hash VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    invited_by_user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE UNIQUE INDEX ix_organization_invitations_token_hash 
    ON organization_invitations (token_hash);
CREATE INDEX ix_organization_invitations_org_status 
    ON organization_invitations (organization_id, status);
```

---

## 5. Governance Invariants

1. **Last-Owner Protection**:
   - The platform prevents demoting, removing, or suspending the sole active `OWNER` of an organization.
   - An organization must retain at least one active `OWNER` at all times.
2. **Self-Escalation Prevention**:
   - Members cannot modify their own role or remove/suspend themselves via administrative endpoints.
3. **Non-Owner Protection**:
   - Only an `OWNER` can assign the `OWNER` role, modify an `OWNER`'s role, or remove an `OWNER`.
   - Attempts by an `ADMINISTRATOR` to modify or remove an `OWNER` return `HTTP 403 Forbidden`.
4. **Tenant Boundary Isolation**:
   - Passing an unauthorized `X-Organization-ID` returns `HTTP 403 Forbidden`.
   - Accessing cross-tenant resources (e.g. Org A user attempting to view Org B members) returns `HTTP 403 Forbidden`.
5. **Personal Sandbox Compatibility**:
   - Requests without organization context (`organization_id is None`) default to personal paper trading.
   - Standard trading operations (`ORDER_CREATE`, `ORDER_READ`, `POSITION_READ`, `TRADE_READ`, `RISK_READ`) succeed.
   - Organization governance and multi-tenant endpoints fail closed with `HTTP 403 Forbidden`.
