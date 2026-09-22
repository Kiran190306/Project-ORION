# EPIC-027 Phase 3: Legal, Trust & Risk Disclosure — Security & Privacy Architecture

**Document Version:** 1.0
**Phase:** EPIC-027 Phase 3
**Status:** DRAFT FOR EXTERNAL LEGAL REVIEW
**Classification:** `B — IMPLEMENTED WITH EXTERNAL LEGAL REVIEW PENDING`
**Date:** 2026-09-22

---

## 1. Security & Privacy Principles

Phase 3 implements legal and consent tracking under strict data minimization, privacy preservation, and defensive engineering practices:

1. **Zero Unnecessary PII Collection (GDPR Art. 5(1)(c))**:
   - The platform minimizes data retained for legal consent tracking.
   - **No raw IP addresses** are stored in the database. Forensic auditability is achieved through immutable user identity, organization context, timestamp, and user-agent string.
2. **Multi-Tenant Isolation (IDOR Defense)**:
   - Every acceptance record is tied to an `organization_id` foreign key.
   - Database queries filter strictly by `user_id` and authorized tenant boundaries.
3. **Immutability of Consent Records**:
   - Legal acceptances cannot be updated or altered. Once recorded, consent records are permanent.
   - Submitting an identical consent for the same document version is deduplicated idempotently without altering timestamps or records.
4. **Append-Only Audit Trail**:
   - Every consent event generates an immutable record in `audit_logs` with event type `LEGAL_DOCUMENT_ACCEPTED`, documenting actor ID, organization context, document type, and version.
5. **Rate-Limiting Defense**:
   - Legal document catalog and detail endpoints (`/api/v1/legal/documents`, `/api/v1/legal/documents/{document_type}`) are public and protected by Phase 2 atomic sliding-window rate limiters.
   - Acceptance submission (`/api/v1/legal/acceptances`) is restricted to authenticated sessions and rate-limited.
6. **Zero Tracking Cookies**:
   - The application does not use tracking cookies, advertising beacons, or third-party analytics pixels.
   - Authentication tokens are maintained in browser `sessionStorage` and destroyed on tab close or sign-out.

---

## 2. Privacy & Data Handling Review

### Stored User Data
| Data Category | Storage Location | Protection Mechanism |
|---|---|---|
| User Credentials | `users` table | `bcrypt` hash with salt |
| Email & Username | `users` table | Multi-tenant isolation |
| Password Reset Tokens | `users` table | Cryptographically random, `SHA-256` hashed before storage |
| Email Verification Tokens | `users` table | Cryptographically random, `SHA-256` hashed before storage |
| Legal Acceptances | `legal_acceptances` table | User/Org FK, No raw IP, immutable |
| Audit Trail | `audit_logs` table | Append-only, indexed by org and actor |
| Browser Session | `sessionStorage` | Ephemeral, destroyed on logout / tab close |

---

## 3. Compliance Transparency & Non-Certification

Project ORION is in active Public Beta and does not falsely claim formal third-party compliance certifications:

1. **SOC 2 & ISO 27001**:
   - System security controls follow best practices (least privilege RBAC, AES-256-GCM encryption at rest, rate limiting, secure password hashing).
   - However, formal SOC 2 Type II or ISO 27001 third-party audit certifications have not been conducted and are not claimed.
2. **PCI DSS**:
   - ORION does not ingest, transmit, process, or store credit card numbers.
   - All payment handling is delegated to Stripe (currently operating in Stripe Test Mode).
3. **GDPR & CCPA**:
   - Engineering controls align with privacy-by-design principles (data minimization, zero cookies, ephemeral session storage, no raw IP retention).
   - Formal Data Protection Officer (DPO) registration and standard contractual clauses are pending external legal counsel review.
4. **Regulatory Non-Registration**:
   - Project ORION is not registered as an investment adviser, broker-dealer, or commodity trading advisor with the SEC, CFTC, FINRA, or NFA.
   - All platform operations are strictly paper trading ($0.00 capital at risk).

---

## 4. Threat Modeling & Abuse Protection

| Threat Vector | Mitigation Strategy | Verification Status |
|---|---|---|
| Registration Consent Bypass | Server-side Pydantic validator rejects registration with HTTP 422 if any consent is false. | Verified in `test_onboarding_legal.py` |
| Invalid Version Acceptance | `LegalService` validates version against active registry; returns HTTP 400 for retired/invalid versions. | Verified in `test_legal_routes.py` |
| Acceptance Flooding / Replay | Idempotent deduplication query returns existing record without inserting duplicate row. | Verified in `test_legal_service.py` |
| Cross-Tenant Consent Tampering | Acceptance submission enforces authenticated user ID from JWT; no cross-user acceptance possible. | Verified in `test_legal_routes.py` |
| Scraping / DoS on Legal Docs | Public legal endpoints are rate-limited via Redis sliding-window counter. | Verified in Phase 2 integration |
| Session Token Hijacking | JWT tokens revoked upon password change (`password_changed_at` check). | Verified in Phase 1 regression |

---

## 5. Security Invariant Confirmation

- [x] Capital at risk: **$0.00**
- [x] Live broker execution: **Disabled**
- [x] Autonomous worker: **Disabled**
- [x] Stripe billing: **Test Mode Only**
- [x] Raw IP addresses in legal tables: **Zero (omitted)**
- [x] Production secrets: **Zero**
- [x] Live trading accounts: **Zero**
