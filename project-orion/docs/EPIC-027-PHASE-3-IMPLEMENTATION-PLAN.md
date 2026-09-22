# EPIC-027 Phase 3 — Legal, Trust & Risk Disclosure Implementation Plan

**Document Version:** 1.0.0
**Date:** 2026-09-22
**Milestone:** EPIC-027 (Public Beta & Commercial Launch Readiness)
**Phase:** Phase 3 — Legal, Trust & Risk Disclosure Foundation
**Author:** Quantitative Architecture, Security, & Engineering Team
**Repository:** `Project-ORION` (Branch: `main`, Baseline Commit: `405ce08`)
**Target Delivery:** Multi-tenant quantitative paper-trading, algorithmic research, and strategy SaaS

---

## 1. Architectural Overview

Project ORION Phase 3 implements the technical and operational foundation for legal, trust, and risk disclosures required for public beta onboarding. The architecture couples version-controlled, static canonical legal texts with a lean, auditable database persistence model and rate-limited public APIs.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                             PUBLIC FRONTEND                              │
│                                                                          │
│  Public Routes: /terms, /privacy, /risk-disclosure, /refund, /security   │
│  Navigation: Shared PublicFooter (Login, Recovery, Verification, Legal)  │
│  In-App: AppShell Legal Links & Billing Page Policy Disclosures          │
└─────────────────────────────────────┬────────────────────────────────────┘
                                      │
                         REST API Requests (JSON)
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         TRADING ENGINE API ROUTER                        │
│                                                                          │
│  GET  /api/v1/legal/documents (Public, RateLimited: 100/min)             │
│  GET  /api/v1/legal/documents/{type} (Public, RateLimited: 100/min)      │
│  POST /api/v1/legal/acceptances (Authenticated JWT, RateLimited)         │
│  POST /api/v1/onboarding/register (Enforces Mandatory Consent Flags)     │
└──────────────────┬──────────────────────────────────┬────────────────────┘
                   │                                  │
                   ▼                                  ▼
┌───────────────────────────────────┐ ┌────────────────────────────────────┐
│         LEGAL SERVICE             │ │       LEGAL DOMAIN REGISTRY        │
│                                   │ │                                    │
│ - Version validation (rejects     │ │ - Canonical document definitions   │
│   unpublished/retired)            │ │ - Semantic version strings (1.0)   │
│ - Deduplication check             │ │ - Effective dates & status         │
│ - Emits audit log event           │ │ - Immutable content text / files   │
└──────────────────┬────────────────┘ └────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     PERSISTENCE LAYER (PostgreSQL)                       │
│                                                                          │
│  Table: legal_acceptances                                                │
│  (id, user_id, org_id, document_type, document_version, accepted_at,     │
│   acceptance_method, ip_hash)                                            │
│                                                                          │
│  Table: audit_logs (Event: LEGAL_DOCUMENT_ACCEPTED)                      │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Legal Documents Required

The following 5 canonical documents will be drafted in neutral, factual language with explicit internal markers (*"Draft for legal review — requires external legal counsel review before commercial launch"*):

1. **Terms of Service (`TERMS_OF_SERVICE` v1.0):**
   - Software license for web-based quantitative research and simulated paper trading.
   - User account obligations and credential protection responsibilities.
   - Strict prohibition of live trading or external broker manipulation.
   - Limitation of liability and disclaimer of warranties (as-is software).
   - Account deactivation and termination terms.
   - Embedded Acceptable Use Policy (prohibiting API scraping, vulnerability exploitation, and load testing).
2. **Privacy Policy (`PRIVACY_POLICY` v1.0):**
   - Inventory of collected data (username, email, hashed password, ephemeral IP for rate limiting).
   - Ephemeral browser session storage disclosure (`sessionStorage` for tokens; zero tracking cookies).
   - Third-party processors disclosure (Render hosting, TwelveData market feeds, Stripe test mode).
   - User rights, data deletion process, and security practices.
   - Explicit disclaimer: *"Jurisdictional legal review required before public commercial launch."*
3. **Paper Trading & Financial Risk Disclosure (`PAPER_RISK_DISCLOSURE` v1.0):**
   - Declaration that all trading activity on ORION is simulated paper trading ($0.00 real capital).
   - Disclaimer that ORION is software, not an investment advisor, broker-dealer, or fiduciary.
   - Hypothetical performance disclosure: Backtests, walk-forward optimizations, and paper fills do not represent live financial returns.
   - Execution differences disclosure (slippage, liquidity, queue priority, and latency are simulated).
   - Embedded Broker Sandbox Disclaimer for OANDA v20 practice integration.
4. **Refund & Cancellation Policy (`REFUND_POLICY` v1.0):**
   - Details self-service subscription cancellation via the billing dashboard.
   - Cancellation takes effect at the end of the current paid billing cycle.
   - SaaS subscription fees are non-refundable once access is provisioned, subject to statutory consumer protection laws.
   - Explicit disclosure of Stripe Test Mode during beta.
5. **Security & Trust Center (`SECURITY_DISCLOSURE` v1.0):**
   - Factual summary of implemented security engineering: HMAC-SHA256 JWT, bcrypt, cryptographic token hashing, sliding-window rate limiting, AES-256-GCM broker key encryption, RBAC, tenant isolation, and audit logging.
   - Explicit statement: *"Security controls currently implemented (no formal SOC 2/ISO certifications claimed)."*

---

## 3. Documents Not Required & Explicit Exclusions

1. **Standalone Cookie Policy / Consent Banner:**
   - **EXCLUDED:** The dashboard uses strictly ephemeral session storage and zero tracking cookies or third-party marketing beacons. A standalone cookie banner is not applicable and would be misleading. Browser storage is disclosed inside the Privacy Policy.
2. **Growth / Marketing Website:**
   - **EXCLUDED:** Full marketing site belongs to Phase 4. Phase 3 focuses solely on public legal surfaces.
3. **Live Stripe Payment Disclosure:**
   - **EXCLUDED:** Stripe operates in Test Mode only.
4. **Live Broker Trading Terms:**
   - **EXCLUDED:** Live broker execution is disabled.

---

## 4. Consent Architecture & Flow

### A. New User Registration Consent (Fail-Closed)
When registering an account via `POST /api/v1/onboarding/register`:
- Client must submit boolean consent flags:
  - `accept_terms: bool` (Must be `True`)
  - `accept_privacy: bool` (Must be `True`)
  - `accept_risk_disclosure: bool` (Must be `True`)
- The onboarding service validates that all three are `True`. If any is missing or `False`, it raises HTTP 422 Unprocessable Entity.
- Upon successful account and organization creation, the service automatically persists 3 records to `legal_acceptances` and logs corresponding audit events.

### B. In-App Acceptance for Existing / Invited Users
- Active users can accept documents via `POST /api/v1/legal/acceptances`.
- Validates user identity from JWT bearer token.
- Validates document type and version against canonical registry.
- Deduplicates: Ignores or confirms repeat submissions of the same version without error.

---

## 5. Document Versioning Model

- Every document is assigned a canonical identifier and semantic version:
  - `TERMS_OF_SERVICE`: `"1.0"`
  - `PRIVACY_POLICY`: `"1.0"`
  - `PAPER_RISK_DISCLOSURE`: `"1.0"`
  - `REFUND_POLICY`: `"1.0"`
  - `SECURITY_DISCLOSURE`: `"1.0"`
- Versions are tracked in `libraries/domain/legal/registry.py`.
- Any material update increments the version string (e.g. `"1.1"` or `"2.0"`).
- Acceptances are permanently associated with the exact version string submitted.

---

## 6. Acceptance Persistence (`legal_acceptances`)

A new database table `legal_acceptances` will be introduced via Alembic migration `0014_legal_acceptance.py`:

```sql
CREATE TABLE legal_acceptances (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id VARCHAR(64) REFERENCES organizations(id) ON DELETE SET NULL,
    document_type VARCHAR(64) NOT NULL,
    document_version VARCHAR(32) NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    acceptance_method VARCHAR(32) NOT NULL,
    ip_hash VARCHAR(64) NULL,
    user_agent VARCHAR(255) NULL
);

CREATE INDEX ix_legal_acceptances_user_id ON legal_acceptances(user_id);
CREATE INDEX ix_legal_acceptances_org_id ON legal_acceptances(organization_id);
CREATE UNIQUE INDEX uq_legal_acceptance_user_doc_ver
    ON legal_acceptances(user_id, document_type, document_version);
```

> [!NOTE]
> To avoid unnecessary PII storage while maintaining forensic attribution, client IP addresses may be stored as an irreversible SHA-256 hash (`ip_hash = sha256(ip + salt)`) or left nullable.

---

## 7. Audit Logging Integration

Every legal acceptance triggers an append-only record in `audit_logs`:
- **Event Type:** `LEGAL_DOCUMENT_ACCEPTED`
- **Component:** `legal_service`
- **Actor:** User email or ID
- **Details:**
  ```json
  {
    "user_id": "usr_...",
    "organization_id": "org_...",
    "document_type": "TERMS_OF_SERVICE",
    "document_version": "1.0",
    "acceptance_method": "WEB_REGISTRATION",
    "timestamp": "2026-09-22T12:00:00Z"
  }
  ```

---

## 8. Frontend Routes & Pages

The following new routes will be added to `apps/dashboard/src/App.tsx`:
- `/terms` -> `TermsPage.tsx`
- `/privacy` -> `PrivacyPage.tsx`
- `/risk-disclosure` -> `RiskDisclosurePage.tsx`
- `/refund-policy` -> `RefundPolicyPage.tsx`
- `/security` -> `SecurityTrustPage.tsx`

All legal pages share a unified layout:
- Sticky public header with branding and link back to Login.
- Table of Contents sidebar for easy navigation through document sections.
- Formatted legal content in readable typography with institutional dark styling.
- Public footer with cross-links to all other legal documents.

---

## 9. Public Navigation & Footer

A reusable `PublicFooter` component will be rendered on:
- `/login`
- `/forgot-password`
- `/reset-password`
- `/verify-email`
- All `/terms`, `/privacy`, `/risk-disclosure`, `/refund-policy`, `/security` pages.

Footer Links:
- `Terms of Service`
- `Privacy Policy`
- `Paper Trading Risk Disclosure`
- `Refund Policy`
- `Security & Trust`
- Subtitle: *"Project ORION is simulated paper trading software. $0.00 Capital at Risk."*

---

## 10. Registration Integration

Update `OnboardingRegisterRequest` schema in `apps/trading-engine/src/schemas.py`:
```python
class OnboardingRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    organization_name: str = Field(..., min_length=2, max_length=100)
    organization_slug: str | None = None
    full_name: str | None = None
    accept_terms: bool = Field(..., description="Must accept Terms of Service")
    accept_privacy: bool = Field(..., description="Must acknowledge Privacy Policy")
    accept_risk_disclosure: bool = Field(..., description="Must acknowledge Paper Trading Risk Disclosure")
```

---

## 11. Billing Page Integration

In `apps/dashboard/src/pages/BillingPage.tsx`:
- Add explicit legal disclosure under plan cards:
  - Link to `/refund-policy` (*"Subscriptions renew automatically. Non-refundable except as required by law."*).
  - Link to `/terms` (*"Governed by Project ORION Terms of Service."*).
- Qualify the Enterprise tier feature:
  - From *"7-Year Audit Trail Compliance"* to *"Long-term system audit log retention (subject to data agreement)"*.
- Highlight that checkouts operate in **Stripe Test Mode**.

---

## 12. Security & Trust Page (`/security`)

Presents a clear, professional breakdown of existing technical controls:
- **Authentication & Sessions:** Stateless JWT tokens, single-use reset tokens, instant revocation upon password reset.
- **Tenant Isolation:** Multi-tenant boundaries enforced in application and database queries.
- **API Defense:** Rate limiting with sliding-window Redis counter and fail-closed authentication endpoints.
- **Credential Storage:** AES-256-GCM authenticated encryption for broker sandbox API keys.
- **Infrastructure Security:** CSP headers, TLS, automated backups.
- **Notice:** Clear statement that ORION does not currently claim SOC 2 or ISO 27001 certifications.

---

## 13. Risk Disclosure Page (`/risk-disclosure`)

Covers:
- **Virtual Capital Only:** All accounts use simulated paper capital ($100,000 USD default balance).
- **Execution Parity:** Differences between simulated fill algorithms and live broker order routing.
- **Hypothetical Backtest Warning:** Historical performance hurdles and walk-forward statistics do not guarantee future performance.
- **No Financial Advice:** Not a broker-dealer, investment advisor, or commodity trading advisor.
- **Broker Sandbox Limitations:** OANDA v20 practice account simulation characteristics.

---

## 14. Refund & Cancellation Policy Page (`/refund-policy`)

Covers:
- Self-service monthly cancellation via the dashboard.
- Immediate vs Period-End cancellation behavior.
- No partial-month prorated refunds for digital access.
- Beta test-mode billing notice.
- Internal marker: *"Draft for legal review — requires owner/legal review."*

---

## 15. Privacy & Data Inventory Page (`/privacy`)

Covers:
- Account information collected upon signup.
- Ephemeral session data stored in `sessionStorage`.
- Explicit notice that no tracking cookies or marketing trackers are used.
- Subprocessors: Cloud infrastructure (Render), payment gateway (Stripe test mode), market data (TwelveData), broker sandbox (OANDA).
- Data access, user rights, and contact placeholder.

---

## 16. Cookie & Storage Analysis

- No cookie tracking scripts exist.
- No cookie consent banner is needed.
- Ephemeral browser storage (`sessionStorage`) is documented transparently in the Privacy Policy.

---

## 17. RBAC Governance

- Viewing legal acceptances within an organization requires the existing `AUDIT_READ` permission.
- No new arbitrary permissions are created.
- Organization Owners and Admins can view audit logs for `LEGAL_DOCUMENT_ACCEPTED` events.

---

## 18. Tenant Isolation Safeguards

- User acceptances cannot be tampered with or submitted across tenant boundaries.
- The `organization_id` on an acceptance record is validated against the user's active organization membership.
- Foreign keys enforce referential integrity.

---

## 19. Rate Limiting Integration

- `GET /api/v1/legal/documents`: Protected by `RateLimitPolicies.PUBLIC_READ` (100 req/min).
- `POST /api/v1/legal/acceptances`: Protected by `RateLimitPolicies.GENERAL_MUTATE` (120 req/min).
- `POST /api/v1/onboarding/register`: Protected by existing `RateLimitPolicies.ONBOARDING_REGISTER` (5 req/hour).

---

## 20. Comprehensive Testing Strategy

1. **Unit Tests (Backend):**
   - `test_legal_registry.py`: Validates canonical document registry, version resolution, and active/retired status.
   - `test_legal_service.py`: Validates document acceptance, deduplication, audit log emission, and invalid version rejection.
2. **Integration Tests (Backend):**
   - `test_legal_routes.py`: Tests `GET /api/v1/legal/documents`, `GET /api/v1/legal/documents/{type}`, and `POST /api/v1/legal/acceptances`.
   - `test_onboarding_legal.py`: Tests that registration without legal consent is rejected with 422, and registration with consent successfully creates acceptance records.
   - `test_migration_0014.py`: Tests upgrade and downgrade of Alembic migration `0014_legal_acceptance.py`.
3. **Frontend Component Tests:**
   - `legal_pages.test.tsx`: Validates rendering of `/terms`, `/privacy`, `/risk-disclosure`, `/refund-policy`, `/security`.
   - `public_footer.test.tsx`: Validates public footer rendering and navigation links.
4. **Regression Tests:**
   - Verify all existing 128 backend tests and 61 frontend tests continue to pass with 100% success.

---

## 21. Migration Strategy

- Migration `0014_legal_acceptance.py` creates table `legal_acceptances` with indices and foreign keys.
- Safe, non-locking migration: Existing tables (`users`, `organizations`, `audit_logs`) are untouched except for adding the foreign key.
- Existing active users: Not blocked from logging in. A non-blocking re-consent banner will be presented in subsequent UX milestones if required.

---

## 22. Rollback Strategy

- Database: `alembic downgrade -1` drops `legal_acceptances` cleanly.
- Code: Clean git commit revert if necessary without impacting Phase 1 auth or Phase 2 rate limiting.

---

## 23. Deployment Strategy

- Continuous integration pipeline runs `pytest` and `npm test` before container build.
- Database migrations execute during container startup prior to traffic routing.
- Zero-downtime deployment on Render.

---

## 24. External Legal-Review Dependencies

The following items are technical drafts and **require qualified legal counsel review** prior to commercial launch:
1. Jurisdiction of incorporation and governing law clauses.
2. Formal statutory refund terms (e.g. EU 14-day right of withdrawal for digital content).
3. Cross-border data transfer mechanisms (EU/UK GDPR Standard Contractual Clauses).
4. Data Protection Officer (DPO) and formal legal notice email addresses.
5. Dispute resolution and binding arbitration venue specifications.

---

## 25. Known Limitations

- Subscriptions operate strictly in Stripe Test Mode; no real funds are processed.
- Automated tier-based data pruning is not yet implemented; database retention requires a future background purging job.
- Legal documents are delivered in English; multi-language localization is deferred to a future milestone.
