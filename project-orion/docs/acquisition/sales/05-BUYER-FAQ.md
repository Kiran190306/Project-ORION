# Project ORION — Buyer Frequently Asked Questions (FAQ)

**Asset Category:** Pre-Revenue Quantitative Software & Intellectual Property Acquisition
**Asking Price:** $24,900 USD
**Document Reference:** `docs/acquisition/sales/05-BUYER-FAQ.md`

---

### Q1: What is Project ORION?
**Answer:** Project ORION is a specialized software platform engineered for quantitative foreign exchange (FX) research, historical backtesting, parameter optimization, walk-forward analysis, strategy deployment governance, and simulated paper execution. It features a modern Python 3.11 / FastAPI backend, a React 19 / TypeScript dashboard, a PostgreSQL 16 database, Redis caching, multi-tenant organization management, role-based access control (RBAC), and pre-wired Stripe subscription billing (configured in Test Mode).

---

### Q2: Why is the asset being sold?
**Answer:** The seller is an engineering team that completed the technical architecture, development, testing harness, and diligence documentation for the platform. The platform is offered as a pure software and intellectual property asset acquisition so that a commercial operator, prop trading firm, or fintech company with marketing, customer acquisition, and distribution capabilities can deploy and monetize the technology.

---

### Q3: What exactly is included in the proposed acquisition?
**Answer:** Subject to executed transaction agreements, the proposed transferable scope includes:
1. Project ORION software repository and documented acquisition assets where audited repository history shows a single-author commit history within the reviewed repository scope.
2. 21 pure Python domain logic packages (`libraries/domain/`).
3. 24 modular FastAPI backend API routers and service orchestrators.
4. React 19 Single-Page Application with 20 client routes (`apps/dashboard/`).
5. 15 linear forward Alembic database migration scripts managing 29 relational tables.
6. Automated test suite with documented historical baseline of 4,260 automated tests across 103 test suites.
7. Declarative Render PaaS blueprint (`render.yaml`) and Dockerfiles.
8. Disaster recovery restoration scripts (`backup/restore-database.sh`).
9. Complete 18-dossier due diligence data room, 8 presentation source docs, 24 visual presentation assets, 7 launch runbooks, and the sales package.

---

### Q4: Does Project ORION support live-money trading?
**Answer:** **No.** Project ORION operates strictly in **Paper-Trading Simulation Mode**. All orders and execution logs permanently stamp `is_paper=True`. The platform maintains **$0.00 live financial capital at risk** and enforces an initial **$100,000.00 USD virtual balance**. It does not contain live broker clearing rails, liquidity provider connections, or FIX protocol execution bridges.

---

### Q5: Does the platform handle or custody customer funds?
**Answer:** **No.** Project ORION is strictly a software application. It does not accept, hold, manage, or custody customer fiat or cryptocurrency deposits. It is not a bank, trust company, or custodial institution.

---

### Q6: What broker integrations are currently supported?
**Answer:** Broker connectivity is implemented exclusively for the **OANDA Practice sandbox** (`https://api-fxpractice.oanda.com`) via `OandaExecutionAdapter`. Attempts to configure live broker clearing URLs (`api-fxtrade.oanda.com`) fail closed and are blocked by `BrokerEndpointValidator`. For offline simulation, the platform provides `MockMarketDataProvider` and `PaperExecutionAdapter` which operate with zero external broker credentials.

---

### Q7: Does the platform have paying customers or active subscribers?
**Answer:** **NOT ESTABLISHED IN REPOSITORY.** Commercial customers and active subscribers are not established in repository evidence. The asset is offered as a pre-revenue software and intellectual property acquisition.

---

### Q8: Is there historical revenue, ARR, or MRR?
**Answer:** **NOT ESTABLISHED IN REPOSITORY.** Historical commercial revenue, ARR, and MRR are not established in repository evidence. The Stripe integration is configured in **Test Mode** with placeholder keys; no live commercial payments have been processed.

---

### Q9: What are the documented SaaS subscription prices in the app?
**Answer:** The codebase contains a pre-configured 4-tier commercial subscription quota model (`pricing.ts`, `subscription_service.py`):
* **Free Sandbox — $0/month:** 1 account, 100 orders/day, 0 workers, 4 major FX pairs, 30-day retention
* **Pro Trader — $99/month:** 3 accounts, 2,500 orders/day, 1 worker, 12 liquid FX pairs, 365-day retention
* **Business Prop Desk — $299/month:** 10 accounts, 50,000 orders/day, 5 workers, all FX pairs, 5-year retention
* **Enterprise — Custom:** Unlimited capacity, 7-year retention

> **Important Commercial Distinction**: These subscription tiers represent the documented in-app software subscription configuration. They are completely separate from the $24,900 software asset asking price.

---

### Q10: What is the acquisition asking price?
**Answer:** **$24,900 USD.** This is the seller's asking price for the proposed software/IP asset transaction. It is not a valuation, independent appraisal, revenue multiple, or SaaS subscription price. Transaction terms and closing arrangements remain subject to definitive bilateral agreements.

---

### Q11: What technology stack is used across the codebase?
**Answer:**
* **Backend:** Python 3.11+, FastAPI (ASGI), Pydantic v2, async SQLAlchemy 2.0 with asyncpg driver.
* **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Lucide icons.
* **Persistence & Caching:** Managed PostgreSQL 16 (15 Alembic migrations, 29 tables) and Redis 7.
* **Infrastructure:** Multi-stage Docker containers and declarative Render PaaS blueprint (`render.yaml`).
* **Telemetry:** Prometheus metrics (`/metrics`) and structured JSON logging.

---

### Q12: What testing and quality evidence exists in the repository?
**Answer:** The repository contains documented historical development evidence of:
* **4,260 Automated Tests:** Across 103 test suites spanning unit, integration, and security checks.
* **99.4% Test Coverage:** Documented across core domain packages and API router modules.
* **~7.2-Second Disaster Recovery Benchmark:** Physical schema and data restoration tested across 29 tables in an isolated testing container.

---

### Q13: What are the known technical limitations of the platform?
**Answer:** Fully disclosed in Dossier 13 (`docs/acquisition/13-KNOWN-LIMITATIONS.md`):
1. Pre-revenue status (no commercial revenue or paying subscribers established).
2. Paper-only execution ($0.00 live capital at risk; no live clearing rails).
3. OANDA integration is restricted strictly to practice sandbox endpoints.
4. Autonomous trading worker is disabled by default (`ORION_WORKER_ENABLED=false`).
5. External TwelveData market data and SMTP transactional email require buyer-provisioned API keys.
6. Candlestick pattern recognition algorithms are NOT IMPLEMENTED.
7. Telegram notification infrastructure adapter is DOMAIN-ONLY / not an operational delivery channel.
8. Software has not undergone third-party penetration testing, SOC 2, ISO 27001, or PCI-DSS certifications.
9. Platform holds zero FINRA, FCA, SEC, or ASIC regulatory licenses.
10. Single-region cloud deployment model.

---

### Q14: What external accounts and services must the buyer provision?
**Answer:** All third-party accounts are strictly **BUYER-PROVISIONED**:
* Render PaaS cloud hosting account (~$14/month documented baseline estimate for the referenced Render configuration; actual buyer operating cost depends on selected resources, region and usage).
* Stripe corporate merchant account.
* TwelveData API account (optional, for live market data).
* OANDA Practice developer account (optional, for external sandbox testing).
* Transactional SMTP relay account (SendGrid, Postmark, AWS SES).
* Custom domain and DNS management, if used.
* Production secrets (JWT signing secret, database passwords).

---

### Q15: Can the buyer deploy the application immediately?
**Answer:** **Yes.** The platform includes a declarative Infrastructure-as-Code blueprint (`render.yaml`). A buyer can connect the repository to their own Render PaaS account, configure environment variables as documented in Dossier 11, and deploy the complete stack (PostgreSQL, Redis, FastAPI web service) with automated pre-deploy migrations. Local development deployment via Docker Compose (`docker compose -f docker-compose.dev.yml up -d`) is also fully supported.

---

### Q16: How is intellectual property ownership transferred?
**Answer:** The proposed transferable scope is transferred via a formal **Software Asset Purchase Agreement (APA)** and an **Intellectual Property Assignment Agreement**. The audited repository history shows a single-author commit history within the reviewed repository scope (`Kiran Thange`). Third-party open-source libraries are governed by permissive licenses (MIT, Apache-2.0, BSD-3-Clause) as audited in Dossier 12 (`12-DEPENDENCY-SBOM.md`).

---

### Q17: How does due diligence work?
**Answer:** Prospective buyers who qualify under the Buyer Qualification framework and execute a standard mutual Non-Disclosure Agreement (NDA) receive full access to the 18-dossier due diligence data room under `docs/acquisition/`, covering technical architecture, security, database migrations, SBOM, operational runbooks, and disaster recovery benchmarks.

---

### Q18: What does the handover process include?
**Answer:** Handover is governed by Dossier 07 (`docs/acquisition/launch/07-HANDOVER-CLOSING-CHECKLIST.md`) and Dossier 04 (`docs/acquisition/04-TECHNICAL-HANDOVER-GUIDE.md`):
* Transfer of GitHub repository administrative ownership or delivery of a clean standalone Git archive.
* Delivery of all 18 due diligence dossiers, presentation assets, and operational runbooks.
* Verification of database schema migration execution (`alembic upgrade head`).
* Credential generation and environment configuration walkthrough.
* Up to 10 business days of async developer orientation support as defined in definitive transaction agreements.
