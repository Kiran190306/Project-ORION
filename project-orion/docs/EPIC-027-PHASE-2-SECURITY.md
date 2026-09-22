# EPIC-027 Phase 2 — Security & Abuse Defense Specification

**Project**: Project ORION
**Milestone**: EPIC-027 (Public Beta & Commercial Launch Readiness)
**Phase**: Phase 2 — Public API Rate Limiting & Abuse Defense
**Classification**: High-Assurance Defense Architecture
**Capital at Risk**: $0.00 (Strictly Paper-Trading / Simulation Mode)

---

## 1. Network Boundary Security & Client IP Resolution

### 1.1 The Threat Model
Attackers frequently forge the HTTP `X-Forwarded-For` header to bypass IP-based rate limiting or poison audit trails. In distributed multi-proxy cloud deployments (e.g. Render, Cloudflare, AWS ALB), trusting arbitrary inbound headers allows attackers to reset their rate limit counters by supplying fake client IP headers on each request.

### 1.2 Trusted Proxy Resolution Algorithm (`ClientIpResolver`)
Project ORION implements strict **Trusted Proxy Traversal** conforming to RFC-7239:
1. **Direct Socket Inspection**: The direct socket address (`request.client.host`) is inspected first.
2. **Untrusted Caller Defense**: If the direct caller's socket IP is **not** in the configured `trusted_proxies` list, all `X-Forwarded-For` headers are **completely ignored**. The socket IP is returned.
3. **Right-to-Left Traversal**: If the direct caller is a verified trusted proxy, the `X-Forwarded-For` chain (`client, proxy1, proxy2`) is evaluated from right to left. The first untrusted IP encountered is returned as the legitimate client IP.
4. **IP Sanitization & Normalization**: All resolved IPs are normalized and validated via Python's standard `ipaddress` module. Zone indices (`fe80::1%eth0`) and malformed strings are stripped, falling back safely to the socket IP.
5. **CIDR Support**: Proxies can be configured as individual IPs (`127.0.0.1`, `::1`) or full CIDR subnets (`10.0.0.0/8`, `172.16.0.0/12`).

```
[Attacker: 198.51.100.10] ──> [Direct Request with Header XFF: "spoofed.ip"]
                             │
                             ▼
               Is 198.51.100.10 trusted? ──> NO ──> IGNORE Header, Client IP = 198.51.100.10

[Attacker: 198.51.100.42] ──> [Trusted Proxy: 10.0.0.1] ──> [Reverse Proxy: 127.0.0.1] ──> [ORION]
                                                           │
                                                           ▼
                             Traverse right-to-left: 127.0.0.1 (trusted) -> 10.0.0.1 (trusted) -> 198.51.100.42 (UNTRUSTED)
                             Client IP = 198.51.100.42
```

---

## 2. Anti-Enumeration Preservation

Rate limiting must never weaken anti-enumeration protections established in Phase 1:
- **Authentication**: Non-existent usernames and incorrect passwords return identical generic `401 Unauthorized` responses until the IP quota is exhausted. Once exhausted, both return identical `429 Too Many Requests` responses. Attackers cannot distinguish registered accounts from unregistered accounts.
- **Password Reset (`/forgot-password`)**: Valid and invalid emails return identical success envelopes (`{"message": "If this email is registered, password reset instructions have been sent."}`). Both consume rate limit tokens identically.
- **Email Verification (`/resend-verification`)**: Follows identical anti-enumeration logic.

---

## 3. Denial-of-Service & Resource Exhaustion Defense

### 3.1 Redis Sliding Window Atomic Counter
- Employs Redis sorted sets with an atomic Lua script (`ZREMRANGEBYSCORE`, `ZCARD`, `ZADD`, `PEXPIRE`).
- Eliminates race conditions under massive concurrency.
- Keys expire automatically via `PEXPIRE`, preventing Redis memory leaks.

### 3.2 In-Memory Fallback Bounding & OOM Defense
- Bounded to `max_keys=10000`.
- Implements active LRU eviction via `OrderedDict.popitem(last=False)`.
- Prevents memory-exhaustion attacks during Redis network partitions.

### 3.3 Key Hierarchy Collision Defense
- Redis keys are formatted with clear semantic prefixes: `rl:v1:{policy}:{scope_key}`.
- IPv6 addresses have colons replaced with underscores (`2001:db8::1` -> `2001_db8__1`) to prevent accidental Redis key delimiter collisions.

---

## 4. Multi-Tenant Separation & Entitlement Boundaries

Rate limiting and subscription entitlement quotas operate independently:
1. **Rate Limiting Layer (Security Perimeter)**:
   - Evaluated at the HTTP boundary via FastAPI dependencies before expensive domain handlers execute.
   - Throttles burst requests (e.g. 60 orders/minute).
2. **Entitlement Layer (Commercial Policy)**:
   - Evaluated by `EntitlementService` during domain execution.
   - Enforces tier-based monthly/daily business quotas (e.g. Free Tier: 50 orders/day, Pro Tier: 1,000 orders/day).
   - Rate limits protect system capacity; entitlements enforce commercial contracts.

---

## 5. Non-Negotiable Safety Invariants

- **Capital at Risk**: Always **\$0.00**.
- **Live Trading Execution**: Strictly **disabled**.
- **Live Broker Connections**: **0** (Zero).
- **Live Broker Credentials**: **None**.
- **Autonomous Worker**: Strictly **disabled**.
- **Execution Mode**: **Paper-trading / Simulation only**.
