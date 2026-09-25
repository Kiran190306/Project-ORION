# Project ORION — Buyer Due Diligence Data Room Guide

**Document Reference:** `docs/acquisition/presentation/07-BUYER-DATA-ROOM-GUIDE.md`  
**Classification:** Confidential — Acquisition Technical Due Diligence  
**Repository Working Copy:** `project-orion/`  
**Git Baseline Commit:** `d5908d0a0cc2feff99fa02573adb12b8eea33782`  
**Navigation Model:** 4-Tier Structured Review for Technical & Commercial Acquirers

---

## 1. Due Diligence Data Room Overview

The Project ORION acquisition closing documentation is organized into 18 exhaustive dossiers under `docs/acquisition/`. This guide establishes an optimized 4-tier reading order tailored for technical buyers, CTOs, legal counsel, and quantitative evaluators.

---

## 2. 4-Tier Buyer Review Navigation Model

```
TIER 1: EXECUTIVE & ARCHITECTURAL ORIENTATION (Initial Review / Executive Sponsors)
  ├── 01-EXECUTIVE-BRIEF.md
  ├── 02-PRODUCT-OVERVIEW.md
  └── 03-ARCHITECTURE-OVERVIEW.md

TIER 2: TECHNICAL DEEP-DIVE & HARNESS AUDIT (Engineering Leadership / Technical Leads)
  ├── 04-TECHNICAL-HANDOVER-GUIDE.md
  ├── 05-DEPLOYMENT-HANDOVER.md
  ├── 06-OPERATIONS-RUNBOOK.md
  ├── 07-SECURITY-OVERVIEW.md
  ├── 08-BACKUP-RESTORE-RUNBOOK.md
  ├── 09-API-DOCUMENTATION.md
  └── 10-DATABASE-MIGRATION-GUIDE.md

TIER 3: OPERATIONAL & DEPENDENCY AUDIT (SRE, Security & Infrastructure Evaluators)
  ├── 11-ENVIRONMENT-VARIABLE-REFERENCE.md
  ├── 12-DEPENDENCY-SBOM.md
  ├── 13-KNOWN-LIMITATIONS.md
  └── 14-INFRASTRUCTURE-TOPOLOGY-MAP.md

TIER 4: TRANSACTION, IP & ACCOUNT TRANSFER (Legal Counsel & Corporate Development)
  ├── 15-IP-ASSIGNMENT-CHECKLIST.md
  ├── 16-ACCOUNT-OWNERSHIP-TRANSFER.md
  ├── 17-DOMAIN-TRANSFER-CHECKLIST.md
  └── 18-DUE-DILIGENCE-DATA-ROOM-INDEX.md
```

---

## 3. Dossier-by-Dossier Review Inventory

### TIER 1: Executive & Architectural Orientation

#### Dossier 01: Executive Brief
* **File:** [`docs/acquisition/01-EXECUTIVE-BRIEF.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/01-EXECUTIVE-BRIEF.md)
* **Audience:** Acquirer CEOs, Heads of Corporate Development, Lead Evaluators.
* **Key Contents:** Executive platform summary, pure software asset positioning, paper-trading capital invariant ($0.00 capital at risk), and high-level technology summary.

#### Dossier 02: Product Overview
* **File:** [`docs/acquisition/02-PRODUCT-OVERVIEW.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/02-PRODUCT-OVERVIEW.md)
* **Audience:** Heads of Product, Quantitative Strategists, Portfolio Managers.
* **Key Contents:** 5-stage research workflow, strategy catalogue profiles, walk-forward analysis, quality gate hurdles, and paper trading execution model.

#### Dossier 03: Architecture Overview
* **File:** [`docs/acquisition/03-ARCHITECTURE-OVERVIEW.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/03-ARCHITECTURE-OVERVIEW.md)
* **Audience:** CTOs, Lead Architects, Senior Software Engineers.
* **Key Contents:** Hexagonal architecture (ports and adapters), FastAPI layer assembly, 21 domain packages, and order execution sequence diagrams.

---

### TIER 2: Technical Deep-Dive & Harness Audit

#### Dossier 04: Technical Handover Guide
* **File:** [`docs/acquisition/04-TECHNICAL-HANDOVER-GUIDE.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/04-TECHNICAL-HANDOVER-GUIDE.md)
* **Audience:** Engineering Onboarding Leads, Core Developers.
* **Key Contents:** Local developer workstation assembly, virtual environment configuration, test runner execution, and code style standards.

#### Dossier 05: Deployment Handover
* **File:** [`docs/acquisition/05-DEPLOYMENT-HANDOVER.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/05-DEPLOYMENT-HANDOVER.md)
* **Audience:** DevOps Engineers, Cloud Infrastructure Architects.
* **Key Contents:** Render PaaS deployment specifications, container build steps, and environment secret injection protocols.

#### Dossier 06: Operations Runbook
* **File:** [`docs/acquisition/06-OPERATIONS-RUNBOOK.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/06-OPERATIONS-RUNBOOK.md)
* **Audience:** SRE Teams, Systems Administrators.
* **Key Contents:** Day-two maintenance procedures, health probe monitoring, log aggregation, and operational troubleshooting.

#### Dossier 07: Security Overview
* **File:** [`docs/acquisition/07-SECURITY-OVERVIEW.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/07-SECURITY-OVERVIEW.md)
* **Audience:** Chief Information Security Officers (CISOs), Security Engineers.
* **Key Contents:** Threat model, JWT authentication, bcrypt password hashing, HTTP security headers, and 7-role RBAC matrix.

#### Dossier 08: Backup & Restore Runbook
* **File:** [`docs/acquisition/08-BACKUP-RESTORE-RUNBOOK.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/08-BACKUP-RESTORE-RUNBOOK.md)
* **Audience:** Database Administrators, Business Continuity Officers.
* **Key Contents:** Physical database restore runbook and documented historical disaster recovery test benchmark (~7.2s across 29 tables).

#### Dossier 09: API Documentation
* **File:** [`docs/acquisition/09-API-DOCUMENTATION.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/09-API-DOCUMENTATION.md)
* **Audience:** Integration Engineers, Frontend Developers.
* **Key Contents:** REST API catalog across all 24 modular FastAPI routers with typed Pydantic v2 schemas.

#### Dossier 10: Database Migration Guide
* **File:** [`docs/acquisition/10-DATABASE-MIGRATION-GUIDE.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/10-DATABASE-MIGRATION-GUIDE.md)
* **Audience:** Data Engineers, Backend Developers.
* **Key Contents:** Alembic version history, 15 linear migration revisions, schema evolution graph, and preDeployCommand hook.

---

### TIER 3: Operational & Dependency Audit

#### Dossier 11: Environment Variable Reference
* **File:** [`docs/acquisition/11-ENVIRONMENT-VARIABLE-REFERENCE.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/11-ENVIRONMENT-VARIABLE-REFERENCE.md)
* **Audience:** DevOps Engineers, Security Officers.
* **Key Contents:** Complete environment configuration reference, default values, validation rules, and secret classification.

#### Dossier 12: Dependency SBOM
* **File:** [`docs/acquisition/12-DEPENDENCY-SBOM.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/12-DEPENDENCY-SBOM.md)
* **Audience:** Open-Source Compliance Officers, Legal Counsel.
* **Key Contents:** Software Bill of Materials, dependency licensing audit (MIT, Apache 2.0, BSD-3-Clause), and vulnerability scan history.

#### Dossier 13: Known Limitations
* **File:** [`docs/acquisition/13-KNOWN-LIMITATIONS.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/13-KNOWN-LIMITATIONS.md)
* **Audience:** Technical Due Diligence Leads, Acquirer Architects.
* **Key Contents:** Transparent documentation of engineering boundaries (stateless REST polling, single-process worker, paper-only execution).

#### Dossier 14: Infrastructure Topology Map
* **File:** [`docs/acquisition/14-INFRASTRUCTURE-TOPOLOGY-MAP.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/14-INFRASTRUCTURE-TOPOLOGY-MAP.md)
* **Audience:** Cloud Architects, Network Engineers.
* **Key Contents:** Cloud network topology, Render resource plans (`starter` API, `basic-1gb` DB), and private network isolation map.

---

### TIER 4: Transaction, IP & Account Transfer

#### Dossier 15: IP Assignment Checklist
* **File:** [`docs/acquisition/15-IP-ASSIGNMENT-CHECKLIST.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/15-IP-ASSIGNMENT-CHECKLIST.md)
* **Audience:** M&A Legal Counsel, Intellectual Property Attorneys.
* **Key Contents:** Proprietary copyright, patent, and trade secret assignment verification, and contributor IP assignment representations.

#### Dossier 16: Account Ownership Transfer
* **File:** [`docs/acquisition/16-ACCOUNT-OWNERSHIP-TRANSFER.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/16-ACCOUNT-OWNERSHIP-TRANSFER.md)
* **Audience:** Corporate Development, Integration Operations.
* **Key Contents:** Vendor account inventory and step-by-step Independent Account Provisioning Path for buyer infrastructure.

#### Dossier 17: Domain Transfer Checklist
* **File:** [`docs/acquisition/17-DOMAIN-TRANSFER-CHECKLIST.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/17-DOMAIN-TRANSFER-CHECKLIST.md)
* **Audience:** IT Operations, Network Administrators.
* **Key Contents:** Custom domain DNS transition runbook and SSL/TLS certificate re-issuance guidelines.

#### Dossier 18: Due Diligence Data Room Index
* **File:** [`docs/acquisition/18-DUE-DILIGENCE-DATA-ROOM-INDEX.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/18-DUE-DILIGENCE-DATA-ROOM-INDEX.md)
* **Audience:** All Due Diligence Participants.
* **Key Contents:** Master data room index, cross-reference tables, and closing dossier inventory.
