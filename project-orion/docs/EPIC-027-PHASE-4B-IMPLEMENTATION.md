# EPIC-027 Phase 4B: Self-Service Registration & Onboarding Funnel — Technical Implementation

**Document Version:** 1.0
**Phase:** EPIC-027 Phase 4B
**Baseline Commit:** `0ded05f feat(legal): implement EPIC-027 phase 3 legal trust and risk disclosure`
**Classification:** `B — COMPLETE WITH EXTERNAL DEPENDENCY` (External legal counsel review and DNS/domain setup remain pending)
**Date:** 2026-09-22

---

## 1. Executive Summary

Phase 4B of EPIC-027 implements the complete self-service registration and institutional onboarding entry funnel for Project ORION. It bridges the gap between public visitors and authenticated institutional trading terminals by providing an automated, atomic, and legally compliant account creation workflow.

### User Flow
```
Public Visitor
    ↓
Login Page (/login)  ←────────────────┐
    ↓                                  │
Register Page (/register)              │
    ↓                                  │
Input Validation & Live Policy Checks  │
    ↓                                  │
Mandatory Legal Consents               │
  • Terms of Service (/terms)          │
  • Privacy Policy (/privacy)          │
  • Paper Risk Disclosure (/risk-disclosure)
    ↓                                  │
Backend Atomic Provisioning            │
  POST /api/v1/onboarding/register     │
  (5 req/hr IP Rate Limited)           │
    ↓                                  │
Email Verification Notice View         │
  • Account: ORION-PAP-XXXXXX          │
  • Initial Balance: $100,000 USD      │
  • Capital at Risk: $0.00 (Strict)    │
  • Verification Email Dispatched      │
    ↓                                  │
Sign In Link ──────────────────────────┘
    ↓
Authenticated Trading Terminal (/dashboard)
```

---

## 2. Implemented Components

### 2.1 API Contract & Data Transfer Objects
- **`apps/dashboard/src/api/types.ts`**:
  - `OnboardingRegisterRequest`: Strongly typed registration payload matching backend schema:
    - `username` (3–50 chars)
    - `email` (5–255 chars)
    - `password` (8–128 chars, max 72 bytes)
    - `organization_name` (2–100 chars)
    - `organization_slug` (optional)
    - `full_name` (optional)
    - `terms_accepted` (boolean, mandatory)
    - `privacy_acknowledged` (boolean, mandatory)
    - `risk_disclosure_acknowledged` (boolean, mandatory)
  - `OnboardingResponse`: Returns provisioned `user_id`, `organization_id`, `organization_name`, `subscription_tier`, `account_id`, `account_number`, `initial_balance`, and `access_token`.

- **`apps/dashboard/src/api/endpoints.ts`**:
  - `onboardingApi.register(data)`: Dispatches `POST /api/v1/onboarding/register` via centralized institutional `apiClient`.

### 2.2 Frontend Registration Component (`apps/dashboard/src/pages/RegisterPage.tsx`)
- Full self-service registration interface with dark slate styling (`bg-slate-950`, border `border-slate-800`).
- Persistent **Paper Trading Badge** and `$0.00 Capital at Risk` visual indicators.
- Real-time password policy guidance:
  - 8 to 72 bytes length requirement (Bcrypt safe boundary)
  - At least one letter (`a-z`, `A-Z`)
  - At least one number or special character
  - Live password confirmation match status
- 3 distinct, non-bundled mandatory legal checkboxes:
  1. **Terms of Service**: Explicit agreement to platform terms (links to `/terms` with `target="_blank" rel="noopener noreferrer"`).
  2. **Privacy Policy**: Acknowledgment of telemetry and storage policies (links to `/privacy` with `target="_blank" rel="noopener noreferrer"`).
  3. **Paper Trading Risk Disclosure**: Mandatory acknowledgment of simulated matching and $0.00 capital risk (links to `/risk-disclosure` with `target="_blank" rel="noopener noreferrer"`).
- Atomic post-registration state:
  - Immediately wipes raw passwords from memory.
  - Switches to a dedicated provisioning summary view showing account number, $100,000 USD paper allocation, organization name, and subscription tier.
  - Displays email verification guidance and routes user cleanly toward `/login` or `/verify-email`.
- Integrated `PublicFooter` featuring all legal and security links.

### 2.3 Login Page Integration (`apps/dashboard/src/pages/LoginPage.tsx`)
- Added clear bidirectional navigation link:
  `Don't have an account? Sign up for paper trading` routing directly to `/register`.

### 2.4 Application Routing (`apps/dashboard/src/App.tsx`)
- Registered public route `<Route path="/register" element={<RegisterPage />} />` alongside existing public legal and authentication routes.

---

## 3. Security, Rate Limiting & Safety Invariants

| Category | Control / Invariant | Status | Verification |
|---|---|---|---|
| **Capital Risk** | Paper-only execution; strictly $0.00 capital at risk | **ENFORCED** | Verified across UI notices, legal disclosures, and backend engine |
| **Worker State** | Autonomous background trading worker disabled (`ORION_WORKER_ENABLED=false`) | **ENFORCED** | Verified inactive |
| **Stripe Billing** | Stripe in Test Mode only; simulated transactions only | **ENFORCED** | Verified test mode |
| **Password Hygiene** | No storage of raw passwords in `localStorage`, `sessionStorage`, or logs; 72-byte Bcrypt boundary | **ENFORCED** | Verified client state wiped on submission |
| **Rate Limiting** | Endpoint bound to `RateLimitPolicies.ONBOARDING_REGISTER` (5 req/hour/IP) | **ENFORCED** | Verified with HTTP 429 UI feedback test |
| **Tenant Isolation** | Atomic database transaction generating discrete user, tenant organization, owner role, and paper account | **ENFORCED** | Verified via backend onboarding integration tests |
| **Legal Assent** | Explicit non-preselected checkboxes; server-side and client-side validation | **ENFORCED** | Verified 422 rejected when unchecked |

---

## 4. Verification & Testing

### 4.1 Frontend Test Suite
- Comprehensive test suite: `apps/dashboard/tests/registration.test.tsx` (13 tests):
  - Form rendering, labels, badges, and structure
  - External disclosure links (`target="_blank"`, `rel="noopener noreferrer"`)
  - Username, email, and organization length validations
  - Live password strength checklist & confirmation match
  - Mandatory legal consent enforcement (blocking submission if unchecked)
  - Successful registration API dispatch & provisioning notice transition
  - Error handling: HTTP 409 Conflict (duplicate username/email/slug)
  - Error handling: HTTP 429 Rate Limit Exceeded
  - LoginPage link integration & AppRoutes routing
- **Results:**
  - Total frontend test files: **21 passed (21)**
  - Total frontend tests: **80 passed (80)**
  - Vite production build: `tsc && vite build` passed with **0 errors**.

### 4.2 Backend Python Regression Suite
- Tested modules:
  - `tests/unit/apps/trading_engine/test_auth_lifecycle.py`
  - `tests/integration/apps/trading_engine/test_onboarding_legal.py`
  - `tests/unit/domain/legal/test_legal_registry.py`
  - `tests/integration/apps/trading_engine/test_legal_routes.py`
- **Results:**
  - Total tests: **34 passed (34)** in 39.27s.

---

## 5. Status & Next Steps

Phase 4B is fully implemented and passes all automated quality gates.
Classification remains `B — COMPLETE WITH EXTERNAL DEPENDENCY`.

```
EPIC-027 PHASE 4B — IMPLEMENTATION COMPLETE — AWAITING VERIFICATION
```
