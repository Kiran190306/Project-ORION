# Project ORION — Buyer Qualification Framework

**Asset Category:** Pre-Revenue Quantitative Software & Intellectual Property Acquisition
**Asking Price:** $24,900 USD
**Document Reference:** `docs/acquisition/sales/06-BUYER-QUALIFICATION.md`

---

## 1. Purpose & Neutral Evaluation Principles

### 1.1 Objective
This qualification framework provides a structured, neutral process to evaluate whether a prospective acquirer possesses the technical competence, domain familiarity, operational infrastructure, and transaction readiness to successfully acquire, deploy, and maintain **Project ORION** (Quantitative FX Research & Paper-Trading SaaS).

### 1.2 Neutrality Mandates
* **No Subjective Ranking:** Prospective buyers are not scored, ranked, or categorized into subjective tiers like "best" or "ideal."
* **Objective Capability Assessment:** Evaluation is restricted strictly to architectural compatibility, technical stack alignment, operational capability, and commercial clarity.
* **Non-Discrimination:** Evaluations are conducted purely on verifiable organizational, technical, and commercial alignment.
* **Outcome Classifications:** Prospective buyer interactions result in one of three objective operational determinations:
  1. `ALIGNED FOR DISCUSSION`: Demonstrated technical fit, acceptance of foundational invariants, and capacity to proceed with technical diligence.
  2. `CLARIFICATION NEEDED`: Incomplete information regarding technical stack, hosting environment, or decision timeline requiring written clarification.
  3. `FUNDAMENTALLY MISALIGNED`: Core requirement conflict (e.g., demanding live fund custody, expecting commercial ARR, requesting guaranteed trading returns, or lacking software development capabilities).

---

## 2. Foundational Invariants (Mandatory Acknowledgment)

Before entering detailed diligence or reviewing confidential code assets, every prospective buyer must explicitly acknowledge and accept the following baseline facts:

1. **Simulation Invariant:** Project ORION is strictly a research and simulation platform (`PaperExecutionAdapter`, `is_paper=True`). It enforces a $100,000 virtual balance and maintains exactly **$0.00 live financial capital at risk**. The software does not provide live broker clearing rails or client money custody.
2. **Commercial Status:** The asset is an outright pre-revenue software and intellectual property acquisition. Customers, subscribers, ARR, MRR, contracts, and historical commercial revenue are **NOT ESTABLISHED IN REPOSITORY**.
3. **PaaS & Account Provisioning:** All external services (Render, PostgreSQL, Redis, Stripe, TwelveData, OANDA, SMTP, custom domain and DNS management, if used) are non-transferable and must be provisioned independently by the buyer (`BUYER-PROVISIONED`).
4. **Asking Price Nature:** The $24,900 USD asking price is the seller's asking price for the proposed software/IP transaction. It is not an appraised valuation, independent valuation, revenue multiple, or SaaS subscription price.

---

## 3. Buyer Information Intake Template

To establish alignment, the following structured information is collected during initial engagement:

```text
================================================================================
PROJECT ORION — PROSPECTIVE BUYER INTAKE FORM
================================================================================

1. BUYER IDENTITY & ORGANIZATION
   - Primary Contact Name: _____________________________________________
   - Professional Title / Role: _________________________________________
   - Corporate Entity Name: _____________________________________________
   - Website / Public Registry: _________________________________________
   - Jurisdiction of Incorporation: _____________________________________

2. ACQUISITION OBJECTIVE & INTENDED USE
   - Primary Strategic Objective:
     [ ] Internal Quantitative Research & Strategy Formulation
     [ ] Prop Trading Incubator / Trader Evaluation Program
     [ ] Trading Academy / Educational Simulation Tool
     [ ] Technology Foundation for Commercial SaaS Launch
     [ ] Re-platforming / Modular Component Integration
     [ ] Other (specify): _____________________________________________
   - Target User Profile: ______________________________________________

3. TECHNICAL REQUIREMENTS & STACK COMPATIBILITY
   - In-house engineering capabilities:
     [ ] Python 3.11+ / FastAPI / AsyncIO
     [ ] React 19 / TypeScript / Vite
     [ ] PostgreSQL / SQLAlchemy / Alembic
     [ ] Docker / Container Deployment
   - Designated Technical Handover Lead: _______________________________
   - Planned Cloud Deployment Target (e.g., Render, AWS, GCP, Self-hosted):
     __________________________________________________________________

4. REQUIRED INTEGRATIONS & ARCHITECTURAL SCOPE
   - Does buyer plan to operate as a standalone platform or embed via API?
     [ ] Standalone Portal     [ ] Embedded via REST API
   - External broker sandbox connectivity required:
     [ ] OANDA Practice (supported out of the box)
     [ ] Other Broker / Practice Sandbox (custom adapter required)
   - External market data required:
     [ ] Synthetic Deterministic Data (supported out of the box)
     [ ] TwelveData External API Feed (supported out of the box)
     [ ] Proprietary Feed (custom ingestion adapter required)

5. DUE DILIGENCE & TRANSACTION PROCESS
   - Authorized Diligence Reviewers (Technical, Legal, Commercial):
     __________________________________________________________________
   - Willingness to execute standard mutual Non-Disclosure Agreement (NDA):
     [ ] Yes     [ ] No
   - Anticipated Diligence Timeline:
     [ ] 1–2 Weeks     [ ] 2–4 Weeks     [ ] 30+ Days
   - Corporate Decision Authority & Approvals Required:
     __________________________________________________________________
   - Available Capital / Transaction Structure:
     [ ] Cash Consideration at Closing ($24,900 USD Asking Price)
     [ ] Staged Escrow Milestone Release
     [ ] Other (specify): _____________________________________________

================================================================================
```

---

## 4. Assessment Matrix & Criteria

The intake information is evaluated across five operational dimensions:

| Evaluation Dimension | Aligned Criteria | Misaligned Indicators |
| :--- | :--- | :--- |
| **1. Strategic & Product Alignment** | Seeks quantitative FX research, backtesting, WFA, or paper-trading simulation. | Demands live-money broker clearing, fiat banking, or hedge fund management. |
| **2. Technical Competence** | Team maintains or can administer Python, React, PostgreSQL, and Docker software. | Lacks modern software engineering personnel; unable to run CLI tools. |
| **3. Operational Capability** | Understands that cloud hosting and external APIs are independently buyer-provisioned. | Expects seller to host, maintain, or pay for production cloud services post-handover. |
| **4. Commercial Expectations** | Understands asset is pre-revenue software/IP (ARR/MRR: NOT ESTABLISHED IN REPOSITORY). | Demands historical customer financial statements, subscriber cohorts, or churn logs. |
| **5. Diligence & Legal Process** | Prepared to sign mutual NDA, review data room dossiers, and execute standard APA. | Refuses standard NDA; demands speculative external fundraising contingencies. |

---

## 5. Qualification Decision Rules

### Outcome 1: `ALIGNED FOR DISCUSSION`
* **Condition:** All foundational invariants acknowledged; technical and strategic alignment verified across all 5 dimensions.
* **Action:**
  1. Execute bilateral mutual Non-Disclosure Agreement (NDA).
  2. Grant Tier 1 & Tier 2 Due Diligence Data Room access (`docs/acquisition/`).
  3. Schedule a 15-minute technical walkthrough following the Demo Call Script.

### Outcome 2: `CLARIFICATION NEEDED`
* **Condition:** 1 or 2 areas have incomplete information (e.g., technical lead unassigned, deployment cloud undecided).
* **Action:**
  1. Send specific written clarification requests.
  2. Provide public overview materials (`01-ACQUISITION-LISTING.md` and `02-SHORT-LISTING.md`).
  3. Re-evaluate upon receipt of written clarifications.

### Outcome 3: `FUNDAMENTALLY MISALIGNED`
* **Condition:** Core conflict with invariants (demanding live client fund custody, expecting commercial ARR, requesting guaranteed trading returns, or unable to administer software).
* **Action:**
  1. Issue polite written communication explaining the architectural misalignment with Project ORION's design as a pre-revenue quantitative research/simulation software asset.
  2. Conclude inquiry respectfully with zero further follow-up.
