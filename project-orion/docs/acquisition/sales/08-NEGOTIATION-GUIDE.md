# Project ORION — Acquisition Negotiation & Transaction Guide

**Asset Category:** Pre-Revenue Quantitative Software & Intellectual Property Acquisition
**Asking Price:** $24,900 USD
**Document Reference:** `docs/acquisition/sales/08-NEGOTIATION-GUIDE.md`

---

## 1. Executive Principles & Pricing Framework

### 1.1 Stated Asking Price
* **ASKING PRICE: $24,900 USD**
* **Price Nature:** This is the seller's asking price for the proposed outright software and intellectual property asset acquisition. It is not an appraised valuation, formal enterprise appraisal, revenue multiple, or SaaS subscription price.
* **Internal Negotiation Policy:** The repository establishes the public asking price of $24,900 USD. No secret minimum price or negotiation floor is established or published in repository documentation. All consideration structures remain subject to bilateral negotiation and definitive written transaction agreements.

### 1.2 Separation of Commercial Concepts
1. **Acquisition Transaction Price ($24,900 USD):** The seller's asking price consideration for the Project ORION software repository and documented acquisition assets (subject to definitive transaction agreements).
2. **Documented SaaS Subscription Pricing (Free Sandbox — $0/month, Pro Trader — $99/month, Business Prop Desk — $299/month, Enterprise — Custom):** The built-in commercial subscription tier quota model implemented in source code (`pricing.ts`, `subscription_service.py`). These tiers reflect how an acquirer can monetize the software with end-users post-acquisition; they are completely separate from the $24,900 transaction asking price.
3. **Operational Cloud Costs:** ~$14/month documented baseline estimate for the referenced Render configuration; actual buyer operating cost depends on selected resources, region and usage. This is an operational expense paid by the buyer directly to Render, not to the seller.

---

## 2. Scope Boundaries & Transaction Structure

### 2.1 Proposed Transferable Scope (Subject to Executed Agreements)
* Project ORION software repository and documented acquisition assets where audited repository history shows a single-author commit history within the reviewed repository scope.
* 21 pure Python domain logic packages (`libraries/domain/`).
* 24 modular FastAPI backend API routers and service orchestrators.
* Complete React 19 / TypeScript / Vite Single-Page Application (`apps/dashboard/`).
* 15 linear forward Alembic database schema migrations managing 29 relational tables.
* Automated test harness with documented historical baseline of 4,260 tests across 103 test suites.
* Declarative Render PaaS blueprint (`render.yaml`), Dockerfiles, and disaster recovery scripts.
* Complete 18-dossier due diligence data room, 8 presentation source docs, 24 visual presentation assets, and 7 launch runbooks.

### 2.2 Buyer-Provisioned External Services (`BUYER-PROVISIONED`)
To ensure clean corporate separation and eliminate third-party vendor lock-in, the acquiring entity independently provisions all external accounts:
* Cloud hosting organization and billing account (Render PaaS or alternative container environment).
* Managed relational database (PostgreSQL 16) and cache instance (Redis 7).
* Payment gateway merchant account (Stripe corporate account).
* External market data API subscription (TwelveData API key).
* External broker sandbox account (OANDA Practice v20 account).
* Transactional email delivery service (SendGrid, Postmark, AWS SES).
* Custom domain and DNS management, if used.
* Production secrets (JWT signing keys, database passwords, API credentials).

*Third-Party Account Rule:* Third-party vendor accounts are non-transferable under provider terms of service. No vendor accounts, API tokens, or billing credits transfer with the codebase.

---

## 3. Buyer Objection Handling Guide

---

### Objection 1: "Why is commercial revenue not established?"
**Factual Response:**
> "Project ORION is being sold as a software and intellectual property asset, not as an operating commercial business with established revenue. The engineering focus was on architecture, strategy engines, walk-forward optimization, simulated execution, multi-tenancy, and automated testing (4,260 tests, 99.4% documented coverage). Commercial subscriber acquisition, marketing, and sales are not established in the repository. The buyer is acquiring an implemented software foundation rather than starting from a blank project, allowing their team to commercialize or integrate the platform."

---

### Objection 2: "Why is the asking price $24,900 USD?"
**Factual Response:**
> "The $24,900 asking price is the seller's asking price reflecting the technical scope and completeness of an implemented, full-stack quantitative software platform—comprising 24 API routers, 21 domain packages, 15 database migrations, a React 19 SPA, 4,260 automated tests, and a 57-document diligence package. It is the seller's asking price for the software and IP assets, not a valuation, appraisal, or revenue multiple. It represents an accessible price point for an organization seeking an implemented software baseline rather than spending months of custom development."

---

### Objection 3: "Can we see the code before purchasing?"
**Factual Response:**
> "Yes, under structured due diligence. Prospective buyers who complete initial qualification and execute a standard mutual Non-Disclosure Agreement (NDA) receive access to our 18-dossier due diligence data room, which includes complete architectural sheets, API specifications, database migration runbooks, and dependency manifests. Full source repository inspection is conducted during the technical diligence phase prior to closing."

---

### Objection 4: "Can we run the software ourselves?"
**Factual Response:**
> "Yes. The platform is designed for standard containerized deployment. Following mutual NDA execution, we can arrange a live guided walkthrough where you can observe the platform running end-to-end, execute backtests, run Walk-Forward Analysis, and submit simulated paper orders. Technical handover runbooks (`04-TECHNICAL-HANDOVER-GUIDE.md`) provide step-by-step instructions for running the codebase via Docker Compose or local Poetry/Node environments."

---

### Objection 5: "Can you deploy it for us?"
**Factual Response:**
> "The platform includes a declarative Infrastructure-as-Code blueprint (`render.yaml`) that automates multi-stage Docker deployment, PostgreSQL database provisioning, Redis setup, and Alembic migrations on Render. Deployment into your own Render account requires connecting the repository and configuring environment variables as documented in Dossier 05 (`05-DEPLOYMENT-HANDOVER.md`). Up to 10 business days of asynchronous developer orientation support is provided to assist your engineering lead with the initial deployment walkthrough."

---

### Objection 6: "Does it trade real money?"
**Factual Response:**
> "No. Project ORION operates strictly in Paper-Trading Simulation Mode ($100,000 virtual balance, exactly $0.00 live financial capital at risk). It does not contain live broker clearing rails, liquidity provider connections, or fund custody rails. Broker connectivity is constrained to the OANDA Practice sandbox, and attempts to connect live broker clearing URLs fail closed. If a buyer wishes to connect live execution, that requires their own engineering investment, broker agreements, and applicable regulatory licensing."

---

### Objection 7: "Can we connect our own broker or custom liquidity provider?"
**Factual Response:**
> "Yes. The architecture is built on Hexagonal Architecture (Ports and Adapters) with Domain-Driven Design principles. The execution layer (`PaperExecutionAdapter`, `OandaExecutionAdapter`) implements an abstract broker interface decoupled from domain logic. Your engineering team can implement a custom execution adapter conforming to the interface without modifying the core strategy, risk, or accounting models."

---

### Objection 8: "Does the software have any existing customers?"
**Factual Response:**
> "No. Commercial customers and active subscribers are NOT ESTABLISHED IN REPOSITORY. The software includes built-in multi-tenant organization models, 7 RBAC roles, and pre-wired Stripe subscription billing in Test Mode, but it has not been marketed to retail or external subscribers. It is sold strictly as a pre-revenue technology asset."

---

### Objection 9: "Can we transfer the existing external accounts (Render, Stripe, OANDA)?"
**Factual Response:**
> "No. To maintain clean corporate separation and adhere to third-party provider terms of service, all external vendor accounts are independently buyer-provisioned (`BUYER-PROVISIONED`). The buyer provisions their own Render cloud account, Stripe merchant account, TwelveData API key, and OANDA Practice sandbox account. Dossier 16 (`16-ACCOUNT-OWNERSHIP-TRANSFER.md`) provides a step-by-step runbook for provisioning these accounts and rotating credentials during closing."

---

## 4. Standard Transaction & Closing Sequence

```text
[Step 1: Inquiry & Qualification]
   │  Prospective buyer reviews listing; submits intake form.
   ▼
[Step 2: Mutual NDA Execution]
   │  Bilateral confidentiality agreement executed.
   ▼
[Step 3: Data Room Access & Technical Demo]
   │  Tier 1 & Tier 2 dossiers unlocked; 15-minute walkthrough conducted.
   ▼
[Step 4: Indication of Interest (IOI) / Offer Submission]
   │  Buyer presents purchase offer based on $24,900 USD asking price.
   ▼
[Step 5: Definitive Agreement Execution]
   │  Parties execute Software Asset Purchase Agreement (APA) & IP Assignment.
   ▼
[Step 6: Escrow Funding & Account Verification]
   │  Buyer deposits consideration into designated escrow (e.g., Escrow.com).
   ▼
[Step 7: Codebase Handover & Credential Delivery]
   │  Project ORION software repository transfer; delivery of documented acquisition assets.
   ▼
[Step 8: Escrow Release & Orientation Support]
   │  Escrow funds released; 10 business days of async developer orientation begins.
```
