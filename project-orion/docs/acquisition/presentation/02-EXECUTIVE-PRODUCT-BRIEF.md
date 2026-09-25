# Project ORION — Executive Product Brief

**Document Reference:** `docs/acquisition/presentation/02-EXECUTIVE-PRODUCT-BRIEF.md`  
**Classification:** Confidential — Acquisition Technical Due Diligence  
**Repository Working Copy:** `project-orion/`  
**Git Baseline Commit:** `d5908d0a0cc2feff99fa02573adb12b8eea33782`  
**Software Positioning:** Quantitative FX Research & Paper-Trading SaaS

---

## 1. Product Identification

* **Product Name:** Project ORION
* **Software Category:** Quantitative Foreign Exchange Research, Algorithmic Backtesting & Paper-Trading SaaS
* **Software Delivery Model:** Multi-tenant web platform and REST API runtime designed for quantitative researchers, algorithmic trading firms, and prop trading desks.
* **Core Value Proposition:** Complete research-to-incubation lifecycle software that eliminates curve-fitted algorithms through walk-forward efficiency validation and tests execution against realistic transaction friction with zero real capital exposure.

---

## 2. Core Capabilities

1. **Deterministic Historical Backtesting:** Sequential bar-by-bar historical backtest engine with strict chronological monotonicity and trade-by-trade analytics.
2. **Temporal Look-Ahead Protection:** `LeakageGuard` validation layer architecturally preventing indicators and strategy logic from accessing future bar timestamps.
3. **Multi-Parameter Optimization:** Systematic parameter space exploration with sensitivity surfaces and configurable search grids.
4. **Walk-Forward Analysis (WFA):** Rolling In-Sample (IS) and Out-Of-Sample (OOS) window evaluation computing Walk-Forward Efficiency ($WFE$) to detect curve-fitting.
5. **Quality Gates Governance:** Automated candidate evaluation hurdles (WFE thresholds, max drawdown ceilings, parameter stability) governing lifecycle promotion.
6. **Realistic Paper Execution:** `PaperExecutionAdapter` simulating market, limit, stop, and trailing stop orders with spread, adverse slippage, and position netting.
7. **Pre-Trade Risk Management:** Dynamic evaluation of required margin, leverage ceilings (e.g. 1:100 default), position size limits, and daily drawdown caps.
8. **Multi-Tenancy & RBAC:** Complete organization tenant isolation with 7 organizational roles governing 41 granular domain permissions.
9. **Structured Auditability:** Immutable audit logging capturing platform actions with actor IDs, component tags, timestamps, and contextual JSON details.
10. **Declarative PaaS Deployment:** Single-command 4-tier cloud infrastructure deployment blueprint via `render.yaml`.

---

## 3. Technology Stack

* **Backend API Engine:** Python 3.11+, FastAPI (ASGI), Pydantic v2 schemas, SQLAlchemy 2.0 Async ORM.
* **Frontend Web Application:** React 18, Vite, TypeScript, Tailwind CSS, TanStack Query, Lucide Icons (20 distinct routes).
* **Database & Persistence:** PostgreSQL 16 relational database with 15 linear Alembic migrations managing 29 tables.
* **Cache & Message Broker:** Redis 7 with graceful in-memory degraded fallback for session and rate-limit handling.
* **Deployment & Containerization:** Docker container builds orchestrated via Render PaaS Infrastructure-as-Code blueprint.

---

## 4. Safety & Capital Risk Model

* **Financial Capital at Risk:** Exactly **$0.00**.
* **Simulated Execution Invariant:** The demonstrated execution path uses simulated paper capital only. All orders are stamped with `is_paper=True`.
* **Broker Boundary:** The platform implements internal simulated execution and an external sandbox adapter for OANDA Practice (`OANDA_ENVIRONMENT=practice`). Live real-money brokerage execution is absent from the software.
* **Market Data Boundary:** Default operation utilizes deterministic synthetic market data generated offline by `MockMarketDataProvider`. External live market quote ingestion is supported via `TwelveDataMarketDataProvider` when provisioned with an operator API key.
* **Autonomous Worker State:** `AutonomousWorkerCoordinator` is implemented in source code with manual execution trigger (`/api/v1/worker/run-once`), but is disabled by default in cloud deployments (`WORKER_ENABLED=false`).

---

## 5. Commercial Status & Monetization

* **Commercial Revenue / ARR / MRR:** **NOT ESTABLISHED IN REPOSITORY** (pre-revenue technology asset).
* **Customer Base & Accounts:** **NOT ESTABLISHED IN REPOSITORY** (clean pre-commercial asset sale).
* **Active Commercial Subscribers:** **NOT ESTABLISHED IN REPOSITORY**.
* **Payment Processing Integration:** Implemented for Stripe Test Mode; live production billing requires buyer merchant account provisioning.
* **Authoritative Implemented Subscription Model:**
  * **Free Sandbox ($0/month):** 1 paper account, 100 daily orders, 0 workers, 4 major FX pairs, 30-day data retention.
  * **Pro Trader ($99/month):** 3 paper accounts, 2,500 daily orders, 1 worker, 12 liquid FX pairs, 365-day data retention.
  * **Business Prop Desk ($299/month):** 10 paper accounts, 50,000 daily orders, 5 workers, all FX pairs, 5-year data retention.
  * **Enterprise Institutional (Custom):** Unlimited accounts, daily orders, and workers; 7-year data retention.

---

## 6. Acquisition Deliverables

Subject to executed transaction documents, the proposed acquisition scope includes:
1. **Source Code Repository:** Complete Git repository including full historical commit provenance and zero hardcoded secrets.
2. **Automated Test Baseline:** Documented historical test baseline of 4,260 automated tests with 99.4% line coverage across 103 test suites.
3. **Database Architecture:** Complete SQLAlchemy 2.0 models and 15 linear Alembic migration scripts.
4. **Closing Due Diligence Dossiers:** 18 comprehensive technical handover dossiers under `docs/acquisition/`.
5. **Infrastructure Blueprints:** Declarative PaaS deployment configuration (`render.yaml`) and Docker container definitions.

---

## 7. External Dependencies (Buyer-Provisioned)

* **Cloud Hosting:** Buyer provisions their own Render account and payment method for PaaS hosting (~$14/month configuration estimate).
* **Payment Gateway:** Buyer provisions their own Stripe merchant account and API keys for live billing.
* **Live Market Data:** Buyer provisions an external TwelveData API key for real-time market quote ingestion.
* **Broker Sandbox:** Buyer registers an OANDA Practice account for external sandbox integration testing.
* **Transactional Email:** Buyer configures an external SMTP server for transactional email delivery.
* **Domain & DNS:** Buyer registers their custom proprietary domain and manages DNS routing.

---

## 8. Known Engineering Limitations

* **Stateless REST Communication:** API communicates over standard HTTP REST with on-demand polling; no continuous WebSocket push endpoints are implemented.
* **Single-Process Worker Loop:** The execution coordinator is designed as a single-process event loop; multi-worker distributed clustering requires future queue infrastructure (e.g. Celery with Redis).
* **Paper Trading Scope:** The software terminates strictly at paper validation; commercial retail broker operations require the buyer to secure regulatory licensing and live brokerage clearing agreements.
