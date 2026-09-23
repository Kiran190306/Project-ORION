# Project ORION — Domain & DNS Transfer Checklist

**Document Version:** 1.0.0
**Target Milestone:** EPIC-027 Phase 7B Acquisition Due Diligence
**Repository Working Copy:** `project-orion/`
**Classification:** Confidential — Due Diligence Technical Data Room (Tier 3 / Closing)
**Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Capital at Risk — Zero Live Broker Endpoints)

---

## 1. Executive Summary & Domain Status

This document details the domain landscape, DNS routing architecture, SSL/TLS certificate automation, and domain handover procedures for **Project ORION**.

### Current Operational Reality
Project ORION's production cloud services currently execute on **Render-managed default subdomains**:
- **Production API:** `https://orion-api-68u2.onrender.com`
- **Production Dashboard:** `https://orion-dashboard-6d3z.onrender.com`

Render automatically provisions, terminates, and renews TLS 1.3 certificates via Let's Encrypt for all `*.onrender.com` hostnames.

### Status of Custom Domains Referenced in Repository
During the repository audit (`docs/acquisition/7B-4-AUDIT.md`), three custom domain references were cataloged:
1. `oriontrading.io`: Referenced as a default configuration template in `libraries/infrastructure/communication/email_service.py` (`from_email = "notifications@oriontrading.io"`).
2. `project-orion.dev`: Referenced in legacy EPIC-016 architectural design documents.
3. `orion.example.com`: Referenced as an illustrative template in Kubernetes Helm charts and Kustomize overlays.

> [!IMPORTANT]
> **LEGAL & FACTUAL DISCLAIMER ON DOMAIN OWNERSHIP:**
> The repository codebase contains **zero proof of domain registration, zero registrar account credentials, zero DNS zone files, and zero private TLS certificates** for `oriontrading.io` or `project-orion.dev`. The presence of domain strings in code or documentation does **NOT** establish that the seller owns, has registered, or is capable of transferring legal title to these domain names.
>
> If the seller owns `oriontrading.io`, domain transfer must be verified via independent registrar records outside this repository. If the seller does not own the domain, it serves strictly as an illustrative template, and the buyer must provision their own commercial domain.

---

## 2. Domain & DNS Inventory Matrix

| Domain / Hostname | Classification | Current Repository Role | Infrastructure Provider | Ownership Status |
|---|---|---|---|---|
| `orion-api-68u2.onrender.com` | Deployed Active Subdomain | Production REST API Gateway | Render Cloud PaaS | Provided by Render runtime; bound to Render service |
| `orion-dashboard-6d3z.onrender.com` | Deployed Active Subdomain | Production Frontend SPA | Render Cloud PaaS | Provided by Render runtime; bound to Render service |
| `oriontrading.io` | Configuration Template | Default sender email template | Unverified | **NOT ESTABLISHED IN REPOSITORY** (Requires seller verification) |
| `project-orion.dev` | Legacy Design Template | EPIC-016 architecture planning | Unverified | **NOT ESTABLISHED IN REPOSITORY** (Historical documentation reference) |
| `orion.example.com` | Example / Mock Domain | Helm & Kustomize examples | Non-operational | Synthetic example domain for Kubernetes manifests |

---

## 3. Domain Registrar Transfer Protocol (If Domain is Seller-Owned)

If independent verification confirms that the seller owns `oriontrading.io` and intends to transfer it to the buyer, the following standard ICANN registrar transfer sequence applies:

```
[Phase 1: Seller Registrar Actions]
 1. Log in to current registrar console (e.g., Namecheap, Cloudflare, GoDaddy, Route53).
 2. Verify WHOIS administrative contact email address is accessible.
 3. Disable Registrar Transfer Lock ("ClientTransferProhibited" status).
 4. Request Authorization / EPP Transfer Code.
 5. Securely transmit EPP Code to buyer via encrypted channel.

[Phase 2: Buyer Registrar Actions]
 6. Log in to buyer's preferred corporate domain registrar.
 7. Initiate "Inbound Domain Transfer" for oriontrading.io.
 8. Enter the EPP Authorization Code.
 9. Confirm administrative contact email and submit payment for transfer/renewal.

[Phase 3: Registry & ICANN Confirmation]
 10. Seller approves automated transfer authorization email from registrar.
 11. Registry completes transfer (typical duration: 1 to 5 calendar days).
 12. Buyer re-enables Registrar Transfer Lock and configures corporate DNS nameservers.
```

---

## 4. Prospective DNS Configuration Checklist (Hypothetical Target Templates)

> **NOTICE ON DNS RECORDS:** The resource records listed below are illustrative target configuration templates for the buyer's DNS registrar. They do NOT represent existing active records in external DNS zones.

Whether using an existing transferred domain or a brand-new corporate domain (e.g. `buyer-trading.com`), the buyer must configure the following standard DNS resource records:

### 4.1 Web & API Routing Records (Render PaaS Mapping)

| Record Name / Subdomain | Type | Target / Value | TTL | Purpose |
|---|:---:|---|:---:|---|
| `api.<domain>` | `CNAME` | `orion-api.onrender.com` (or buyer's Render slug) | 300s | Routes REST API traffic to Render Trading Engine |
| `app.<domain>` | `CNAME` | `orion-dashboard.onrender.com` (or buyer's Render slug) | 300s | Routes web application traffic to Render SPA Dashboard |
| `<domain>` (Apex / Root) | `ALIAS` / `ANAME` | `orion-dashboard.onrender.com` | 300s | Optional: Apex domain forwarding to dashboard |

*Note: In the Render dashboard, navigate to **Custom Domains -> Add Custom Domain**, enter `api.<domain>` and `app.<domain>`, and click "Verify". Render automatically verifies the CNAME records and provisions Let's Encrypt certificates.*

---

### 4.2 Transactional Email Authentication Records

To ensure 100% inbox delivery and protect against domain spoofing and phishing, configure the following DNS records for the sending domain (e.g. `<domain>`):

#### 1. SPF (Sender Policy Framework)
- **Type:** `TXT`
- **Host:** `@` (Apex)
- **Target / Value:**
  ```text
  v=spf1 include:<smtp-provider-spf-domain> ~all
  ```
  *(Example for SendGrid: `v=spf1 include:sendgrid.net ~all`; example for Mailgun: `v=spf1 include:mailgun.org ~all`)*

#### 2. DKIM (DomainKeys Identified Mail)
- **Type:** `CNAME` (or `TXT`)
- **Host:** `<selector>._domainkey.<domain>`
- **Target / Value:** Value provided by the buyer's transactional email provider console.
- **Purpose:** Cryptographically signs outbound verification and password-reset emails.

#### 3. DMARC (Domain-based Message Authentication, Reporting & Conformance)
- **Type:** `TXT`
- **Host:** `_dmarc.<domain>`
- **Target / Value:**
  ```text
  v=DMARC1; p=quarantine; pct=100; rua=mailto:dmarc-reports@<domain>; aspf=r;
  ```
- **Purpose:** Instructs receiving mail exchangers to quarantine unauthenticated messages claiming to originate from the domain.

---

### 4.3 SSL/TLS & Certificate Authority Records

#### CAA (Certification Authority Authorization)
- **Type:** `CAA`
- **Host:** `@` (Apex)
- **Target / Value:**
  ```text
  0 issue "letsencrypt.org"
  ```
- **Purpose:** Explicitly authorizes Let's Encrypt to issue TLS certificates for Render custom domains, preventing unauthorized certificate generation.

---

## 5. Environment Variable Configuration for Custom Domains

Once DNS records are active and Render custom domains are verified, update the following environment variables across the platform:

### 5.1 Trading Engine Backend Configuration (Render PaaS)

| Environment Variable | New Value for Custom Domain | Location in Source Code |
|---|---|---|
| `ORION_CORS_ORIGINS` | `https://app.<domain>,https://<domain>` | `apps/trading-engine/src/config.py` |
| `ORION_FRONTEND_URL` | `https://app.<domain>` | `libraries/infrastructure/communication/email_service.py` |
| `ORION_SMTP_FROM_EMAIL` | `notifications@<domain>` | `libraries/infrastructure/communication/email_service.py` |
| `ORION_SMTP_FROM_NAME` | `"Project ORION"` (or buyer brand) | `libraries/infrastructure/communication/email_service.py` |

### 5.2 Dashboard Frontend Configuration (Build Environment)

| Environment Variable | New Value for Custom Domain | Location in Source Code |
|---|---|---|
| `VITE_API_URL` | `https://api.<domain>` (or `""` if reverse proxied) | `apps/dashboard/src/api/client.ts`, `render.yaml` |

---

## 6. Zero-Downtime Domain Cutover & Migration Plan

```
[Phase 1: Pre-Cutover Preparation (T - 48 Hours)]
 1. Buyer provisions and verifies custom domain in Render console.
 2. Add DNS CNAME records with low TTL (300 seconds).
 3. Wait for Render to issue Let's Encrypt SSL/TLS certificates.
 4. Verify SSL handshake: curl -vI https://api.<domain>/health/live.

[Phase 2: Environment Variable Updates (T - 2 Hours)]
 5. Update backend ORION_CORS_ORIGINS to include https://app.<domain>.
 6. Update backend ORION_FRONTEND_URL to https://app.<domain>.
 7. Update frontend build parameter VITE_API_URL=https://api.<domain>.
 8. Trigger redeployment of API and Dashboard in Render.

[Phase 3: Live Verification & Testing (T - 0)]
 9. Test API liveness via custom domain: GET https://api.<domain>/health/live.
 10. Test API readiness via custom domain: GET https://api.<domain>/health/ready.
 11. Test Dashboard UI load via custom domain: https://app.<domain>.
 12. Test end-to-end authentication: Log in and verify CORS preflight (OPTIONS 200).
 13. Test transactional email: Trigger password reset; verify link points to https://app.<domain>.

[Phase 4: Post-Cutover Hardening (T + 24 Hours)]
 14. Increase DNS TTL from 300s to 3600s for cache stability.
 15. Verify DMARC reports for proper SPF/DKIM alignment.
 16. Monitor Prometheus metrics endpoint for CORS or network anomalies.
```

---

## 7. Rollback & Contingency Plan

If unexpected DNS propagation failures, SSL certificate issuance errors, or CORS preflight rejections occur during cutover:

1. **Immediate Fallback to Render Subdomains:**
   - The default Render hostnames (`https://orion-api-68u2.onrender.com` and `https://orion-dashboard-6d3z.onrender.com`) remain active simultaneously during custom domain testing.
   - Revert `ORION_CORS_ORIGINS` to include the default Render dashboard URL.
   - Revert `VITE_API_URL` to point back to the default Render API URL.
2. **Trigger Rapid Redeploy:**
   - In Render dashboard, click **Manual Deploy -> Clear Build Cache & Deploy**.
   - Service restores operational baseline within 90 seconds.
3. **Debug Offline:**
   - Troubleshoot DNS propagation using `dig +trace CNAME api.<domain>`.
   - Verify Let's Encrypt challenge response before re-attempting cutover.

---

## 8. Buyer-Owned New-Domain Alternative

If `oriontrading.io` is unavailable or not owned by the seller, the buyer has complete architectural freedom:
- The Project ORION codebase has **zero hardcoded domain couplings** in binary assets.
- All domain references are strictly Twelve-Factor externalized.
- The buyer may choose any commercial domain (e.g. `quanttrade.ai`, `institutional-orion.com`, `apexforex.io`) and execute the identical DNS setup in Section 4.
