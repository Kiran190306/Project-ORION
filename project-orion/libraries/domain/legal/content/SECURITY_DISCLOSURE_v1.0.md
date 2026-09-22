# Security & Trust Architecture

**Document Version:** 1.0
**Effective Date:** 2026-09-22
**Status:** Technical disclosure — factual description of implemented engineering controls.

---

### Non-Certification Disclosure
> **Notice:** Project ORION is currently in active Public Beta. The platform has not undergone external third-party SOC 2, ISO 27001, or PCI DSS compliance audits. This document outlines the technical security controls **currently implemented** within the software architecture. It does not constitute a formal security certification or compliance warranty.

---

### 1. Authentication & Session Security
- **Stateless JWT Protection:** Authentication utilizes HMAC-SHA256 signed JSON Web Tokens (JWT). In production environments, secret keys are strictly validated at startup, requiring high-entropy keys (minimum 32 characters) and failing closed against default developmental secrets.
- **Bcrypt Password Hashing:** User passwords are encrypted using `bcrypt` with random salt generation prior to database persistence. Plaintext passwords are never logged, transmitted, or stored.
- **Token Hashing & Single-Use Enforcement:** Password reset tokens and email verification tokens are generated using cryptographically secure random bytes (`secrets.token_urlsafe(32)`), hashed with `SHA-256` before persistence, and destroyed upon single use.
- **Session Revocation Invariant:** Passwords modifications immediately update a `password_changed_at` timestamp on the user record. Any active JWT access token issued prior to this timestamp is instantly rejected across all platform endpoints.
- **Account Deactivation:** Suspended or deactivated accounts immediately fail closed during authentication and cannot establish active sessions.

### 2. Abuse Defense & Rate Limiting (Phase 2 Hardening)
- **Atomic Sliding-Window Counters:** Public API endpoints are protected by Redis sorted-set sliding-window rate limiters executed via atomic Lua scripts to prevent race conditions.
- **Fail-Closed Sensitive Endpoints:** Sensitive authentication routes (`/login`, `/forgot-password`, `/resend-verification`) fail closed if the Redis cluster is unreachable, preventing brute-force attacks during infrastructure degradation.
- **Bounded In-Memory Fallback:** General API routes employ an in-memory sliding-window fallback bounded to 10,000 keys with LRU eviction to prevent memory exhaustion (OOM).
- **Proxy-Aware IP Resolution:** Client IP evaluation traverses `X-Forwarded-For` headers from right-to-left, discarding untrusted proxy addresses and validating against configured CIDR proxy ranges with full IPv4 and IPv6 normalization.

### 3. Multi-Tenant Isolation & Access Control (RBAC)
- **Mandatory Tenant Context:** All tenant-scoped operations require and validate the `X-Organization-ID` context header.
- **SQL-Level Isolation:** Database queries enforce explicit organizational boundaries (`WHERE organization_id = :org_id`), preventing cross-tenant data leakage or horizontal IDOR vulnerabilities.
- **Role-Based Access Control:** Fine-grained permissions enforce least privilege across platform roles:
  - `OWNER`: Full organizational governance, membership management, billing, and audit access.
  - `ADMIN`: Operational management, user invitations, and trading controls.
  - `TRADER`: Order submission, strategy optimization, and paper portfolio execution.
  - `VIEWER`: Read-only access to portfolio statistics and performance tearsheets.
- **Sole Active Owner Protection:** Administrative logic strictly prohibits an organization's sole active owner from being deleted, deactivated, or demoted.

### 4. Credential & Data Encryption
- **AES-256-GCM Broker Key Encryption:** User-supplied API keys for broker sandbox integrations (such as OANDA practice credentials) are encrypted at rest using AES-256 in Galois/Counter Mode (GCM) with random 12-byte initialization vectors and 16-byte authentication tags. Keys are never logged and are decrypted only in memory when executing sandbox calls.
- **Transport Security:** All HTTP traffic is secured via modern TLS encryption.

### 5. Application & Infrastructure Hardening
- **HTTP Security Headers:** The web application reverse proxy enforces strict Content-Security-Policy (CSP), `X-Frame-Options: DENY` (anti-clickjacking), `X-Content-Type-Options: nosniff` (MIME sniffing mitigation), and `Referrer-Policy: strict-origin-when-cross-origin`.
- **SSRF Mitigation:** Internal network requests validate target URLs and IP ranges to prevent Server-Side Request Forgery.
- **Immutable Audit Logging:** Key administrative and tenant-level actions (including user invitations, role changes, billing events, and legal document acceptances) are permanently recorded in an append-only audit trail.

### 6. Vulnerability Reporting
If you discover a potential security vulnerability within Project ORION, please report it directly to platform security contacts for prompt triage and remediation.
