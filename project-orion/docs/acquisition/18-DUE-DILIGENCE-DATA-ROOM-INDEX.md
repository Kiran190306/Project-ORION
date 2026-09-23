# Project ORION — Master Due Diligence Data Room Index

**Document Version:** 1.0.0
**Target Milestone:** EPIC-027 Phase 7B Acquisition Due Diligence
**Repository Working Copy:** `project-orion/`
**Classification:** Confidential — Due Diligence Technical Data Room (Master Index)
**Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Capital at Risk — Outright Software Asset Sale)

---

## 1. Executive Data Room Architecture & Disclosure Principles

This Master Due Diligence Data Room Index serves as the comprehensive navigational guide and evidence verification matrix for prospective acquirers evaluating the outright software asset sale of **Project ORION**.

### Core Disclosure Principles
1. **Evidence-Based Due Diligence:** Every affirmative technical representation in this data room is verifiable from concrete repository source files, Git commit logs, database migrations, configuration manifests, or automated test executions.
2. **Strict Disclosure of Non-Established Items:** Where corporate, commercial, or legal artifacts do not exist within the software repository (e.g., historical revenue, active customer contracts, formal corporate entity records, trademark registrations), they are explicitly designated as **NOT ESTABLISHED IN REPOSITORY**. No commercial traction or corporate infrastructure is invented or implied.
3. **Three-Tier Access Classification:**
   - **Tier 1 (Public / Introductory / Executive):** High-level strategic dossiers and product architecture overviews suitable for preliminary executive review under standard terms.
   - **Tier 2 (Confidential Technical Due Diligence / Under NDA):** In-depth technical specifications, security models, API catalogs, database migration runbooks, and disaster recovery demonstration certifications.
   - **Tier 3 (Confidential Legal, Transfer & Closing / Binding Stage):** Intellectual property assignment checklists, cloud account handover protocols, domain transfer checklists, and closing execution sequences.

---

## 2. Master Acquisition Dossier Index (Documents 01 through 18)

| Doc ID | Document Title | Tier | Primary Purpose | Repository Evidence / Source | Evidentiary Status |
|:---:|---|:---:|---|---|:---:|
| **01** | `01-EXECUTIVE-BRIEF.md` | Tier 1 | Strategic executive brief, software asset transaction overview, core technical metrics | Monorepo structure, build manifests | **Available** |
| **02** | `02-PRODUCT-OVERVIEW.md` | Tier 1 | Functional capabilities, paper trading workflows, strategy lab, risk controls | `apps/dashboard/`, `libraries/domain/` | **Available** |
| **03** | `03-ARCHITECTURE-OVERVIEW.md` | Tier 2 | System architecture, FastAPI async engine, PostgreSQL asyncpg, Redis, React SPA | `apps/`, `libraries/` | **Available** |
| **04** | `04-TECHNICAL-HANDOVER-GUIDE.md` | Tier 2 | Developer orientation, local setup, Poetry/Node environments, test execution runbook | `pyproject.toml`, `package.json` | **Available** |
| **05** | `05-DEPLOYMENT-HANDOVER.md` | Tier 2 | Render PaaS blueprint, container definitions, migration decoupling, deployment SOPs | `render.yaml`, `docker/` | **Available** |
| **06** | `06-OPERATIONS-RUNBOOK.md` | Tier 2 | Standard operating procedures, service health checks, logs, telemetry, incident runbooks | `apps/trading-engine/src/routes/` | **Available** |
| **07** | `07-SECURITY-OVERVIEW.md` | Tier 2 | RBAC (41 permissions), TenantContext, AES-GCM credential encryption, anti-enumeration | `libraries/domain/organization/` | **Available** |
| **08** | `08-BACKUP-RESTORE-RUNBOOK.md` | Tier 2 | Disaster recovery runbook, demonstrated 7-second physical restore duration (certifying RTO < 60m SLA), and operational RPO target (< 24h) protocol | `backup/`, `docs/EPIC-027-*.md` | **Available** |
| **09** | `09-API-DOCUMENTATION.md` | Tier 2 | Complete REST API specification: 122 endpoints across 19 routers + 4 ASGI docs routes | `apps/trading-engine/src/routes/` | **Available** |
| **10** | `10-DATABASE-MIGRATION-GUIDE.md` | Tier 2 | 15 linear Alembic database schema migrations base to head `0015_onboarding_progress` | `alembic/versions/` (15 scripts) | **Available** |
| **11** | `11-ENVIRONMENT-VARIABLE-REFERENCE.md` | Tier 2 | 44 configuration settings, Twelve-Factor compliance, template drift catalog | `apps/trading-engine/src/config.py` | **Available** |
| **12** | `12-DEPENDENCY-SBOM.md` | Tier 2 | Third-party open-source packages, licenses, SaaS dependencies, legal verification note | `poetry.lock`, `package-lock.json` | **Available** |
| **13** | `13-KNOWN-LIMITATIONS.md` | Tier 2 | Transparent register of 20 architectural, functional, and operational limitations | Codebase-wide audit | **Available** |
| **14** | `14-INFRASTRUCTURE-TOPOLOGY-MAP.md` | Tier 2 | Render cloud topology, VPC private networking, edge routing, egress SaaS integrations | `render.yaml`, network specs | **Available** |
| **15** | `15-IP-ASSIGNMENT-CHECKLIST.md` | Tier 3 | Intellectual property asset scope, single-author git history audit, assignment contracts | Git log (46 commits), `LICENSE` | **Available** |
| **16** | `16-ACCOUNT-OWNERSHIP-TRANSFER.md` | Tier 3 | Cloud workspace, Stripe test mode, TwelveData, OANDA sandbox, and credential rotation | `render.yaml`, service configs | **Available** |
| **17** | `17-DOMAIN-TRANSFER-CHECKLIST.md` | Tier 3 | Render subdomains (`*.onrender.com`), custom domain DNS checklist, email SPF/DKIM/DMARC | `email_service.py`, Render DNS | **Available** |
| **18** | `18-DUE-DILIGENCE-DATA-ROOM-INDEX.md` | Tier 3 | Master data room navigation index, evidence verification matrix, non-established items | All acquisition documents | **Available** |

---

## 3. Explicit Due-Diligence Disclosure Register (Non-Established Items)

To protect both buyer and seller during technical due diligence, the table below provides transparent accounting of items commonly reviewed during mergers and acquisitions that are **NOT established within repository files**:

| Subject Area | Scope / Question | Repository Status | Clarification & Due-Diligence Guidance |
|---|---|:---:|---|
| **Revenue / MRR / ARR** | Historical recurring revenue, sales records, gross margins | **NOT ESTABLISHED IN REPOSITORY** | NOT ESTABLISHED IN REPOSITORY: No historical customer revenue, ARR, or MRR records exist within repository files. As an outright software and intellectual property asset sale, seller verification is required to confirm commercial status. |
| **Customer Contracts** | Active client agreements, SLAs, enterprise contracts | **NOT ESTABLISHED IN REPOSITORY** | NOT ESTABLISHED IN REPOSITORY: No client contracts, customer subscription agreements, or commercial SLAs exist in repository files. |
| **Subscriber Data** | Paying user accounts, customer PII, credit card records | **NOT ESTABLISHED IN REPOSITORY** | NOT ESTABLISHED IN REPOSITORY: The database schema and repository files contain zero customer production data or customer PII; application code enforces Stripe Test Mode. |
| **Financial Statements** | P&L statements, balance sheets, audit reports, tax filings | **NOT ESTABLISHED IN REPOSITORY** | Financial accounting records are external to the software codebase; seller verification required. |
| **Corporate Formation** | Articles of incorporation, state registrations, corporate bylaws | **NOT ESTABLISHED IN REPOSITORY** | "Project ORION" is an asset title. Legal entity identity holding title requires seller legal disclosure. |
| **IP Ownership Title** | Legal title deeds, invention assignments, chain of title | **REPOSITORY-DERIVED / LEGAL REVIEW** | Git history shows single author (`Kiran Thange`); formal legal title requires Bilateral IP Assignment Agreement. |
| **Third-Party Licenses** | Permissive vs copyleft open-source compliance | **REPOSITORY-SUPPORTED FACT** | Audited in `12-DEPENDENCY-SBOM.md`; 100% runtime packages are permissive (MIT, Apache-2.0, BSD, ISC, PSF). |
| **Security Audits** | Formal SOC 2 Type II or ISO 27001 audit certifications | **NOT ESTABLISHED IN REPOSITORY** | Platform verified via internal automated CI tests; no third-party audit reports exist. |
| **Penetration Testing** | External third-party ethical hacking / penetration test reports | **NOT ESTABLISHED IN REPOSITORY** | No third-party penetration testing has been commissioned; buyer must conduct their own security tests. |
| **Vendor Agreements** | Enterprise negotiated contracts with Render, Stripe, TwelveData | **NOT ESTABLISHED IN REPOSITORY** | Software integrates with standard public SaaS APIs; buyer must provision their own vendor commercial accounts. |
| **Cloud Hosting Accounts** | Cross-account administrative transfer of Render PaaS | **NOT ESTABLISHED IN REPOSITORY** | Transferability not guaranteed by PaaS; primary path is deploying `render.yaml` Blueprint in buyer account. |
| **Domain Ownership** | Legal domain registration and WHOIS records for `oriontrading.io` | **NOT ESTABLISHED IN REPOSITORY** | Operational URLs are `*.onrender.com`; custom domain ownership requires seller verification. |
| **Trademark / Patents** | Registered patent numbers, state/federal trademark registrations | **NOT ESTABLISHED IN REPOSITORY** | "Project ORION" is an unregistered mark; no patents or registered trademarks exist in the repository. |
| **Incident History** | Formal corporate security breach logs or outage history | **NOT ESTABLISHED IN REPOSITORY** | Zero security breach logs or incident disclosures exist in repository files. |
| **Corporate Insurance** | Commercial general liability, errors & omissions (E&O), cyber insurance | **NOT ESTABLISHED IN REPOSITORY** | Corporate insurance policies are external to software codebase. |
| **Employment Agreements** | Proprietary Information and Inventions Agreements (PIIA), non-competes | **NOT ESTABLISHED IN REPOSITORY** | Requires seller representation affirming no employer or contractor encumbrances exist. |

---

## 4. Technical Evidence Mapping Matrix

This matrix connects every technical due-diligence assertion to its concrete, inspectable repository artifacts:

```
┌───────────────────────────────────────────────┬─────────────────────────────────────────────────────────┐
│ Technical Due-Diligence Claim                 │ Authoritative Repository Evidence & Source Location     │
├───────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
│ Asynchronous Trading Engine REST API          │ apps/trading-engine/src/main.py, routes/, schemas.py     │
│ Multi-Tenant RBAC (41 Enforced Permissions)   │ libraries/domain/organization/permissions.py            │
│ Strict Paper-Trading Guard ($0.00 Capital)    │ libraries/infrastructure/execution/broker_adapter.py    │
│ Broker Sandbox Practice Execution             │ libraries/infrastructure/execution/oanda_execution.py   │
│ Market Data Feed Ingest & SSRF Guards         │ libraries/infrastructure/market_data/config.py          │
│ Stripe Test Mode Enforcement                  │ libraries/infrastructure/billing/config.py              │
│ Anti-Enumeration Authentication Hardening     │ apps/trading-engine/src/routes/auth.py                  │
│ Relational Schema Evolution (15 Migrations)   │ alembic/versions/0001_... through 0015_...              │
│ Demonstrated 7-Second Physical Disaster Restore│ docs/EPIC-027-PHASE-6C-RESTORE-DEMONSTRATION.md         │
│ Automated Database Backup & Encryption        │ backup/database-backup.sh, backup/restore-database.sh   │
│ Cloud Infrastructure Blueprint (IaC)          │ render.yaml, docker/apps/trading-engine/Dockerfile      │
│ Single-Author Clean Git Commit History        │ Git Log (46 commits: Kiran Thange)                      │
│ Automated Test Suite Coverage (100+ Tests)    │ tests/unit/, tests/integration/, tests/security/        │
│ React 18 Single-Page Application (SPA)        │ apps/dashboard/src/ (Vite, TypeScript, React Router)   │
└───────────────────────────────────────────────┴─────────────────────────────────────────────────────────┘
```

---

## 5. Architectural Decision Records (ADRs) & Engineering History

For engineering due-diligence teams evaluating historical technical trade-offs, seven Architectural Decision Records are maintained in `docs/adr/`:

1. **`ADR-001-high-availability-topology.md`:** Multi-region failover and DNS routing architecture.
2. **`ADR-002-data-storage-strategy.md`:** PostgreSQL relational storage paired with Redis for caching and rate limiting.
3. **`ADR-003-event-broker-selection.md`:** Async in-memory and Redis pub/sub messaging patterns.
4. **`ADR-004-strategy-execution-model.md`:** Autonomous strategy worker lifecycle and thread safety.
5. **`ADR-005-market-data-ingestion.md`:** Real-time quote polling, caching, and stale feed circuit breakers.
6. **`ADR-006-testing-strategy.md`:** Multi-layered testing pyramid (unit, integration, mock broker, security).
7. **`ADR-007-secret-management.md`:** Twelve-Factor environment variable secret management.

---

## 6. Prospective Buyer Technical Due-Diligence Q&A

**Q1: What exactly is being sold in this transaction?**
*A:* An outright software and intellectual property asset sale comprising the entire `project-orion` monorepo: proprietary Python backend services, React frontend application, 15 relational database migrations, algorithmic strategy engines, test suites, container configurations, and operational documentation.

**Q2: Are there active paying customers or subscriber accounts?**
*A:* No. The platform is offered strictly as a software and intellectual property asset. There is no historical customer revenue, ARR, or MRR. The database contains zero production customer records.

**Q3: Can the platform execute live trades on a brokerage right now?**
*A:* No. The platform is structurally constrained to simulated paper trading and broker practice sandbox environments ($0.00 Capital at Risk). Live execution endpoints are actively rejected by software safety guards. Connecting live capital would require the buyer to design and validate production broker adapters at their own discretion.

**Q4: How does the buyer take operational control of the platform?**
*A:* The buyer receives repository ownership, provisions an independent Render account, launches the `render.yaml` Blueprint, restores the database schema via `backup/restore-database.sh`, and configures their own Stripe Test Mode and TwelveData market data credentials.

---

## 7. Data Room Completion & Closing Protocol

When technical and legal due diligence concludes satisfactorily, closing proceeds under the following four-stage execution gate:

```
[Gate 1: Technical Acceptance]
- Buyer clones repository and executes test suite: poetry run pytest
- 100% test pass rate confirmed

[Gate 2: Legal Execution]
- Mutual execution of Software Asset Purchase Agreement (APA)
- Mutual execution of Bill of Sale & IP Assignment Agreement
- Delivery of seller title representations

[Gate 3: Asset Delivery & Account Handover]
- GitHub repository ownership transferred to buyer organization
- Render Blueprint deployed into buyer cloud tenant
- Buyer injects independently generated JWT secrets and API credentials

[Gate 4: Closing & Escrow Release]
- Buyer confirms operational liveness on buyer cloud endpoint
- Escrow purchase consideration released to seller
- Transaction officially closed
```
