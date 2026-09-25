# Project ORION — Short Acquisition Listing

**Asset Category:** Pre-Revenue Quantitative Software & Intellectual Property Acquisition
**Asking Price:** $24,900 USD
**Document Reference:** `docs/acquisition/sales/02-SHORT-LISTING.md`

---

### Opportunity Overview
**Project ORION** is an implemented software foundation for quantitative foreign exchange (FX) research, backtesting, and simulated paper-trading. The platform is designed to take algorithmic FX trading strategies from mathematical formulation through historical backtesting and Walk-Forward Analysis (WFA) to simulated paper execution.

The asset is offered as an outright software and intellectual property acquisition. The buyer is acquiring an implemented software foundation rather than starting from a blank project.

---

### Asking Price & Transaction Terms
* **ASKING PRICE:** **$24,900 USD**
* *Price Disclosure Notice:* This is the seller's asking price for the proposed software/IP asset transaction. It is not a valuation, independent appraisal, revenue multiple, or SaaS subscription price.
* *Transaction Structure:* Outright software and intellectual property asset acquisition, subject to executed transaction agreements.

---

### Key Technical Capabilities
* **Quantitative Research & Indicators:** Vectorized indicator engine (EMA, RSI, MACD, ATR) with an extensible strategy registry supporting 4 concrete strategy classes and 9 parameter catalogue profiles.
* **Deterministic Backtesting:** Chronological bar traversal modeling bid/ask spreads, commissions, and execution slippage with reproducible trade journals.
* **Temporal Leakage Controls (`LeakageGuard`):** Strict point-in-time timestamp monotonicity checks designed to mitigate temporal leakage and look-ahead bias through chronological data validation and LeakageGuard controls.
* **Walk-Forward Analysis (WFA):** Rolling In-Sample (IS) training and Out-of-Sample (OOS) validation window slicing; computes Walk-Forward Efficiency (WFE) ratios to measure parameter stability across market regimes.
* **Strategy Deployment Governance:** 5-stage lifecycle state machine (`DRAFT` → `BACKTESTED` → `OPTIMIZED` → `INCUBATING` → `PROMOTED`) governing strategy readiness prior to simulation deployment.
* **Paper Execution Engine:** `PaperExecutionAdapter` modeling resting order queues, spread variance, volume decay, and adverse execution slippage.
* **Pre-Trade Risk Governance:** Pre-trade validation enforcing maximum drawdown limits, leverage ceilings (1:100 default limit), margin reservations, and daily loss caps.
* **Multi-Tenant SaaS Foundation:** Organization-scoped entity isolation via `organization_id` foreign keys, 7 RBAC roles, 41 domain permissions, append-only audit logging, and pre-wired Stripe billing (Test Mode).

---

### Technical Asset Inventory & Technology Stack
* **Backend:** Python 3.11 with FastAPI (ASGI), async SQLAlchemy 2.0, asyncpg (24 API router modules, 21 pure Python domain packages).
* **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Lucide icons (20 client routes).
* **Persistence & Cache:** Managed PostgreSQL 16 (15 linear forward Alembic migrations managing 29 tables) and Redis 7.
* **Infrastructure:** Declarative Render PaaS blueprint (`render.yaml`), Docker container manifests, and disaster recovery shell scripts.
* **Quality Evidence:** Historical development evidence records 4,260 automated tests and 99.4% documented historical test coverage across 103 test suites, with a documented ~7.2-second physical database restoration benchmark.
* **Diligence Data Room:** Complete 18-dossier technical due diligence data room, 8 presentation source docs, and 24 visual presentation assets.

---

### Paper-Trading Safety Boundary
* **Initial Account Balance:** Default virtual starting balance of **$100,000.00 USD**. Real funds are never accepted.
* **Financial Risk:** Strictly **$0.00 live financial capital at risk** across all demonstrated execution pathways.
* **Order Tagging:** All simulated orders and trade logs permanently stamp `is_paper=True`.
* **Broker Connectivity:** Restricted exclusively to OANDA Practice sandbox endpoints (`api-fxpractice.oanda.com`). Production live endpoints fail closed and are blocked by `BrokerEndpointValidator`.
* **Autonomous Worker Invariant:** Background trading worker is disabled by default (`ORION_WORKER_ENABLED=false`).
* **Market Data:** `MockMarketDataProvider` operates with internal deterministic synthetic data; TwelveData external feeds require buyer-provisioned API credentials.

---

### Commercial Status
* **Operating Model:** Pre-Revenue Technology / Software Asset.
* **Commercial Metrics:** Customers, subscribers, ARR, MRR, contracts, and historical commercial revenue are **NOT ESTABLISHED IN REPOSITORY**.
* **Billing System Mode:** Stripe Test Mode configured with placeholder test keys.
* **Documented SaaS Subscription Plans:** Free Sandbox — $0/month, Pro Trader — $99/month, Business Prop Desk — $299/month, Enterprise — Custom. *(Note: These are documented in-app subscription entitlement tiers. They are separate from the $24,900 software asset asking price).*
* **Hosting Overhead:** ~$14/month documented baseline estimate for the referenced Render configuration; actual buyer operating cost depends on selected resources, region and usage.

---

### Acquisition Scope & Handover
* **Proposed Transferable Scope:** Project ORION software repository and documented acquisition assets, including 21 domain packages, 24 API routers, React frontend, 15 migrations, 103 test suites, Dockerfiles, IaC blueprints, 18 diligence dossiers, presentation decks, and launch runbooks (subject to executed transaction agreements).
* **Buyer-Provisioned Services:** Cloud hosting (Render), payment gateway (Stripe), market data (TwelveData), broker sandbox (OANDA Practice), transactional SMTP, and custom domain and DNS management, if used, are independently provisioned by the buyer.
* **Key Limitations:** Pre-revenue asset; paper simulation only (no live broker clearing rails); candlestick pattern recognition is NOT IMPLEMENTED; Telegram adapter is DOMAIN-ONLY / not an operational delivery channel; no third-party SOC 2 or ISO 27001 certifications; uncertified/unregulated software asset.

---

### Next Steps & Contact
Request the buyer presentation, technical diligence package, or guided demonstration for further evaluation.
