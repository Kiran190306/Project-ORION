# Project ORION — Security Overview & Threat Model Audit

**Document Version:** 1.0.0<br>
**Target Milestone:** EPIC-027 Phase 7B Acquisition Due Diligence<br>
**Repository Working Copy:** `project-orion/`<br>
**Classification:** Confidential — Due Diligence Technical Data Room (Tier 2 / NDA)<br>
**Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Capital at Risk — Zero Live Broker Endpoints)

---

## 1. Executive Security Summary

Project ORION is engineered with a **defense-in-depth security architecture** designed to protect multi-tenant financial simulation data, user credentials, and operational execution pipelines.

### Core Security Posture
- **Paper-Only Isolation:** Financial safety is structurally guaranteed by restricting all order execution to internal simulated order books and practice sandboxes ($0.00 capital at risk). Live broker connections fail closed.
- **Credential Hygiene:** Passwords are protected using salted Bcrypt cryptographic hashing. Single-use tokens are hashed with SHA-256 before database storage. Raw secrets are never written to logs.
- **Tenant Isolation:** Multi-tenancy is enforced via row-level `organization_id` foreign keys and dependency-injected `TenantContext` validation, preventing Insecure Direct Object References (IDOR).
- **Anti-Enumeration Hardening:** Public authentication endpoints return identical generic responses on missing accounts or transport timeouts to mitigate user presence enumeration.

> [!NOTE]
> **COMPLIANCE & AUDIT DISCLAIMER:** Project ORION has been verified extensively via automated unit, integration, and security test suites in automated CI. The platform has not undergone formal third-party compliance audits (such as SOC 2 Type II or ISO 27001 certification) and has not engaged third-party external penetration testers. All security representations in this document reflect actual codebase implementations verifiable directly from repository source code.

---

## 2. Security Scope and Trust Boundaries

```
+─────────────────────────────────────────────────────────────────────────────+
|                         UNTRUSTED PUBLIC INTERNET                           |
|       External Clients  |  Web Browsers  |  Potential Attackers             |
+─────────────────────────────────────────────────────────────────────────────+
                                       │
                                       ▼ (HTTPS Ingress / Rate Limited)
+─────────────────────────────────────────────────────────────────────────────+
|                    APPLICATION TRUST BOUNDARY (FASTAPI)                     |
|  - RateLimitMiddleware (Redis sliding-window token bucket)                  |
|  - CORS Ingress Control (Exact origin whitelist)                            |
|  - JWT Signature Verification (HS256, 32+ char key)                         |
|  - TenantContext Dependency Injection & Role Enforcement                    |
+─────────────────────────────────────────────────────────────────────────────+
                                       │
                                       ▼ (Private Service Mesh)
+─────────────────────────────────────────────────────────────────────────────+
|                   INTERNAL DATA BOUNDARY (ZERO PUBLIC IP)                   |
|  - PostgreSQL 15 (Scoped SQL: WHERE organization_id = :org_id)              |
|  - Redis 7 (Protected cache keys, rate-limit counters)                      |
|  - PaperExecutionAdapter ($0 Capital Invariant)                             |
+─────────────────────────────────────────────────────────────────────────────+
```

---

## 3. Authentication Framework

- **Classification:** **A — IMPLEMENTED + TESTED** (`test_auth_lifecycle.py`)
- **Mechanism:** OAuth2 password flow issuing JSON Web Tokens (JWT).
- **Access Tokens:** Signed with HMAC-SHA256 (`HS256`). Contain user ID, username, superuser flag, issued-at timestamp (`iat`), and expiration timestamp (`exp`, default 30 minutes).
- **Session Management:** Stateless JWT access tokens. Sessions terminate upon token expiration or when invalidated by user password modification.
- **Secret Enforcement:** In production (`ORION_ENVIRONMENT=production`), the system raises a fatal `ConfigurationError` during startup if `ORION_JWT_SECRET_KEY` is missing, matches development defaults, or contains fewer than 32 characters.

---

## 4. Password Security & Storage

- **Classification:** **A — IMPLEMENTED + TESTED** (`test_auth_lifecycle.py`)
- **Hashing Algorithms:** Implemented directly via `bcrypt` (`bcrypt.gensalt()`, `bcrypt.hashpw()`, `bcrypt.checkpw()`).
- **Salt Generation:** Unique, cryptographically secure salts generated automatically per user password via `bcrypt.gensalt()`.
- **Complexity Policy:** Enforced during registration and password resets (`validate_password_strength`):
  - Minimum 8 characters (maximum 72 bytes due to bcrypt limitation).
  - At least one letter (`[a-zA-Z]`).
  - At least one numeric digit or symbol (non-alphanumeric).

---

## 5. JWT Lifecycle and Immediate Revocation

- **Classification:** **A — IMPLEMENTED + TESTED** (`test_auth_lifecycle.py`)
- **Vulnerability Mitigated:** Stolen or active JWTs remaining valid after password reset.
- **Implementation:**
  - The database records `users.password_changed_at` (timezone-aware UTC).
  - When decoding an access token, `decode_access_token()` compares the token's `iat` claim against the user's `password_changed_at` timestamp.
  - If `iat < password_changed_at`, the token is rejected immediately with HTTP 401 Unauthorized, revoking all active sessions across all devices upon password change.

---

## 6. Password Reset & Email Verification Token Lifecycle

- **Classification:** **A — IMPLEMENTED + TESTED** (`test_auth_lifecycle.py`)
- **Mechanism:**
  - Cryptographically secure 256-bit random tokens are generated via `secrets.token_urlsafe(32)`.
  - The raw token is transmitted to the user exclusively via outbound email URL parameter (`?token=...`).
  - The database stores only the SHA-256 digest (`hashlib.sha256(raw_token.encode()).hexdigest()`) in `auth_tokens`.
  - Database compromise does not expose usable reset or verification tokens.
- **Single-Use Replay Protection:** Upon successful verification or reset, the token record is deleted from `auth_tokens`. Replay attempts fail closed.
- **Expiration:** Verification tokens expire after 24 hours; password reset tokens expire after 15 minutes.

---

## 7. Anti-Enumeration Controls

- **Classification:** **A — IMPLEMENTED + TESTED** (`test_email_service.py`)
- **Vulnerability Mitigated:** Account existence enumeration via timing or response differences.
- **Implementation:**
  - Route `/api/v1/auth/forgot-password` always returns HTTP 200 with the generic response: `"If an account exists for this email, password reset instructions have been sent."`
  - Route `/api/v1/auth/resend-verification` always returns HTTP 200 with generic confirmation.
  - Failures in outbound SMTP network transport are caught inside route-level `try...except` blocks and logged internally with masked email addresses, ensuring that network timeouts or provider outages cannot leak user existence to an external caller.

---

## 8. Public API Rate Limiting

- **Classification:** **A — IMPLEMENTED + TESTED** (`test_security_audit.py`)
- **Engine:** Redis-backed sliding-window token bucket implemented via atomic Lua scripts.
- **Configured Tiers:**
  - Authentication Endpoints (`/api/v1/auth/login`, `/register`, `/forgot-password`): 5 requests per minute per IP.
  - Order Submission (`/api/v1/orders/`): 60 requests per minute per tenant.
  - Heavy Quantitative Endpoints (`/api/v1/optimization/run`): 5 requests per minute per tenant.
  - Standard REST Endpoints: 120 requests per minute per tenant.
- **Enforcement:** Exceeding thresholds returns HTTP 429 Too Many Requests with standard `Retry-After` headers.

---

## 9. Trusted Proxy & Client IP Handling

- **Classification:** **A — IMPLEMENTED + TESTED** (`test_security_audit.py`)
- **Vulnerability Mitigated:** Rate-limit bypass via forged `X-Forwarded-For` HTTP headers.
- **Implementation:**
  - Managed by `ClientIPResolver` (`apps/trading-engine/src/middleware/ip_resolver.py`).
  - Evaluates `X-Forwarded-For` only if the immediate connecting socket IP matches an address in `ORION_TRUSTED_PROXIES` (default `127.0.0.1,::1`).
  - Untrusted clients supplying forged headers have their actual network socket IP evaluated, preventing spoofing.

---

## 10. Authorization & Role-Based Access Control (RBAC)

- **Classification:** **A — IMPLEMENTED + TESTED** (`test_operational_readiness.py`)
- **Granular Permissions:** Exactly **41 granular permissions defined by the current RBAC permission model** in `libraries/domain/organization/permissions.py`.
- **Roles:** 7 organization roles (`OWNER`, `ADMINISTRATOR`, `PORTFOLIO_MANAGER`, `RISK_OFFICER`, `TRADER`, `AUDITOR`, `VIEWER`).
- **Enforcement:** Declared at route level via `@require_permission(Permission.<NAME>)`. Unauthorized attempts fail closed with HTTP 403 Forbidden.

---

## 11. Multi-Tenant Isolation & IDOR Defenses

- **Classification:** **A — IMPLEMENTED + TESTED** (`test_auth_lifecycle.py`, `test_phase4_onboarding.py`)
- **Mechanism:**
  - Shared-database / row-level logical partitioning.
  - All database queries for tenant entities (`accounts`, `orders`, `positions`, `trades`, `billing_customers`, `onboarding_progress`) automatically include `WHERE organization_id = :org_id`.
  - `TenantContext` is resolved cryptographically from JWT claims; arbitrary `organization_id` parameters in request bodies are ignored or validated against active memberships.
  - Attempting to access an entity belonging to another tenant returns HTTP 404 Not Found, preventing existence enumeration.

---

## 12. Broker Endpoint Safety & Sandbox Boundary

- **Classification:** **A — IMPLEMENTED + TESTED** (`test_broker_sandbox.py`)
- **Mechanism:**
  - `BrokerEndpointValidator` evaluates all outbound broker URLs.
  - Explicitly restricts broker endpoints to practice domains (e.g. `api-fxpractice.oanda.com`).
  - Any connection attempt containing live production broker hostnames (e.g. `api-fxtrade.oanda.com`) raises a fatal `BrokerConfigurationError` and aborts connection.

---

## 13. Paper-Only Financial Safety

- **Classification:** **A — IMPLEMENTED + TESTED** (`test_broker_sandbox.py`)
- **Invariant:** **Strictly $0.00 Capital at Risk.**
- **Enforcement:**
  - Order execution routes exclusively through `PaperExecutionAdapter` and `MockBrokerAdapter`.
  - Database accounts explicitly record `is_live=False` and `broker_name="paper"`.
  - Zero bank transfer, deposit, or withdrawal endpoints exist in the application.

---

## 14. Stripe Test-Mode Safety

- **Classification:** **A — IMPLEMENTED + TESTED** (`test_billing.py`)
- **Mechanism:**
  - `BillingConfig` strictly validates all supplied Stripe API keys.
  - If a live Stripe API key (with live-mode secret prefix) or live publishable key is supplied in configuration, `LiveCredentialsForbiddenError` is raised immediately, halting process startup.
  - Webhooks enforce raw byte HMAC-SHA256 signature verification with a 300-second clock-skew tolerance window.

---

## 15. Credential Encryption & Masking

- **Classification:** **A — IMPLEMENTED + TESTED** (`test_email_service.py`)
- **Memory & Logging Masking:**
  - `SmtpConfig.__repr__` masks passwords with `***`.
  - Outbound email logging masks user email addresses (e.g. `t***r@example.com`).
  - Database connection strings have user passwords stripped before structured logging.
- **Backup Encryption (Classification B):** `backup/database-backup.sh` supports AES-256-CBC encryption using OpenSSL (`-pbkdf2`) when `BACKUP_ENCRYPTION_KEY` is provided.

---

## 16. Audit Logging

- **Classification:** **A — IMPLEMENTED + TESTED** (`test_phase4_onboarding.py`)
- **Mechanism:** Immutable append-only audit trail in PostgreSQL table `audit_logs`.
- **Recorded Events:** User registration, login failures, password changes, organization role updates, subscription status transitions, and paper order dispatches.

---

## 17. HTTP Security Headers & CORS

- **Classification:** **A — IMPLEMENTED + TESTED** (`test_operational_readiness.py`)
- **CORS Ingress Control:** Strict origin whitelist parsed via `ORION_CORS_ORIGINS`. Wildcard origins (`*`) are prohibited when credentials (`allow_credentials=True`) are enabled.
- **Security Headers:** The Nginx reverse proxy injects defensive HTTP headers:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`

---

## 18. Container Security

- **Classification:** **A — IMPLEMENTED + TESTED** (`docker/apps/trading-engine/Dockerfile`)
- **Non-Root Execution:** API container creates and switches to unprivileged user `orion` (`uid=999`).
- **Minimal Surface:** Production images use minimal base images (`python:3.11-slim`, `nginx:1.27-alpine-slim`). Build compilers (`gcc`, `g++`) are discarded in multi-stage builds.

---

## 19. Backup & Restore Security

- **Classification:** **A — IMPLEMENTED + TESTED** (`docs/EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md`)
- **Integrity Validation:** Backups generate cryptographic SHA-256 checksum sidecars verified before restore execution.
- **Destructive Command Ban:** `backup/restore-database.sh` explicitly forbids `DROP DATABASE` and `CREATE DATABASE` commands.
- **Demonstrated Physical Restore Duration:** **7 seconds** on isolated test container (within <60-minute operational RTO target; documented operational RPO target is <24 hours).

---

## 20. Security Testing Evidence Summary

The automated security test suite comprises dedicated regression test modules:

| Test Module | Domain Tested | Test Count | Pass Rate | Evidence Commit |
|---|---|:---:|:---:|:---:|
| `test_auth_lifecycle.py` | Auth, Password Policy, Token Hashing, Revocation | 18 | **100%** | `e075004` |
| `test_email_service.py` | Anti-Enumeration, SMTP Safety, Password Masking | 21 | **100%** | `e075004` |
| `test_security_audit.py` | Rate Limiting, Proxy IP Spoofing, Headers | 14 | **100%** | `e075004` |
| `test_billing.py` | Stripe Key Rejection, Webhook Signatures | 17 | **100%** | `e075004` |
| `test_broker_sandbox.py` | Broker Endpoint Validator, Live Rejection | 12 | **100%** | `e075004` |

---

## 21. External Verification Requirements

The following controls require external accounts/credentials for live validation:
1. Real Stripe webhook events from `api.stripe.com` to test public internet HMAC timing.
2. Real OANDA practice token over public internet TLS to verify broker certificate chains.
3. Live outbound SMTP delivery over port 587 STARTTLS to verify external relay handshakes.
4. Production S3 backup upload using AWS IAM access keys.

---

## 22. Known Security Limitations

1. **Static JWT Secrets:** Secret rotation requires application restart; dynamic secret leasing via Vault is not implemented.
2. **Single Redis Instance:** Rate limiting state is bound to a single Redis instance; failover requires manual intervention.
3. **Absence of Formal Audits:** No third-party SOC 2 or penetration testing certifications exist.

---

## 23. Security Due-Diligence Checklist

- [x] Passwords hashed with salted Bcrypt algorithm.
- [x] Zero plain-text secrets in repository or Git history.
- [x] Strict JWT expiration and immediate revocation on password change.
- [x] Reset tokens hashed in database (SHA-256).
- [x] Anti-enumeration defenses on public authentication routes.
- [x] Multi-tenant isolation verified via automated IDOR tests.
- [x] Granular RBAC enforcing 41 granular permissions defined by the current RBAC permission model.
- [x] Live broker endpoints structurally rejected.
- [x] Live Stripe credentials structurally rejected.
- [x] Docker containers execute as unprivileged non-root users.
- [x] Database migrations execute within atomic transactions.
- [x] Physical database restore verified (7 seconds demonstrated duration within <60-minute operational RTO target).
