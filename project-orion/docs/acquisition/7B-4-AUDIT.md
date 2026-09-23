# EPIC-027 Phase 7B-4 Audit

**Audit Date:** 2026-09-24
**Auditor:** Quantitative Architecture, Security, & Acquisition Due-Diligence Agent
**Repository Working Copy:** `project-orion/`
**Current Baseline Commit:** `29494cf3041992d8e73dfd96bca19c1d2d1f3949` (`docs(acquisition): add API database environment and SBOM dossier`)
**Target Milestone:** EPIC-027 Phase 7B-4 Acquisition Closing & Data Room Dossier

---

## 1. Executive Summary

This audit establishes the factual, legal, and operational baseline for the final documentation batch of **Project ORION** acquisition due diligence (Phase 7B-4).

Phase 7B-4 encompasses four closing-stage due-diligence documents:
1. `docs/acquisition/15-IP-ASSIGNMENT-CHECKLIST.md`
2. `docs/acquisition/16-ACCOUNT-OWNERSHIP-TRANSFER.md`
3. `docs/acquisition/17-DOMAIN-TRANSFER-CHECKLIST.md`
4. `docs/acquisition/18-DUE-DILIGENCE-DATA-ROOM-INDEX.md`

The audit examined git authorship records, commit histories, software license manifests, container infrastructure blueprints, payment configurations, broker execution interfaces, market data connectors, domain references, and secret storage architectures across the codebase.

**Key Findings:**
- **Authorship & Chain of Title:** 100% of the 46 commits in the repository history are authored and committed by a single contributor: `Kiran Thange <thangekiran2006@gmail.com>`. No merge commits or contributions from secondary parties exist in git history.
- **Pure Software Asset Sale:** The platform is structured as an outright software and intellectual-property asset sale ($0.00 capital at risk, paper-trading simulation only). No customer contracts, MRR/ARR, or active subscriber accounts exist in the repository.
- **External SaaS Accounts:** The repository integrates with third-party providers (Render, Stripe, TwelveData, OANDA, SMTP relay), but third-party vendor accounts cannot be assumed to be automatically transferable. The documentation must clearly distinguish repository assets from buyer-provisioned vendor accounts.
- **Domain & DNS Reality:** Active deployments operate on Render subdomains (`*.onrender.com`). Custom domains (`oriontrading.io`, `project-orion.dev`) appear as default configuration templates and examples in code and documentation; ownership of these domains cannot be verified from repository files alone and requires seller verification.
- **Zero Secret Exposure:** Zero active production credentials or signing keys are checked into the repository. Configuration strictly adheres to Twelve-Factor design.

---

## 2. Baseline

- **Repository Root:** `C:\Users\Shree\CascadeProjects\forex-trading-platform-architecture\project-orion`
- **Git Commit Baseline:** `29494cf3041992d8e73dfd96bca19c1d2d1f3949`
- **Remote Origin:** `https://github.com/Kiran190306/Project-ORION.git`
- **Synchronization:** `HEAD == origin/main == 29494cf3041992d8e73dfd96bca19c1d2d1f3949`
- **Git History Extent:** 46 commits from `2026-07-18 18:13:02 +0530` to `2026-09-24 00:53:20 +0530`.
- **Working Tree State:** All tracked files in `project-orion/` are clean and committed. Existing parent-level untracked scratch files remain preserved and untouched.

---

## 3. Current Acquisition Dossier Inventory

Fourteen buyer-facing due-diligence documents are committed under `docs/acquisition/`:

| Document ID & Filename | Target Milestone | Classification | Content Summary |
|---|---|---|---|
| `01-EXECUTIVE-BRIEF.md` | Phase 7B-3 | Tier 1 (Public / Exec) | High-level asset summary, planned software sale disclaimer, no historical MRR/ARR |
| `02-PRODUCT-OVERVIEW.md` | Phase 7B-3 | Tier 1 (Public / Product) | Capabilities, paper-only trading invariants, strategy backtesting/optimization |
| `03-ARCHITECTURE-OVERVIEW.md` | Phase 7B-2 | Tier 2 (Confidential / NDA) | FastAPI async engine, PostgreSQL asyncpg, Redis, React Vite dashboard |
| `04-TECHNICAL-HANDOVER-GUIDE.md` | Phase 7B-3 | Tier 2 (Confidential / NDA) | Repository structure, developer environment setup, local test suite commands |
| `05-DEPLOYMENT-HANDOVER.md` | Phase 7B-2 | Tier 2 (Confidential / NDA) | Render PaaS blueprint, service definitions, environment configuration, migrations |
| `06-OPERATIONS-RUNBOOK.md` | Phase 7B-3 | Tier 2 (Confidential / NDA) | Day-to-day operations, service health checks, logs, incident response procedures |
| `07-SECURITY-OVERVIEW.md` | Phase 7B-2 | Tier 2 (Confidential / NDA) | RBAC (41 permissions), TenantContext multi-tenancy, AES-GCM credential encryption |
| `08-BACKUP-RESTORE-RUNBOOK.md` | Phase 7B-3 | Tier 2 (Confidential / NDA) | Render snapshots, logical backups (`database-backup.sh`), demonstrated 7s restore |
| `09-API-DOCUMENTATION.md` | Phase 7B-1 | Tier 2 (Confidential / NDA) | Authoritative reference for 122 application endpoints across 19 domain routers |
| `10-DATABASE-MIGRATION-GUIDE.md` | Phase 7B-1 | Tier 2 (Confidential / NDA) | 15 linear Alembic migrations base to head `0015_onboarding_progress` |
| `11-ENVIRONMENT-VARIABLE-REFERENCE.md`| Phase 7B-1 | Tier 2 (Confidential / NDA) | 44 configuration settings, Twelve-Factor compliance, template drift catalog |
| `12-DEPENDENCY-SBOM.md` | Phase 7B-1 | Tier 2 (Confidential / NDA) | Third-party packages, licenses, SaaS dependencies, legal verification disclaimer |
| `13-KNOWN-LIMITATIONS.md` | Phase 7B-3 | Tier 2 (Confidential / NDA) | Transparent register of 20 system limitations (single region, paper-only, etc.) |
| `14-INFRASTRUCTURE-TOPOLOGY-MAP.md` | Phase 7B-2 | Tier 2 (Confidential / NDA) | Render PaaS topology, private networking, edge proxy, egress integrations |

---

## 4. IP Assignment Findings (Document 15)

### 4.1 Repository Supported Facts
1. **Root License Notice:** The repository root contains a `LICENSE` file declaring:
   ```text
   PROPRIETARY SOFTWARE LICENSE AGREEMENT
   Copyright (c) 2026 Project ORION. All rights reserved.
   This software is proprietary and confidential.
   ```
2. **Git Commit Authorship:** Across the entire repository lifecycle (46 commits), exactly one individual identity appears in the git log:
   - Author: `Kiran Thange <thangekiran2006@gmail.com>`
   - Committer: `Kiran Thange <thangekiran2006@gmail.com>`
   - No third-party contributors, bots, or external committers appear in the commit metadata.
3. **Proprietary Source Scope:**
   - Backend: `apps/trading-engine/` (FastAPI services, middleware, routes, schemas).
   - Frontend: `apps/dashboard/` (React 18 SPA, UI components, state stores, charts).
   - Domain Libraries: `libraries/domain/` (trading models, strategies, risk rules, billing, RBAC, legal models).
   - Infrastructure Libraries: `libraries/infrastructure/` (persistence ORM models, caching, market data, execution adapters).
   - Database Migrations: `alembic/versions/` (15 linear Alembic migration scripts).
   - Test Automation: `tests/` (100+ unit, integration, and security tests).
   - Deployment Specs: `render.yaml`, `docker/`, `scripts/deploy/`, `backup/`.
   - Documentation: Comprehensive documentation under `docs/` and `docs/acquisition/`.
4. **Third-Party Open-Source Components:** As audited in `12-DEPENDENCY-SBOM.md`, third-party packages are standard open-source libraries governed by permissive licenses (MIT, Apache-2.0, BSD-3-Clause, ISC, PSF). GPL-licensed dev tooling (`pylint`) is strictly quarantined to offline developer workstations and never distributed.

### 4.2 Items Requiring Seller / Legal Verification
- **Seller Legal Identity:** "Project ORION" is an asset/project name, not an incorporated legal entity. Whether title is held individually by Kiran Thange or by a corporate entity must be confirmed by seller legal counsel.
- **Invention Assignment & Work-Made-for-Hire:** Seller must confirm that the software was created free of any conflicting obligations to employers, clients, or third parties, and execute formal IP Assignment Agreements and Bills of Sale.
- **Trademarks & Patents:** No registered patents, patent applications, or registered trademarks exist in repository files. "Project ORION" represents an unregistered trademark/brand. Legal counsel must confirm that no third-party trademark conflicts exist.

---

## 5. Account Ownership Transfer Findings (Document 16)

### 5.1 Account & Platform Inventory
The repository interacts with the following external platforms:

1. **GitHub (`Kiran190306/Project-ORION`):**
   - **Repository Facts:** Remote URL is `https://github.com/Kiran190306/Project-ORION.git`.
   - **Transfer Mechanism:** GitHub provides two standard transfer paths:
     - *Path A (Direct Transfer):* Seller transfers repository ownership via GitHub Settings to the buyer's GitHub organization or account.
     - *Path B (Mirror/Fork):* Buyer clones repository and pushes to a clean repository in their own GitHub organization.
   - **Verification:** Repository does not contain `.github/` workflows or organization-level metadata. Account type (personal vs org) cannot be verified from local git files.
2. **Render Cloud PaaS:**
   - **Repository Facts:** Services configured in `render.yaml` (`orion-postgres`, `orion-redis`, `orion-api`, `orion-dashboard`). Active production deployed on `*.onrender.com`.
   - **Transfer Mechanism:** Render does not provide automated cross-account transfer of managed databases. Handover is accomplished via:
     - *Path A (Blueprint Deployment in Buyer Account — Recommended):* Buyer provisions a new Render account, links their GitHub repository, launches the `render.yaml` Blueprint, and imports the database snapshot via `backup/restore-database.sh`.
     - *Path B (Team Workspace Invitation):* Seller invites buyer as Owner to the existing Render Team workspace, then seller account is removed.
3. **Stripe (Payment Processing):**
   - **Repository Facts:** Configured strictly for Stripe Test Mode (`price_test_*`, `sk_test_*`). Live keys are forbidden by application startup guards (`LiveCredentialsForbiddenError`).
   - **Transfer Mechanism:** Stripe accounts are bound to legal entity identity and bank accounts; they cannot be transferred between unrelated legal entities. The buyer **must provision a new Stripe account**, configure matching pricing tiers in Test/Live mode, and inject keys into environment variables.
4. **TwelveData (Market Data):**
   - **Repository Facts:** Consumes API key via `ORION_MARKET_DATA_API_KEY`.
   - **Transfer Mechanism:** External SaaS subscription. Buyer provisions their own TwelveData corporate subscription. Seller account is not transferred.
5. **OANDA (Broker Sandbox):**
   - **Repository Facts:** Practice REST API connector (`https://api-fxpractice.oanda.com`). Credentials stored encrypted in database table `broker_sandbox_accounts`.
   - **Transfer Mechanism:** Demo sandbox accounts contain no real capital. Buyer registers their own OANDA v20 fxTrade demo account.
6. **Transactional SMTP Provider:**
   - **Repository Facts:** Configured via `ORION_SMTP_*`.
   - **Transfer Mechanism:** Buyer provisions transactional SMTP credentials (e.g. SendGrid, Mailgun, Amazon SES).
7. **Offsite Backup Storage (AWS S3 / Cloudflare R2):**
   - **Repository Facts:** Documented in backup runbooks; buyer provisions bucket and IAM credentials.

---

## 6. Domain Transfer Findings (Document 17)

### 6.1 Domain References in Codebase
The repository contains references to several domain strings:
1. `oriontrading.io`: Referenced in `libraries/infrastructure/communication/email_service.py` (`from_email: "notifications@oriontrading.io"`).
2. `project-orion.dev`: Referenced in legacy EPIC-016 architectural planning documents.
3. `orion.example.com`: Referenced in Helm and Kustomize template files (`deployment/helm/`, `deployment/kustomize/`).
4. `*.onrender.com`: Active cloud production hostnames (`orion-api-68u2.onrender.com`, `orion-dashboard-6d3z.onrender.com`).

### 6.2 Verification & Transfer Status
- **No Domain Registration Proof:** The repository contains no DNS registrar accounts, EPP transfer codes, WHOIS records, or domain renewal receipts.
- **Operational Reality:** Production services run on Render-managed default subdomains (`*.onrender.com`), with TLS automatically provisioned by Render via Let's Encrypt.
- **Seller Verification Required:** Seller must confirm whether `oriontrading.io` is an active domain owned by the seller.
  - *If Owned:* Transfer requires registrar unlock, EPP authorization code generation, and transfer initiation by the buyer.
  - *If Not Owned / Placeholder:* The buyer must register their preferred commercial domain and configure DNS CNAME records pointing to Render service slugs.
- **DNS Record Checklist:** Document 17 must provide the complete DNS configuration template (API CNAME, Dashboard CNAME, SPF/DKIM/DMARC TXT records for email deliverability).

---

## 7. Data Room Findings (Document 18)

### 7.1 Architecture of the Acquisition Data Room
The data room will index all 18 acquisition documents across three access tiers:

```
docs/acquisition/
├── Tier 1: Executive & Commercial (Public / Teaser)
│   ├── 01-EXECUTIVE-BRIEF.md
│   └── 02-PRODUCT-OVERVIEW.md
├── Tier 2: Technical Due Diligence (Confidential / NDA)
│   ├── 03-ARCHITECTURE-OVERVIEW.md
│   ├── 04-TECHNICAL-HANDOVER-GUIDE.md
│   ├── 05-DEPLOYMENT-HANDOVER.md
│   ├── 06-OPERATIONS-RUNBOOK.md
│   ├── 07-SECURITY-OVERVIEW.md
│   ├── 08-BACKUP-RESTORE-RUNBOOK.md
│   ├── 09-API-DOCUMENTATION.md
│   ├── 10-DATABASE-MIGRATION-GUIDE.md
│   ├── 11-ENVIRONMENT-VARIABLE-REFERENCE.md
│   ├── 12-DEPENDENCY-SBOM.md
│   ├── 13-KNOWN-LIMITATIONS.md
│   └── 14-INFRASTRUCTURE-TOPOLOGY-MAP.md
└── Tier 3: Legal, Transfer & Closing (Confidential / Closing)
    ├── 15-IP-ASSIGNMENT-CHECKLIST.md
    ├── 16-ACCOUNT-OWNERSHIP-TRANSFER.md
    ├── 17-DOMAIN-TRANSFER-CHECKLIST.md
    └── 18-DUE-DILIGENCE-DATA-ROOM-INDEX.md
```

### 7.2 Evidence-Based Cross-References
Every claim in the data room must link directly to verifiable files in the repository:
- Architectural claims -> `apps/`, `libraries/`
- Schema claims -> `alembic/versions/`, `apps/trading-engine/src/schemas.py`
- Operational claims -> `render.yaml`, `backup/`, `docker/`
- Verification claims -> `tests/`, `docs/EPIC-*.md` reports

---

## 8. Repository-Supported Facts

1. **Clean Linear Git History:** 46 commits, single author `Kiran Thange <thangekiran2006@gmail.com>`.
2. **Proprietary Copyright Header:** Root `LICENSE` asserts proprietary copyright 2026 by "Project ORION".
3. **Twelve-Factor Secret Handling:** 0 production credentials, private keys, or API tokens committed in git.
4. **Cloud Infrastructure Blueprint:** `render.yaml` specifies 4 core services (`orion-postgres`, `orion-redis`, `orion-api`, `orion-dashboard`).
5. **Stripe Test Mode Invariant:** Software raises `LiveCredentialsForbiddenError` on any live keys.
6. **Broker Sandbox Invariant:** Broker adapter factory rejects live broker URLs and restricts connections to practice endpoints (`api-fxpractice.oanda.com`).
7. **Disaster Recovery Proof:** Documented 7-second physical database restore demonstration (`docs/EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md`).
8. **Comprehensive Testing:** 100+ tests spanning unit, integration, and security boundaries.

---

## 9. Seller Verification Required

1. **Legal Title Confirmation:** Confirm that Kiran Thange holds sole, unencumbered legal title to the software repository.
2. **Domain Status:** Confirm whether `oriontrading.io` is registered and owned by the seller, and identify its current registrar.
3. **GitHub Account Transfer:** Confirm readiness to transfer the GitHub repository `Kiran190306/Project-ORION` to the buyer.
4. **Render Account Status:** Confirm whether the Render workspace can be handed over via team invite, or if the buyer should deploy via blueprint into a fresh account.
5. **Absence of Undisclosed Liabilities:** Confirm no prior commercial licensing, liens, or ongoing disputes exist.

---

## 10. Buyer Verification Required

1. **Independent Code Due Diligence:** Clone repository, run automated test suites (`pytest`, `vitest`), and audit code quality.
2. **Open-Source License Review:** Legal audit of open-source dependencies listed in `12-DEPENDENCY-SBOM.md`.
3. **Third-Party SaaS Provisioning:** Provision buyer accounts for Render, Stripe, TwelveData, and transactional SMTP relay.
4. **Custom Domain Acquisition & DNS Setup:** Secure preferred corporate domain and configure DNS CNAME/TXT records.
5. **Compliance & Penetration Audits:** Conduct formal external penetration testing and SOC 2 / ISO 27001 audits if needed for buyer operations.

---

## 11. Legal Review Required

1. **Definitive Asset Purchase Agreement (APA):** Draft bilateral contract governing the purchase price, representations, and warranties.
2. **Bill of Sale & Intellectual Property Assignment Agreement:** Formal legal instruments transferring copyright, source code, documentation, and goodwill.
3. **Representations & Warranties:** Legal clauses affirming non-infringement, lack of liens, and clean chain of title.
4. **Terms of Service & Privacy Policy Localization:** Replace placeholder legal text in `libraries/domain/legal/content/` with the buyer's corporate identity, jurisdiction, and governing law.

---

## 12. Unknown / Not Established in Repository

1. **Seller Corporate Entity:** No formal registered corporate entity, address, or incorporation state is defined.
2. **Domain Registrar Information:** No registrar account or ownership certificate for `oriontrading.io` exists in files.
3. **Registered Trademarks or Patents:** No trademark registration numbers or patent records exist.
4. **Historical Customer Revenue / Contracts:** No paying users, subscriptions, or contracts exist.
5. **Third-Party SaaS Account Transferability:** Cannot guarantee that external providers will permit direct account transfers.

---

## 13. Proposed 7B-4 Document Structure

### Document 15: `15-IP-ASSIGNMENT-CHECKLIST.md`
- **Section 1:** Executive IP Overview & Asset Scope
- **Section 2:** Proprietary Codebase & Asset Inventory (Backend, Frontend, Libraries, Migrations, Docs)
- **Section 3:** Authorship, Contribution History & Chain of Title (Single author audit)
- **Section 4:** Open-Source Dependency Licensing Review & Quarantines (SBOM alignment)
- **Section 5:** Trademarks, Branding & Proprietary Nomenclature
- **Section 6:** Patents & Proprietary Algorithms (Strategy models, walk-forward analysis)
- **Section 7:** Formal Legal Instruments Checklist (APA, Bill of Sale, IP Assignment Agreement)
- **Section 8:** Legal Disclaimers & Independent Verification Mandate

### Document 16: `16-ACCOUNT-OWNERSHIP-TRANSFER.md`
- **Section 1:** Account Transfer Principles & Vendor Policies
- **Section 2:** Master SaaS & Infrastructure Matrix (GitHub, Render, Stripe, TwelveData, OANDA, SMTP)
- **Section 3:** GitHub Repository Transfer Runbook (Direct transfer vs clone/mirror)
- **Section 4:** Cloud Infrastructure Handover (Render blueprint vs workspace transfer)
- **Section 5:** Payment Gateway Strategy (Buyer-provisioned Stripe account)
- **Section 6:** Market Data & Broker Sandbox Handover (TwelveData & OANDA setup)
- **Section 7:** Transactional Email & Offsite Storage Handover
- **Section 8:** Post-Transfer Security Credential Rotation Checklist

### Document 17: `17-DOMAIN-TRANSFER-CHECKLIST.md`
- **Section 1:** Domain Landscape & Current Repository References
- **Section 2:** Operational Status (Active `*.onrender.com` vs custom domain templates)
- **Section 3:** Domain Registrar Transfer Protocol (Auth code, unlock, transfer request)
- **Section 4:** DNS Architecture & Authoritative Record Checklist (CNAME, A, ALIAS)
- **Section 5:** Transactional Email Authentication Configuration (SPF, DKIM, DMARC)
- **Section 6:** SSL/TLS Certificate Lifecycle (Render Let's Encrypt automation)
- **Section 7:** Domain Handover Verification & Cutover Checklist

### Document 18: `18-DUE-DILIGENCE-DATA-ROOM-INDEX.md`
- **Section 1:** Data Room Overview & Navigation Guidelines
- **Section 2:** Tiered Information Architecture (Tier 1 Public, Tier 2 Confidential, Tier 3 Closing)
- **Section 3:** Master Document Index (Complete 18-document catalog with summaries)
- **Section 4:** Technical Evidence Mapping Matrix (Linking claims to concrete repository files)
- **Section 5:** Architectural Decision Records (ADRs) & EPIC Verification Reports Cross-Index
- **Section 6:** Technical Due Diligence Q&A / FAQs for Prospective Buyers
- **Section 7:** Due Diligence Completion & Closing Protocol

---

## 14. Contradictions / Risks

| Risk / Contradiction | Description | Mitigation Strategy in Documentation |
|---|---|---|
| **Domain Ownership Assumption** | Code references `notifications@oriontrading.io`, which could be misconstrued as an active, verified corporate domain. | Explicitly document that `oriontrading.io` is a default template and requires seller confirmation of registration/ownership. |
| **SaaS Account Transfer Assumption** | Assuming Stripe or TwelveData accounts transfer automatically with the sale. | Document that payment processors require buyer-owned corporate accounts for KYC/AML compliance. Make buyer provisioning the default. |
| **GitHub Transfer Friction** | Transferring `Kiran190306/Project-ORION` directly depends on seller personal account action. | Provide dual transfer paths: (1) GitHub organization transfer, and (2) git clone/mirror push into buyer's repository. |
| **Entity Ambiguity** | Root license references "Project ORION" as copyright holder. | Clarify that "Project ORION" is an asset name, and legal title transfer must be executed by the individual/entity holding legal rights. |

---

## 15. Recommended Implementation Plan

1. **Step 1 — Audit Review:** Present this audit report (`docs/acquisition/7B-4-AUDIT.md`) for human authorization.
2. **Step 2 — Document Creation:** Upon approval, author the four Phase 7B-4 target documents:
   - `docs/acquisition/15-IP-ASSIGNMENT-CHECKLIST.md`
   - `docs/acquisition/16-ACCOUNT-OWNERSHIP-TRANSFER.md`
   - `docs/acquisition/17-DOMAIN-TRANSFER-CHECKLIST.md`
   - `docs/acquisition/18-DUE-DILIGENCE-DATA-ROOM-INDEX.md`
3. **Step 3 — Factual Verification:** Perform cross-document consistency checks and automated secret pattern scans across the new files.
4. **Step 4 — Non-Mutating Quality Gates:** Execute `git status --short` and `git diff --check`.
5. **Step 5 — Final Report & Staging Request:** Present the completed dossier for staging and commit authorization.

---

## 16. Final Classification

**A — READY FOR IMPLEMENTATION**

The audit has confirmed all underlying repository facts, established clear boundaries between codebase reality and legal/seller representations, and designed an airtight, evidence-backed structure for documents 15 through 18.

---

## Reference Lists

### Files Inspected
- `LICENSE`
- `render.yaml`
- `pyproject.toml`
- `apps/dashboard/package.json`
- `apps/trading-engine/src/config.py`
- `apps/trading-engine/src/routes/broker_sandbox.py`
- `apps/trading-engine/src/services/onboarding_service.py`
- `libraries/domain/billing/config.py`
- `libraries/domain/legal/content/TERMS_OF_SERVICE_v1.0.md`
- `libraries/domain/legal/content/PRIVACY_POLICY_v1.0.md`
- `libraries/domain/organization/permissions.py`
- `libraries/infrastructure/billing/config.py`
- `libraries/infrastructure/billing/stripe_adapter.py`
- `libraries/infrastructure/communication/email_service.py`
- `libraries/infrastructure/execution/oanda_execution.py`
- `libraries/infrastructure/market_data/config.py`
- `docs/acquisition/01-EXECUTIVE-BRIEF.md` through `14-INFRASTRUCTURE-TOPOLOGY-MAP.md`
- `docs/EPIC-016-PRODUCTION-DEPLOYMENT-AND-SAAS-FOUNDATION.md`
- `docs/EPIC-019-FINAL-BILLING-REPORT.md`
- `docs/EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md`

### Relevant Repository Paths
- `apps/trading-engine/` — Backend FastAPI application
- `apps/dashboard/` — Frontend React dashboard
- `libraries/domain/` — Core trading, risk, strategy, and business domain logic
- `libraries/infrastructure/` — Adapters for database, Redis, broker, billing, email, market data
- `alembic/versions/` — 15 database schema migrations
- `docker/` — Container build configurations
- `backup/` — Database backup and restore shell scripts
- `docs/acquisition/` — Complete acquisition due-diligence data room

### External Services Discovered
- **GitHub:** `https://github.com/Kiran190306/Project-ORION.git` (Source code repository)
- **Render Cloud PaaS:** Host for Web API, Dashboard, PostgreSQL 15, Redis 7
- **Stripe:** Billing subscription integration (Stripe Test Mode only)
- **TwelveData:** Market data provider integration (`api.twelvedata.com`)
- **OANDA:** Broker sandbox practice integration (`api-fxpractice.oanda.com`)
- **External SMTP Relay:** Outbound transactional email service
- **AWS S3 / Cloudflare R2:** Documented targets for offsite database backup replication

### Ownership-Sensitive Items
- **Git Authorship:** Single committer `Kiran Thange <thangekiran2006@gmail.com>`.
- **GitHub Namespace:** `Kiran190306` (personal namespace).
- **Domain Template:** `oriontrading.io` (referenced in email configuration).
- **Brand Name:** "Project ORION" (unregistered mark).
- **Render Cloud Workspace:** Currently active hosting instances on `*.onrender.com`.

### Unresolved Questions for Seller / Legal Counsel
1. Is Kiran Thange selling the asset as an individual, or through an incorporated entity?
2. Is `oriontrading.io` currently registered and owned by the seller?
3. What is the preferred GitHub transfer mechanism (direct transfer vs organization transfer vs mirror push)?
4. Will the seller transfer the Render workspace, or will the buyer deploy the blueprint from scratch?

---

## IMPLEMENTATION GATE

**Status:** **READY FOR IMPLEMENTATION**
The repository audit is complete and the factual boundaries are verified. Documents 15 through 18 are fully mapped and ready to be created upon human authorization.

*No implementation has occurred.*
*No commits have been created.*
*No code has been pushed.*
