# Project ORION — Buyer Qualification Rubric
## Objective Framework for Assessing Strategic, Technical, and Commercial Alignment

```
Document Reference: docs/acquisition/launch/04-BUYER-QUALIFICATION-RUBRIC.md
Document Version:   1.0.0
Release Status:     Acquisition Diligence Launch Package
Source Baseline:    Repository Git Commit d5908d0a0cc2feff99fa02573adb12b8eea33782
Canonical System:   Project ORION — Quantitative FX Research & Paper-Trading SaaS
Execution Boundary: Strictly Paper Trading ($100,000 Virtual Starting Balance; $0.00 Live Capital at Risk)
Commercial Status:  Pre-revenue / Commercial Traction Not Established in Repository
```

---

## 1. Objective & Usage Guidelines

### 1.1 Purpose
This rubric provides a neutral, objective, and source-grounded framework to evaluate whether a prospective buyer possesses the technical competence, domain familiarity, infrastructure capacity, and operational readiness to successfully acquire, operate, and maintain **Project ORION** (Quantitative FX Research & Paper-Trading SaaS).

### 1.2 Non-Discrimination & Neutrality Mandate
- **No Ranking of Specific Buyers**: This rubric does NOT rank, compare, or generate a "best buyer" hierarchy.
- **No Sensitive or Political Scoring**: Evaluations are restricted strictly to architectural fit, technical compatibility, organizational capabilities, and transaction readiness.
- **No Arbitrary Financial Valuations**: This document does not establish an asking price or compute an enterprise valuation. Transaction terms remain subject to bilateral negotiation between parties.
- **Outcome Categories**: Prospective buyer engagements are categorized exclusively into three operational states:
  1. `QUALIFIED FOR DISCUSSION`: High alignment across technical and transaction capabilities; suitable for Tier 2/3 data room access and live walkthroughs.
  2. `REQUIRES FURTHER INFORMATION`: Incomplete information or minor capability gaps; requires clarification before progressing into deep diligence.
  3. `NOT CURRENTLY ALIGNED`: Fundamental misalignment (e.g., seeking live broker execution with financial custody, expecting commercial subscriber revenue, or lacking modern software engineering staff).

---

## 2. Global Invariants & Prerequisite Understandings

Prior to detailed qualification, the prospective buyer must acknowledge and accept three foundational repository realities:

1. **Simulation Invariant**: Project ORION is strictly a research and simulation platform (`PaperExecutionAdapter`, `is_paper=True`). It enforces a $100,000 virtual balance and maintains exactly $0.00 live financial capital at risk. Prospective buyers requiring turn-key live broker execution or client money custody are out of alignment.
2. **Commercial Status**: The codebase represents complete intellectual property and software architecture supported by historical development evidence of 4,260 automated tests and 99.4% documented coverage; however, customers, subscribers, ARR, MRR, contracts, and historical commercial revenue are **`NOT ESTABLISHED IN REPOSITORY`** (pre-revenue technology asset).
3. **PaaS & Account Provisioning**: Third-party vendor accounts (Render, PostgreSQL, Redis, Stripe, TwelveData, OANDA, SMTP) are non-transferable and must be provisioned independently by the buyer (`BUYER-PROVISIONED`).

---

## 3. The 10 Qualification Dimensions

### Dimension 1: Strategic Fit
Evaluates whether the acquisition of a quantitative FX research and simulation platform aligns with the buyer's strategic roadmap, product offering, or investment thesis.

- **Evidence to Request**: 
  - Overview of buyer's existing business lines, products, or investment mandate.
  - Stated rationale for acquiring an off-the-shelf quantitative research and paper-trading platform.
  - Anticipated timeline for integration, white-labeling, or deployment.
- **Questions to Ask**:
  - What strategic problem does Project ORION solve for your organization (e.g., accelerating time-to-market, adding educational simulation, bootstrapping prop trader research)?
  - How does this codebase complement your existing software ecosystem?
- **Red Flags**:
  - Buyer expects an established revenue-generating business with recurring subscriber ARR.
  - Buyer is seeking an operational hedge fund, broker-dealer license, or regulatory umbrella.
  - Strategic intent contradicts educational/paper-trading boundaries.
- **Verification Method**: Corporate website review, public filings/press releases, introductory executive discovery meeting.

---

### Dimension 2: Technical Fit (Software Stack & Architecture)
Evaluates whether the buyer's technical team has the capability to maintain and extend a modern Python/FastAPI and React/TypeScript codebase.

- **Evidence to Request**:
  - Confirmation of in-house or contracted engineering experience with Python 3.11+, async frameworks (FastAPI/asyncio), and modern TypeScript/React.
  - Familiarity with asynchronous ORMs (SQLAlchemy 2.0 with `asyncpg`) and schema migration workflows (Alembic).
- **Questions to Ask**:
  - Does your team maintain asynchronous Python services in production?
  - Who will be the designated technical lead responsible for repository handover and maintenance?
- **Red Flags**:
  - Buyer's technical stack is exclusively legacy monolithic technologies (e.g., PHP, .NET Framework 4.x, Java EE) with no Python capability.
  - Complete lack of internal or designated technical personnel.
- **Verification Method**: Technical diligence conversation with Lead Engineer or CTO; review of team engineering profiles.

---

### Dimension 3: Product Fit (User Workflows & Feature Set)
Evaluates whether the buyer's target user personas and desired feature set align with Project ORION's implemented functional modules.

- **Evidence to Request**:
  - Target audience definition (e.g., retail algorithmic traders, prop incubator candidates, quantitative finance students).
  - Feature roadmap requirements compared against the 9 strategy profiles and research tools.
- **Questions to Ask**:
  - Which specific platform capabilities are critical for your users (Strategy Lab, Walk-Forward Analysis, Paper Incubator, RBAC)?
  - Do your product requirements align with the bar-by-bar OHLCV backtesting engine?
- **Red Flags**:
  - Expectation of high-frequency tick-by-tick order book simulation.
  - Expectation of built-in candlestick chart pattern recognition (explicitly not implemented; see `docs/acquisition/13-KNOWN-LIMITATIONS.md`).
  - Expectation of native iOS/Android mobile applications (Project ORION is a responsive web application).
- **Verification Method**: Product diligence review against `docs/acquisition/02-PRODUCT-OVERVIEW.md`.

---

### Dimension 4: Integration Capability
Evaluates the buyer's ability to integrate Project ORION's REST APIs, authentication tokens, and webhook handlers into existing corporate infrastructure.

- **Evidence to Request**:
  - Architecture diagram or technical overview of existing systems to be interfaced (e.g., central SSO, CRM, custom broker bridges).
  - API consumption capability and experience with OpenAPI 3.0 / FastAPI documentation.
- **Questions to Ask**:
  - Do you intend to run Project ORION as a standalone portal or embed its components via API?
  - Do you have experience managing webhook endpoints (e.g., Stripe subscription events)?
- **Red Flags**:
  - Inability to ingest standard OpenAPI JSON specifications.
  - Insistence on turnkey, out-of-the-box integration with proprietary, undocumented internal systems without engineering investment.
- **Verification Method**: Review of integration scope during Technical Handover review (`docs/acquisition/04-TECHNICAL-HANDOVER-GUIDE.md`).

---

### Dimension 5: Trading / Quant Domain Relevance
Evaluates the buyer's operational grasp of quantitative FX concepts, backtesting methodologies, and risk metrics.

- **Evidence to Request**:
  - Experience in financial markets, currency pairs (major/minor FX), technical indicators (EMA, RSI, MACD, Bollinger), and quantitative metrics (Sharpe, Sortino, Calmar, Max Drawdown).
  - Familiarity with Walk-Forward Analysis (WFA) concepts: in-sample optimization, out-of-sample testing, and Walk-Forward Efficiency (WFE).
- **Questions to Ask**:
  - How does your research team currently evaluate strategy robustness and prevent curve-fitting?
  - Are your quants familiar with temporal look-ahead leakage prevention (`LeakageGuard`)?
- **Red Flags**:
  - Buyer expresses belief in "guaranteed trading returns" or "zero-loss" algorithmic systems.
  - Buyer does not understand the difference between backtest simulation and real-money execution.
- **Verification Method**: Quant-to-quant diligence review focusing on `libraries/domain/research/` and `libraries/domain/backtesting/`.

---

### Dimension 6: Infrastructure Capability
Evaluates the buyer's operational capacity to manage containerized applications, cloud environments, relational databases, and disaster recovery runbooks.

- **Evidence to Request**:
  - Experience with Docker containerization, cloud PaaS (Render, AWS, GCP, or Azure), and Linux runtime environments.
  - Capability to administer PostgreSQL 16 (running Alembic migrations, managing connection pools) and Redis 7 (caching, eviction policies).
- **Questions to Ask**:
  - What cloud hosting environment do you plan to utilize for production deployment?
  - Do you have an established operational backup and recovery workflow for relational databases?
- **Red Flags**:
  - Buyer expects the seller to host, maintain, or pay for production cloud resources post-handover.
  - Inability to execute basic Docker or database migration CLI commands.
- **Verification Method**: Review of operational runbooks with buyer DevOps/Infra personnel (`docs/acquisition/06-OPERATIONS-RUNBOOK.md` and `08-BACKUP-RESTORE-RUNBOOK.md`).

---

### Dimension 7: Due Diligence Readiness
Evaluates the buyer's readiness to execute structured due diligence under appropriate confidentiality and security standards.

- **Evidence to Request**:
  - Willingness to execute a mutual Non-Disclosure Agreement (NDA) prior to receiving confidential source documents or code access.
  - Designation of authorized diligence reviewers (legal, technical, commercial).
- **Questions to Ask**:
  - What is your standard technical and legal due diligence process and expected timeframe?
  - Who will participate in code review and architecture inspection?
- **Red Flags**:
  - Refusal to sign standard mutual confidentiality agreements.
  - Unstructured, open-ended requests for full proprietary intellectual property prior to qualification.
- **Verification Method**: Execution of mutual NDA; establishment of designated diligence communication channel.

---

### Dimension 8: Transaction Readiness
Evaluates whether the buyer has the organizational mandate, corporate structure, and capital resources to execute a software asset acquisition.

- **Evidence to Request**:
  - Confirmation of buyer entity legal formation and jurisdiction.
  - Authority of the primary contact to negotiate and execute commercial transactions.
  - Target transaction timeline.
- **Questions to Ask**:
  - Has your organization completed software or intellectual property acquisitions previously?
  - What corporate approvals (Board, Investment Committee, Managing Partner) are required to execute a definitive agreement?
- **Red Flags**:
  - Unregistered or unverifiable entity.
  - Contingent acquisition structures requiring speculative external fundraising before closing.
- **Verification Method**: Entity verification via public business registries; verification of signatory authority.

---

### Dimension 9: Account Provisioning Capability
Evaluates the buyer's understanding and readiness to independently provision required vendor services.

- **Evidence to Request**:
  - Confirmation that buyer understands all vendor accounts are strictly `BUYER-PROVISIONED`:
    - Cloud Hosting: Render PaaS (or container alternative).
    - Database: Managed PostgreSQL 16.
    - Caching / Rate Limiting: Redis 7.
    - Payments: Stripe account (developer dashboard).
    - Market Data: TwelveData API account.
    - Execution Sandbox: OANDA Developer / Practice account.
    - Email Delivery: SMTP provider (SendGrid, Postmark, AWS SES).
- **Questions to Ask**:
  - Does your organization already maintain accounts with these or equivalent vendors?
  - Do you understand that no vendor subscriptions, credits, or credentials transfer with the codebase?
- **Red Flags**:
  - Expectation that seller-owned API keys, Stripe accounts, or cloud subscriptions transfer automatically upon closing.
- **Verification Method**: Explicit written acknowledgement during review of `docs/acquisition/16-ACCOUNT-OWNERSHIP-TRANSFER.md`.

---

### Dimension 10: Legal / Procurement Readiness
Evaluates the buyer's ability to review and execute standard software intellectual property assignment and transaction agreements.

- **Evidence to Request**:
  - Availability of internal or external legal counsel experienced in software asset transfers, copyright assignments, and technology transactions.
  - Familiarity with open-source software licensing audits (MIT, Apache-2.0, BSD-3-Clause).
  - Explicit acceptance that the intellectual property boundary is defined as: "Proposed Transferable Software / IP Scope, subject to executed transaction agreements."
  - Understanding that third-party dependencies remain subject to their applicable licenses.
- **Questions to Ask**:
  - Do you have legal counsel prepared to review the Software Asset Purchase Agreement and IP Assignment documentation?
  - Have you reviewed the Software Bill of Materials (SBOM) and licensing audit (`docs/acquisition/12-DEPENDENCY-SBOM.md`)?
- **Red Flags**:
  - Demand for warranties or indemnifications that contradict repository evidence (e.g., demanding real-money brokerage regulatory compliance warranties).
  - Refusal to recognize third-party open-source dependencies in the software scope.
- **Verification Method**: Counsel-to-counsel coordination on transaction documentation (`docs/acquisition/15-IP-ASSIGNMENT-CHECKLIST.md`).

---

## 4. Assessment Matrix & Outcome Determination

The qualification lead assesses each dimension and compiles an objective evaluation profile:

| Qualification Dimension | Status (`Satisfactory` / `Clarification Needed` / `Misaligned`) | Verified Evidence / Notes |
|:---|:---:|:---|
| **1. Strategic Fit** | — | — |
| **2. Technical Fit** | — | — |
| **3. Product Fit** | — | — |
| **4. Integration Capability** | — | — |
| **5. Trading / Quant Domain Relevance** | — | — |
| **6. Infrastructure Capability** | — | — |
| **7. Due Diligence Readiness** | — | — |
| **8. Transaction Readiness** | — | — |
| **9. Account Provisioning Capability** | — | — |
| **10. Legal / Procurement Readiness** | — | — |

---

## 5. Qualification Decision Rules

### Outcome 1: `QUALIFIED FOR DISCUSSION`
- **Criteria**: All 10 dimensions evaluated as `Satisfactory` (or minor clarification in non-critical areas). Buyer explicitly understands simulation boundaries ($0.00 live risk), pre-revenue status, and account provisioning obligations.
- **Next Steps**:
  1. Execute mutual NDA or equivalent confidentiality agreement.
  2. Grant Tier 1 and Tier 2 Data Room access (Dossiers 01–10).
  3. Schedule live technical walkthrough or structured demo session.

### Outcome 2: `REQUIRES FURTHER INFORMATION`
- **Criteria**: 1 to 3 dimensions have information gaps or require organizational clarification (e.g., engineering lead unassigned, hosting environment undecided, legal counsel not yet engaged).
- **Next Steps**:
  1. Issue specific, structured clarification request covering outstanding dimensions.
  2. Provide public overview materials (`docs/acquisition/01-EXECUTIVE-BRIEF.md` and listing overview).
  3. Re-evaluate upon receipt of written clarifications.

### Outcome 3: `NOT CURRENTLY ALIGNED`
- **Criteria**: Fundamental conflict with core invariants (e.g., demanding live fund custody, expecting commercial ARR, requesting guaranteed trading returns, or unable to administer Python/PostgreSQL software).
- **Next Steps**:
  1. Issue polite, professional communication noting misalignment between the buyer's requirements and Project ORION's design as a pre-revenue quantitative research/simulation software asset.
  2. Close inquiry respectfully with zero further follow-up.

---
*End of Document — Project ORION Acquisition Launch Suite*
