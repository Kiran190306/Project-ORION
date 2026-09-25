# Project ORION

### Quantitative FX Research & Paper-Trading SaaS Platform

> **Acquisition Due Diligence Notice**: Project ORION is a pre-revenue quantitative software and intellectual property asset. This repository contains the complete source code, algorithmic research engines, automated testing suites, infrastructure blueprints, and formal acquisition diligence materials.
>
> **Financial & Execution Boundary**: Project ORION operates strictly in **Paper-Trading Simulation Mode**. The software maintains **$0.00 live financial capital at risk**, enforces a **$100,000 virtual paper balance**, and executes orders exclusively through internal simulated order books (`PaperExecutionAdapter`, `is_paper=True`) and external practice sandboxes (OANDA Practice). The platform does **not** provide live broker execution, client money custody, or fund administration.

---

## Repository Structure & Navigation

The active, maintained software platform and diligence package reside entirely inside the [`project-orion/`](project-orion/) directory. Root-level legacy artifacts in this repository reflect historical engineering milestones and architecture freezes from early development cycles.

```text
.
├── project-orion/                  # Active software platform & acquisition package
│   ├── apps/                       # Applications (FastAPI backend & React dashboard)
│   │   ├── trading-engine/         # Core ASGI REST API & domain services
│   │   └── dashboard/              # React 19 / TypeScript web interface
│   ├── libraries/                  # Domain-driven packages & infrastructure adapters
│   │   ├── domain/                 # Pure business logic (research, risk, execution, etc.)
│   │   ├── infrastructure/         # External integrations (persistence, market data, broker)
│   │   └── observability/          # Structured logging, metrics, and tracing
│   ├── database/                   # Relational persistence & Alembic migrations
│   ├── tests/                      # Automated test suites (unit, integration, e2e)
│   ├── backup/                     # Database and cache backup/restore shell automation
│   ├── docker/                     # Multi-stage production container definitions
│   ├── render.yaml                 # Render PaaS infrastructure blueprint
│   └── docs/                       # Complete engineering & diligence documentation
│       └── acquisition/            # Formal buyer acquisition packages (Dossiers, Visuals, Launch)
│           ├── 01-18               # 18 canonical due diligence dossiers
│           ├── presentation/       # Buyer presentation source docs & visual assets
│           └── launch/             # 7 acquisition launch & closing runbooks
└── README.md                       # Repository root overview (this document)
```

---

## Acquisition & Due Diligence

A comprehensive, structured technical diligence and transaction package is prepared and maintained under [`project-orion/docs/acquisition/`](project-orion/docs/acquisition/). The package consists of **18 canonical acquisition dossiers**, **8 presentation source documents**, **24 visual presentation assets**, and **7 acquisition launch documents**:

### Primary Buyer Resources
* **[Buyer Pitch Memo](project-orion/docs/acquisition/launch/02-BUYER-PITCH-MEMO.md)** — Executive investment thesis, architectural highlights, monetization model, and operational cost profile.
* **[Executive Product Brief](project-orion/docs/acquisition/presentation/02-EXECUTIVE-PRODUCT-BRIEF.md)** — Core product overview, target markets, user personas, and feature matrix.
* **[Technical Architecture Sheet](project-orion/docs/acquisition/presentation/03-TECHNICAL-ARCHITECTURE-SHEET.md)** — Hexagonal domain architecture, component boundaries, data flows, and infrastructure specifications.
* **[Acquisition Listing](project-orion/docs/acquisition/launch/01-ACQUISITION-LISTING.md)** — Asset sale summary, technical stack specifications, operational requirements, and transaction boundaries.
* **[Due Diligence Data Room Index](project-orion/docs/acquisition/18-DUE-DILIGENCE-DATA-ROOM-INDEX.md)** — Four-tier due diligence taxonomy mapping all repository evidence across 18 canonical dossiers.
* **[Buyer FAQ](project-orion/docs/acquisition/presentation/05-BUYER-FAQ.md)** — Direct answers to common technical, architectural, operational, and commercial buyer questions.
* **[Demo Environment Runbook](project-orion/docs/acquisition/launch/06-DEMO-ENVIRONMENT-RUNBOOK.md)** — 15-minute standardized walkthrough script for technical and commercial evaluation.
* **[Handover & Closing Checklist](project-orion/docs/acquisition/launch/07-HANDOVER-CLOSING-CHECKLIST.md)** — Day-1 technical transfer, credential rotation, DNS cutover, and escrow release protocol.
* **[Presentation Source Package](project-orion/docs/acquisition/presentation/)** — Complete collection of buyer slide decks, operator guides, and claim control frameworks.
* **[Visual Presentation Package](project-orion/docs/acquisition/presentation/visual/)** — Generated PDF briefing sheets, PowerPoint deck (`.pptx`), and standalone SVG architecture diagrams.

---

## Product Capabilities

Project ORION is structured around an event-driven, domain-centric model delivering quantitative research and simulated paper trading:

* **Market Data Abstraction:** Pluggable market data provider architecture supporting deterministic internal simulation (`MockMarketDataProvider`) and external rate-limited FX feeds (TwelveData integration).
* **Technical Indicators:** High-performance vectorized indicator implementations including Exponential Moving Average (EMA), Relative Strength Index (RSI), Moving Average Convergence Divergence (MACD), and Average True Range (ATR).
* **Quantitative Strategy Engine:** Extensible strategy framework with 4 concrete implementations (`EMAStrategy`, `RSIStrategy`, `MACDStrategy`, `ATRStrategy`) and 9 strategy catalogue profiles.
* **Historical Backtesting Framework:** Event-driven backtesting simulator with configurable slippage, spread, and commission modeling.
* **Walk-Forward Analysis (WFA):** Out-of-sample robustness testing across rolling optimization windows to identify parameter decay and evaluate overfitting risk.
* **Strategy Parameter Optimization:** Multi-parameter grid and random search engines with parameter space validation and efficiency constraints.
* **Temporal Leakage Controls (`LeakageGuard`):** Strict point-in-time timestamp enforcement preventing look-ahead bias during backtesting, feature generation, and parameter optimization.
* **Deployment Governance Pipeline:** 5-stage lifecycle state machine (`DRAFT` → `BACKTESTED` → `OPTIMIZED` → `INCUBATING` → `PROMOTED`) governing strategy readiness prior to simulation deployment.
* **Simulated Execution Engine:** Internal paper execution engine (`PaperExecutionAdapter`, `is_paper=True`) executing orders against simulated liquidity books.
* **Risk & Position Controls:** Pre-trade validation enforcing maximum drawdown limits, maximum leverage thresholds, position sizing guardrails, and daily loss caps.
* **Trading Ledger & Lifecycle:** Full double-entry style auditability for simulated orders, executions, fills, and portfolio positions.
* **Multi-Tenant Organization Model:** Architectural multi-tenancy with tenant isolation enforced via `organization_id` foreign key relationships and role-based authorization across all tenant-scoped data.
* **Role-Based Access Control (RBAC):** 7 pre-configured organizational roles (`OWNER`, `ADMIN`, `PORTFOLIO_MANAGER`, `TRADER`, `ANALYST`, `AUDITOR`, `VIEWER`) and 41 granular domain permissions across 14 functional domains.
* **Audit Logging:** Immutable security and operational event logging capturing administrative, authentication, and execution activities.
* **Commercial Billing Integration:** Pre-wired Stripe billing infrastructure configured in Test Mode supporting subscription lifecycle webhooks and tier quota enforcement.
* **Authentication & Onboarding:** JWT authentication (HS256) with salted bcrypt password hashing, organization self-provisioning, and default paper account allocation.
* **Disaster Recovery Automation:** Shell-based backup and physical database restoration automation with verified checksum validation.
* **Health & Observability:** Production liveness (`/health/live`), readiness (`/health/ready`), and Prometheus telemetry metrics.

> **Feature Boundary Notice**:
> * **Candlestick Pattern Recognition:** *Not implemented in repository.*
> * **Telegram Alerts:** *Domain data structures only; not configured as a live operational notification channel.*

---

## Architecture & Technology Stack

The platform is designed under Clean Architecture and Domain-Driven Design (DDD) principles, decoupling core business logic from infrastructure adapters and presentation layers:

* **Backend Framework:** Python 3.11 with FastAPI (ASGI, asynchronous event loop, Pydantic v2 schemas).
* **Frontend Application:** React 19, TypeScript, Vite, Tailwind CSS, Lucide icons.
* **Database & Persistence:** PostgreSQL 16 managed relational store utilizing async SQLAlchemy 2.0 with asyncpg driver; 15 Alembic schema migrations across 29 relational tables.
* **Cache & Coordination:** Redis 7 in-memory cache supporting sliding-window API rate limiting, real-time market data caching, and distributed synchronization.
* **Containerization:** Multi-stage Docker container builds with non-root security execution.
* **Cloud Infrastructure:** Infrastructure-as-Code blueprint (`render.yaml`) targeting Render PaaS with automated pre-deploy migrations.
* **Broker Connectivity Boundary:** Broker-agnostic abstraction; practice sandbox adapter for OANDA (`api-fxpractice.oanda.com`). Live trading endpoints are actively blocked.

*(Note: The platform utilizes a single-region deployment configuration. Kubernetes, Go microservices, and active-active multi-region clustering are neither implemented nor claimed).*

---

## Verified Engineering Evidence

The following metrics represent verified, documented engineering baselines established in repository verification audits:

* **Automated Test Suite:** 4,260 automated tests across 103 test suites (*documented historical baseline*).
* **Test Code Coverage:** 99.4% overall test coverage (*documented historical baseline*).
* **Database Restoration Speed:** ~7.2-second physical schema and data restore benchmark across 29 tables in isolated container testing.
* **API Surface Area:** 24 FastAPI router modules exposing REST endpoints.
* **Domain Structure:** 21 internal domain modules organizing business rules and value objects.
* **Database Schema:** 15 Alembic migration revisions managing 29 relational tables.
* **Strategy Models:** 4 concrete strategy implementations and 9 parameter catalogue profiles.
* **Access Control:** 7 RBAC roles governing 41 granular permissions across 14 functional domains.

*(Note: These figures reflect documented historical verification benchmarks and are not live real-time runtime guarantees).*

---

## Commercial Model & Subscription Pricing

The codebase contains pre-configured SaaS subscription plans governing feature access, compute quotas, and historical data retention:

| Plan | Price | Paper Accounts | Daily Orders | Workers | Asset Coverage | Data Retention |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Free Sandbox** | **$0 / month** | 1 Account | 100 / day | 0 Workers | 4 Major Pairs | 30 Days |
| **Pro Trader** | **$99 / month** | 3 Accounts | 2,500 / day | 1 Worker | 12 Liquid Pairs | 365 Days |
| **Business Prop** | **$299 / month** | 10 Accounts | 50,000 / day | 5 Workers | All Supported Pairs | 5 Years (1,825 Days) |
| **Enterprise** | **Custom** | Unlimited | Unlimited | Unlimited | All Supported Pairs | 7 Years |

> **Important Commercial Distinction**:  
> The subscription pricing tiers above represent the documented in-app software subscription configuration implemented in code (`apps/dashboard/src/config/pricing.ts`). They do **not** represent the transaction acquisition price for the software asset itself.

---

## Commercial Status & Operational Baseline

* **Commercial Status:** Pre-revenue technology asset.
* **Customer & Revenue Disclosure:** Active paying customers, recurring subscribers, ARR, MRR, contracts, and commercial revenue are **not established in the repository**.
* **Billing System Mode:** Stripe integration is configured strictly in **Test Mode** (`sk_test_...` placeholders). No live payments have been processed.
* **Hosting Cost Baseline:** Baseline cloud hosting on Render is configured for approximately **$14/month** ($7 managed PostgreSQL + $7 API web service; Redis free tier).

---

## Paper-Trading Safety & Operational Controls

Project ORION is engineered with strict safeguards to isolate simulated trading operations:

1. **Virtual Capital Allocation:** Accounts are provisioned with an initial virtual balance of **$100,000.00 USD**. Real funds are never accepted.
2. **Zero Capital Risk:** All trading execution occurs via `PaperExecutionAdapter` with `is_paper=True`. The platform maintains **$0.00 live financial capital at risk**.
3. **Sandbox Broker Integration:** Broker connectivity is constrained to OANDA Practice (`api-fxpractice.oanda.com`). Production broker endpoints (`api-fxtrade.oanda.com`) fail closed and are blocked by `BrokerEndpointValidator`.
4. **Autonomous Worker Invariant:** The background trading worker is disabled by default (`ORION_WORKER_ENABLED=false`).
5. **No Financial Guarantees:** Backtests and Walk-Forward Analysis evaluate historical hypotheses only; past simulated performance provides no guarantee of future live market results.

---

## Known Limitations & Transaction Boundaries

Prospective buyers should review the following transparent operational boundaries (documented fully in [`project-orion/docs/acquisition/13-KNOWN-LIMITATIONS.md`](project-orion/docs/acquisition/13-KNOWN-LIMITATIONS.md)):

* **Simulated Execution Only:** No live trading broker gateway or FIX protocol adapter is implemented.
* **External Provider Provisioning:** Third-party vendor accounts (TwelveData API, OANDA Practice, Stripe, transactional SMTP, Render cloud hosting) must be provisioned independently by the acquiring entity.
* **Single-Region Deployment:** Configured for single-region deployment; multi-region geo-replication is not implemented.
* **Compliance & Certifications:** The software has not undergone SOC 2, ISO 27001, PCI-DSS, or third-party penetration-test audits. It is not licensed by FINRA, FCA, or the SEC.
* **Commercial Traction:** Commercial traction, subscriber cohorts, and historical revenue are not established in the repository.

---

## Intellectual Property & Software Transfer

Proposed transferable software and intellectual property scope is documented in the acquisition materials and remains subject to executed transaction agreements. 

The software utilizes standard open-source libraries (e.g., FastAPI, SQLAlchemy, React, Tailwind CSS) governed by permissive licenses (MIT, Apache 2.0, BSD). Full dependency manifests and transfer checklists are available in:
* **[Dependency SBOM Dossier](project-orion/docs/acquisition/12-DEPENDENCY-SBOM.md)**
* **[IP Assignment Checklist](project-orion/docs/acquisition/15-IP-ASSIGNMENT-CHECKLIST.md)**
