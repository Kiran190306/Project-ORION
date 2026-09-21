# PROJECT ORION — EPIC-020 IMPLEMENTATION PLAN
## Product UX / Dashboard 2.0 Architectural Plan

**Author:** Principal Product Architect, Senior Frontend Architect & Production QA Lead  
**Date:** September 20, 2026  
**Status:** DRAFT — PENDING SENIOR AUDIT GATE  
**Repository:** `Project-ORION` (`project-orion/`)  
**Target Git Branch:** `main`

---

## 1. Executive Mission & Platform Scope

The objective of **EPIC-020: Product UX / Dashboard 2.0** is to evolve Project ORION from a functional frontend prototype into an institutional-grade SaaS multi-tenant trading operations dashboard while strictly preserving:
1. **Paper-Trading Invariants:** 100% paper trading only, $0.00 capital at risk, `is_paper=True`, zero live broker connections.
2. **Safety Controls:** `ORION_WORKER_ENABLED=false` enforced, no frontend activation toggles.
3. **Billing Safety:** Stripe Test Mode only (`sk_test_...`), zero cardholder data (PAN/CVV) handled.
4. **Backend Security & DDD:** Existing FastAPI endpoints, domain models, and database migrations remain authoritative; tenant isolation (`organization_id`) and RBAC (7 roles, 25 permissions) strictly respected.
5. **No Code Duplication or Faked Data:** All displayed metrics come directly from verified backend endpoints.

---

## 2. Baseline Audit Summary (Phase 0)

### 2.1 Frontend Architecture (`apps/dashboard/`)
- **Framework:** React 18.3.1 with Vite 5.4.2, TypeScript 5.5.3, React Router 6.26.2, Lucide React icons.
- **Styling:** Custom CSS design system with CSS custom variables in `src/index.css` (Institutional Dark Theme `#090d16`, `#0f172a`, `#111927`).
- **HTTP Client:** Custom `apiClient` in `src/api/client.ts` with JWT bearer injection, correlation ID propagation (`X-Correlation-ID`), and normalized `ApiError` handling.
- **State Management:** React Context (`AuthContext` for auth/session, `ToastContext` for notifications).
- **Existing Pages (10):**
  - `LoginPage.tsx`
  - `DashboardPage.tsx`
  - `OrdersPage.tsx`
  - `PositionsPage.tsx`
  - `TradesPage.tsx`
  - `PortfolioPage.tsx`
  - `StrategiesPage.tsx`
  - `RiskPage.tsx`
  - `WorkerPage.tsx`
  - `BillingPage.tsx` (from EPIC-019)
- **Existing Layout Components (3):** `AppShell.tsx`, `Sidebar.tsx`, `Topbar.tsx`.
- **Existing Common Components (7):** `Badge.tsx`, `Button.tsx`, `Card.tsx`, `Modal.tsx`, `Pagination.tsx`, `Table.tsx`, `Toast.tsx`.
- **Existing Chart Components (2):** `EquityCurveChart.tsx`, `ExposureBarChart.tsx`.
- **Existing Test Coverage:** 12 test suites, 27 Vitest unit tests in `apps/dashboard/tests/`.

### 2.2 Backend Architecture (`apps/trading-engine/`)
- **FastAPI Engine:** Verified routes covering auth, onboarding, accounts, orders, positions, trades, portfolio, strategies, risk, worker, dashboard, organizations, members, invitations, audit logs, and billing.
- **Tenant Context (`dependencies.py`):**
  - Resolves `TenantContext` using `X-Organization-ID` request header or default membership.
  - Automatically verifies active membership and organization status fail-closed (403 Forbidden).
- **RBAC Matrix (`libraries/domain/organization/permissions.py`):**
  - 7 Institutional Roles: `OWNER`, `ADMINISTRATOR`, `PORTFOLIO_MANAGER`, `RISK_OFFICER`, `TRADER`, `AUDITOR`, `VIEWER`.
  - 25 Permissions covering organization, members, accounts, orders, positions, trades, strategies, risk, worker, subscription, and audit.
- **Consolidated Dashboard Endpoint (`/api/v1/dashboard/`):**
  - Returns unified payload: `account`, `performance`, `trading`, `strategy`, `risk`, `worker`, `system`.
- **Audit Logs (`/api/v1/organizations/{id}/audit-logs`):**
  - Returns compliance audit trail with automated secret redaction.

---

## 3. UX Gap Analysis Matrix (Phase 1)

| Area | Current State | Identified Gap | Required Change | Backend API Needed? | Frontend Only? | Risk | Test Strategy |
|---|---|---|---|---|---|---|---|
| **Multi-Tenant Context** | Topbar only shows username and superuser status; no organization switching | User cannot view current organization, switch organizations, or see tenant role | Add `OrganizationContext`, organization selector in Topbar, pass `X-Organization-ID` in `apiClient` | NO (Already exists: `GET /api/v1/organizations`) | YES | Low (Server enforces isolation) | Test organization switching, header propagation |
| **RBAC Integration** | Frontend displays all action buttons regardless of role | Non-privileged users (e.g. VIEWER, AUDITOR) see action buttons that fail with 403 upon click | Add permission-aware UI helpers (`hasPermission`, `<RequirePermission>`); disable/hide unauthorized actions | NO (Roles returned from membership and `/auth/me`) | YES | Low | Test button visibility across roles (VIEWER vs TRADER vs OWNER) |
| **Design System** | Basic components exist; metric cards, breadcrumbs, skeletons, tabs, and confirmation dialogs duplicated across pages | Inconsistent card layouts, missing skeleton loaders, duplicated delete/close confirmation modals | Standardize `MetricCard`, `PageHeader`, `Breadcrumbs`, `Skeleton`, `ConfirmationDialog`, `Tabs`, `Dropdown`, `EmptyState` | NO | YES | Low | Visual test & unit tests for new design components |
| **Executive Dashboard** | Single monolithic page; basic grid | Dense but lacks quick-action paper order button, responsive charts, and status indicators | Elevate `DashboardPage.tsx` with high-density institutional KPI cards, quick paper order modal, and responsive layout | NO (Already supported by `/api/v1/dashboard/`) | YES | Low | Vitest assertions for dashboard blocks and values |
| **Organization Management** | No frontend UI for organization governance | Users cannot manage organization name, view team members, invite members, or update roles | Implement `/organization` page wrapping `organizationApi` | NO (Already exists in `organization.py`) | YES | Low | Vitest test for team list, invite modal, role changes |
| **Compliance & Audit** | No frontend UI for audit logs | Compliance officers and auditors cannot inspect system audit trail in UI | Implement `/audit` page wrapping `list_organization_audit_logs` | NO (Already exists in `organization.py`) | YES | Low | Vitest test for audit log rendering, filtering |
| **Order Management** | Existing orders page works but lacks advanced filters | Filtering only by symbol/status; lacks clear risk constraints feedback | Enhance `OrdersPage.tsx` with refined search, pagination, order detail drawer, and cancel confirmation modal | NO (Already exists in `orders.py`) | YES | Low | Vitest test for order submission, cancellation, validation |
| **Position Management** | Basic table with close button | Close confirmation modal is inline and basic | Enhance `PositionsPage.tsx` with P&L heat-coloring, position details drawer, and paper-only close modal | NO (Already exists in `positions.py`) | YES | Low | Vitest test for position list and closing |
| **Strategy Center** | Basic parameter form | Complex configuration schema is hard to navigate | Standardize `StrategiesPage.tsx` with parameter validator, parameter schema viewer, and active status badge | NO (Already exists in `strategies.py`) | YES | Low | Vitest test for strategy configuration |
| **Risk Center** | Read-only metrics grid | Lacks clear visual warning hierarchy for emergency stop and margin thresholds | Enhance `RiskPage.tsx` with margin level gauge, exposure visualizer, and emergency stop banner | NO (Already exists in `risk.py`) | YES | Low | Vitest test for risk limits and statuses |
| **Worker Center** | Status page exists | Could be clearer regarding disabled autonomous state | Update `WorkerPage.tsx` with prominent `AUTONOMOUS WORKER DISABLED` banner, cycle metrics, and zero live controls | NO (Already exists in `worker.py`) | YES | Low | Vitest test for worker status display |
| **Billing Integration** | Standalone page from EPIC-019 | Integrated, but can be harmonized with design system and topbar organization context | Harmonize `BillingPage.tsx` with standardized design system components | NO (Already exists in `billing.py`) | YES | Low | Vitest regression pass |
| **Responsive & Accessibility** | Basic responsive sidebar | Tables horizontally overflow on mobile (< 768px); missing accessible ARIA live regions | Add responsive table wrappers, mobile bottom-sheet/drawer, ARIA labels, focus traps | NO | YES | Low | Multi-viewport tests (375px, 768px, 1440px) |

---

## 4. Product Information Architecture (Phase 2)

### 4.1 Navigation Hierarchy
```
Dashboard Shell
├── Primary Trading Views
│   ├── [LayoutDashboard] /dashboard      -> Executive Overview (KPIs, Active Positions, Performance, Quick Paper Order)
│   ├── [PieChart]        /portfolio      -> Portfolio & Balances (Equity Curve, Exposure, P&L Breakdown)
│   ├── [ClipboardList]   /orders         -> Order Management (Open, Pending, History, Paper Order Placement)
│   ├── [Layers]          /positions      -> Active Positions (Open Positions, Unrealized P&L, Close Controls)
│   └── [History]         /trades         -> Execution Journal (Fills, Realized P&L, Transaction Audit)
├── Autonomous & Algorithmic Views
│   ├── [Sliders]         /strategies     -> Strategy Center (Catalog, Configurations, Parameter Validation)
│   ├── [ShieldAlert]     /risk           -> Risk Controls (Exposure Limits, Margin Gauges, Circuit Breakers)
│   └── [Cpu]             /worker         -> Autonomous Worker (Telemetry, Disabled Banner, Cycle Metrics)
└── Institutional Governance & SaaS
    ├── [CreditCard]      /billing        -> Billing & Plans (Subscription Tier, Stripe Checkout, Invoices)
    ├── [Users]           /organization   -> Team & Organization (Settings, Member Roles, Invitations)
    └── [FileText]        /audit          -> Compliance Audit Trail (Audit Logs, Actor Tracking, Event Filtering)
```

### 4.2 RBAC Navigation Guarding
- **Navigation item visibility** is dynamically evaluated against the active user's role:
  - `/organization`: Requires `ORGANIZATION_READ` or `MEMBER_READ`.
  - `/audit`: Requires `AUDIT_READ` (visible to `OWNER`, `ADMINISTRATOR`, `PORTFOLIO_MANAGER`, `RISK_OFFICER`, `AUDITOR`; hidden from `TRADER`, `VIEWER`).
  - Action buttons (`Cancel Order`, `Close Position`, `Configure Strategy`, `Invite Member`) conditionally disabled/hidden based on granular permissions (`ORDER_CANCEL`, `POSITION_CLOSE`, `STRATEGY_CONFIGURE`, `MEMBER_INVITE`).
- **Defense in Depth:** Backend FastAPI routes strictly enforce `require_permission(...)` regardless of frontend state.

---

## 5. Design System Standardization (Phase 3)

### 5.1 Reusable Component Library (`apps/dashboard/src/components/common/`)
1. **`MetricCard.tsx`**: Standardized institutional KPI card with label, formatted monetary/percentage value, change indicator (profit/loss), trend icon, and optional tooltip.
2. **`PageHeader.tsx`**: Consistent header with title, subtitle, breadcrumbs, action button group, and live paper-trading badge.
3. **`Breadcrumbs.tsx`**: Accessible navigation trail (`Dashboard > Portfolio`).
4. **`StatusBadge.tsx`**: Standardized statuses (`ACTIVE`, `PENDING`, `FILLED`, `CANCELLED`, `REJECTED`, `HEALTHY`, `WARNING`, `CRITICAL`).
5. **`ConfirmationDialog.tsx`**: Accessible modal for destructive or critical actions (Cancel Order, Close Position, Revoke Invitation) with explicit paper-trading context.
6. **`Skeleton.tsx`**: Shimmering placeholder components for loading states (cards, table rows, text blocks).
7. **`EmptyState.tsx`**: Professional empty state display with icon, title, message, and optional CTA button.
8. **`ErrorState.tsx`**: Resilient error display with correlation ID, clear message, and retry button.
9. **`Tabs.tsx`**: Accessible tabbed container for multi-section views.
10. **`Dropdown.tsx`**: Accessible dropdown menu for organization selector and user profile actions.

---

## 6. Global Application Shell (Phase 4)

### 6.1 Topbar & Organization Selector
- **Tenant Selector:** Dropdown displaying active organization name and slug. Fetches user organizations via `GET /api/v1/organizations`. Selecting an organization persists the selection and attaches `X-Organization-ID` to subsequent API requests.
- **Active Role Badge:** Displays user's role in the active organization (`OWNER`, `TRADER`, etc.) with role-specific color coding.
- **Safety Indicator:** Prominent, persistent `PAPER TRADING ONLY` badge with amber pulse indicator.
- **System Telemetry:** Live UTC clock and backend connection status indicator.
- **User Actions:** User avatar, username, superuser badge, and quick logout.

### 6.2 Responsive Collapsible Sidebar
- Collapsible on desktop for maximum data density.
- Mobile slide-over drawer with backdrop overlay.
- Grouped navigation links: `Trading Operations`, `Algorithmic Engine`, `Governance & SaaS`.

---

## 7. View Implementations (Phase 5 - Phase 15)

### 7.1 Executive Dashboard (`DashboardPage.tsx` - Phase 5)
- **Top Metric Cards:** Account Balance, Total Equity, Available Cash, Used Margin, Free Margin, Realized P&L, Unrealized P&L, Daily P&L.
- **Main Content Grid:**
  - Active Positions summary table with quick link to `/positions`.
  - Recent Trade Fills summary table with quick link to `/trades`.
  - Pending Orders summary table with quick link to `/orders`.
- **Side Panel:**
  - Active Strategy card with parameters and timeframe.
  - Risk Controls card with margin level gauge and exposure.
  - Worker Status card with state and disabled notice.
  - System Health card with engine status and timestamp.
- **Preserved Existing Assertions:** Keeps all existing text and values so `dashboard.test.tsx` passes 100%.

### 7.2 Portfolio View (`PortfolioPage.tsx` - Phase 6)
- Standardized `MetricCard` summary of balance, equity, margin, exposure, drawdown.
- Responsive SVG Equity Curve chart with interactive hover tooltip and timeframe toggle.
- Asset Exposure bar chart and P&L breakdown by currency pair.

### 7.3 Orders Management (`OrdersPage.tsx` - Phase 7)
- Paginated orders table with symbol, side (BUY/SELL), type, quantity, status badge, created date.
- Paper Trading Order placement modal:
  - Strictly paper order execution.
  - Client-side validation: positive quantity, valid symbol.
  - Stop loss and take profit optional inputs.
- Cancel Order confirmation modal with permission check (`ORDER_CANCEL`).

### 7.4 Positions Management (`PositionsPage.tsx` - Phase 8)
- Open positions table with symbol, side, quantity, open price, current price, unrealized P&L (colored green/red), and exposure.
- Close Position confirmation modal with explicit `PAPER TRADING` warning and permission check (`POSITION_CLOSE`).

### 7.5 Trade History (`TradesPage.tsx` - Phase 9)
- Historical fills journal with fill ID, order ID, symbol, side, filled price, quantity, realized P&L, and timestamp.
- Filtering by symbol and date range with pagination.

### 7.6 Strategy Center (`StrategiesPage.tsx` - Phase 10)
- Strategy catalog card view (`trend_following`, `mean_reversion`, `breakout`).
- Current account strategy configuration viewer and editor (`STRATEGY_CONFIGURE`).
- Parameter schema display with validation constraints.

### 7.7 Risk Center (`RiskPage.tsx` - Phase 11)
- Risk telemetry cards: Max Leverage, Total Exposure, Margin Level, Emergency Stop state.
- Daily loss limits and max drawdown gauges.
- Circuit breaker status with clear severity indicators (`HEALTHY`, `WARNING`, `CRITICAL`).

### 7.8 Worker Center (`WorkerPage.tsx` - Phase 12)
- Prominent persistent notice: `AUTONOMOUS WORKER DISABLED (ORION_WORKER_ENABLED=false)`.
- Telemetry cards: State, Uptime, Last Cycle timestamp, Cycle Count, Error status.
- Zero live controls or activation buttons.

### 7.9 Billing Experience (`BillingPage.tsx` - Phase 13)
- Retains existing EPIC-019 verified functionality: current tier card, upgrade options (Starter, Pro, Enterprise), Stripe Checkout redirection, cancellation modal, and invoice table.
- Harmonized with new design system `PageHeader`, `MetricCard`, and `Badge`.

### 7.10 Organization & Team Governance (`OrganizationPage.tsx` - Phase 14) [NEW]
- Route: `/organization`
- Organization details card: Name, Slug, Status, Created date, Update form (`ORGANIZATION_UPDATE`).
- Team Members table: User, Role badge, Status badge, Joined date.
- Role management dropdown (`MEMBER_UPDATE`).
- Remove member action (`MEMBER_REMOVE`).
- Single-use cryptographically secure invitation modal (`MEMBER_INVITE`).
- Pending invitations table with revocation action.
- Role capability matrix reference card explaining institutional permissions.

### 7.11 Compliance Audit Trail (`AuditPage.tsx` - Phase 15) [NEW]
- Route: `/audit`
- Compliance audit table: Timestamp, Actor, Action/Event Type, Component, Details (with automated secret redaction), Result.
- Event type filter and pagination.
- Only visible to users with `AUDIT_READ` permission.

---

## 8. API Integration Layer (Phase 19)

### 8.1 API Endpoints Mapping
All required endpoints are **already implemented** in the FastAPI backend! No additive backend endpoints are required.

```typescript
// Organization API Client (to be added to apps/dashboard/src/api/endpoints.ts)
export const organizationApi = {
  listUserOrganizations: (): Promise<OrganizationResponse[]> =>
    apiClient<OrganizationResponse[]>('/api/v1/organizations', { method: 'GET' }),

  getById: (orgId: string): Promise<OrganizationResponse> =>
    apiClient<OrganizationResponse>(`/api/v1/organizations/${encodeURIComponent(orgId)}`, { method: 'GET' }),

  update: (orgId: string, req: UpdateOrganizationRequest): Promise<OrganizationResponse> =>
    apiClient<OrganizationResponse>(`/api/v1/organizations/${encodeURIComponent(orgId)}`, {
      method: 'PATCH',
      body: JSON.stringify(req),
    }),

  listMembers: (orgId: string): Promise<OrganizationMemberResponse[]> =>
    apiClient<OrganizationMemberResponse[]>(`/api/v1/organizations/${encodeURIComponent(orgId)}/members`, { method: 'GET' }),

  updateMemberRole: (orgId: string, userId: string, role: string): Promise<OrganizationMemberResponse> =>
    apiClient<OrganizationMemberResponse>(
      `/api/v1/organizations/${encodeURIComponent(orgId)}/members/${encodeURIComponent(userId)}/role`,
      {
        method: 'PATCH',
        body: JSON.stringify({ role }),
      }
    ),

  removeMember: (orgId: string, userId: string): Promise<void> =>
    apiClient<void>(
      `/api/v1/organizations/${encodeURIComponent(orgId)}/members/${encodeURIComponent(userId)}`,
      { method: 'DELETE' }
    ),

  inviteMember: (orgId: string, req: CreateInvitationRequest): Promise<InvitationResponse> =>
    apiClient<InvitationResponse>(
      `/api/v1/organizations/${encodeURIComponent(orgId)}/members/invite`,
      {
        method: 'POST',
        body: JSON.stringify(req),
      }
    ),

  listAuditLogs: (orgId: string, params?: { limit?: number; offset?: number; event_type?: string }): Promise<AuditLogResponse[]> =>
    apiClient<AuditLogResponse[]>(
      `/api/v1/organizations/${encodeURIComponent(orgId)}/audit-logs`,
      {
        method: 'GET',
        params: params as Record<string, string | number | boolean | undefined>,
      }
    ),
};
```

### 8.2 Client Header Injection
- In `api/client.ts`, add helper functions:
  ```typescript
  export function getStoredOrgId(): string | null { ... }
  export function setStoredOrgId(orgId: string | null): void { ... }
  ```
- In `apiClient`, inject header if `orgId` is set:
  ```typescript
  const orgId = getStoredOrgId();
  if (orgId && !headers.has('X-Organization-ID')) {
    headers.set('X-Organization-ID', orgId);
  }
  ```

---

## 9. Security & Multi-Tenancy Architecture (Phase 21)

1. **Strict Organization Scoping:** `X-Organization-ID` is verified server-side on every request by `get_tenant_context`. Users cannot forge access to organizations they do not belong to.
2. **Server-Authoritative RBAC:** UI hides/disables controls based on client-side permissions, but backend `require_permission(...)` rejects any unauthorized requests with 403 Forbidden.
3. **Secret Redaction:** Frontend never receives or handles secrets, tokens, or live API credentials. Audit log details are pre-redacted by backend.
4. **Paper-Trading Invariant:** `is_paper=True` is verified on all account and order payloads. No live broker connectivity exists.

---

## 10. Testing Strategy & Quality Gates (Phase 22 - Phase 25)

### 10.1 Frontend Test Suite (`npm test` via Vitest)
- Preserve all existing 27 tests across the 11 test suites.
- Add test suites for:
  1. `organization.test.tsx`: Organization switching, team member listing, invite dialog, role update.
  2. `audit.test.tsx`: Audit log list, filtering, secret redaction display.
  3. `rbac.test.tsx`: Permission evaluation, button hiding/disabling for unauthorized roles.
  4. `design_system.test.tsx`: MetricCard, PageHeader, ConfirmationDialog, Skeleton.
- Target: 35+ frontend tests passing, 0 failures.

### 10.2 Quality Gates
- **TypeScript Compilation:** `tsc -b` completes with 0 errors.
- **Frontend Build:** `vite build` produces clean distribution in `dist/`.
- **Python Unit Regression:** `python -m pytest tests/unit/ -v` passes 429/429 tests.
- **Python Linter:** `python -m ruff check ...` passes with 0 errors.
- **Cloud Production Probing:** Render API `/health/live` (200), `/health/ready` (200), `/metrics` (200), and Dashboard (200) verified non-destructively.

---

## 11. Release Classification & Git Safety

- **Release Classification Target:** **B — PRODUCT UX READY WITH EXTERNAL VERIFICATION PENDING** (Internal verification 100% complete; external live cloud testing pending deployment synchronization).
- **Single Atomic Git Commit:**
  `feat(ux): implement EPIC-020 dashboard 2.0`
- **Push to:** `origin/main`
