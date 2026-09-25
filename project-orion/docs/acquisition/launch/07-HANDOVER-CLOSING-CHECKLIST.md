# Project ORION — Handover & Closing Checklist
## Master Operational, Legal, and Technical Closing Procedure Across 23 Verification Gates

```
Document Reference: docs/acquisition/launch/07-HANDOVER-CLOSING-CHECKLIST.md
Document Version:   1.0.0
Release Status:     Acquisition Diligence Launch Package
Source Baseline:    Repository Git Commit d5908d0a0cc2feff99fa02573adb12b8eea33782
Canonical System:   Project ORION — Quantitative FX Research & Paper-Trading SaaS
Execution Boundary: Strictly Paper Trading ($100,000 Virtual Starting Balance; $0.00 Live Capital at Risk)
Commercial Status:  Pre-revenue / Commercial Traction Not Established in Repository
```

---

## 1. Executive Summary & Protocol Principles

This master checklist governs the final operational, technical, legal, and administrative handover of **Project ORION** (Quantitative FX Research & Paper-Trading SaaS) upon execution of definitive transaction agreements between Seller and Buyer.

### Governing Rules
1. **IP Scope & Phrasing**: All intellectual property transferred is defined as: *"Proposed Transferable Software / IP Scope, subject to executed transaction agreements."*
2. **Third-Party Accounts Non-Transferable**: In accordance with third-party terms of service, no vendor accounts (Render, Stripe, TwelveData, OANDA, SMTP) transfer between corporate entities. Every external service must be independently provisioned by the buyer and is designated as `BUYER-PROVISIONED`.
3. **Execution Boundary**: Handover preserves the core platform invariant: simulated execution only (`PaperExecutionAdapter`, `is_paper=True`), $100,000 virtual balance, and exactly $0.00 live financial capital at risk.
4. **Pre-Revenue Commercial Reality**: The buyer acknowledges that commercial subscriber metrics are `NOT ESTABLISHED IN REPOSITORY`. The asset sale constitutes source code, intellectual property, and technical architecture.
5. **Sign-Off Accountability**: Every gate requires explicit verification by authorized representatives of both Buyer and Seller prior to closing or escrow release (escrow, if used, will be governed by the executed transaction agreement and the transaction provider selected by the parties).

---

## 2. Master 23-Gate Handover & Closing Sequence

```
   [LEGAL & IP]           [CODEBASE & ARTIFACTS]      [INFRASTRUCTURE & ACCOUNTS]
   Gate 01: Agreement     Gate 03: Repo Transfer      Gate 06: Cloud Account (Render)
   Gate 02: IP Assignment Gate 04: Git Provenance     Gate 07: Domain / DNS
                          Gate 05: Dossier Transfer   Gate 08: Stripe (Test Mode)
                                                      Gate 09: SMTP Service
                                                      Gate 10: TwelveData API
                                                      Gate 11: OANDA Practice

   [DATABASE & SECRETS]   [DEPLOYMENT & QA]           [FINAL CLOSING & ACCESS]
   Gate 12: Secrets Config Gate 17: PaaS Deployment   Gate 20: Final Access Transfer
   Gate 13: DB Migration   Gate 18: Health Probes     Gate 21: Seller Access Removal
   Gate 14: Redis Cache    Gate 19: Buyer Acceptance  Gate 22: Closing Evidence
   Gate 15: Backup Conf                               Gate 23: Support (If Agreed)
   Gate 16: Restore Valid
```

---

### Gate 1: Definitive Transaction Agreement
- **Description**: Execution of the definitive Software Asset Purchase Agreement (APA) or Technology Transfer Agreement by authorized corporate signatories.
- **Verification Requirement**: Countersigned APA and Bill of Sale; transaction funding or escrow deposit confirmed (escrow, if used, will be governed by the executed transaction agreement and the transaction provider selected by the parties).
- **Responsible Parties**: Seller Legal / Buyer Legal.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 2: Intellectual Property Assignment
- **Description**: Formal execution of the standalone Intellectual Property Assignment Agreement conveying all copyrights, patents (if any), trade secrets, documentation, and proprietary code.
- **Standard Wording**: *"Proposed Transferable Software / IP Scope, subject to executed transaction agreements."*
- **Reference**: Cross-reference `docs/acquisition/15-IP-ASSIGNMENT-CHECKLIST.md`.
- **Verification Requirement**: Executed IP Assignment Agreement including employee/contractor invention assignment certificates and confirmation of clean SBOM licensing audit (MIT/Apache-2.0).
- **Responsible Parties**: Seller Legal / Buyer Legal.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 3: Canonical Repository Transfer
- **Description**: Transfer of administrative ownership of the primary Git repository (`project-orion`) to the buyer's designated GitHub, GitLab, or self-hosted Git organization.
- **Verification Requirement**: Buyer designated account promoted to Organization Owner; repository visibility confirmed; push permissions verified.
- **Responsible Parties**: Seller DevOps / Buyer DevOps.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 4: Git History & Provenance Verification
- **Description**: Verification that the repository commit history matches the verified baseline commit (`d5908d0a0cc2feff99fa02573adb12b8eea33782`) without history rewriting, orphan branches, or detached tags.
- **Verification Requirement**: `git log -1` on buyer mirror matches baseline commit hash; `git fsck --full` reports zero corruption.
- **Responsible Parties**: Buyer Lead Engineer.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 5: Acquisition Dossier & Presentation Artifact Transfer
- **Description**: Formal delivery of the 18 canonical technical due diligence dossiers and the Phase 0.6/0.7 visual presentation package.
- **Deliverables**:
  - 18 Dossiers under `docs/acquisition/` (`01-EXECUTIVE-BRIEF.md` through `18-DUE-DILIGENCE-DATA-ROOM-INDEX.md`).
  - Presentation visual package under `docs/acquisition/presentation/visual/` (Executive Brief PDF, 15-slide PPTX with 100% speaker notes coverage, 5 SVGs).
  - Launch suite under `docs/acquisition/launch/` (7 documents).
- **Verification Requirement**: Full directory archive delivered with SHA-256 manifest.
- **Responsible Parties**: Seller Tech Lead / Buyer Tech Lead.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 6: Cloud Account Provisioning (`BUYER-PROVISIONED`)
- **Description**: Buyer independently provisions a cloud PaaS organization (Render PaaS or equivalent cloud container environment) to host the trading engine and frontend.
- **Economic Context**: Approximately $14/month baseline configuration hosting estimate based on the documented Render configuration ($7 Managed PostgreSQL + $7 Web Service under published 2026 Render pricing); actual cloud pricing may vary and is buyer-provisioned (see `docs/acquisition/14-INFRASTRUCTURE-TOPOLOGY-MAP.md`).
- **Account Type**: `BUYER-PROVISIONED` (non-transferable).
- **Verification Requirement**: Buyer confirms active Render account with billing details established.
- **Responsible Parties**: Buyer DevOps.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 7: Domain & DNS Management
- **Description**: Handover of platform domain name and DNS zone configuration to the buyer's domain registrar.
- **Reference**: Cross-reference `docs/acquisition/17-DOMAIN-TRANSFER-CHECKLIST.md`.
- **Verification Requirement**: EPP authorization transfer code generated and submitted to buyer's registrar; DNS zone records verified; SSL/TLS certificates issued.
- **Responsible Parties**: Seller DevOps / Buyer DevOps.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 8: Stripe Payment Infrastructure (`BUYER-PROVISIONED`)
- **Description**: Buyer provisions their own Stripe account, configures webhook endpoints, and establishes API keys.
- **Operating Mode**: Stripe Test Mode initially configured with product tiers: Free Sandbox ($0), Pro Trader ($99), Business Prop ($299), Enterprise (Custom).
- **Account Type**: `BUYER-PROVISIONED` (seller customer data/Stripe accounts do not transfer).
- **Verification Requirement**: Buyer populates `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, and `STRIPE_WEBHOOK_SECRET` in their deployment environment; test checkout session executes successfully.
- **Responsible Parties**: Buyer Engineering / Buyer Finance.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 9: Transactional Email / SMTP Provider (`BUYER-PROVISIONED`)
- **Description**: Buyer provisions a transactional email delivery service (SendGrid, Postmark, AWS SES, or Brevo) for user registration verification, password resets, and alert notifications.
- **Account Type**: `BUYER-PROVISIONED`.
- **Verification Requirement**: Buyer configures `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, and `SMTP_PASSWORD`; test verification email successfully delivered.
- **Responsible Parties**: Buyer DevOps.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 10: TwelveData Market Data API (`BUYER-PROVISIONED`)
- **Description**: Buyer establishes an API account with TwelveData (or alternate supported market data vendor) for historical and live OHLCV candle ingestion.
- **Account Type**: `BUYER-PROVISIONED`.
- **Verification Requirement**: Buyer inserts valid `TWELVE_DATA_API_KEY` into environment; market data service fetches historical daily/hourly FX candles for EUR/USD.
- **Responsible Parties**: Buyer Data Engineer.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 11: OANDA Practice Sandbox Account (`BUYER-PROVISIONED`)
- **Description**: Buyer provisions an OANDA Developer Practice (sandbox) account to test external broker adapter integration without capital exposure.
- **Operating Invariant**: Execution boundary remains practice/simulation only.
- **Account Type**: `BUYER-PROVISIONED`.
- **Verification Requirement**: Buyer configures `OANDA_ACCOUNT_ID` and `OANDA_ACCESS_TOKEN` for `https://api-fxpractice.oanda.com`; account status query returns successfully.
- **Responsible Parties**: Buyer Quant / Trading Tech Lead.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 12: Production Environment Secrets Configuration
- **Description**: Injection of buyer-owned production secrets into the deployment environment following `docs/acquisition/11-ENVIRONMENT-VARIABLE-REFERENCE.md`.
- **Verification Requirement**: All required production variables configured with zero placeholder values:
  - `SECRET_KEY` (cryptographically random 64-char hex string)
  - `DATABASE_URL` (buyer PostgreSQL connection string with TLS `sslmode=require`)
  - `REDIS_URL` (buyer Redis instance with TLS `rediss://`)
  - `STRIPE_SECRET_KEY` & `STRIPE_WEBHOOK_SECRET`
  - `SMTP_PASSWORD`
  - `TWELVE_DATA_API_KEY`
- **Responsible Parties**: Buyer DevOps / Security Officer.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 13: PostgreSQL Database Migration Execution
- **Description**: Execution of the 15 versioned Alembic migrations on the buyer's managed PostgreSQL 16 database.
- **Reference**: Cross-reference `docs/acquisition/10-DATABASE-MIGRATION-GUIDE.md`.
- **Verification Requirement**: `alembic upgrade head` executes with exit code 0; all 29 relational tables verified with proper primary keys, foreign keys, and indexes (encompassing 28 application model tables and the `alembic_version` migration metadata table).
- **Responsible Parties**: Buyer DBA / DevOps.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 14: Redis 7 Cache & Rate-Limiter Initialization
- **Description**: Connectivity verification and memory configuration for the buyer's standalone Redis 7 instance.
- **Verification Requirement**: Redis responds to `PING` with `PONG`; eviction policy configured to `volatile-lru` or `allkeys-lru`; rate limiting middleware registers keys properly.
- **Responsible Parties**: Buyer DevOps.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 15: Operational Backup Configuration
- **Description**: Configuration of automated daily logical database backups and WAL archiving.
- **Reference**: Cross-reference `docs/acquisition/08-BACKUP-RESTORE-RUNBOOK.md`.
- **Verification Requirement**: Automated backup schedule activated (daily `pg_dump` with gzip compression); offsite storage target (AWS S3, Cloudflare R2, or GCP Cloud Storage) configured and tested.
- **Responsible Parties**: Buyer Infrastructure Lead.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 16: Disaster Recovery / Restore Validation
- **Description**: Verification that the buyer's engineering team can successfully restore the database from a backup artifact in compliance with documented operational standards.
- **Historical Benchmark**: Benchmark record in Dossier 08 documents ~7.2-second restoration across 29 tables during development verification.
- **Verification Requirement**: Buyer executes a test restore to a staging database; schema and row integrity verified.
- **Responsible Parties**: Buyer DevOps / DBA.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 17: Production PaaS Deployment
- **Description**: Deployment of the containerized trading engine API and Vite static dashboard on the buyer's cloud infrastructure.
- **Verification Requirement**: Docker container build completes cleanly; API service starts listening on assigned port; dashboard static assets served via CDN or web service.
- **Responsible Parties**: Buyer DevOps.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 18: Application Health & Liveness Probe Verification
- **Description**: Execution of automated application health and liveness probes against deployed services (application liveness probe verifies web service availability, distinct from live financial trading).
- **Endpoints**:
  - `GET /health/live` — Returns HTTP 200 `{"status": "healthy"}`.
  - `GET /health/ready` — Returns HTTP 200 `{"status": "ready", "database": "connected", "redis": "connected"}`.
  - `GET /metrics` — Prometheus metrics endpoint returns scrapeable telemetry.
- **Verification Requirement**: HTTP 200 responses received on all probes without error logs.
- **Responsible Parties**: Buyer DevOps / QA Lead.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 19: Buyer Technical Acceptance Testing (BAT)
- **Description**: Formal technical acceptance testing by the buyer's engineering team against the 16 canonical demonstration flows in `docs/acquisition/launch/06-DEMO-ENVIRONMENT-RUNBOOK.md`.
- **Core Acceptance Criteria**:
  1. User registration, JWT login, and tenant onboarding succeed.
  2. Strategy Catalog loads all 4 strategies and 9 profiles.
  3. Backtest engine executes historical simulation with `LeakageGuard` active.
  4. Walk-Forward Analysis computes in-sample / out-of-sample window metrics.
  5. Simulated paper order executes via `PaperExecutionAdapter` stamping `is_paper=True`.
  6. $100,000 virtual balance correctly tracks simulated P&L ($0.00 capital at risk).
  7. RBAC permissions block unauthorized actions across roles.
- **Verification Requirement**: Formal written acceptance notice signed by Buyer Technical Lead.
- **Responsible Parties**: Buyer Technical Lead / Lead Quant.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 20: Final Administrative Access Transfer
- **Description**: Transfer of all remaining administrative keys, repository master roles, DNS accounts, and documentation repositories to the buyer.
- **Verification Requirement**: Buyer confirms sole possession of all primary administrative roles.
- **Responsible Parties**: Seller Lead / Buyer Lead.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 21: Seller Access Removal & Environment Cleandown
- **Description**: Systematic removal of all seller developer access, SSH keys, deployment tokens, and staging credentials.
- **Verification Requirement**:
  - Seller accounts removed from Git repository.
  - Seller access removed from Render, DNS, and communication channels.
  - Seller signs declaration of complete deletion of proprietary buyer secrets.
- **Responsible Parties**: Seller Tech Lead / Buyer Security Officer.
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 22: Closing Evidence Package Assembly
- **Description**: Compilation of the immutable Closing Evidence Package recording transaction execution.
- **Evidence Contents**:
  - Countersigned Asset Purchase Agreement and IP Assignment Agreement.
  - Buyer written Technical Acceptance Notice.
  - Repository transfer confirmation timestamp and Git commit hash.
  - Checksum manifest of transferred dossiers and presentation assets.
  - Transaction closing confirmation or escrow release confirmation receipt (escrow release, if applicable, subject to executed transaction documents and agreed closing conditions).
- **Verification Requirement**: Complete PDF evidence binder archived by legal counsel of both parties.
- **Responsible Parties**: Transaction Legal Counsel / Escrow Agent (if applicable).
- **Status**: `[ ] Pending` | `[ ] Verified`

---

### Gate 23: Post-Closing Support Boundary (Optional / If Agreed)
- **Description**: Optional post-closing transition support, if agreed in the transaction documents.
- **Contractual Dependency**: Post-closing support terms are subject to the executed transaction agreement.
- **Representative Scope (Subject to Agreement)**:
  - Duration: As agreed in definitive transaction documents (e.g., standard 30 calendar day orientation window if specified).
  - Scope: Asynchronous advisory support for repository orientation, build clarification, and architecture questions.
  - Exclusions: Does not include custom feature development, bespoke third-party broker integrations, new strategy engineering, or production 24/7 on-call incident response.
- **Verification Requirement**: Designated transition communication channel (Slack/email) established between lead engineers, if support is contracted.
- **Responsible Parties**: Seller Tech Lead / Buyer Tech Lead.
- **Status**: `[ ] Optional / Pending Agreement` | `[ ] Verified`

---

## 3. Handover Completion Sign-Off

Upon completion of all 23 verification gates, authorized representatives execute this formal sign-off:

```text
================================================================================
                        TRANSACTION HANDOVER SIGN-OFF
================================================================================
Software Asset:         Project ORION (Quantitative FX Research & Paper-Trading SaaS)
Baseline Commit Hash:   d5908d0a0cc2feff99fa02573adb12b8eea33782
Date of Handover:       ____________________
Transaction / Escrow Reference ID (if applicable):  ____________________

SELLER ACKNOWLEDGEMENT:
I hereby certify that the Proposed Transferable Software and IP Scope, canonical
Git repositories, 18 technical diligence dossiers, visual presentation package,
and launch documentation have been fully delivered in accordance with executed
transaction agreements. All seller access has been decommissioned.

Authorized Seller Signature:   ___________________________________
Printed Name and Title:        ___________________________________
Organization:                  ___________________________________

BUYER ACKNOWLEDGEMENT:
I hereby certify that the buyer has independently provisioned required cloud and
vendor accounts (BUYER-PROVISIONED), successfully verified database migrations,
deployed the platform, completed Technical Acceptance Testing, and received full
administrative ownership of the software repository.

Authorized Buyer Signature:    ___________________________________
Printed Name and Title:        ___________________________________
Organization:                  ___________________________________
================================================================================
```

---
*End of Document — Project ORION Acquisition Launch Suite*
