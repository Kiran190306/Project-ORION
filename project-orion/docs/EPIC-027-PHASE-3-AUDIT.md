# EPIC-027 Phase 3 — Legal, Trust & Risk Disclosure Audit

**Document Version:** 1.0.0
**Date:** 2026-09-22
**Milestone:** EPIC-027 (Public Beta & Commercial Launch Readiness)
**Phase:** Phase 3 — Legal, Trust & Risk Disclosure Foundation
**Author:** Quantitative Architecture, Security, & Legal Compliance Audit Team
**Repository:** `Project-ORION` (Branch: `main`, Baseline Commit: `405ce08`)
**Product Target:** Multi-tenant quantitative paper-trading, algorithmic research, and strategy SaaS

---

## Executive Summary

This audit establishes the definitive baseline of Project ORION's legal, trust, privacy, risk disclosure, and commercial billing posture prior to implementing Phase 3.

Project ORION is a multi-tenant quantitative trading platform designed for strategy research, walk-forward optimization, and deterministic paper execution. The platform is strictly constrained to **Paper Trading ($0.00 capital at risk)** with execution against an internal simulated matching engine and a read-only OANDA practice environment (`api-fxpractice.oanda.com`). Live broker connectivity and live execution workers are disabled.

Prior to Phase 3, **zero legal documents, privacy notices, risk disclosures, or consent persistence mechanisms existed in the codebase**. While existing engineering controls for security (JWT secret fail-closed, rate limiting, RBAC, tenant isolation, AES-256-GCM broker key encryption) are robust, there is an absence of contractual terms, data collection disclosures, and financial disclaimers necessary for external beta users.

This document inventories all product claims, third-party processors, browser storage usage, database storage, billing behaviors, and consent architecture requirements to establish an auditable, legally sound foundation.

---

## Section A: Current Product Positioning & Public Claims

### 1. Product Name & Branding
- **Canonical Name:** `Project ORION` (version `0.1.0` in package/app metadata; architectural version `1.0.0 FROZEN`).
- **Dashboard Branding:** `PROJECT ORION` with tagline `INSTITUTIONAL FOREX TRADING PLATFORM` (`apps/dashboard/src/pages/LoginPage.tsx:58`).
- **Browser Title:** `Project ORION – Institutional Trading Platform (Paper Mode)` (`apps/dashboard/index.html:7`).
- **App Shell Footer:** `Project ORION v0.1.0 • Institutional Forex Trading Architecture • Paper Simulation Mode Active` (`apps/dashboard/src/components/layout/AppShell.tsx:21`).

### 2. Terminology & Claims Analysis
An automated codebase scan of all Python, TypeScript, HTML, and JSON files was conducted to detect financial, investment, performance, and legal terminology.

| Term / Category | Codebase Hits | Context & Location | Classification | Risk & Recommendation |
| :--- | :---: | :--- | :---: | :--- |
| **"Institutional"** | 70 | Headers, badges, role labels, billing tier name (`Enterprise Institutional`), client logger. | **MARKETING / POSITIONING** | **RISK:** External beta users could misinterpret "Institutional Platform" as meaning ORION is an authorized financial institution or regulated execution venue. <br>**RECOMMENDATION:** Retain institutional aesthetic but pair everywhere with explicit subtitle: *"Quantitative Paper Trading Software — Not a Registered Broker or Financial Advisor"*. |
| **"Guaranteed"** | 4 | 1. `DeploymentPipelinePage.tsx:600`: *"A Quality Gate PASS indicates historical compliance... It MUST NEVER be interpreted as guaranteed profitability."*<br>2. `OptimizationStudioPage.tsx:761`: IS/OOS boundary guarantees data non-contamination.<br>3. `RiskPage.tsx:90`: JSX comment `{/* Institutional Read-Only Guarantee */}`.<br>4. `market_data.py:160`: Simulated ticks guarantee deterministic paper trading. | **FACTUAL / TECHNICAL** | **NO RISK:** All occurrences are explicit technical invariants or explicit profit disclaimers. |
| **"AI Predicts" / "Predict"** | 0 | None found across entire codebase. | **FACTUAL** | **NO RISK:** No deceptive algorithmic predictive claims are made. |
| **"Risk-Free"** | 0 | None found. | **FACTUAL** | **NO RISK:** No claims of risk-free investing. |
| **"Beats Market" / "High Returns"** | 0 | None found. | **FACTUAL** | **NO RISK:** Zero promotional marketing copy promising alpha. |
| **"Profit" / "Profitable"** | 48 | Backtest & optimization metrics: `profit_factor`, `net_profit`, `realized_pnl`, `unrealized_pnl`. | **FACTUAL / QUANTITATIVE** | **NO RISK:** Standard mathematical backtest ratios. Must be accompanied by standard simulated performance disclaimer. |
| **"Investment Advice" / "Fiduciary"** | 0 | None found. | **FACTUAL** | **NO RISK:** Platform never claims to provide advisory services. |
| **"Certifications" (SOC 2, ISO, PCI)** | 0 | Zero claims in code or docs. | **FACTUAL** | **NO RISK:** Platform does not claim unverified certifications. |
| **"Regulatory" (SEC, FCA, FINRA, etc.)** | 0 | Zero regulatory registration claims. | **FACTUAL** | **NO RISK:** Platform does not claim regulatory oversight. |

---

## Section B: Existing Legal Content Inventory

A global search of all terms (`Terms`, `Privacy`, `Cookie`, `Refund`, `Cancellation`, `Risk Disclosure`, `Disclaimer`, `Consent`, `Agreement`) revealed:

1. **Terms of Service:** DOES NOT EXIST. No file, route, or endpoint exists.
2. **Privacy Policy:** DOES NOT EXIST. No file, route, or endpoint exists.
3. **Paper Trading Risk Disclosure:** DOES NOT EXIST as a standalone document. Only an inline text alert on the deployment pipeline page exists (`DeploymentPipelinePage.tsx:600`).
4. **Refund & Cancellation Policy:** DOES NOT EXIST. No document or route exists.
5. **Security & Trust Center:** DOES NOT EXIST.
6. **Cookie Policy:** DOES NOT EXIST.
7. **Legal Document Versioning / Acceptance Tracking:** DOES NOT EXIST in the database schema or API.

---

## Section C: Authentication & Account Lifecycle Integration Points

| Lifecycle Stage | Current Implementation | Legal Integration Opportunity | UX & Architectural Approach |
| :--- | :--- | :--- | :--- |
| **Registration / Onboarding** | `POST /api/v1/onboarding/register` atomically creates user, organization, free subscription, and paper account. | **PRIMARY ACCEPTANCE GATE** | Add mandatory consent checkboxes/payload for Terms of Service, Privacy Policy, and Paper Risk Disclosure. Fails with HTTP 422 if unaccepted. |
| **Organization Invitations** | `POST /api/v1/organizations/invitations/{token}/accept` allows invited members to join an organization. | **SECONDARY ACCEPTANCE GATE** | If an invited user is completing account registration, enforce consent acceptance prior to joining. |
| **Login** | `POST /api/v1/auth/login` issues JWT access token. | **NON-BLOCKING AUDIT** | Do not block routine logins. If a major legal version revision occurs, present an in-app modal or banner prompting re-acknowledgement. |
| **Password Reset** | `POST /forgot-password`, `POST /reset-password` | N/A | No legal consent required. Must remain accessible for account recovery. |
| **Email Verification** | `GET /verify-email`, `POST /resend-verification` | N/A | Verification confirms email ownership; legal consent already captured at registration. |
| **Account Deactivation** | Phase 1 `DEACTIVATED` user status fails closed. | N/A | Preserves historical acceptance records for audit. |

---

## Section D: Commercial Billing & Stripe Posture

### 1. Current Billing Engine State
- **Stripe Mode:** Strictly **TEST MODE**.
- **Guardrails:** `BillingConfig` explicitly raises `LiveCredentialsForbiddenError` if `sk_live_` or `pk_live_` keys are detected (`libraries/infrastructure/billing/config.py:30-39`).
- **Mock Fallback:** When keys are absent or `ORION_BILLING_USE_MOCK=true`, the system operates using `MockStripeAdapter` with deterministic in-memory session and invoice generation.
- **Published Tiers:**
  - **Free Sandbox:** `$0/month` — 1 account, 100 orders/day, 0 workers, 1 liquid FX pair (EUR/USD), 30-day retention.
  - **Pro Strategy Engine:** `$49/month` — 3 accounts, 2,500 orders/day, 1 worker, 12 FX pairs, 365-day retention.
  - **Business Prop Desk:** `$299/month` — 10 accounts, 50,000 orders/day, 5 workers, all FX pairs, 1,825-day retention.
  - **Enterprise Institutional:** `Custom` — Unlimited accounts, unlimited workers, 2,555-day retention.

### 2. Legal Disclosures Required for Billing
- **Test Mode Notice:** Public beta users must be clearly informed that checkouts use Stripe Test Mode and no real currency is charged during beta.
- **Auto-Renewal & Cancellation:** Subscriptions renew automatically monthly until cancelled. Cancellation takes effect at period end.
- **Entitlement Degradation:** Non-payment or cancellation automatically degrades the organization to Free Sandbox limits without deleting historical trading data.

---

## Section E: Refund & Cancellation Handling

### 1. Existing Behavior
- **Cancellation:** Supported via `POST /api/v1/billing/subscription/cancel` with `at_period_end: bool` (defaults to `True`).
- **Period-End Cancellation:** Subscription status remains `active` with `cancel_at_period_end=True` until Stripe emits `customer.subscription.deleted`.
- **Immediate Cancellation:** If `at_period_end=False`, subscription status immediately becomes `canceled` and entitlements degrade to Free tier.
- **Refunds:** **Zero automated refund logic exists** in the codebase. Webhooks do not handle `charge.refunded` or `refund.created`.

### 2. Required Policy
- Must publish a dedicated **Refund & Cancellation Policy**:
  - Outlines self-service cancellation via the Dashboard Billing page.
  - States that subscriptions are non-refundable except where mandatory under applicable statutory consumer law.
  - Clearly marked internally: *"Draft for legal review — requires owner/legal review"*.

---

## Section F: Data Inventory & Privacy Posture

### 1. Data Collected & Stored (PostgreSQL & Redis)

| Domain | Entities & Fields | Purpose | Access Control | Storage Duration |
| :--- | :--- | :--- | :--- | :--- |
| **Identity & Account** | `username`, `email`, `hashed_password` (bcrypt), `status` (ACTIVE/DEACTIVATED), `email_verified`, `password_changed_at`, `full_name`, `meta_data`. | Authentication, account security, communications. | User, Tenant Owner, System Admin. | **Indefinite** until account deletion. *(Requires product/legal decision)*. |
| **Security Tokens** | SHA-256 token hashes, `purpose` (PASSWORD_RESET, EMAIL_VERIFICATION), `expires_at`, `is_used`, `used_at`. | One-time password reset and email verification. | System internal only. | Ephemeral TTL (15 min / 24 hr). |
| **Abuse & Rate Limiting** | Client IP addresses (normalized IPv4/IPv6), sliding-window request timestamps. | DoS defense, brute-force mitigation. | Redis internal only. | Ephemeral TTL (1 hr to 24 hr). |
| **Tenant & Roles** | `organizations`, `organization_members` (roles: OWNER, ADMIN, TRADER, VIEWER), `organization_invitations`. | Multi-tenant isolation, RBAC governance. | Tenant members (scoped). | Indefinite. |
| **Trading Operations** | `accounts` (virtual paper balance), `orders` (paper orders, limit/stop prices), `fills` (simulated execution prices), `positions` (simulated open positions, PnL), `trades`. | Core paper-trading simulation, performance tracking. | Tenant members with `TRADING_READ`. | Permanent in PostgreSQL. *(Tier retention limits not auto-purged; requires decision)*. |
| **Research & AI** | `research_experiments`, `optimization_jobs`, `deployment_candidates` (backtests, parameters, tearsheets). | Algorithmic strategy evaluation. | Tenant members with `RESEARCH_READ`. | Permanent in PostgreSQL. |
| **Broker Sandbox** | `broker_connections`: OANDA account ID, AES-256-GCM encrypted API token, sync state. | Broker sandbox read-only synchronization. | Tenant members with `BROKER_READ`. | Until connection deleted. |
| **Commercial Billing** | `billing_customers` (Stripe customer ID, email), `billing_subscriptions` (Stripe sub ID, status, period), `billing_invoices` (amounts, invoice PDF links), `billing_events` (deduplicated webhooks). | Subscription management and entitlement enforcement. | Tenant members with `SUBSCRIPTION_READ`. | Permanent in PostgreSQL. |
| **Compliance Audit** | `audit_logs` (event_type, component, actor, details, timestamp). | Immutable compliance trail for tenant governance. | Tenant members with `AUDIT_READ`. | Permanent in PostgreSQL. |

### 2. Critical Privacy Finding: Data Retention
While plan limits define `retention_days` (30 to 2555 days), **no automated background job currently deletes historical records** from the database based on subscription tier. Data persists indefinitely unless manually removed.
- **Classification:** `Retention policy requires product/legal decision.`

---

## Section G: Cookies & Browser Storage Audit

A full audit of `apps/dashboard/src` was performed:
1. **Cookies:** `document.cookie` is **NEVER set or read** by frontend application code.
2. **`localStorage`:** **0 occurrences** across the entire dashboard codebase.
3. **`IndexedDB`:** **0 occurrences**.
4. **Third-Party Analytics & Marketing Trackers:** **0 scripts or SDKs** (no Google Analytics, Segment, Mixpanel, Datadog RUM, or Meta Pixel).
5. **`sessionStorage`:** Exactly two ephemeral keys:
   - `orion_access_token`: Ephemeral JWT access token for the active browser session.
   - `orion_active_org_id`: Active tenant organization UUID for the active session.
   Both are cleared on user logout and discarded when the browser tab closes.

### Privacy UX Determination
Because Project ORION uses **strictly ephemeral session storage and zero tracking cookies or third-party marketing beacons**, displaying a traditional European ePrivacy / cookie consent banner is **NOT applicable** and would mislead users. Instead, a transparent **Browser Storage & Session Disclosure** within the Privacy Policy is the correct and legally accurate approach.

---

## Section H: Existing Security Controls (Trust Inventory)

The following controls are fully implemented, verified by automated test suites, and factual:
- **Authentication:** Stateless JWT bearer tokens signed with HMAC-SHA256, strictly validated against environment secrets in production (`ORION_JWT_SECRET_KEY`, min 32 chars).
- **Password Security:** Salted `bcrypt` password hashing via `passlib`.
- **Token Hardening:** SHA-256 hashing of all password reset and email verification tokens prior to storage; single-use consumption.
- **Session Revocation:** Immediate JWT invalidation upon password change via `password_changed_at` timestamp comparison.
- **Rate Limiting & Abuse Defense:** Atomic Redis sliding-window limiter (sorted sets) with bounded in-memory LRU fallback (10,000 keys) and fail-closed defense on sensitive authentication endpoints.
- **Proxy-Aware IP Resolution:** `ClientIpResolver` with right-to-left untrusted proxy traversal and IPv4/IPv6 CIDR validation.
- **Multi-Tenant Isolation:** Mandatory `X-Organization-ID` context header validation; SQL-level tenant isolation across all tables.
- **Role-Based Access Control:** Granular permission system enforcing least privilege across OWNER, ADMIN, TRADER, VIEWER roles.
- **Credential Encryption:** AES-256-GCM symmetric authenticated encryption for all external broker sandbox tokens (`ORION_BROKER_ENCRYPTION_KEY`).
- **HTTP Security Headers:** Nginx reverse proxy enforces strict Content-Security-Policy (CSP), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, and `Referrer-Policy: strict-origin-when-cross-origin`.
- **Audit Logging:** Structured, immutable audit trail persisted in `audit_logs` table.

> [!NOTE]
> Project ORION has **not** undergone external SOC 2, ISO 27001, or PCI DSS certification audits. In accordance with strict legal guidelines, the Trust Center must describe these items as *"Security controls currently implemented"* and must never use the word *"Certified"*.

---

## Section I: Paper Trading Risk & Execution Engine Behavior

### 1. Simulated Matching Engine Characteristics (`PaperExecutionAdapter`)
- Supported Order Types: Market, Limit, Stop, Trailing Stop.
- Simulated Mechanics:
  - Spread simulation (default 1.0 pip on major pairs).
  - Adverse slippage model (configurable Gaussian distribution).
  - Commission modeling ($7.00 USD per standard lot / million).
  - Overnight swap rate modeling (long/short swap charges).
  - Execution latency simulation (50ms mean Gaussian latency).
  - Partial fill modeling.
  - Virtual initial account balance: $100,000.00 USD virtual currency.
  - Leverage: 100:1 virtual margin.

### 2. Disclosures Required
- **No Real Capital:** Capital at risk is strictly **$0.00**.
- **Execution Parity Disclaimer:** Simulated paper fills do not reflect real market conditions, market depth, queue priority, or exchange latency.
- **Hypothetical Performance Disclaimer:** Past backtest and paper trading performance is hypothetical and does not predict future live trading profitability.
- **No Advisory Status:** Project ORION is software, not an investment adviser, broker-dealer, or fiduciary.

---

## Section J: Marketing & Public Routes

### 1. Existing Public Routes
- `/login`
- `/forgot-password`
- `/reset-password`
- `/verify-email`

### 2. Phase 3 Public Legal Routes Required
- `/terms` — Terms of Service
- `/privacy` — Privacy Policy & Storage Disclosure
- `/risk-disclosure` — Paper Trading & Financial Risk Disclosure
- `/refund-policy` — Refund & Cancellation Policy
- `/security` — Security & Trust Architecture

---

## Section K: Consent & Acceptance Model Design

### 1. Architectural Analysis
To maintain high auditability and fast enforcement without unnecessary PII collection:
- **Canonical Documents:** Maintained in code as an immutable registry (`libraries/domain/legal/registry.py`) and static frontend documents with explicit semantic versions (`1.0`).
- **Acceptance Persistence:** A lean database table `legal_acceptances` tracking:
  - `id`: Unique UUID (`lacc_{uuid}`).
  - `user_id`: Foreign key to `users.id`.
  - `organization_id`: Foreign key to `organizations.id` (nullable for direct user signups).
  - `document_type`: Enum string (`TERMS_OF_SERVICE`, `PRIVACY_POLICY`, `PAPER_RISK_DISCLOSURE`, `REFUND_POLICY`).
  - `document_version`: String (`"1.0"`).
  - `accepted_at`: UTC timestamp.
  - `acceptance_method`: Enum (`WEB_REGISTRATION`, `WEB_IN_APP`, `API`).
  - `ip_address`: Optional / Nullable (Hashed or masked to respect privacy).
- **Audit Logging:** Every acceptance triggers an immutable `LEGAL_DOCUMENT_ACCEPTED` audit log event.
- **Unique Constraint:** `uq_legal_acceptance_user_doc_ver(user_id, document_type, document_version)` prevents duplicate records while preserving complete historical audit trails.

---

## Section L: Tenant & Organization Consent Scope

- In Project ORION's multi-tenant model, an individual user signs up and either creates an organization or accepts an invitation.
- **Legal consent is bound to the User (`user_id`)**.
- When an Owner creates an Organization during onboarding, their acceptance is recorded with both their `user_id` and the new `organization_id`.
- Tenant isolation is strictly preserved: a member of Organization A cannot view or accept legal terms on behalf of Organization B.

---

## Section M: Admin & Superuser Governance

- Standard tenant users and organization Owners **cannot modify legal document texts or versions**.
- Legal documents represent contractual terms governed by software release and git version control.
- Organization Owners and Admins with `AUDIT_READ` permission can view acceptance records for members within their organization via the audit log.

---

## Section N: Document Versioning Strategy

- Legal documents must adhere to semantic versioning:
  - `TERMS_OF_SERVICE` v1.0
  - `PRIVACY_POLICY` v1.0
  - `PAPER_RISK_DISCLOSURE` v1.0
  - `REFUND_POLICY` v1.0
- Backend endpoints validate that submitted versions match active versions in the canonical registry.
- Unpublished or retired versions are rejected with HTTP 400.

---

## Section O: Document Classification Matrix

| Document Type | Classification | Rationale |
| :--- | :---: | :--- |
| **Terms of Service** | **REQUIRED** | Fundamental contract governing platform use, software license, liability limitations, and user obligations. |
| **Privacy Policy** | **REQUIRED** | Mandatory disclosure of PII collection, credential handling, session storage, and third-party processors. |
| **Paper Trading Risk Disclosure** | **REQUIRED** | Vital financial disclaimer stating $0.00 capital, simulated fills, and lack of investment advisory status. |
| **Refund & Cancellation Policy** | **REQUIRED** | Essential for commercial billing clarity; covers subscription renewal, cancellation, and test-mode status. |
| **Security & Trust Center** | **RECOMMENDED** | Publicly documents implemented security controls (JWT, AES-256, rate limiting, RBAC) without false certification claims. |
| **Broker Sandbox Disclaimer** | **RECOMMENDED** | Embedded within Risk Disclosure; clarifies OANDA v20 practice environment limitations. |
| **Acceptable Use Policy** | **RECOMMENDED** | Embedded within Terms of Service; prohibits API abuse, reverse engineering, and credential stuffing. |
| **Cookie Policy (Standalone Banner)** | **NOT APPLICABLE** | Platform uses zero tracking cookies or third-party analytics. Session storage is covered in the Privacy Policy. |

---

## Section P: Third-Party Service Inventory

| Service Provider | Role in Project ORION | Data Shared | Production Status |
| :--- | :--- | :--- | :--- |
| **Render** | Cloud hosting, container runtime, managed PostgreSQL, Redis. | Application data, database records, server logs. | **Active Hosting Provider** |
| **Stripe** | Subscription billing and payment processing. | Customer email, org ID, billing name, plan code. | **Active in TEST MODE only** |
| **TwelveData** | External market data provider. | Instrument symbols requested by engine. | **Active Market Data Feed** |
| **OANDA** | Broker practice environment (`api-fxpractice.oanda.com`). | Practice account ID, encrypted API token, read-only order requests. | **Active Sandbox Only** |
| **GitHub** | Source repository, issue tracking, CI/CD. | Codebase, commit metadata (zero customer data). | **Developer Tooling** |
| **Email Service** | System notifications, password reset, email verification. | Destination email address, verification link tokens. | **Mock / Console / SMTP port** |

---

## Section Q: International Data Processing

- Project ORION is accessible via public Internet endpoints hosted in cloud regions (e.g. Render US-East/EU-Frankfurt).
- The platform collects user email and username upon registration and processes payments via Stripe.
- **Compliance Finding:** Cross-border data transfer mechanisms, standard contractual clauses (SCCs), and jurisdiction-specific privacy compliance (GDPR Article 28, CCPA notices, UK Data Protection Act) cannot be certified by automated code.
- **Classification:** `Jurisdictional legal review required before public commercial launch.`

---

## Section R: Audit Logging Integration

- Legal acceptance events will seamlessly integrate with the existing `AuditLogModel` schema in `audit_logs`.
- Event Type: `LEGAL_DOCUMENT_ACCEPTED`.
- Component: `legal_service`.
- Actor: `user.email`.
- Details Payload:
  ```json
  {
    "user_id": "usr_...",
    "organization_id": "org_...",
    "document_type": "TERMS_OF_SERVICE",
    "document_version": "1.0",
    "acceptance_method": "WEB_REGISTRATION"
  }
  ```

---

## Section S: Frontend UX Architecture

1. **Public Navigation & Footer:**
   - Add a shared public footer component (`apps/dashboard/src/components/layout/PublicFooter.tsx`) rendered on `/login`, `/forgot-password`, `/reset-password`, `/verify-email`, and all `/terms`, `/privacy`, `/risk-disclosure`, `/refund-policy`, `/security` pages.
2. **Authenticated AppShell Footer:**
   - Update `apps/dashboard/src/components/layout/AppShell.tsx` to include concise links: `Terms • Privacy • Risk Disclosure • Security`.
3. **Billing Page Enhancements:**
   - In `apps/dashboard/src/pages/BillingPage.tsx`, embed direct links to the Refund & Cancellation Policy and Terms of Service adjacent to upgrade buttons.
4. **Registration Flow:**
   - When user onboarding UI is rendered, present explicit checkboxes linking to Terms, Privacy, and Risk Disclosure.

---

## Section T: Public API Design

1. `GET /api/v1/legal/documents`
   - Public read endpoint returning list of active canonical documents, versions, titles, and effective dates.
   - Rate limited under `RateLimitPolicies.PUBLIC_READ` (100 req/min).
2. `GET /api/v1/legal/documents/{document_type}`
   - Public read endpoint returning full document content, summary, and version metadata.
3. `POST /api/v1/legal/acceptances`
   - Authenticated endpoint allowing active users to submit acceptance of a document version.
   - Requires valid JWT bearer token.
4. `POST /api/v1/onboarding/register`
   - Updated request model validating mandatory legal consent fields.

---

## Section U: Security & Tamper Resistance

- **Cross-Tenant Isolation:** Acceptances are strictly tied to the caller's authenticated `user_id` and validated `tenant_context`.
- **Immutability:** Acceptance records are append-only. No `UPDATE` or `DELETE` endpoints exist.
- **Version Integrity:** Submitting an invalid or retired version string results in HTTP 400 Bad Request.
- **Anti-Tampering:** Content of legal documents is hardcoded in version-controlled repository files, preventing dynamic SQL injection or unauthorized database modification.

---

## Section V: Product Claim Safety Matrix

| Current Claim in UI / Code | Location | Current State | Risk Rating | Required Modification |
| :--- | :--- | :--- | :---: | :--- |
| `"INSTITUTIONAL FOREX TRADING PLATFORM"` | `LoginPage.tsx:58` | Prominent uppercase header | Medium | Add subtitle: *"Simulated Paper Trading Software • $0.00 Capital at Risk"*. |
| `"Enterprise Institutional"` | `BillingPage.tsx:130` | Tier name | Low | Retain tier name, but qualify description: *"For institutional research teams (paper trading only)"*. |
| `"7-Year Audit Trail Compliance"` | `BillingPage.tsx:138` | Feature bullet | Medium | Change to: *"Long-term system audit log retention (subject to data agreement)"*. |
| `"Institutional capital protection"` | `RiskPage.tsx:80` | Header subtitle | Low | Clarify: *"Pre-trade risk filtering and simulated portfolio drawdown protection"*. |
| `"Immutable compliance records for institutional governance"` | `AuditPage.tsx:78` | Subtitle | Low | Accurate description of append-only audit trail. Keep as is. |

---

## Section W: Phase Boundary & Scope Guardrails

Phase 3 is strictly scoped to establishing the **Legal, Trust & Risk Disclosure Foundation**.
- **EXCLUDED from Phase 3:**
  - Marketing website and landing pages (belongs to Phase 4).
  - Growth funnels, SEO campaigns, blog engine.
  - Live Stripe payment mode activation.
  - Live broker trading adapters or live broker credentials.
  - Live trading worker activation.
  - Formal external legal certifications or regulatory filings.
- **INCLUDED in Phase 3:**
  - 5 canonical legal and disclosure documents (`TERMS_OF_SERVICE`, `PRIVACY_POLICY`, `PAPER_RISK_DISCLOSURE`, `REFUND_POLICY`, `SECURITY_DISCLOSURE`).
  - Database persistence model and migration for legal acceptances (`0014_legal_acceptance.py`).
  - Canonical legal domain registry and validation service.
  - Public legal REST API endpoints with rate limiting.
  - Frontend legal routing and viewing pages with shared navigation and footer.
  - Registration legal consent validation contract.
  - Comprehensive unit, integration, and frontend tests.
