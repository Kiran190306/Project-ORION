# Project ORION — EPIC-027 Release Gates & Go/No-Go Criteria
# Public Beta & Commercial Launch Readiness

**Document Version:** 1.0.0
**Date:** 2026-09-22
**Milestone:** EPIC-027 (Public Beta Gate Definition)
**Author:** Quantitative Architecture, Security, & Release Committee
**Repository:** `Project-ORION` (Branch: `main`)

---

## 1. Release Governance Framework

The Project ORION Public Beta release gate provides a binary, mathematically verifiable decision framework governing when the platform may transition from a private engineering system to an open, public-facing beta SaaS.

```
       +-------------------------------------------------------------+
       |             EPIC-027 GO / NO-GO DECISION GATE               |
       +-------------------------------------------------------------+
                                      |
              +-----------------------+-----------------------+
              |                                               |
     [ ANY BLOCKER PRESENT? ]                       [ ALL GATES PASS? ]
              |                                               |
             YES                                             YES
              |                                               |
              v                                               v
     +-----------------+                             +-----------------+
     | NO-GO: REJECTED |                             |  GO: APPROVED   |
     | (D - NOT READY) |                             | (A - BETA READY)|
     +-----------------+                             +-----------------+
```

---

## 2. Zero-Tolerance Release Blockers (Immediate NO-GO)

If ANY of the following 10 conditions exist, the release is immediately rejected with verdict **`NO-GO (D — NOT READY)`**:

| # | Blocker Code | Description | Verification Method |
|---|---|---|---|
| **B-01** | `LIVE_TRADING_PATH` | Any execution pathway exists that routes orders to real-money market accounts or live broker connections. | Static code scan; `SecurityViolationError` assertions. |
| **B-02** | `CAPITAL_AT_RISK` | Real capital at risk exceeds $0.00 under any circumstance. | Financial invariants check; account balance assertions. |
| **B-03** | `TENANT_ISOLATION_LEAK` | Cross-tenant access (IDOR) succeeds or leaks data across organizations. | Automated multi-tenant penetration tests (HTTP 404 requirement). |
| **B-04** | `AUTH_BYPASS` | Any unauthenticated request accesses private trading, financial, or organizational state. | Security integration tests (HTTP 401 requirement). |
| **B-05** | `RBAC_BYPASS` | Any role executes an action outside its canonical 41-permission matrix. | RBAC matrix unit & integration test suite. |
| **B-06** | `CREDENTIAL_EXPOSURE` | Plaintext passwords, API keys, or broker tokens appear in logs, API responses, or repository git history. | Log inspection, API response assertions, git history scan. |
| **B-07** | `FINANCIAL_CORRUPTION` | Unilateral local database mutation occurs during broker state reconciliation without audit approval. | Reconciliation engine tolerance & zero-silent-mutation tests. |
| **B-08** | `DUPLICATE_ORDER_FILL` | Network timeout or retry logic produces duplicate order fills at the execution venue. | Idempotency tests; `UNKNOWN` timeout state handling. |
| **B-09** | `BROKEN_ONBOARDING` | New visitor cannot complete self-registration, terms acceptance, or first paper trade. | E2E onboarding automation test. |
| **B-10** | `MISSING_LEGAL_SURFACE` | Platform lacks Terms of Service, Privacy Policy, or explicit Paper Trading Risk Disclosure. | Public route accessibility and legal text presence. |

---

## 3. Mandatory Quality Gates (All Must PASS)

Each of the 18 quality gates must achieve a verified **`PASS`** before Public Beta approval:

### Gate 1: Identity & Authentication Hardening
- [ ] User self-service registration operates with email, username, password validation.
- [ ] Password reset via cryptographic, time-limited token (15-min TTL).
- [ ] In-process rate limiting strictly enforced on `/api/v1/auth/login` (<= 5 req/min per IP).
- [ ] Default JWT secret fallback fails closed with `ConfigurationError` when `ORION_ENVIRONMENT=production`.

### Gate 2: Self-Service Onboarding & First Trade Flow
- [ ] New user signup automatically provisions tenant organization, free subscription, and paper account with $100,000 balance.
- [ ] Mandatory checkbox requires explicit acceptance of Terms of Service, Privacy Policy, and Paper Trading Risk Disclosure.
- [ ] Interactive onboarding modal guides user through balance selection and initial strategy archetype.
- [ ] First simulated paper market order executes cleanly with instant fill and balance deduction.

### Gate 3: Tenant Isolation & IDOR Immunity
- [ ] Cross-tenant requests to `/api/v1/accounts`, `/orders`, `/positions`, `/research`, `/optimization`, `/deployments`, `/broker-sandbox`, and `/billing` strictly return HTTP 404 Not Found.
- [ ] `X-Organization-ID` header tampering cannot access foreign tenant records.

### Gate 4: Canonical RBAC Enforcement
- [ ] All 41 permissions correctly verified across all 7 canonical roles.
- [ ] Least privilege and separation-of-duties strictly maintained (e.g. Administrator cannot execute trades; Trader cannot invite members).

### Gate 5: Subscription Entitlements & Quota Limits
- [ ] FREE tier enforces 1 paper account, 50 daily orders, 0 workers, 5 monthly optimizations.
- [ ] Quota exceedance returns HTTP 403 Forbidden or HTTP 429 with descriptive error message.
- [ ] No client-side-only quota enforcement; 100% server-side verified in `EntitlementService`.

### Gate 6: Paper Trading Core Ledger
- [ ] Order book handles Market, Limit, and Stop orders.
- [ ] Real-time mark-to-market position valuation and margin tracking.
- [ ] Position netting correctly closes positions and records realized P&L.
- [ ] Paper account reset restores starting balance and purges paper positions cleanly.

### Gate 7: Risk Management & Circuit Breakers
- [ ] `RiskEngine` enforces max drawdown, max daily loss, max position size, and leverage limits.
- [ ] Zero orders can bypass `RiskEngine` or `OrderValidator`.
- [ ] Read-only risk telemetry exposed to frontend; risk threshold modifications require authorized officer role.

### Gate 8: Dashboard 2.0 UX & Accessibility
- [ ] All 15 internal dashboard views feature verified loading skeletons, empty state illustrations, and error state retry triggers.
- [ ] Amber Paper Trading badge (`SIMULATED PAPER EXECUTION — $0.00 REAL CAPITAL`) is permanently visible across topbar, sidebar, and modals.
- [ ] Dark theme accessible with high-contrast `:focus-visible` styling and ARIA attributes.
- [ ] Responsive layout adapts cleanly from mobile (single column) to desktop (multi-column).

### Gate 9: Strategy Lab & Deterministic Backtesting
- [ ] Backtest simulations produce identical results given identical seeds and historical data.
- [ ] Look-ahead leakage guards prevent future-bar peek.
- [ ] Equity curves, trade ledgers, drawdown series, and Monte Carlo confidence intervals render accurately.

### Gate 10: Optimization Studio & Walk-Forward AI
- [ ] Parameter sweeps execute within memory bounds.
- [ ] Multi-window Walk-Forward Analysis (WFA) evaluates Out-Of-Sample (OOS) robustness.
- [ ] Overfitting guards and parameter stability plateaus calculate accurately.
- [ ] Candidate leaderboard allows one-click promotion into deployment pipeline.

### Gate 11: Deployment Pipeline & Paper Incubator
- [ ] Candidates evaluated across 5 quality gates (WFE >= 50%, Regime Robustness, Stability, Trade Count, Sharpe).
- [ ] State machine enforces fail-closed transitions terminating strictly at `PAPER_VALIDATED` or `PROMOTION_CANDIDATE`.
- [ ] Incubation policy monitors active paper performance against historical backtest benchmarks.

### Gate 12: Broker Sandbox & SSRF Protection
- [ ] `MockBrokerAdapter` simulates partial fills, rejections, rate limits, latency, and timeouts.
- [ ] `BrokerEndpointValidator` blocks loopback, private RFC 1918 subnets, cloud metadata (`169.254.169.254`), and all production broker URLs.
- [ ] Credential secrets authenticated and encrypted at rest with AES-256-GCM.
- [ ] State reconciliation engine follows strict `ALERT + AUDIT + MANUAL REVIEW` policy with zero silent local mutations.

### Gate 13: Commercial Billing (Stripe Test Mode)
- [ ] Plan pricing, checkout session creation, customer portal, and invoice history operational in Stripe Test Mode.
- [ ] Webhook signature verification rejects forged payloads.
- [ ] Idempotent webhook processing prevents duplicate billing events.

### Gate 14: Legal, Trust & Risk Disclosure Pages
- [ ] Terms of Service (`/terms`) published and accessible.
- [ ] Privacy Policy (`/privacy`) published and accessible.
- [ ] Paper Trading Risk Disclosure (`/risk-disclosure`) published, declaring $0.00 real capital, simulated execution, and no investment advisory status.
- [ ] Refund & Cancellation Policy published.

### Gate 15: Public Marketing Website
- [ ] Public landing page at `/` presents factual product capabilities, institutional architecture, and plan pricing.
- [ ] Factual messaging only: no claims of guaranteed profits, risk-free returns, or AI market prediction.
- [ ] Primary CTA `"Start Free Paper Trading"` navigates directly to `/signup`.

### Gate 16: Public API Abuse Defense & Rate Limiting
- [ ] Inbound HTTP rate limiting middleware active on all public and authenticated endpoints.
- [ ] Maximum request body size enforced (10 MB).
- [ ] Exceeding limits returns HTTP 429 Too Many Requests with `Retry-After` header.

### Gate 17: Observability & Health Readiness
- [ ] `/health/live` returns HTTP 200 OK.
- [ ] `/health/ready` validates PostgreSQL, Redis, Market Data feed, and Worker state.
- [ ] `/metrics` exposes Prometheus counters, gauges, and histograms.
- [ ] Structured JSON logging preserves correlation IDs and automatically redacts credentials.

### Gate 18: Backup & Disaster Recovery
- [ ] PostgreSQL managed database includes automated daily snapshots.
- [ ] Documented restore runbook tested with RTO < 60 min and RPO < 24 hrs.
- [ ] Alembic migration chain contiguous across all revisions with verified upgrade/downgrade cycles.

---

## 4. Verification Execution Checklist

```markdown
[ ] Step 1: Execute Full Backend Regression Suite
    Command: poetry run pytest tests/ -v
    Requirement: 100% PASS, 0 FAIL, 0 ERROR.

[ ] Step 2: Execute Frontend Vitest Suite
    Command: npm test (in apps/dashboard)
    Requirement: 100% PASS across all test files.

[ ] Step 3: Execute Production Frontend Build
    Command: npm run build (in apps/dashboard)
    Requirement: 0 TypeScript compilation errors.

[ ] Step 4: Execute Dedicated Security & SSRF Suite
    Command: poetry run pytest tests/security/ -v
    Requirement: 16/16 PASS.

[ ] Step 5: Execute Inbound Rate Limiting Verification
    Command: poetry run pytest tests/security/test_rate_limiting.py -v
    Requirement: 429 Too Many Requests on burst traffic.

[ ] Step 6: Verify Public Legal & Marketing Routes
    Requirement: / (Landing), /pricing, /terms, /privacy, /risk-disclosure load cleanly without auth.

[ ] Step 7: Verify E2E Onboarding Flow
    Requirement: Register -> Accept Terms -> Select Balance -> Execute First Paper Order.

[ ] Step 8: Verify Zero-Capital Safety Invariant
    Requirement: Capital at Risk = $0.00, Live Connections = 0, Worker = disabled.
```

---

## 5. Decision Authority & Sign-Off Matrix

| Role | Sign-Off Responsibilities | Gate Focus | Required Verdict |
|---|---|---|:---:|
| **Principal Architect** | System integrity, DDD boundaries, paper/live separation | Gates 6, 9, 10, 11 | **APPROVED** |
| **Security Engineer** | SSRF defense, AES-256-GCM cipher, rate limiting, IDOR | Gates 1, 3, 4, 12, 16 | **APPROVED** |
| **Compliance Officer** | Legal terms, privacy policy, risk disclosure, audit logs | Gates 2, 14, 15 | **APPROVED** |
| **QA / Reliability Lead** | Automated test regression, health checks, backup RTO/RPO | Gates 5, 8, 17, 18 | **APPROVED** |

**Final Public Beta Release Condition:**
All four signatures must be **APPROVED**. If any role dissents or flags an active blocker, release classification remains **`D — NOT READY`** until remediated.
