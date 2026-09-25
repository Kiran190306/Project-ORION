# Project ORION — Master Sales Package Index & Diligence Directory

**Asset Category:** Pre-Revenue Quantitative Software & Intellectual Property Acquisition
**Asking Price:** $24,900 USD
**Document Reference:** `docs/acquisition/sales/09-SALES-PACKAGE-INDEX.md`

---

## 1. Directory Structure & Authoritative Hierarchy

This index maps the complete buyer-facing acquisition sales suite and connects it to the frozen, authoritative technical due diligence packages within the Project ORION repository.

### Authoritative Hierarchy & Status Rules
```text
TIER 1 (Authoritative Implementation) ──► apps/, libraries/, database/, tests/, render.yaml
TIER 2 (Frozen Canonical Dossiers)    ──► docs/acquisition/ (Dossiers 01 through 18) [FROZEN]
TIER 3 (Frozen Buyer Presentation)     ──► docs/acquisition/presentation/ [FROZEN]
TIER 4 (Frozen Buyer Launch Package)   ──► docs/acquisition/launch/ [FROZEN]
TIER 5 (Active Sales Package)          ──► docs/acquisition/sales/ (This Package)
```

> **Frozen Directory Notice**: Directories `docs/acquisition/` (Dossiers 01–18), `docs/acquisition/presentation/`, and `docs/acquisition/launch/` are **FROZEN**. They serve as verified, unalterable technical diligence baselines. The documents in `docs/acquisition/sales/` provide active sales, outreach, and negotiation materials compiled directly from these frozen sources.

---

## 2. Sales Package Inventory (`docs/acquisition/sales/`)

The sales package consists of 9 structured commercial and outreach documents:

| Document ID | Filename | Primary Purpose | Key Contents & Disclosures |
| :---: | :--- | :--- | :--- |
| **01** | [`01-ACQUISITION-LISTING.md`](01-ACQUISITION-LISTING.md) | Comprehensive Marketplace Listing | Full 26-section acquisition memorandum: $24,900 asking price, capabilities, architecture, safety boundaries, limitations. |
| **02** | [`02-SHORT-LISTING.md`](02-SHORT-LISTING.md) | Short Marketplace & Buyer Outreach Listing | Concise 500-word overview for acquisition marketplaces, direct strategic-buyer outreach, and founder/operator communications. |
| **03** | [`03-BUYER-PITCH.md`](03-BUYER-PITCH.md) | Strategic Buyer Pitch Memorandum | Detailed problem/solution mapping, research workflow, architecture, use cases, and acquisition scope. |
| **04** | [`04-BUYER-OUTREACH-TEMPLATES.md`](04-BUYER-OUTREACH-TEMPLATES.md) | Multi-Persona Outreach Sequences | Email and LinkedIn templates for 5 buyer personas (CEO, CTO, Product, Quant, M&A) with follow-up sequences. |
| **05** | [`05-BUYER-FAQ.md`](05-BUYER-FAQ.md) | Buyer Frequently Asked Questions | 18 factual answers addressing common technical, operational, and commercial buyer questions. |
| **06** | [`06-BUYER-QUALIFICATION.md`](06-BUYER-QUALIFICATION.md) | Buyer Qualification Framework | Neutral intake questionnaire and 5-dimension assessment matrix (Aligned / Clarification / Misaligned). |
| **07** | [`07-DEMO-CALL-SCRIPT.md`](07-DEMO-CALL-SCRIPT.md) | 15-Minute Operator Demo Script | Minute-by-minute live walkthrough script covering Strategy Lab, WFA, deployment governance, and paper execution. |
| **08** | [`08-NEGOTIATION-GUIDE.md`](08-NEGOTIATION-GUIDE.md) | Negotiation & Transaction Guide | Factual guidance on asking price ($24,900), scope separation, closing sequence, and objection handling. |
| **09** | [`09-SALES-PACKAGE-INDEX.md`](09-SALES-PACKAGE-INDEX.md) | Master Sales Directory (This Document) | Architectural navigation index connecting the sales package to all frozen diligence tiers. |

---

## 3. Frozen Canonical Due Diligence Dossiers (`docs/acquisition/01-18`)

The canonical 18-dossier due diligence data room is organized across 4 tiers:

### Tier 1: Executive & Strategic Dossiers
* **[01-EXECUTIVE-BRIEF.md](../01-EXECUTIVE-BRIEF.md)** — High-level strategic briefing, technical asset summary, and core metrics.
* **[02-PRODUCT-OVERVIEW.md](../02-PRODUCT-OVERVIEW.md)** — Comprehensive product taxonomy, user journeys, feature matrix, and subscription quotas.
* **[03-ARCHITECTURE-OVERVIEW.md](../03-ARCHITECTURE-OVERVIEW.md)** — Hexagonal domain architecture, component boundaries, and technology stack.

### Tier 2: Technical & Operational Runbooks
* **[04-TECHNICAL-HANDOVER-GUIDE.md](../04-TECHNICAL-HANDOVER-GUIDE.md)** — Developer orientation, local setup (Poetry/npm), testing execution, and CI/CD.
* **[05-DEPLOYMENT-HANDOVER.md](../05-DEPLOYMENT-HANDOVER.md)** — Render PaaS blueprint (`render.yaml`), container definitions, and deployment SOPs.
* **[06-OPERATIONS-RUNBOOK.md](../06-OPERATIONS-RUNBOOK.md)** — Standard operating procedures, health checks (`/health/live`, `/health/ready`), and monitoring.
* **[07-SECURITY-OVERVIEW.md](../07-SECURITY-OVERVIEW.md)** — Security architecture, RBAC (41 permissions), TenantContext, and anti-enumeration.
* **[08-BACKUP-RESTORE-RUNBOOK.md](../08-BACKUP-RESTORE-RUNBOOK.md)** — Disaster recovery runbooks and documented ~7.2s physical restoration benchmark across 29 tables.
* **[09-API-DOCUMENTATION.md](../09-API-DOCUMENTATION.md)** — REST API specification covering 122 endpoints across 24 modular FastAPI routers.
* **[10-DATABASE-MIGRATION-GUIDE.md](../10-DATABASE-MIGRATION-GUIDE.md)** — 15 linear forward Alembic database schema migrations managing 29 tables.

### Tier 3: Operational References & Limitations
* **[11-ENVIRONMENT-VARIABLE-REFERENCE.md](../11-ENVIRONMENT-VARIABLE-REFERENCE.md)** — 44 configuration settings, Twelve-Factor compliance, and template drift catalog.
* **[12-DEPENDENCY-SBOM.md](../12-DEPENDENCY-SBOM.md)** — Software Bill of Materials; 100% runtime packages audited as permissive open source (MIT/Apache/BSD).
* **[13-KNOWN-LIMITATIONS.md](../13-KNOWN-LIMITATIONS.md)** — Transparent register of 20 architectural, functional, and operational boundaries.
* **[14-INFRASTRUCTURE-TOPOLOGY-MAP.md](../14-INFRASTRUCTURE-TOPOLOGY-MAP.md)** — Render PaaS topology, VPC private networking, and egress SaaS integrations.

### Tier 4: Transaction & Transfer Checklists
* **[15-IP-ASSIGNMENT-CHECKLIST.md](../15-IP-ASSIGNMENT-CHECKLIST.md)** — Intellectual property scope, audited single-author Git history documentation, and proposed assignment contracts.
* **[16-ACCOUNT-OWNERSHIP-TRANSFER.md](../16-ACCOUNT-OWNERSHIP-TRANSFER.md)** — Cloud workspace cutover, Stripe Test Mode, TwelveData, and credential rotation.
* **[17-DOMAIN-TRANSFER-CHECKLIST.md](../17-DOMAIN-TRANSFER-CHECKLIST.md)** — Render subdomains (`*.onrender.com`), custom domain DNS, and email SPF/DKIM/DMARC.
* **[18-DUE-DILIGENCE-DATA-ROOM-INDEX.md](../18-DUE-DILIGENCE-DATA-ROOM-INDEX.md)** — Master due diligence navigation index and non-established items disclosure register.

---

## 4. Frozen Buyer Presentation Suite (`docs/acquisition/presentation/`)

> **Presentation Reference Notice**: The frozen presentation materials in `docs/acquisition/presentation/` provide slide decks, executive summaries, and visual assets. Reviewers should navigate via the canonical due diligence index (`18-DUE-DILIGENCE-DATA-ROOM-INDEX.md`) or presentation suite files (`01-BUYER-PRESENTATION.md`). Note that frozen Phase 0.5 presentation source files contain historical development file links and should not be relied upon for active code navigation.

The presentation package contains executive slide decks, briefing sheets, and visual assets:
* **[01-BUYER-PRESENTATION.md](../presentation/01-BUYER-PRESENTATION.md)** — 15-slide widescreen presentation deck script with speaker notes.
* **[02-EXECUTIVE-PRODUCT-BRIEF.md](../presentation/02-EXECUTIVE-PRODUCT-BRIEF.md)** — 1-page executive product briefing memorandum.
* **[03-TECHNICAL-ARCHITECTURE-SHEET.md](../presentation/03-TECHNICAL-ARCHITECTURE-SHEET.md)** — 2-page technical architecture and component boundary sheet.
* **[04-ACQUISITION-IP-SCOPE.md](../presentation/04-ACQUISITION-IP-SCOPE.md)** — Intellectual property and transferable software asset definition.
* **[05-BUYER-FAQ.md](../presentation/05-BUYER-FAQ.md)** — Preliminary 18-question buyer FAQ.
* **[06-DEMO-PREFLIGHT-CHECKLIST.md](../presentation/06-DEMO-PREFLIGHT-CHECKLIST.md)** — Preflight verification checklist for technical demonstrations.
* **[07-BUYER-DATA-ROOM-GUIDE.md](../presentation/07-BUYER-DATA-ROOM-GUIDE.md)** — Guided navigation manual for data room diligence reviewers.
* **[08-CLAIM-CONTROL-MATRIX.md](../presentation/08-CLAIM-CONTROL-MATRIX.md)** — Non-negotiable claim control matrix defining safe vs. prohibited terminology.
* **[visual/](../presentation/visual/)** — 24 visual presentation assets:
  * **PDFs:** 7 publication-ready briefing sheets (`Project-ORION-Executive-Brief.pdf`, `Technical-Architecture.pdf`, etc.).
  * **PPTX:** Widescreen slide deck (`Project-ORION-Buyer-Presentation.pptx`).
  * **SVGs:** 5 standalone vector architecture diagrams (hexagonal map, 5-stage pipeline, state machines).
  * **Templates & Scripts:** 7 HTML print templates and 3 automated Python build scripts.

---

## 5. Frozen Buyer Launch Package (`docs/acquisition/launch/`)

The launch package provides transaction and closing operational runbooks:
* **[01-ACQUISITION-LISTING.md](../launch/01-ACQUISITION-LISTING.md)** — Preliminary acquisition listing specification.
* **[02-BUYER-PITCH-MEMO.md](../launch/02-BUYER-PITCH-MEMO.md)** — Preliminary buyer pitch memo.
* **[03-OUTREACH-SEQUENCES.md](../launch/03-OUTREACH-SEQUENCES.md)** — Multi-channel stakeholder outreach sequences.
* **[04-BUYER-QUALIFICATION-RUBRIC.md](../launch/04-BUYER-QUALIFICATION-RUBRIC.md)** — 10-dimension buyer qualification rubric.
* **[05-DATA-ROOM-ACCESS-RUNBOOK.md](../launch/05-DATA-ROOM-ACCESS-RUNBOOK.md)** — Staged data room access protocols and evidence mapping.
* **[06-DEMO-ENVIRONMENT-RUNBOOK.md](../launch/06-DEMO-ENVIRONMENT-RUNBOOK.md)** — Standardized 15-minute live operator demo walkthrough.
* **[07-HANDOVER-CLOSING-CHECKLIST.md](../launch/07-HANDOVER-CLOSING-CHECKLIST.md)** — Day-1 technical transfer, credential rotation, and closing sequence.

---

## 6. Public Landing Documentation (`README.md`)

* **Repository Root README ([`README.md`](../../../../README.md)):** Primary public landing page on GitHub providing product overview, architecture summary, paper-trading invariants, and direct links to all acquisition materials.
* **Project README ([`project-orion/README.md`](../../../README.md)):** Detailed technical documentation covering local installation, database migrations, testing commands, and architecture boundaries.

---

## 7. Next Steps for Prospective Buyers
Request the buyer presentation, technical diligence package, or guided demonstration for further evaluation.
