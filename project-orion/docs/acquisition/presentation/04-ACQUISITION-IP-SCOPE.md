# Project ORION — Acquisition Scope & IP Deliverables

**Document Reference:** `docs/acquisition/presentation/04-ACQUISITION-IP-SCOPE.md`  
**Classification:** Confidential — Acquisition Technical Due Diligence  
**Repository Working Copy:** `project-orion/`  
**Git Baseline Commit:** `d5908d0a0cc2feff99fa02573adb12b8eea33782`  
**Legal Context:** Proposed Software Asset & Intellectual Property Transfer Specification

---

## 1. Executive Transaction Scope

Proposed acquisition scope includes the repository source code and documented intellectual property deliverables, subject to executed transaction documents. 

The transaction is structured as a pure software and intellectual property asset acquisition. The acquiring entity obtains complete, unencumbered ownership of all proprietary codebases, algorithmic research engines, database schemas, test harnesses, and technical documentation. Third-party vendor accounts, cloud hosting instances, merchant billing keys, and external API subscriptions are not transferred as active corporate accounts; they are independently provisioned by the buyer under their corporate entity.

---

## 2. Transferable Assets vs. Buyer-Provisioned Accounts

| Asset / Component | Proposed Transferable Intellectual Property | Buyer-Provisioned External Obligations |
|---|---|---|
| **Application Source Code** | **100% Transferable:** Complete Git repository including React SPA, FastAPI trading engine, and all internal tooling. | None. Transferred via Git repository transfer or mirror. |
| **Domain Logic Layer** | **100% Transferable:** 21 pure domain packages (`libraries/domain/`) containing algorithmic strategies, backtesting, and risk logic. | None. Fully self-contained in repository. |
| **Automated Test Harness** | **100% Transferable:** Complete test harness with documented historical baseline of 4,260 automated tests across 103 test suites. | None. Executes in any standard Python 3.11+ environment. |
| **Database Architecture** | **100% Transferable:** SQLAlchemy 2.0 declarative models and 15 linear Alembic migrations managing 29 database tables. | Buyer provisions target PostgreSQL 16 database (local Docker or Render PaaS). |
| **Disaster Recovery Assets** | **100% Transferable:** Database backup/restore scripts (`backup/restore-database.sh`) and demonstration runbooks. | Buyer configures automated snapshot schedules on their cloud database instance. |
| **Technical Documentation** | **100% Transferable:** All 18 closing due diligence dossiers, API specifications, and operational maintenance runbooks. | None. Stored directly within `docs/acquisition/`. |
| **PaaS Cloud Blueprint** | **100% Transferable:** Declarative `render.yaml` Infrastructure-as-Code blueprint and Docker container definitions. | **Buyer-Provisioned:** Buyer creates their own Render team account and enters billing payment method. |
| **Commercial Billing Engine** | **100% Transferable:** Stripe webhook handlers, subscription service orchestration, and customer portal integration routes. | **Buyer-Provisioned:** Buyer establishes their own Stripe merchant account and inputs live/test API keys. |
| **Market Data Ingestion** | **100% Transferable:** `MockMarketDataProvider` engine and `TwelveDataMarketDataProvider` integration adapter. | **Buyer-Provisioned:** Buyer secures their own TwelveData API key if real-time market data is desired. |
| **Broker Sandbox Layer** | **100% Transferable:** `PaperExecutionAdapter` matching engine and `OandaBrokerAdapter` sandbox integration. | **Buyer-Provisioned:** Buyer registers their own OANDA Practice account for external sandbox testing. |
| **Transactional Email** | **100% Transferable:** Notification client service and operational HTML/text email templates. | **Buyer-Provisioned:** Buyer inputs their corporate SMTP server credentials (`SMTP_HOST`, `SMTP_USER`). |
| **Web Domain & SSL** | **100% Transferable:** Reverse proxy routing, CSP security policies, and frontend SPA build configurations. | **Buyer-Provisioned:** Buyer purchases custom domain, configures DNS A/CNAME records, and manages TLS. |

---

## 3. Intellectual Property Provenance & Cleanliness

1. **Clean Commit Provenance:**  
   The codebase contains an unbroken, linear Git commit history originating from initial architectural assembly through to the closing acquisition audit (`d5908d0a`).
2. **Zero Proprietary Third-Party Code Contamination:**  
   As documented in [`docs/acquisition/12-DEPENDENCY-SBOM.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/12-DEPENDENCY-SBOM.md), all external third-party dependencies are licensed under commercially permissive open-source licenses (MIT, Apache 2.0, BSD-3-Clause). Zero copyleft (GPL / AGPL) dependencies contaminate the proprietary domain layer.
3. **Zero Secrets in Repository History:**  
   The repository has been scanned with automated secret detection tools; all authentication tokens, JWT secrets, and database passwords are ingested dynamically via environment variables (`AppSettings`), ensuring no production credentials exist in the Git tree.
4. **Clean Corporate Separation:**  
   The asset transfer checklist in [`docs/acquisition/15-IP-ASSIGNMENT-CHECKLIST.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/15-IP-ASSIGNMENT-CHECKLIST.md) details the formal execution of intellectual property assignment agreements, confirming complete transfer of all copyright, patent, trademark, and trade secret claims.

---

## 4. Vendor Account Transition Protocol

Third-party SaaS account transferability is not established in the repository; whether external providers permit direct account assignment between distinct corporate entities requires vendor-specific verification. To eliminate third-party transfer friction and establish regulatory/KYC compliance under the buyer’s corporate identity, the acquisition runbook specifies the **Independent Account Provisioning Path**:

```
Step 1: Code Repository Transfer
  └── Transfer GitHub repository or provide clean git bundle export to buyer organization.

Step 2: Cloud Infrastructure Initialization
  ├── Buyer creates new organization on Render (https://render.com).
  ├── Buyer enters payment method (supporting ~$14/month base infrastructure).
  └── Buyer connects transferred GitHub repository and deploys render.yaml blueprint.

Step 3: Environment Secret Injection
  ├── Render automatically generates ORION_JWT_SECRET_KEY.
  ├── Render automatically binds internal ORION_DATABASE_URL and ORION_REDIS_URL.
  └── Buyer injects optional external API keys (TWELVE_DATA_API_KEY, STRIPE_SECRET_KEY).

Step 4: Database Schema Initialization
  └── preDeployCommand automatically executes python scripts/deploy/migrate.py,
      running 15 linear Alembic migrations to construct all 29 database tables.

Step 5: Domain & Brand Association
  ├── Buyer adds custom domain (e.g. trading.buyer-firm.com) in Render dashboard.
  └── Buyer creates DNS CNAME records pointing to Render edge routing.
```

---

## 5. Commercial Asset Representations

* **Pre-Revenue Status:** The platform is sold as a completed software technology and intellectual property asset. Commercial revenue, paying customers, and recurring subscribers are **NOT ESTABLISHED IN REPOSITORY**.
* **Liability & Capital Warranty:** The software is delivered as a simulation and research platform. The platform operates with exactly $0.00 live financial capital at risk.
* **Regulatory Invariant:** Project ORION does not possess regulatory financial licenses. Commercial operation as a public retail broker requires the acquiring entity to obtain appropriate financial licensing.
