# Project ORION — Data Room Access Runbook
## Staged Due Diligence Protocol & Information Disclosure Architecture

```
Document Reference: docs/acquisition/launch/05-DATA-ROOM-ACCESS-RUNBOOK.md
Document Version:   1.0.0
Release Status:     Acquisition Diligence Launch Package
Source Baseline:    Repository Git Commit d5908d0a0cc2feff99fa02573adb12b8eea33782
Canonical System:   Project ORION — Quantitative FX Research & Paper-Trading SaaS
Execution Boundary: Strictly Paper Trading ($100,000 Virtual Starting Balance; $0.00 Live Capital at Risk)
Commercial Status:  Pre-revenue / Commercial Traction Not Established in Repository
```

---

## 1. Purpose

This runbook defines the formal operational procedure by which qualified prospective acquirers, their technical leadership, and legal counsel access, review, and evaluate the **18 canonical due diligence dossiers** and supporting technical artifacts of **Project ORION** (Quantitative FX Research & Paper-Trading SaaS).

The objective is to provide a structured, transparent, and legally disciplined information disclosure pathway that protects sensitive architectural details and trade secrets while facilitating thorough buyer due diligence.

---

## 2. Disclosure Principles

All diligence disclosure activities are governed by five core operational principles:

1. **Progressive Disclosure**: Information is released in four discrete tiers, moving from high-level architectural concepts to detailed operational guides, security profiles, and transaction assignment schedules as buyer commitment and qualification advance.
2. **Source-of-Truth Rigor**: All disclosed information is strictly grounded in repository evidence (`project-orion` at commit baseline `d5908d0a0cc2feff99fa02573adb12b8eea33782`). No speculative, unverified, or forward-looking claims may be introduced.
3. **Execution Boundary Transparency**: Prospective buyers must be informed at every stage that execution is strictly simulated (`PaperExecutionAdapter`, `is_paper=True`), maintaining a $100,000 virtual starting balance with exactly $0.00 live financial capital at risk.
4. **Commercial Truthfulness**: Commercial status must be disclosed as `Pre-revenue / Commercial Traction Not Established in Repository`. Subscription tiers ($0 Sandbox, $99 Pro, $299 Business, Custom Enterprise) reflect built-in SaaS code configuration, not historical subscriber volume.
5. **Zero Live Credential Sharing**: Production API keys, third-party vendor secrets, and developer passwords are never stored in or disclosed via the data room. All third-party vendor services are marked `BUYER-PROVISIONED`.

---

## 3. Initial Information Package (Public / Pre-NDA)

Before execution of formal confidentiality agreements, prospective buyers who meet initial screening criteria may receive the Public Acquisition Information Package:

- **Acquisition Listing**: `docs/acquisition/launch/01-ACQUISITION-LISTING.md`
- **Buyer Pitch Memo**: `docs/acquisition/launch/02-BUYER-PITCH-MEMO.md`
- **Executive Brief PDF**: `docs/acquisition/presentation/visual/pdf/01-EXECUTIVE-BRIEF.pdf` (1 A4 page overview)
- **High-Level Visual Assets**: Platform UI flow and core workflow lifecycle diagrams.

This package provides complete functional and technical orientation without exposing granular schema details, operational runbooks, or IP assignment schedules.

---

## 4. NDA / Confidentiality Boundary

Access to detailed technical, operational, security, and transaction documentation (Tiers 1 through 4) is granted exclusively after formal execution of confidentiality documentation:

> **Confidentiality Standard**: Access requires an **"NDA or equivalent confidentiality agreement, as agreed by the transaction parties."**

### Procedure:
1. Seller provides a standard bilateral Non-Disclosure Agreement (or reviews buyer's corporate NDA).
2. The agreement must explicitly cover:
   - Proprietary source code architecture, algorithm designs, and mathematical models.
   - Database schemas, migration scripts, and operational procedures.
   - Security controls, vulnerability assessments, and disaster recovery metrics.
   - Bilateral transaction discussions, negotiations, and pricing proposals.
3. Execution is completed via authorized electronic signature by legal representatives of both parties.
4. Upon countersignature, buyer is provisioned with a secure, tracked data room account.

---

## 5. Tier 1 Access: Platform Orientation & Core Architecture

**Prerequisite**: Executed NDA or equivalent confidentiality agreement.  
**Audience**: Founder, CEO, CTO, Head of Product, Lead Quant.

### Disclosed Dossiers:
- **Dossier 01 — Executive Brief** (`docs/acquisition/01-EXECUTIVE-BRIEF.md`): High-level executive synthesis, core metrics, tech stack summary, and IP transfer summary.
- **Dossier 02 — Product Overview** (`docs/acquisition/02-PRODUCT-OVERVIEW.md`): End-to-end product taxonomy, user journeys, feature matrix, RBAC role definitions, and subscription tier boundaries ($0/$99/$299/Custom).
- **Dossier 03 — Architecture Overview** (`docs/acquisition/03-ARCHITECTURE-OVERVIEW.md`): System architecture, Domain-Driven Design (DDD) layering, service interactions, Strategy Registry, backtest engine, and execution simulation boundaries.

### Supporting Artifacts:
- Visual Presentation Slides: `docs/acquisition/presentation/visual/pptx/01-BUYER-PRESENTATION.pptx`
- Architecture Topology SVG: `docs/acquisition/presentation/visual/svg/01-ARCHITECTURE-TOPOLOGY-MAP.svg`
- Core Workflow Lifecycle SVG: `docs/acquisition/presentation/visual/svg/03-CORE-WORKFLOW-LIFECYCLE.svg`

---

## 6. Tier 2 Access: Technical Handover & Operational Runbooks

**Prerequisite**: Successful Tier 1 review and confirmed technical qualification (`QUALIFIED FOR DISCUSSION`).  
**Audience**: CTO, VP of Engineering, Lead Software Engineers, System Architects.

### Disclosed Dossiers:
- **Dossier 04 — Technical Handover Guide** (`docs/acquisition/04-TECHNICAL-HANDOVER-GUIDE.md`): Comprehensive codebase structure, local development environment setup, dependencies, build procedures, and test suite execution.
- **Dossier 05 — Deployment Handover** (`docs/acquisition/05-DEPLOYMENT-HANDOVER.md`): PaaS configuration, Render blueprint specifications (`render.yaml`), multi-stage Docker build, and container topology.
- **Dossier 06 — Operations Runbook** (`docs/acquisition/06-OPERATIONS-RUNBOOK.md`): Day-to-day operations, log aggregation, Prometheus metrics scraping, health probe monitoring, and autonomous worker management.
- **Dossier 07 — Security Overview** (`docs/acquisition/07-SECURITY-OVERVIEW.md`): Threat model, JWT authentication lifecycle, RBAC enforcement matrix (7 roles, 41 permissions), CORS/CSP headers, and secret management hygiene.
- **Dossier 08 — Backup & Restore Runbook** (`docs/acquisition/08-BACKUP-RESTORE-RUNBOOK.md`): PostgreSQL disaster recovery procedures, point-in-time recovery, schema verification, and historical ~7.2s restoration test record.
- **Dossier 09 — API Documentation** (`docs/acquisition/09-API-DOCUMENTATION.md`): Complete inventory of 24 FastAPI routers, OpenAPI 3.0 schemas, authentication headers, error envelopes, and endpoint signatures.
- **Dossier 10 — Database Migration Guide** (`docs/acquisition/10-DATABASE-MIGRATION-GUIDE.md`): Relational schema map across 29 tables, 15 versioned Alembic migrations, tenant isolation foreign keys, and upgrade/downgrade procedures.

### Supporting Artifacts:
- Database Entity-Relationship SVG: `docs/acquisition/presentation/visual/svg/02-DATABASE-ERD.svg`
- Security Architecture Map SVG: `docs/acquisition/presentation/visual/svg/05-SECURITY-ARCHITECTURE.svg`

---

## 7. Tier 3 Access: Environment Specifications, SBOM & Known Limitations

**Prerequisite**: Deep engineering diligence and formal interest in transaction structuring.  
**Audience**: Security Officers, DevOps Leads, Legal/Compliance Counsel.

### Disclosed Dossiers:
- **Dossier 11 — Environment Variable Reference** (`docs/acquisition/11-ENVIRONMENT-VARIABLE-REFERENCE.md`): Comprehensive audit of all runtime environment variables, default values, sensitivity ratings, and validation rules.
- **Dossier 12 — Dependency SBOM & Open Source Audit** (`docs/acquisition/12-DEPENDENCY-SBOM.md`): Software Bill of Materials covering all Python and npm dependencies, license classifications (MIT, Apache-2.0, BSD-3-Clause), and zero GPL/AGPL copyleft verification.
- **Dossier 13 — Known Limitations** (`docs/acquisition/13-KNOWN-LIMITATIONS.md`): Full, transparent disclosure of system constraints (paper execution only, OANDA Practice only, Stripe Test Mode, disabled worker by default, single-process worker, lack of external pentest, absence of SOC 2 certification).
- **Dossier 14 — Infrastructure Topology Map** (`docs/acquisition/14-INFRASTRUCTURE-TOPOLOGY-MAP.md`): Network topology, ingress routing, PaaS service isolation, database connection pooling, and baseline configuration hosting estimate (~$14/month).

### Supporting Artifacts:
- Infrastructure Topology SVG: `docs/acquisition/presentation/visual/svg/04-INFRASTRUCTURE-TOPOLOGY.svg`

---

## 8. Tier 4 Access: IP Assignment, Account Transfer & Transaction Closing

**Prerequisite**: Active transaction negotiations, agreed Non-Binding Term Sheet or Letter of Intent (LOI).  
**Audience**: Corporate Development, Transaction Legal Counsel, Managing Partners.

### Disclosed Dossiers:
- **Dossier 15 — IP Assignment Checklist** (`docs/acquisition/15-IP-ASSIGNMENT-CHECKLIST.md`): Proprietary software scope definition ("Proposed Transferable Software / IP Scope, subject to executed transaction agreements"), copyright assignment mechanics, third-party software disclosures, and developer waiver verification.
- **Dossier 16 — Account Ownership Transfer** (`docs/acquisition/16-ACCOUNT-OWNERSHIP-TRANSFER.md`): Master checklist designating all cloud, database, payment, data, and broker services as `BUYER-PROVISIONED`, establishing clean vendor account boundaries.
- **Dossier 17 — Domain Transfer Checklist** (`docs/acquisition/17-DOMAIN-TRANSFER-CHECKLIST.md`): DNS registrar transfer mechanics, DNS zone file export, SSL certificate rotation, and domain ownership handover.
- **Dossier 18 — Due Diligence Data Room Index** (`docs/acquisition/18-DUE-DILIGENCE-DATA-ROOM-INDEX.md`): Master navigation index, SHA-256 verification hashes, cross-reference matrix, and document version tracking.

---

## 9. Technical Diligence Protocol

During technical due diligence, the buyer's engineering team is permitted to conduct structured investigations:

1. **Architecture Walkthrough**: A scheduled 60-minute technical review session with the lead architect walking through `apps/trading-engine/` and `libraries/domain/`.
2. **Codebase Inspection**: Guided or direct read-only repository inspection under NDA to verify:
   - Implementation of Strategy Registry (`libraries/domain/strategy/registry.py`).
   - Mitigation of temporal leakage via `LeakageGuard` controls (`libraries/domain/research/leakage_guard.py`).
   - Walk-Forward Analysis engine (`libraries/domain/research/walk_forward_engine.py`).
   - Paper execution adapter (`libraries/infrastructure/execution/paper_execution.py`).
3. **Test Suite Verification**: Inspection of the 4,260 automated test files and pytest execution logs documenting 4,260 automated tests and 99.4% documented historical test coverage.
4. **Database Inspection**: Verification of the 15 Alembic migration scripts and 29 PostgreSQL table definitions in `libraries/infrastructure/persistence/models/`.

---

## 10. Security Diligence Protocol

During security due diligence, the buyer's security personnel review system controls against `docs/acquisition/07-SECURITY-OVERVIEW.md`:

1. **Authentication & Session Security**: Review of JWT signing (HS256 with configurable RS256 readiness), token expiration, password hashing (bcrypt with per-user salt), and revocation handling.
2. **Authorization Enforcement**: Audit of FastAPI dependency injection enforcing role-based permissions across all 24 routers; verification that tenant-owned application entities are organization-scoped through `organization_id` relationships and authorization controls (migration metadata such as `alembic_version` is decoupled).
3. **HTTP Security Headers**: Inspection of security headers middleware in `main.py` (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Cache-Control: no-store`, strict CORS whitelist).
4. **Vulnerability Disclosure**: Review of known operational boundaries:
   - Project ORION has undergone thorough internal development audits.
   - Project ORION has NOT undergone a third-party penetration test.
   - Project ORION holds NO formal SOC 2, ISO 27001, or PCI-DSS certifications.

---

## 11. IP / Dependency Diligence Protocol

Legal counsel reviews intellectual property provenance and software bill of materials:

1. **Ownership Scope**: Review of "Proposed Transferable Software / IP Scope, subject to executed transaction agreements."
2. **Third-Party Dependency Audit**: Verification against `docs/acquisition/12-DEPENDENCY-SBOM.md`: the documented dependency review identifies MIT, Apache-2.0, and BSD-3-Clause licenses within the reviewed dependency set. Final legal and IP review remains subject to buyer diligence. Third-party dependencies remain subject to their applicable licenses.
3. **Copyleft Review**: The repository dependency review did not identify copyleft licenses (such as GPL-3.0 or AGPL-3.0) within the reviewed production dependency set.
4. **Commit Provenance**: Verification of clean git commit history originating from primary repository development without external disputed contributions.

---

## 12. Commercial Diligence Protocol

Commercial diligence evaluates platform monetization capabilities and economic models:

1. **Pre-Revenue Status**: Buyer acknowledges that customers, subscribers, ARR, MRR, contracts, and historical commercial revenue are `NOT ESTABLISHED IN REPOSITORY` (pre-revenue technology asset).
2. **SaaS Billing Architecture**: Verification of implemented Stripe billing integration in `apps/trading-engine/src/services/billing_service.py` and `routes/billing.py`.
3. **Configured Tiers**: Confirmation of 4 implemented subscription tiers:
   - Free Sandbox ($0/month, 5 backtests/day, 1 paper strategy)
   - Pro Trader ($99/month, 50 backtests/day, 5 paper strategies)
   - Business Prop ($299/month, 500 backtests/day, 20 paper strategies, Walk-Forward Analysis)
   - Enterprise (Custom Contract, unlimited volume, dedicated support)
4. **Hosting Economics**: Review of approximately $14/month baseline configuration hosting estimate based on the documented Render configuration ($7 PostgreSQL + $7 API service); actual cloud pricing may vary and is buyer-provisioned (see `docs/acquisition/14-INFRASTRUCTURE-TOPOLOGY-MAP.md`).

---

## 13. Transaction Diligence Protocol

Transaction diligence defines legal and operational steps leading to closing:

1. **Definitive Agreement Review**: Review of the Software Asset Purchase Agreement (APA) and Bill of Sale.
2. **Closing Checklist Review**: Joint review of `docs/acquisition/launch/07-HANDOVER-CLOSING-CHECKLIST.md`.
3. **Buyer Provisioning Verification**: Confirmation that the buyer has provisioned independent Render, PostgreSQL, Redis, Stripe, TwelveData, and OANDA developer accounts.
4. **Escrow / Settlement**: Escrow, if used, will be governed by the executed transaction agreement and the transaction provider selected by the parties.

---

## 14. Evidence Request Tracking & Artifact Mapping

When a prospective buyer requests specific technical or operational evidence, requests are mapped to canonical repository artifacts. Response timing to be agreed between transaction parties without fixed SLA guarantees:

| Request Category | Approved Response & Disclosed Artifact | Diligence Tracking Protocol |
|:---|:---|:---|
| **Architecture / Topology** | Disclose Dossiers 03 & 14; provide SVG topology maps. | Disclosed upon verification under NDA; response timing to be agreed between transaction parties. |
| **API Endpoints & Schemas** | Disclose Dossier 09 (`09-API-DOCUMENTATION.md`) or exported OpenAPI JSON. | Disclosed upon verification under NDA; response timing to be agreed between transaction parties. |
| **Database Schema / ERD** | Disclose Dossier 10 (`10-DATABASE-MIGRATION-GUIDE.md`) and ERD SVG. | Disclosed upon verification under NDA; response timing to be agreed between transaction parties. |
| **Test Logs & Coverage** | Provide development test execution summary documenting 4,260 automated tests and 99.4% historical coverage. | Disclosed upon verification under NDA; response timing to be agreed between transaction parties. |
| **Disaster Recovery Proof** | Disclose Dossier 08 (`08-BACKUP-RESTORE-RUNBOOK.md`) documenting ~7.2s historical restore benchmark. | Disclosed upon verification under NDA; response timing to be agreed between transaction parties. |
| **Dependency SBOM** | Disclose Dossier 12 (`12-DEPENDENCY-SBOM.md`). | Disclosed upon verification under NDA; response timing to be agreed between transaction parties. |
| **Third-Party Live Accounts** | **Not Provided**: All vendor accounts are strictly `BUYER-PROVISIONED`. | Non-transferable; buyer independently provisions vendor accounts. |

---

## 15. Sensitive Information Handling

To safeguard the intellectual property and maintain strict security hygiene:

1. **No Production Credentials**: The data room contains zero production API keys, database connection strings with live passwords, or private signing keys.
2. **Redaction of Development Secrets**: Any historical local development secrets in test fixtures or mock environments are clearly labeled `MOCK_SECRET_FOR_TESTING_ONLY`.
3. **No Direct Production Database Access**: Prospective buyers are never granted direct access to operational databases or infrastructure prior to closing.
4. **Watermarking & Access Logging**: When utilizing virtual data room software, documents should be watermarked with the buyer's organization name, and access logs must be reviewed weekly.

---

## 16. Final Handover Protocol

Upon execution of definitive transaction agreements and satisfaction of agreed closing conditions (including escrow funding, if applicable):

1. **Data Room Archive**: The complete 18-dossier technical package and launch suite are packaged into an immutable ZIP archive with SHA-256 integrity checksums.
2. **Repository Transfer**: Administrative transfer or push-mirror of the canonical Git repository (`project-orion`) to the buyer's designated GitHub/GitLab organization.
3. **Execution of Closing Checklist**: Both parties systematically execute all 23 items in `docs/acquisition/launch/07-HANDOVER-CLOSING-CHECKLIST.md`.
4. **Seller Access Revocation**: Formal revocation of seller access from repository and transaction communication channels, accompanied by written confirmation of closing.

---
*End of Document — Project ORION Acquisition Launch Suite*
