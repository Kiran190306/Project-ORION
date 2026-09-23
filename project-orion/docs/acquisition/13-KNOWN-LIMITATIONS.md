# Project ORION — Known Limitations & Technical Risk Register

**Document Version:** 1.0.0<br>
**Target Milestone:** EPIC-027 Phase 7B Acquisition Due Diligence<br>
**Repository Working Copy:** `project-orion/`<br>
**Classification:** Confidential — Due Diligence Technical Data Room (Tier 2 / NDA)<br>
**Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Capital at Risk — Zero Live Broker Endpoints)

---

## 1. Due-Diligence Notice & Purpose

This document provides a comprehensive, transparent register of all known architectural, functional, infrastructure, and operational limitations in **Project ORION**, prepared specifically for technical due-diligence teams evaluating an outright software asset sale.

To ensure transparent buyer evaluation, each limitation is categorized with its current state, operational impact, available mitigation or workaround, external dependencies, and repository evidence.

---

## 2. Master Limitations Register

| # | Limitation Title | Current State in Repository | Operational Impact | Mitigation / Recommended Workaround | Source / Evidence |
|---|---|---|---|---|---|
| **1** | **Paper-Only Execution** | All trade routing and order matching executes strictly via internal simulated order books. | The platform cannot execute real-money trades against live liquidity pools. | By design ($0.00 capital at risk). Live broker execution requires implementing and testing live broker adapters. | `paper_execution.py`, `models.py` |
| **2** | **OANDA Practice Sandbox Boundary** | Outbound broker integration is restricted to official OANDA v20 practice endpoints (`api-fxpractice.oanda.com`). | Live execution through OANDA is structurally blocked; live endpoint configurations fail closed. | Connects to practice accounts for demo order validation. Live execution requires updating the broker validator. | `oanda_adapter.py`, `test_broker_sandbox.py` |
| **3** | **Stripe Test Mode Enforcement** | Billing configuration validates API keys and raises `LiveCredentialsForbiddenError` if live keys are supplied. | Live payment transactions cannot be processed by the default billing configuration. | Designed to prevent accidental charges during testing. Enabling live billing requires updating `BillingConfig`. | `libraries/infrastructure/billing/config.py` |
| **4** | **Transactional SMTP Dependency** | Outbound transactional email delivery (`SMTPEmailAdapter`) relies on standard RFC 5321 SMTP transport. | Password reset and email verification require an active SMTP relay server. | The buyer must provision an external transactional email provider (SendGrid, Postmark, AWS SES). | `email_service.py`, `render.yaml` |
| **5** | **Render Paid Plan Dependency** | `render.yaml` specifies `starter` web service tier and `basic-1gb` PostgreSQL tier. | The Render blueprint cannot be deployed on Render's free tier because `preDeployCommand` requires a paid plan. | The buyer must maintain an active credit card on the deploying Render account. | `render.yaml`, Render PaaS Documentation |
| **6** | **Custom Domain & DNS Delegation** | The default deployment operates on Render subdomains (`*.onrender.com`). | Production custom domains (e.g. `api.domain.com`, `app.domain.com`) are not pre-configured. | The buyer must configure DNS CNAME/ALIAS records with their DNS registrar. | `render.yaml`, `05-DEPLOYMENT-HANDOVER.md` |
| **7** | **Autonomous Strategy Worker Gated** | The background trading loop is disabled by default (`ORION_WORKER_ENABLED: "false"`). | The engine acts solely as an ASGI API server until the worker is explicitly enabled. | Gated intentionally for deployment safety. Operators can activate the worker via environment settings. | `apps/trading-engine/src/config.py` |
| **8** | **Single-Worker Process Architecture** | The strategy worker runs as an in-process asynchronous task within the ASGI process. | High strategy counts cannot be distributed across a worker cluster. | Suitable for low-to-medium strategy volumes. Scale horizontally via distributed queues (Celery/Temporal). | `apps/trading-engine/src/worker.py` |
| **9** | **Single-Region Cloud Deployment** | The Render blueprint provisions resources within a single cloud region. | A major regional cloud outage will cause downtime until the service is restored. | Manual regional redeployment via Render Dashboard. Geo-redundancy requires active-active database clustering. | `render.yaml`, `14-INFRASTRUCTURE-TOPOLOGY-MAP.md` |
| **10** | **Absence of Penetration Testing** | The repository contains extensive internal security test suites but no external penetration test audit. | No formal third-party attestation of application security or ethical hacking audit. | The buyer should commission an independent third-party penetration test prior to high-volume public launch. | `07-SECURITY-OVERVIEW.md` |
| **11** | **Absence of Compliance Certifications** | The platform holds zero formal regulatory or compliance certifications (SOC 2, ISO 27001, PCI-DSS). | The platform cannot market formal compliance attestations to enterprise buyers. | Standard for early-stage software assets. The buyer must pursue formal audit processes if required. | `07-SECURITY-OVERVIEW.md` |
| **12** | **Offsite Backup Storage Dependency** | Backup scripts (`backup/database-backup.sh`) write to local or mounted filesystem paths. | Physical hardware destruction of the local backup host risks backup archive loss. | The buyer must implement an external wrapper or cron job (e.g. `aws s3 sync`) to copy dumps offsite. | `backup/database-backup.sh` |
| **13** | **Redis High Availability Limitation** | Redis is provisioned as a standalone single-node instance without Sentinel or Cluster failover. | A Redis crash temporarily degrades rate limiting and session caching until restarted. | Redis data is ephemeral and reconstructable. Critical relational state resides safely in PostgreSQL. | `render.yaml`, `backup/redis-backup.sh` |
| **14** | **External Alerting Integration** | Platform exposes Prometheus metrics at `/metrics` but contains no built-in PagerDuty or Opsgenie webhooks. | Automated operational alerts require an external scraping server. | The buyer must configure an external Prometheus server and Alertmanager/PagerDuty alerting rules. | `apps/trading-engine/src/routes/metrics.py` |
| **15** | **Static JWT Secret Key Rotation** | Rotating `ORION_JWT_SECRET_KEY` invalidates the signature of all active access tokens. | Users must re-authenticate across all devices whenever the signing key is rotated. | Acceptable trade-off for stateless auth. Implement key versioning (kid) or dynamic secret leasing via Vault. | `apps/trading-engine/src/services/auth.py` |
| **16** | **Stateless JWT Session Management** | The platform does not implement server-side refresh token rotation or granular token blacklists. | Stolen access tokens remain valid until expiration (30m) or until user changes password. | Mitigation provided by `password_changed_at` revocation check and short token expiration window. | `apps/trading-engine/src/services/auth.py` |
| **17** | **Market Data Provider Subscription** | Live and historical market data ingestion requires a valid TwelveData subscription API key. | Without a valid TwelveData key, the platform falls back to offline synthetic Brownian motion quotes. | The buyer must provision and fund a TwelveData API account. | `apps/trading-engine/src/config.py` |
| **18** | **Absence of Historical Commercial Traction** | The repository contains no customer subscriber contracts, paying user data, or historical P&L records. | The asset is sold strictly as a software and intellectual property asset without existing ARR/MRR. | Buyer must acquire customers and execute their own commercial go-to-market strategy. | Repository-wide audit |
| **19** | **Legacy Repository Documentation Drift** | Early repository documentation (`README.md`, operations drafts) references Kubernetes, Go, and mobile apps. | New developers reading legacy documentation may become confused about the current architecture. | `04-TECHNICAL-HANDOVER-GUIDE.md` clarifies that Python 3.11, React 18, and Render PaaS are authoritative. | Root `README.md`, `docs/operations/` |
| **20** | **IP Assignment & Account Transfer** | The repository is transferred as a software codebase; third-party vendor accounts require separate transfer. | Legal ownership of domains, PaaS accounts, and payment accounts requires administrative handover. | Bilateral execution of definitive software purchase agreements and account invitation handover. | `05-DEPLOYMENT-HANDOVER.md` |

---

## 3. Architectural & Functional Deep Dive

### 3.1 Pure Simulation Model
The most significant architectural invariant of Project ORION is its strict restriction to simulated paper trading ($0.00 capital at risk). The execution engine contains no interfaces to Swift, FIX protocol engines, or clearing firm custodians. Any buyer intending to deploy Project ORION as a live brokerage execution engine must build live broker adapters and obtain appropriate financial regulatory licenses.

### 3.2 Single-Worker Execution Model
The strategy execution worker (`apps/trading-engine/src/worker.py`) is designed as a single-process event loop. This architectural design eliminates race conditions during paper order placement and simplifies state synchronization. However, running dozens of complex strategies across hundreds of currency pairs simultaneously will eventually require transitioning the worker loop to a distributed queue architecture (e.g. Celery with Redis or Temporal.io).

---

## 4. Compliance & Security Transparency

### Absence of Third-Party Certifications
While Project ORION implements modern defensive security practices (salted Bcrypt password hashing, SHA-256 token hashing, anti-enumeration timing delay, sliding-window token bucket rate limiting, non-root containers, and private PaaS networking), the software has **not been audited by an accredited external security firm** and holds no SOC 2 Type II, ISO 27001, or PCI-DSS certifications. This absence of certification does not imply insecurity, but means the buyer cannot rely on third-party compliance attestations.

---

## 5. Commercial Asset Transfer Notice

Project ORION is offered as an outright software asset sale. All prospective acquirers should explicitly recognize that:
1. **Zero Customer Revenue:** No historical revenue, Monthly Recurring Revenue (MRR), Annual Recurring Revenue (ARR), or customer subscriber contracts are included in this asset transfer.
2. **Clean IP Assignment:** Final legal title, copyright transfer, and intellectual property warranties are governed strictly by the definitive software asset purchase agreement negotiated between buyer and seller legal counsel.
