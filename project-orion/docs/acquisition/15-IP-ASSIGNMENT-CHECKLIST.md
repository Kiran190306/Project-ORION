# Project ORION — Intellectual Property Assignment & Asset Checklist

**Document Version:** 1.0.0
**Target Milestone:** EPIC-027 Phase 7B Acquisition Due Diligence
**Repository Working Copy:** `project-orion/`
**Classification:** Confidential — Due Diligence Technical Data Room (Tier 3 / Closing)
**Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Capital at Risk — Outright Software Asset Sale)

---

## 1. Executive Summary & Legal Framework

This Intellectual Property (IP) Assignment Checklist establishes the comprehensive asset inventory, chain-of-title audit, and legal handover requirements for the outright software asset sale of **Project ORION**.

### Scope of the Asset Transaction
Project ORION is structured strictly as an outright software and intellectual-property asset transaction. The transaction contemplates the complete transfer of proprietary source code, algorithmic strategy definitions, architectural blueprints, database migration chains, automated test suites, deployment scripts, and technical documentation comprising the `project-orion` repository.

### Classification Taxonomy
To provide absolute clarity during buyer technical and legal due diligence, all checklist items are classified into five explicit evidentiary tiers:
1. `[REPOSITORY-SUPPORTED FACT]`: Verifiable directly from repository commit logs, source files, or build manifests.
2. `[SELLER VERIFICATION REQUIRED]`: Requires factual affirmation or disclosure by the seller outside repository files.
3. `[BUYER VERIFICATION REQUIRED]`: Requires independent technical audit, execution, or validation by the buyer.
4. `[LEGAL REVIEW REQUIRED]`: Governed by definitive legal instruments drafted and negotiated by legal counsel.
5. `[NOT ESTABLISHED]`: Explicitly unevidenced in repository files; must not be assumed or fabricated.

> [!IMPORTANT]
> **LEGAL NOTICE ON TITLE:** While the repository provides technical provenance (e.g., git commit logs, license headers, and file timestamps), repository contents and git commit histories do not constitute legal title or a warranty of non-infringement under applicable property law. Final transfer of legal ownership requires bilateral execution of a definitive Software Asset Purchase Agreement (APA), Bill of Sale, and formal IP Assignment Agreement.

---

## 2. Comprehensive Due-Diligence Checklist

### 1. Proprietary Source Code
- **Status:** `[REPOSITORY-SUPPORTED FACT]`
- **Repository Evidence:**
  - Backend Engine: `apps/trading-engine/src/` (FastAPI services, domain routers, middleware, event loop, telemetry).
  - Frontend Application: `apps/dashboard/src/` (React 18 SPA, UI views, state stores, charting components).
  - Domain Libraries: `libraries/domain/` (execution, risk rules, strategies, portfolio, multi-tenant RBAC, billing, legal models).
  - Infrastructure Adapters: `libraries/infrastructure/` (SQLAlchemy async models, Redis caching, market data, broker adapters, email dispatch).
- **Transfer Action:** 100% of proprietary source code is encapsulated within the repository and transfers with repository delivery.

### 2. Git Repository & Remote Provenance
- **Status:** `[REPOSITORY-SUPPORTED FACT]` / `[SELLER VERIFICATION REQUIRED]`
- **Repository Evidence:**
  - Remote Origin: `https://github.com/Kiran190306/Project-ORION.git`.
  - Local repository contains complete Git object database (`.git`), commit graph, and branch pointers (`main`).
- **Seller Verification Required:** Seller must confirm sole administrative control over the GitHub repository and execute formal repository transfer or provide a clean mirror push to the buyer's organization.

### 3. Git History & Authorship Audit
- **Status:** `[REPOSITORY-SUPPORTED FACT]` / `[LEGAL REVIEW REQUIRED]`
- **Repository Evidence:**
  - Exactly **46 commits** span the repository lifecycle from `2026-07-18 18:13:02 +0530` to `2026-09-24 00:53:20 +0530`.
  - **100% of commits** are authored and committed by a single individual identity: `Kiran Thange <thangekiran2006@gmail.com>`.
  - Exactly zero merge commits from external branches, zero pull requests from external contributors, and zero commits from bot accounts exist in the git history.
- **Legal Review Distinction:** Git authorship demonstrates technical provenance and commit contribution, but is **not legally equivalent to legal title**. Seller legal counsel must warrant that no external parties, employers, or contractors possess claims to these contributions.

### 4. Technical Documentation & Acquisition Dossiers
- **Status:** `[REPOSITORY-SUPPORTED FACT]`
- **Repository Evidence:**
  - Complete 18-document acquisition data room under `docs/acquisition/` (Documents 01 through 18).
  - Architectural Decision Records (ADRs 001–007) under `docs/adr/`.
  - Domain architecture specifications under `docs/domain/`.
  - Epic completion and quality gate reports under `docs/EPIC-*.md`.
- **Transfer Action:** All documentation is authored in standard Markdown and transfers unencumbered with the repository.

### 5. Relational Database Schema Migrations
- **Status:** `[REPOSITORY-SUPPORTED FACT]`
- **Repository Evidence:**
  - Exactly 15 linear Alembic database migrations (`alembic/versions/0001_...` through `0015_...`).
  - Authoritative HEAD revision: `0015_onboarding_progress`.
  - Migration execution and rollback procedures detailed in `docs/acquisition/10-DATABASE-MIGRATION-GUIDE.md`.
- **Transfer Action:** Complete DDL definitions and historical schema versions transfer as proprietary code assets.

### 6. Infrastructure & Deployment Configuration
- **Status:** `[REPOSITORY-SUPPORTED FACT]`
- **Repository Evidence:**
  - Cloud deployment blueprint: `render.yaml` (specifying PostgreSQL 15, Redis 7, Trading Engine API, and Dashboard SPA).
  - Containerization manifests: `docker/apps/trading-engine/Dockerfile`, `apps/dashboard/Dockerfile`.
  - Deployment scripts: `scripts/deploy/migrate.py`.
- **Transfer Action:** Re-usable Infrastructure-as-Code (IaC) blueprints transfer unencumbered.

### 7. Automated Test Suites & Quality Verification
- **Status:** `[REPOSITORY-SUPPORTED FACT]`
- **Repository Evidence:**
  - Comprehensive unit, integration, and security test suites located in `tests/`.
  - Frontend test suites located in `apps/dashboard/src/**/__tests__/`.
  - Documented physical restore demonstration: `docs/EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md`.
- **Buyer Verification Required:** Buyer runs automated suites (`poetry run pytest`, `npm run test`) to verify test execution and passing status.

### 8. Operational & Maintenance Scripts
- **Status:** `[REPOSITORY-SUPPORTED FACT]`
- **Repository Evidence:**
  - Database backup script: `backup/database-backup.sh`.
  - Database restore script: `backup/restore-database.sh`.
  - Retention enforcement script: `backup/retention-policy.sh`.
- **Transfer Action:** All operational utility scripts transfer as part of repository tooling.

### 9. Branding, Trademarks & Product Nomenclature
- **Status:** `[REPOSITORY-SUPPORTED FACT]` / `[NOT ESTABLISHED]` / `[LEGAL REVIEW REQUIRED]`
- **Repository Evidence:**
  - Product name "Project ORION" and associated UI styling/logos in `apps/dashboard/src/assets/`.
- **Not Established in Repository:** No registered trademark certificates, state/federal trademark serial numbers, or Madrid Protocol filings exist in repository files.
- **Legal Review Required:** "Project ORION" is transferred as an unregistered common-law trade name and brand asset. Buyer legal counsel must conduct independent trademark clearance in buyer's target operating jurisdictions.

### 10. Proprietary Copyright Notices
- **Status:** `[REPOSITORY-SUPPORTED FACT]`
- **Repository Evidence:**
  - Root `LICENSE` file asserts:
    ```text
    PROPRIETARY SOFTWARE LICENSE AGREEMENT
    Copyright (c) 2026 Project ORION. All rights reserved.
    ```
  - Terms of Service (`libraries/domain/legal/content/TERMS_OF_SERVICE_v1.0.md`, Section 5) asserts proprietary copyright protection over all algorithms, interfaces, and visual designs.
- **Transfer Action:** Seller warrants that all proprietary copyright notices will be assigned exclusively to the buyer upon closing.

### 11. Third-Party Open-Source Dependencies
- **Status:** `[REPOSITORY-SUPPORTED FACT]` / `[BUYER VERIFICATION REQUIRED]`
- **Repository Evidence:**
  - Exhaustive Software Bill of Materials (SBOM) cataloged in `docs/acquisition/12-DEPENDENCY-SBOM.md`.
  - Backend dependencies managed via `pyproject.toml` and `poetry.lock`.
  - Frontend dependencies managed via `apps/dashboard/package.json` and `package-lock.json`.
- **Buyer Action:** Buyer audits dependencies against buyer corporate open-source policies.

### 12. Dependency Licenses & Legal Compliance
- **Status:** `[REPOSITORY-SUPPORTED FACT]` / `[LEGAL REVIEW REQUIRED]`
- **Repository Evidence:**
  - 100% of runtime production libraries utilize permissive open-source licenses: MIT, Apache-2.0, BSD-3-Clause, ISC, and PSF.
  - Zero copyleft licenses (e.g. GPL, AGPL) exist within production runtime container images.
- **Legal Review Required:** Legal confirmation that declared licenses match upstream registry terms (see legal disclaimer in `12-DEPENDENCY-SBOM.md`).

### 13. Developer-Only Tooling Quarantine
- **Status:** `[REPOSITORY-SUPPORTED FACT]`
- **Repository Evidence:**
  - The Python code linter `pylint` (licensed under GPL-2.0-or-later) is strictly quarantined within `poetry.group.dev.dependencies`.
  - Developer tooling is excluded from Docker container images and production deployment builds (`render.yaml`).
- **Conclusion:** No GPL reciprocal obligations attach to Project ORION proprietary source code.

### 14. External SaaS & Cloud Integrations
- **Status:** `[REPOSITORY-SUPPORTED FACT]` / `[NOT ESTABLISHED]`
- **Repository Evidence:**
  - Software contains adapters for Render, Stripe Test Mode, TwelveData, OANDA Practice API, and SMTP relay.
- **Not Established:** Third-party vendor accounts are **not repository assets**. As detailed in `16-ACCOUNT-OWNERSHIP-TRANSFER.md`, external SaaS accounts require buyer provisioning.

### 15. Generated Data & Test Artifacts
- **Status:** `[REPOSITORY-SUPPORTED FACT]`
- **Repository Evidence:**
  - Backtest results, optimization surfaces, and synthetic market candles are ephemeral or test artifacts.
  - No customer proprietary trading models or personal financial data exist in the database schema or seed files.
- **Transfer Action:** All test fixtures and sample data transfer with the repository.

### 16. Employee, Contractor & Invention-Assignment Verification
- **Status:** `[NOT ESTABLISHED]` / `[SELLER VERIFICATION REQUIRED]` / `[LEGAL REVIEW REQUIRED]`
- **Not Established in Repository:** The repository does not contain employment contracts, proprietary information and inventions agreements (PIIA), or contractor assignment agreements.
- **Seller Verification Required:** Seller must formally represent and warrant that:
  1. The software was developed solely by the identified contributor without unauthorized assistance.
  2. No third-party employer facilities, equipment, or confidential IP were utilized during development.
  3. No former employer or client possesses a valid "work-made-for-hire" or assignment claim.

### 17. Seller Legal Identity & Title Representation
- **Status:** `[NOT ESTABLISHED]` / `[SELLER VERIFICATION REQUIRED]` / `[LEGAL REVIEW REQUIRED]`
- **Not Established in Repository:** "Project ORION" is an asset title; the legal entity or individual holding formal legal title is not defined within the codebase.
- **Seller Verification Required:** Seller must provide certificate of incorporation / good standing (if a corporate entity) or government-issued identification (if an individual proprietor).

### 18. Formal IP Assignment Agreement
- **Status:** `[LEGAL REVIEW REQUIRED]`
- **Requirements:** A comprehensive bilateral contract assigning to the buyer:
  - All copyrights, design rights, and moral rights (where waiveable).
  - All patent rights, trade secret rights, and algorithmic know-how.
  - All rights to enforce past, present, and future infringement claims.

### 19. Bill of Sale & Receipt of Consideration
- **Status:** `[LEGAL REVIEW REQUIRED]`
- **Requirements:** Formal Bill of Sale transferring tangible and intangible software assets in exchange for the agreed commercial purchase consideration.

### 20. Trademark & Patent Verification
- **Status:** `[NOT ESTABLISHED]` / `[SELLER VERIFICATION REQUIRED]` / `[LEGAL REVIEW REQUIRED]`
- **Not Established in Repository:** Zero registered patents or trademarks exist.
- **Seller Representation Required:** Seller warrants that to seller's knowledge, the software does not infringe any third-party patent or trademark, and seller has received no cease-and-desist notices or infringement threats.

### 21. Open-Source Compliance Sign-Off
- **Status:** `[BUYER VERIFICATION REQUIRED]`
- **Requirements:** Buyer's open-source compliance officer or external counsel signs off on the SBOM audit (`12-DEPENDENCY-SBOM.md`), confirming compatibility with buyer's commercial deployment plans.

### 22. Buyer Acceptance & Closing Protocol
- **Status:** `[BUYER VERIFICATION REQUIRED]` / `[LEGAL REVIEW REQUIRED]`
- **Requirements:**
  - Technical verification of repository clone, test suite pass rate, and container build.
  - Mutual execution of definitive transaction agreements.
  - Exchange of purchase consideration and release of administrative control.

---

## 3. Due-Diligence Summary Matrix

| Checklist Item | Evidentiary Tier | Primary Repository Location | Seller Action Required | Buyer Action Required |
|---|:---:|---|---|---|
| **01. Source Code** | `[REPOSITORY-SUPPORTED FACT]` | `apps/`, `libraries/` | Deliver repository commit access | Technical inspection & clone |
| **02. Git Repository** | `[REPOSITORY-SUPPORTED FACT]` | Remote: `Kiran190306/Project-ORION` | Execute transfer or mirror push | Accept repository into buyer org |
| **03. Git History** | `[REPOSITORY-SUPPORTED FACT]` | 46 commits (single author) | Warrant unencumbered sole title | Audit commit provenance |
| **04. Documentation** | `[REPOSITORY-SUPPORTED FACT]` | `docs/`, `docs/acquisition/` | Transfer documentation assets | Review technical specifications |
| **05. Migrations** | `[REPOSITORY-SUPPORTED FACT]` | `alembic/versions/` (15 files) | Warrant complete schema chain | Verify migration upgrade/downgrade |
| **06. IaC Blueprints** | `[REPOSITORY-SUPPORTED FACT]` | `render.yaml`, `docker/` | Transfer configuration files | Verify blueprint syntax |
| **07. Test Suites** | `[REPOSITORY-SUPPORTED FACT]` | `tests/` | None | Execute pytest / vitest gates |
| **08. Utility Scripts**| `[REPOSITORY-SUPPORTED FACT]` | `backup/`, `scripts/` | Transfer operational scripts | Verify script execution |
| **09. Trademarks** | `[NOT ESTABLISHED]` | Common-law "Project ORION" | Disclose any known conflicts | Trademark clearance search |
| **10. Copyrights** | `[REPOSITORY-SUPPORTED FACT]` | `LICENSE`, legal models | Assign all copyright interests | Record assignment documentation |
| **11. Open Source** | `[REPOSITORY-SUPPORTED FACT]` | `pyproject.toml`, `package.json` | None | Legal open-source audit |
| **12. Licenses** | `[REPOSITORY-SUPPORTED FACT]` | Documented in `12-DEPENDENCY-SBOM` | None | Verify permissive licensing |
| **13. GPL Tooling** | `[REPOSITORY-SUPPORTED FACT]` | `poetry.group.dev` (`pylint`) | None | Confirm dev-only quarantine |
| **14. SaaS Accounts**| `[NOT ESTABLISHED]` | External dependencies | Document account handover | Independently provision accounts |
| **15. Test Data** | `[REPOSITORY-SUPPORTED FACT]` | `tests/fixtures/` | None | Verify absence of personal data |
| **16. PIIA / Title** | `[SELLER VERIFICATION REQUIRED]`| Not in repository | Execute title representations | Legal due diligence on chain of title |
| **17. Seller Entity**| `[SELLER VERIFICATION REQUIRED]`| Not in repository | Provide proof of entity/identity | Entity verification & KYC |
| **18. Assignment** | `[LEGAL REVIEW REQUIRED]` | Closing documentation | Execute IP Assignment | Execute IP Assignment |
| **19. Bill of Sale** | `[LEGAL REVIEW REQUIRED]` | Closing documentation | Execute Bill of Sale | Execute Bill of Sale |
| **20. Patents** | `[NOT ESTABLISHED]` | Zero patents in repository | Non-infringement representation | Freedom-to-operate analysis |
| **21. OSS Sign-off** | `[BUYER VERIFICATION REQUIRED]` | Documented in `12-DEPENDENCY-SBOM` | None | Sign off on OSS license audit |
| **22. Acceptance** | `[BUYER VERIFICATION REQUIRED]` | Quality gates & runbooks | Execute transfer protocols | Complete technical acceptance |

---

## 4. Closing Protocol & Document Execution Sequence

```
                    ┌──────────────────────────────────────────────┐
                    │ 1. Preliminary Technical Due Diligence       │
                    │    - Buyer inspects code & runs tests        │
                    │    - Buyer reviews SBOM & Architecture       │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ 2. Legal Disclosures & Chain-of-Title Review │
                    │    - Seller proves legal identity & title    │
                    │    - Seller confirms sole author / no liens  │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ 3. Execution of Definitive Transaction Docs  │
                    │    - Software Asset Purchase Agreement (APA) │
                    │    - Bill of Sale & IP Assignment Agreement  │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ 4. Technical Asset Transfer & Handover       │
                    │    - GitHub repository ownership transferred │
                    │    - Cloud infrastructure blueprint deployed │
                    │    - Buyer provisions independent SaaS keys  │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ 5. Post-Closing Acceptance & Fund Release    │
                    │    - Buyer verifies deployment in buyer PaaS │
                    │    - Escrow release / Closing complete       │
                    └──────────────────────────────────────────────┘
```

---

## 5. Non-Reliance & Disclaimer Notice

1. **Independent Legal Advice:** This checklist is an architectural due-diligence document prepared to assist engineering and legal teams during commercial negotiations. It does not constitute legal advice. Both buyer and seller must retain independent legal counsel.
2. **Repository Boundary:** All representations regarding code structure, testing, architecture, and licensing reflect the state of the codebase at commit `29494cf`. Subsequent commits, branches, or modifications outside this working tree are excluded.
3. **No Implied Warranties:** Except as explicitly set forth in definitive bilateral legal agreements, the repository is provided on an "as is" software asset basis without statutory warranties of merchantability or fitness for a particular commercial purpose.
