# Project ORION — EPIC-027 Phase 1 Auth Audit
# Current Authentication & Identity System Analysis

**Document Version:** 1.0.0
**Date:** 2026-09-22
**Milestone:** EPIC-027 (Phase 1 Auth Hardening)
**Author:** Quantitative Architecture & Security Auditor
**Repository:** `Project-ORION` (Branch: `main`)

---

## 1. Audit Findings & Answers to Mandatory Questions

### A. How Passwords Are Stored
- **Mechanism:** Bcrypt hashing with standard salt generation via Python `bcrypt` package (`bcrypt.gensalt()`, `bcrypt.hashpw()`).
- **Input Limit & Truncation:** Passwords are truncated safely to 72 bytes (`plain_password.encode("utf-8")[:72]`) to avoid runtime crashes from bcrypt's inherent 72-byte buffer limit.
- **Verification:** `bcrypt.checkpw(plain_bytes, hash_bytes)`.
- **Security Assessment:** Strong and compliant; plaintext is never stored or logged.

### B. How JWTs Are Generated
- **Library:** `python-jose` with cryptography backend (`jwt.encode`).
- **Algorithm:** Default `HS256` (`ORION_JWT_ALGORITHM`).
- **Payload Contents:** `{"sub": user.id, "username": user.username, "exp": expire}`.
- **Secret Key:** Loaded from `ORION_JWT_SECRET_KEY` with fallback to `DEFAULT_SECRET_KEY = "insecure-dev-secret-key-change-in-production-institutional-orion-2026"`.
- **Security Assessment:** Lacks fail-closed guard in production if default secret is unconfigured.

### C. JWT Expiration Behavior
- **TTL:** 30 minutes by default (`ORION_JWT_EXPIRE_MINUTES`).
- **Validation:** `decode_access_token()` verifies `exp` claim; expired tokens raise `JWTError`, resulting in `HTTP 401 Unauthorized` with `detail: "Invalid or expired token"`.
- **Revocation:** Access tokens are currently stateless. Password changes or deactivations rely on the database check in `get_current_user`. Adding `password_changed_at` / `token_version` timestamp validation in the JWT payload will ensure immediate token revocation upon password reset.

### D. Whether Refresh Tokens Already Exist
- **Status:** **DOES NOT EXIST**.
- No refresh token model, endpoint, storage, or rotation logic exists in the codebase.

### E. Whether Email Verification Exists Anywhere
- **Status:** **DOES NOT EXIST**.
- `UserModel` contains no `email_verified` column. No email token generation, persistence, or verification endpoints exist.

### F. Whether Password Reset Exists Anywhere
- **Status:** **DOES NOT EXIST**.
- No `/forgot-password`, `/reset-password`, reset token generator, or reset token model exists.

### G. Whether User Active/Deactivated Status Exists
- **Status:** **PARTIALLY EXISTS**.
- `UserModel.is_active` exists as a boolean (default `True`).
- `apps/trading-engine/src/routes/auth.py` checks `if not user.is_active: raise HTTPException(403, detail="User account is disabled")`.
- `apps/trading-engine/src/dependencies.py` checks `user.is_active` on every authenticated request and rejects disabled users.
- **Gaps:** No explicit status enum (`ACTIVE`, `DEACTIVATED`), no self-service or admin deactivation endpoint, no guard preventing the last owner of an organization from deactivating, and no audit trail on deactivation.

### H. Whether Organization Status Affects Authentication
- **Status:** **YES (Verified Complete)**.
- `require_active_organization` in `dependencies.py` checks `organization.status == OrganizationStatus.ACTIVE.value`. Suspended or deactivated organizations fail closed with HTTP 403 Forbidden.

### I. Whether Existing Audit Events Exist
- **Status:** **PARTIALLY EXISTS**.
- `AuditLogModel` exists and records tenant onboarding, order submissions, risk limit evaluations, and subscription events.
- **Gaps:** Auth-specific lifecycle events (`USER_REGISTERED`, `PASSWORD_RESET_REQUESTED`, `PASSWORD_RESET_COMPLETED`, `PASSWORD_CHANGED`, `EMAIL_VERIFIED`, `USER_DEACTIVATED`) are not currently recorded.

### J. Whether Frontend Auth State Survives Page Refresh
- **Status:** **YES**.
- Access token is stored in `sessionStorage` (`orion_access_token`).
- Upon page load, `AuthContext.refreshUser()` calls `GET /api/v1/auth/me`. If valid, user state is hydrated; if invalid/expired (HTTP 401), session is cleared and user is redirected to `/login`.

---

## 2. Identified Vulnerabilities & Technical Debt

1. **Insecure JWT Secret in Production:** `AppSettings.jwt_secret_key` and `auth.py` fallback to a static hardcoded development string if `ORION_JWT_SECRET_KEY` is unset.
2. **Missing Token Recovery Infrastructure:** Users who forget passwords have zero recourse other than direct database manipulation.
3. **Missing Token Table:** No database table exists to track time-limited, single-use security tokens (password reset, email verification).
4. **Missing Email Abstraction:** No infrastructure-neutral `EmailServicePort` exists to dispatch transactional messages cleanly across development, test, and production environments.
5. **No Owner Deactivation Protection:** An organization owner could hypothetically be deactivated or delete their account, leaving an orphaned tenant with running paper accounts and billing liabilities.

---

## 3. Architecture Action Plan for Phase 1

1. **Phase 1.1:** Guard `AppSettings` — fail closed on missing/default secret in production.
2. **Phase 1.2 & 1.7:** Add `auth_tokens` table via Alembic migration `0013_auth_and_account_hardening.py` and enhance `UserModel` with `status`, `email_verified`, `password_changed_at`.
3. **Phase 1.3:** Formalize password policy validation (min 8 chars, max 72 bytes, complexity check).
4. **Phase 1.4:** Implement `POST /api/v1/auth/forgot-password` and `POST /api/v1/auth/reset-password` with SHA-256 token hashing and anti-enumeration generic responses.
5. **Phase 1.5:** Implement `POST /api/v1/auth/verify-email` and `POST /api/v1/auth/resend-verification`.
6. **Phase 1.6:** Implement `EmailServicePort` with `MockEmailAdapter` for testing and `ConsoleEmailAdapter` for development.
7. **Phase 1.8:** Enforce JWT invalidation after password reset via `password_changed_at` check.
8. **Phase 1.9:** Harden registration in `OnboardingService` with transaction rollback.
9. **Phase 1.10:** Implement `POST /api/v1/auth/deactivate` with last-owner protection.
10. **Phase 1.11:** Record all 10 canonical auth audit events.
11. **Phase 1.12:** Add frontend pages: `ForgotPasswordPage.tsx`, `ResetPasswordPage.tsx`, `VerifyEmailPage.tsx`.
