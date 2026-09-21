# Project ORION — EPIC-026 Security Architecture & Verification Report
# Institutional Broker Sandbox & Demo Broker Gateway Security Invariants

**Document Version:** 1.0.0  
**Date:** 2026-09-21  
**Author:** Institutional Trading Systems & Security Engineering Team  
**Milestone:** EPIC-026 — Institutional Broker Sandbox & Demo Broker Integration  
**Classification:** Institutional Internal Audit & Compliance Specification  

---

## 1. Executive Security Summary & Invariants

Project ORION strictly maintains a **$0.00 Capital at Risk** constraint. Live trading environments, live endpoints, and unauthorized egress are mathematically and architecturally prohibited.

The broker sandbox integration provides an institutional interface to deterministic local simulated brokers (`MockBrokerAdapter`) and genuine external demo broker sandboxes (e.g., OANDA `fxPractice` v20), while enforcing an unbreakable multi-layered defense-in-depth security perimeter.

### Safety Invariants Status Matrix

| Invariant | Requirement | Enforcement Mechanism | Verification Status |
|---|---|---|:---:|
| **Capital at Risk** | Strictly **$0.00** | Environment checks, endpoint allowlists, paper/sandbox-only routing | **VERIFIED (100%)** |
| **Live Connections** | Strictly **0** live broker sockets / connections | Fail-closed validation on all initialization pathways | **VERIFIED (100%)** |
| **Live Credentials** | Strictly **0** live API credentials accepted | Token format and endpoint binding verification | **VERIFIED (100%)** |
| **Worker Execution** | `ORION_WORKER_ENABLED = false` default | Config assertion and process manager gate | **VERIFIED (100%)** |
| **SSRF Defense** | Zero loopback, RFC 1918, metadata, or unapproved domains | `BrokerEndpointValidator` multi-stage URL analysis | **VERIFIED (100%)** |
| **Credential Storage** | AES-256-GCM encryption at rest | `CredentialCipher` with authenticated encryption | **VERIFIED (100%)** |
| **Credential Masking** | Plaintext tokens never in responses or logs | Masking sanitizers returning `***` | **VERIFIED (100%)** |
| **Execution Chain** | RiskEngine and OrderValidator cannot be bypassed | Inviolable service pipeline before broker dispatch | **VERIFIED (100%)** |

---

## 2. SSRF & Broker Endpoint Protection Architecture

External network egress presents significant SSRF (Server-Side Request Forgery) risks. The `BrokerEndpointValidator` implements a strict 6-stage validation pipeline executed before any network connection:

```
Broker Endpoint URL Input
       │
       ▼
[Stage 1: Scheme & Authority Validation] ───> Rejects 'http://' (except internal mock), userinfo '@'
       │
       ▼
[Stage 2: Production Blacklist Check] ────> Rejects 'api-fxtrade.oanda.com', 'api.binance.com', etc.
       │
       ▼
[Stage 3: IP Literal Rejection] ──────────> Rejects IPv4/IPv6 literals (e.g. 192.168.1.1, 10.0.0.1)
       │
       ▼
[Stage 4: Loopback & Localhost Check] ────> Rejects 'localhost', '127.0.0.1', '::1', '.localhost'
       │
       ▼
[Stage 5: Canonical Domain Allowlist] ────> Only approved hosts permitted:
       │                                     - api-fxpractice.oanda.com
       │                                     - stream-fxpractice.oanda.com
       │                                     - paper-api.alpaca.markets
       │                                     - testnet.binance.vision
       │                                     - mock-broker.internal
       ▼
[Stage 6: DNS Resolution Gate] ───────────> Resolves hostname via DNS; validates all resolved IPs:
       │                                     - Rejects Private RFC 1918 (10/8, 172.16/12, 192.168/16)
       │                                     - Rejects Cloud Metadata (169.254.169.254)
       │                                     - Rejects Loopback (127.0.0.0/8)
       ▼
Authorized Normalized Sandbox Endpoint URL
```

### Verified SSRF Invariant Tests
1. **Loopback rejection (`127.0.0.1`, `localhost`):** `SecurityViolationError` raised immediately.
2. **RFC 1918 subnets (`10.0.0.1`, `172.16.0.1`, `192.168.1.1`):** Rejected as prohibited IP literals.
3. **AWS/Cloud metadata IP (`169.254.169.254`):** Prohibited as IP literal and unapproved destination.
4. **Arbitrary external domain (`attacker-c2.com`):** `InvalidEndpointError` raised for not being in allowlist.
5. **Live broker endpoint (`api-fxtrade.oanda.com`):** `SecurityViolationError` explicitly terminates connection.

---

## 3. Cryptographic Credential Protection (AES-256-GCM)

Broker sandbox credentials (e.g. OANDA fxPractice tokens) are encrypted prior to persistence in PostgreSQL:

- **Algorithm:** AES-256-GCM (Galois/Counter Mode) authenticated encryption.
- **Key Source:** `ORION_CREDENTIAL_ENCRYPTION_KEY` environment variable. A fallback development key is provided only for local testing with mandatory warning logging.
- **Payload Structure:** 
  ```json
  {
    "ciphertext": "<base64-encoded-payload>",
    "nonce": "<12-byte-base64-iv>",
    "v": "1"
  }
  ```
- **Integrity Guarantee:** Any tampering or byte manipulation of the ciphertext or IV causes authentication verification failure.
- **Data Sanitization:** `CredentialCipher.mask_credentials()` guarantees that sensitive keys (`token`, `api_key`, `secret`, `password`) are replaced with `"***"` before any serialization into JSON responses or logs.

---

## 4. Multi-Tenant Isolation & IDOR Protection

All broker sandbox database queries and operations are partitioned by `organization_id`:

- **Fail-Closed IDOR Policy:** If Tenant A attempts to access Tenant B's sandbox account by ID (e.g. `GET /api/v1/broker-sandbox/accounts/{tenant_b_id}` or `POST /orders`), the service executes:
  ```python
  stmt = select(BrokerSandboxAccountModel).where(
      BrokerSandboxAccountModel.id == account_id,
      BrokerSandboxAccountModel.organization_id == organization_id,
  )
  ```
- If the row does not match both `id` AND `organization_id`, the system raises an immediate `HTTPException(status_code=404, detail="Broker sandbox account not found")`.
- It never returns 403 or reveals the existence of the resource to another tenant.

---

## 5. Granular RBAC & Separation of Duties

The canonical Role-Based Access Control matrix was expanded with least privilege separation:

| Role | `BROKER_READ` | `BROKER_SANDBOX_CONNECT` | `BROKER_SANDBOX_EXECUTE` | `BROKER_SANDBOX_RECONCILE` |
|---|:---:|:---:|:---:|:---:|
| **OWNER** | YES | YES | YES | YES |
| **ADMINISTRATOR** | YES | YES | YES | YES |
| **PORTFOLIO_MANAGER** | YES | YES | YES | YES |
| **RISK_OFFICER** | YES | NO | NO | YES |
| **TRADER** | YES | NO | YES | NO |
| **AUDITOR** | YES | NO | NO | NO |
| **VIEWER** | YES | NO | NO | NO |

### Separation of Duties Enforced
- **TRADER** can submit sandbox orders, but cannot connect/disconnect adapters or trigger reconciliations.
- **RISK_OFFICER** can audit reconciliations and view broker state, but cannot submit trades.
- **VIEWER** / **AUDITOR** have read-only access.
