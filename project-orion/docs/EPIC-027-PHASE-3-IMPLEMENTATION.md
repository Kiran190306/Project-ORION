# EPIC-027 Phase 3: Legal, Trust & Risk Disclosure — Technical Implementation

**Document Version:** 1.0
**Phase:** EPIC-027 Phase 3
**Status:** DRAFT FOR EXTERNAL LEGAL REVIEW
**Classification:** `B — IMPLEMENTED WITH EXTERNAL LEGAL REVIEW PENDING`
**Date:** 2026-09-22

---

## 1. Executive Summary

Phase 3 of EPIC-027 establishes the legal, trust, and risk disclosure foundation for Project ORION prior to commercial beta onboarding. The engineering objective is to provide complete transparency regarding system behavior, rigorous versioned consent persistence, immutable audit logging, paper-trading risk disclosures, and comprehensive public navigation—while explicitly avoiding fabricated legal advice, uncertified compliance claims, or invented corporate and statutory details.

All platform disclosures remain marked as **"Draft for legal review"** until approved by qualified external legal counsel.

---

## 2. Architecture & Domain Layer

The legal disclosure architecture decouples legal metadata and consensus state from document prose.

```
project-orion/
├── libraries/domain/legal/
│   ├── __init__.py
│   ├── models.py                   # Domain types, Enums, DTOs
│   ├── registry.py                 # File-backed Markdown loader & registry
│   └── content/                    # Versioned Markdown disclosure files
│       ├── TERMS_OF_SERVICE_v1.0.md
│       ├── PRIVACY_POLICY_v1.0.md
│       ├── PAPER_RISK_DISCLOSURE_v1.0.md
│       ├── REFUND_POLICY_v1.0.md
│       └── SECURITY_DISCLOSURE_v1.0.md
```

### Domain Models (`libraries/domain/legal/models.py`)
- `LegalDocumentType`:
  - `TERMS_OF_SERVICE`: Platform terms of service.
  - `PRIVACY_POLICY`: Privacy & data handling disclosure.
  - `PAPER_RISK_DISCLOSURE`: Paper-trading and simulation limitations.
  - `REFUND_POLICY`: Beta billing and subscription cancellation policy.
  - `SECURITY_DISCLOSURE`: Security controls and architecture disclosure.
- `LegalConsentKind`:
  - `AGREEMENT`: Formal contractual assent (Terms of Service).
  - `ACKNOWLEDGEMENT`: Receipt and notice acknowledgement (Privacy, Risk Disclosure).
  - `INFORMATIONAL`: Public informational disclosure (Security, Refund).
- `DocumentStatus`: `DRAFT`, `ACTIVE`, `RETIRED`.
- `LegalAcceptanceMethod`: `WEB_FORM_CHECKBOX`, `ONBOARDING_REGISTRATION`, `API_DIRECT`.
- `LegalDocumentMetadata`: Immutable metadata including type, title, active version, effective date, summary, and mandatory flag.
- `LegalAcceptanceRecord`: Domain entity representing a recorded user acceptance.

### Legal Registry (`libraries/domain/legal/registry.py`)
- Maintains canonical metadata for all 5 document types.
- Provides dynamic loading of document prose from `libraries/domain/legal/content/*.md`.
- Enforces active version validation and filters documents requiring mandatory consent at registration.

---

## 3. Persistence Layer & Migration 0014

### Database Schema (`libraries/infrastructure/persistence/models/legal_acceptance.py`)
Table: `legal_acceptances`
- `id` (VARCHAR(36), PK): UUID.
- `user_id` (VARCHAR(36), FK -> `users.id`, nullable=False): User providing consent.
- `organization_id` (VARCHAR(36), FK -> `organizations.id`, nullable=False): Organization context.
- `document_type` (VARCHAR(64), nullable=False): Type identifier.
- `version` (VARCHAR(32), nullable=False): Document version accepted (e.g. `1.0`).
- `consent_kind` (VARCHAR(32), nullable=False): `AGREEMENT` or `ACKNOWLEDGEMENT`.
- `acceptance_method` (VARCHAR(64), nullable=False): Method used to capture consent.
- `user_agent` (VARCHAR(512), nullable=True): Sanitized browser user-agent header.
- `accepted_at` (DATETIME, nullable=False): UTC timestamp.
- Unique Constraint: `uq_legal_acceptance_user_doc_ver` (`user_id`, `document_type`, `version`).

### Privacy-Preserving Attribution
In compliance with privacy minimization principles (GDPR Art. 5(1)(c)), **no raw IP addresses** are stored in the legal acceptances table. Forensic attribution is provided by `user_id`, `organization_id`, `accepted_at`, and `user_agent`.

### Alembic Migration 0014 (`database/migrations/versions/0014_legal_acceptance.py`)
- Creates table `legal_acceptances`.
- Creates indices on `user_id`, `organization_id`, and `document_type`.
- Creates unique constraint on `(user_id, document_type, version)`.

---

## 4. Service Layer & Audit Trail

### `LegalService` (`apps/trading-engine/src/services/legal_service.py`)
- `list_active_documents()`: Returns active document metadata catalogue.
- `get_document_metadata(document_type)`: Retrieves metadata for a document type.
- `get_document_content(document_type)`: Loads markdown prose from disk.
- `record_acceptance()`:
  - Validates document type and active version (rejects invalid/retired versions).
  - Performs idempotent deduplication: if the exact `(user_id, document_type, version)` record exists, returns existing record without duplicate insertion.
  - Persists `LegalAcceptanceModel`.
  - Emits immutable event `LEGAL_DOCUMENT_ACCEPTED` to `audit_logs` table.
- `record_registration_consents()`: Batch records the 3 mandatory consents during user onboarding (`TERMS_OF_SERVICE`, `PRIVACY_POLICY`, `PAPER_RISK_DISCLOSURE`).
- `list_user_acceptances()`: Retrieves legal acceptance history for a user.

---

## 5. API Layer & Registration Integration

### Legal Router (`apps/trading-engine/src/routes/legal.py`)
- Mounted at `/api/v1/legal`:
  - `GET /documents`: Public list of active legal documents. Protected by public sliding-window rate limit.
  - `GET /documents/{document_type}`: Public detail endpoint returning metadata and full markdown prose.
  - `POST /acceptances`: Authenticated endpoint recording user acceptance.
  - `GET /acceptances`: Authenticated endpoint returning user's acceptance history.

### Onboarding Registration Enforcement
- Request Schema (`apps/trading-engine/src/schemas.py`):
  - `terms_accepted`: bool (must be `true`)
  - `privacy_acknowledged`: bool (must be `true`)
  - `risk_disclosure_acknowledged`: bool (must be `true`)
  - Pydantic `@field_validator` raises `ValueError` (HTTP 422) if any of the three flags is false.
- Service Integration (`apps/trading-engine/src/services/onboarding_service.py`):
  - Injects `LegalService` into `OnboardingService`.
  - Automatically records the 3 consents upon organization creation within the same database transaction.

---

## 6. Frontend Presentation & Navigation

### Public Legal Pages (`apps/dashboard/src/pages/`)
1. `TermsPage.tsx`: Terms of Service, scope of software, paper trading invariant ($0.00 capital at risk), user accounts, acceptable use, warranty disclaimers, liability limitations.
2. `PrivacyPage.tsx`: Personal data categories, HTML5 `sessionStorage` disclosure (`orion_access_token`, `orion_active_org_id`), zero cookie policy, third-party infrastructure processors, retention.
3. `RiskDisclosurePage.tsx`: Mandatory CFTC 4.41 hypothetical performance warning, execution simulation differences, slippage/spread modeling, $0.00 capital at risk invariant.
4. `RefundPolicyPage.tsx`: Beta Stripe test mode disclaimer, recurring billing rules, self-service cancellation workflow, dispute resolution procedures.
5. `SecurityTrustPage.tsx`: Non-certification disclosure (SOC 2 / ISO 27001 / PCI DSS pending external audit), authentication architecture, rate limiting defense, RBAC isolation, AES-256-GCM encryption at rest, coordinated vulnerability disclosure.

### Shared Layout & Navigation
- `LegalPageLayout.tsx`: Reusable layout featuring sticky header with "Return to Terminal", version badge, "Draft for Legal Review" indicator, hero banner, interactive table of contents, and responsive content column.
- `PublicFooter.tsx`: Public footer rendered on unauthenticated pages (e.g. `LoginPage`), providing direct links to all 5 legal pages and displaying the persistent paper-trading notice.
- `AppShell.tsx`: Authenticated application shell includes persistent footer links to Terms, Privacy, Risk Disclosure, and Security.
- `BillingPage.tsx`: Includes Commercial Terms & Billing Notice card with direct links to `/refund-policy`, `/terms`, and `/risk-disclosure`. Enterprise retention description qualified as subject to data agreement.
- `LoginPage.tsx`: Updated to integrate `PublicFooter` and reiterate simulated execution ($0.00 capital at risk).
- `App.tsx`: Routes registered for `/terms`, `/privacy`, `/risk-disclosure`, `/refund-policy`, `/security`.

---

## 7. Compliance Verification & Invariants

1. **Safety Invariants**:
   - Platform operates in Paper Trading Mode only ($0.00 capital at risk).
   - Live broker connections disabled.
   - Autonomous background worker disabled.
   - Stripe billing in Test Mode only.
2. **Phase 1 & Phase 2 Preserved**:
   - Production JWT secret validation fail-closed, user lifecycle, and token hashing remain active.
   - Redis atomic sliding-window rate limiters protect all public endpoints.
3. **Draft Status Maintained**:
   - All legal prose and frontend pages explicitly feature "Draft for legal review" or "Public Beta Legal Disclosure".
