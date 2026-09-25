# Project ORION — Acquisition Marketplace Listing Specification

**Document Reference:** `docs/acquisition/launch/01-ACQUISITION-LISTING.md`  
**Classification:** Confidential / Prospective Acquirer Memorandum  
**Asset Baseline Commit:** `d5908d0a0cc2feff99fa02573adb12b8eea33782`  
**Execution Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Live Financial Capital at Risk)  

---

## 1. Listing Title
**Project ORION — Quantitative FX Research, Algorithmic Backtesting & Simulated Paper-Trading SaaS**

---

## 2. One-Line Description
A modern Python 3.11 / React 18 multi-tenant SaaS platform delivering institutional-architecture quantitative Forex strategy research, Walk-Forward Analysis, and adverse-slippage paper trading with zero live financial capital at risk.

---

## 3. Executive Summary
Project ORION is an implementation-complete quantitative software asset engineered to take foreign exchange algorithmic strategies from mathematical formulation through historical backtesting and Walk-Forward Analysis (WFA) to simulated paper execution. Built upon Domain-Driven Design (DDD) and Hexagonal Architecture principles, the platform decouples pure algorithmic logic from external infrastructure.

The asset is offered as a pure software and intellectual property asset acquisition. It provides an existing technical foundation that a buyer can evaluate, adapt, and extend. The monorepo includes a complete FastAPI ASGI backend, a React 18 / TypeScript / Vite Single-Page Application (SPA), a PostgreSQL 16 schema with 15 linear forward migrations across 29 tables, a declarative 4-tier PaaS deployment blueprint for Render, an automated test harness with 4,260 automated tests and 99.4% documented historical test coverage, and an 18-dossier due diligence data room.

---

## 4. What Project ORION Is
Project ORION is a specialized quantitative engineering platform tailored for quantitative researchers, algorithmic trading prop desks, fintech software operators, and financial technology holding companies. 

### Explicit Negative Declarations
To maintain strict compliance and absolute transparency, Project ORION is explicitly **NOT**:
* A live-money trading brokerage or registered broker-dealer.
* An investment advisor, commodity trading advisor (CTA), or asset management fund.
* A custodian of customer funds or bank deposits.
* A live financial execution venue or liquidity provider.
* A regulated financial institution holding SEC, FINRA, FCA, or ASIC certifications.

All virtual execution, position tracking, margin requirements, and trade logging operate strictly within virtual simulation environments ($0.00 live financial capital at risk).

---

## 5. Core Product Capabilities
The platform implements a comprehensive quantitative research and paper trading lifecycle:

1. **Modular Strategy Engine:** Strategy registry supporting trend-following, momentum, mean-reversion, and breakout archetypes with typed Pydantic v2 parameter schemas.
2. **Deterministic Backtesting:** Sequential chronological bar traversal modeling bid/ask spreads with cent-level reproducible trade journals and performance statistics (Sharpe, Sortino, Calmar, Max Drawdown).
3. **Temporal Leakage Protection (`LeakageGuard`):** Enforces point-in-time timestamp monotonicity across indicator calculations, mathematically preventing look-ahead bias.
4. **Combinatorial Grid Optimization:** Multi-parameter search traversing bounded hyperparameter spaces with objective function ranking.
5. **Walk-Forward Analysis (WFA):** Rolling In-Sample (IS) training and Out-of-Sample (OOS) validation slices computing Walk-Forward Efficiency (WFE) ratios to detect curve-fitting.
6. **Strategy Deployment Pipeline:** Programmatic 5-state lifecycle governance (`PENDING_GATES` $\rightarrow$ `GATES_PASSED` $\rightarrow$ `INCUBATING` $\rightarrow$ `PAPER_VALIDATED` $\rightarrow$ `PROMOTION_CANDIDATE`).
7. **Adverse Slippage Paper Execution:** `PaperExecutionAdapter` models resting order queues, spread volatility, order volume decay, and execution slippage ($0.00 live capital at risk).
8. **Pre-Trade Risk Governance:** Dynamic pre-trade evaluation of margin consumption, leverage limits (1:100 default ceiling), drawdown limits, and daily loss limits.
9. **Multi-Tenant SaaS Architecture:** Tenant-owned application entities are organization-scoped via `organization_id` foreign keys and authorization controls, validated against signed JWT `TenantContext` tokens (migration metadata tables such as `alembic_version` are non-tenant system records).
10. **Role-Based Access Control (RBAC):** 7 organization roles governing 41 granular permissions across administrative, research, and paper-trading functional domains.
11. **Immutable Audit Logging:** Append-only operational logging capturing acting user IDs, timestamps, event actions, and structured JSON context.
12. **Commercial Billing Integration:** Stripe subscription billing integrated in Stripe Test Mode across 4 distinct tier quotas.
13. **User Onboarding Workflow:** Persisted 5-step onboarding state machine guiding users through registration, risk acceptance, and paper readiness.
14. **System Health & Observability:** Production health probes (`/health/live`, `/health/ready`), Prometheus metric scraping (`/metrics`), and correlation ID request tracing.

*Note on Roadmap Items:* Candlestick pattern recognition algorithms and Telegram notification infrastructure adapters are not currently implemented in the repository (documented in Dossier 13).

---

## 6. Quantitative Research Workflow
ORION implements a disciplined, 5-stage research pipeline designed to enforce mathematical hygiene:

```
[1. Strategy Formulation] ──► [2. Backtest Engine] ──► [3. WFA / Optimization]
         │                            │                          │
         ▼                            ▼                          ▼
Typed Parameter Schema        Deterministic Bars          LeakageGuard Check
4 Built-in Strategies        Arbitrary Decimal Math       IS/OOS Window Slicing
                                                                 │
                                                                 ▼
[5. Promotion Review]     ◄── [4. Paper Incubation]  ◄── [Quality Gates Hurdle]
         │                            │                          │
         ▼                            ▼                          ▼
Terminal Candidate           Simulated Execution          WFE >= 0.50
Governance Gate              $0.00 Capital at Risk        Max DD <= 15%
```

---

## 7. Paper Trading / Risk Boundary
* **Initial Account Balance:** Provisioned at a default virtual balance of **$100,000**.
* **Financial Risk:** Strictly **$0.00 live capital at risk** across all demonstrated execution pathways.
* **Order Immutability:** Simulated orders permanently stamp `is_paper=True`.
* **Broker Practice Sandbox:** External broker communication is strictly restricted to practice sandbox environments (OANDA Practice v20 endpoints). Attempts to configure live broker clearing URLs fail closed.

---

## 8. Architecture
* **Design Pattern:** Hexagonal Architecture (Ports and Adapters) with Domain-Driven Design (DDD).
* **Backend Tier:** Python 3.11+, FastAPI (ASGI), Pydantic v2, SQLAlchemy 2.0 Async ORM (24 modular API routers).
* **Frontend Tier:** React 18, Vite, TypeScript, Tailwind CSS, TanStack Query, Lucide Icons (20 client routes).
* **Domain Layer:** 21 pure Python domain packages under `libraries/domain/` with zero framework dependencies.
* **Database Layer:** PostgreSQL 16 managed via 15 linear forward Alembic migrations across 29 relational tables.
* **Cache & Rate Limiting:** Redis 7 with graceful in-memory degraded fallback for sessions and rate limiting.

---

## 9. Technical Asset Inventory
* **Repository:** Monorepo containing frontend SPA, backend engine, domain libraries, migrations, and scripts.
* **Routers & Routes:** 24 FastAPI API router modules assembled in the application factory.
* **Domain Packages:** 21 pure Python internal packages (`libraries/domain/`).
* **Database Architecture:** 15 linear Alembic migrations managing 29 tables.
* **Automated Test Harness:** Historical development evidence records 4,260 automated tests and 99.4% documented historical test coverage across 103 test suites.
* **Disaster Recovery Benchmark:** Tested shell scripts benchmarked at ~7.2 seconds for full database restoration across 29 tables in an isolated test container.
* **Due Diligence Suite:** 18 canonical dossiers under `docs/acquisition/`.
* **Visual Presentation Suite:** 15-slide widescreen PPTX deck with speaker notes, 5 standalone vector SVGs, and 7 A4 publication PDFs.

---

## 10. Commercial Status
* **Operating Model:** Pre-revenue technology asset.
* **Commercial Metrics:** Customers, subscribers, ARR, MRR, contracts, and historical commercial revenue are **`NOT ESTABLISHED IN REPOSITORY`** (pre-revenue technology asset).
* **Billing System:** Implemented in **Stripe Test Mode / Developer Sandbox** with mock webhook handling.
* **Basis of Sale:** Outright software and intellectual property asset acquisition. Acquisition terms and purchase price are subject to bilateral negotiations between transaction parties.

---

## 11. Subscription Pricing Architecture
The platform enforces a 4-tier commercial subscription quota model in source code (`subscription_service.py`, `pricing.ts`):

| Subscription Tier | Monthly SaaS Fee | Virtual Paper Accounts | Daily Order Cap | Autonomous Workers | FX Pairs & Retention |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Free Sandbox** | **$0 / month** | 1 Account ($100k balance) | 100 orders / day | 0 Workers | 4 Major Pairs │ 30-Day History |
| **Pro Trader** | **$99 / month** | 3 Accounts | 2,500 orders / day | 1 Worker | 12 Liquid Pairs │ 365-Day History |
| **Business Prop** | **$299 / month** | 10 Accounts | 50,000 orders / day | 5 Workers | All Pairs │ 5-Year History |
| **Enterprise** | **Custom Contract** | Unlimited | Unlimited Capacity | Custom Pool | Full Cross-Asset │ 7-Year History |

*Note: SaaS subscription pricing reflects the end-user monetization capability built into the software and does not represent an acquisition asking price or valuation.*

---

## 12. Proposed Transferable Software / IP Scope
Subject to executed transaction agreements, the proposed transferable scope includes:
1. Complete Git repository source tree with linear commit provenance.
2. 21 internal domain logic packages (`libraries/domain/`).
3. 24 modular FastAPI backend routers and application factory.
4. React 18 Single-Page Application with 20 client routes.
5. 15 linear forward Alembic database migration scripts.
6. 103 automated test suites (historical baseline of 4,260 tests).
7. Declarative Render PaaS blueprint (`render.yaml`) and Dockerfiles.
8. Disaster recovery restoration scripts (`backup/restore-database.sh`).
9. Complete 18-dossier due diligence data room (`docs/acquisition/`).
10. Full visual presentation package (PPTX, PDFs, SVGs, HTML templates).

---

## 13. Buyer-Provisioned Infrastructure (BUYER-PROVISIONED)
To ensure clean corporate separation and eliminate third-party vendor lock-in, the acquirer independently provisions all external services (designated as BUYER-PROVISIONED):
* **Cloud Hosting Account:** Buyer provisions their own Render PaaS organization (`render.yaml` deployed under buyer billing).
* **Payment Gateway:** Buyer establishes an independent Stripe corporate merchant account.
* **Market Data Subscription:** Buyer secures a TwelveData API key if live external market data quotes are desired.
* **Broker Practice Account:** Buyer registers an OANDA Practice account for external sandbox testing.
* **Transactional Email Relay:** Buyer provisions an external SMTP service (SendGrid, Postmark, AWS SES).
* **Custom Domain & DNS:** Buyer purchases their proprietary web domain and delegates DNS routing.
* **Production Secrets:** Buyer generates and manages production JWT signing secrets and database passwords.

---

## 14. External Dependencies
* **Render PaaS:** Approximately $14/month baseline configuration hosting estimate based on the documented Render configuration ($7 managed DB + $7 web service under published 2026 pricing); actual cloud pricing may vary and is buyer-provisioned.
* **TwelveData API:** External market data feed adapter (optional; offline synthetic data works out-of-the-box).
* **OANDA Practice API:** External broker sandbox adapter (optional; internal matching works out-of-the-box).
* **Stripe:** Merchant billing client (configured in Test Mode).
* **Open-Source Packages:** The documented dependency review identifies MIT, Apache-2.0, BSD-3-Clause, and ISC licenses within the reviewed dependency set (see Dossier 12 SBOM). The repository dependency review did not identify copyleft licenses within the reviewed dependency set. Final legal and IP review remains subject to buyer diligence.

---

## 15. Known Limitations
In accordance with full disclosure standards, the following technical limitations are registered (Dossier 13):
1. **Paper-Only Execution:** Platform routes virtual orders only; contains no real-money clearing rails ($0.00 capital at risk).
2. **Autonomous Worker Gated:** Background trading loop is disabled by default in cloud runtime (`WORKER_ENABLED=false`).
3. **Single-Process Worker Loop:** Async event loop; horizontal cluster scaling requires Celery/Redis queue adoption.
4. **Stateless REST Polling:** Client UI updates via on-demand HTTP polling; continuous WebSocket push is not implemented.
5. **No External Penetration Test:** Extensive internal security test coverage exists, but no third-party ethical hacking audit has been conducted.
6. **No Formal Regulatory Certifications:** Software holds zero SOC 2, ISO 27001, or PCI-DSS compliance certifications.
7. **Single-Region Deployment:** The Render deployment is configured for a single selected deployment region; the documented configuration can target a supported region such as Oregon or Frankfurt, subject to buyer provisioning.
8. **Offsite Backup Replication:** Backup scripts write locally; offsite cloud bucket replication requires buyer cron configuration.
9. **Telegram Adapter:** Domain models defined; infrastructure delivery adapter is not implemented.
10. **Candlestick Patterns:** OHLCV candle structures exist; pattern recognition algorithms are not implemented.

---

## 16. Demo Availability
A self-contained technical demonstration can be conducted immediately without external API credentials:
* **Offline Demo Path:** Uses `MockMarketDataProvider` for deterministic synthetic market data and `PaperExecutionAdapter` for virtual matching.
* **Demonstration Coverage:** Full walkthrough of authentication, strategy configuration, deterministic backtesting, `LeakageGuard` inspection, Walk-Forward Analysis, order placement, pre-trade risk evaluation, and audit logging.
* **Preflight Verification:** Supported by `Project-ORION-Demo-Operator-Sheet.pdf` and Dossier 06.

---

## 17. Due Diligence Data Room
A structured, 18-dossier technical due diligence data room is organized under `docs/acquisition/` across 4 tiers:
* **Tier 1 (Executive):** Dossiers 01–03 (Executive Brief, Product Overview, Architecture Overview).
* **Tier 2 (Technical):** Dossiers 04–10 (Handover Guide, Deployment, Runbooks, Security, DR, API Docs, Migrations).
* **Tier 3 (Operational):** Dossiers 11–14 (Environment Reference, SBOM, Known Limitations, PaaS Topology).
* **Tier 4 (Transaction):** Dossiers 15–18 (IP Checklist, Account Transfer, Domain Transfer, Master Index).

---

## 18. Acquisition Scope & Transaction Terms
* **Transaction Structure:** Outright software and intellectual property asset purchase.
* **Legal Qualification:** Proposed Transferable Software / IP Scope, subject to executed transaction agreements.
* **No Premature Transfer:** Legal title and intellectual property rights do not transfer prior to transaction closing.

---

## 19. Technical Evidence
* **Source Monorepo:** Clean Git working copy at baseline commit `d5908d0a0cc2feff99fa02573adb12b8eea33782`.
* **Automated Tests & Coverage:** Historical development evidence records 4,260 automated tests and 99.4% documented historical test coverage across 103 test suites.
* **Database DR Benchmark:** Isolated test container demonstration benchmarked at ~7.2 seconds restoration across 29 tables.
* **Code Provenance:** Verifiable single-author linear Git commit history.

---

## 20. Important Disclosures
* The platform contains no historical customer revenue, paying subscriber contracts, or audited investment returns.
* Past backtest, optimization, or WFA results are simulated calculations and do not constitute representations of future live market profitability.
* All financial transactions and cloud hosting accounts are provisioned directly by the buyer under their corporate entity.

---

## 21. Buyer Next Steps
1. **Review Executive Summary:** Inspect `01-EXECUTIVE-BRIEF.md` and the 1-page `Project-ORION-Executive-Brief.pdf`.
2. **Execute Mutual NDA:** Sign standard bilateral confidentiality agreement to unlock detailed diligence.
3. **Access Due Diligence Data Room:** Review Tiers 1 through 4 dossiers under `docs/acquisition/`.
4. **Conduct Technical Demo:** Schedule a live operator walkthrough following the Demo Operator Sheet.
5. **Submit Indication of Interest (IOI):** Present proposed transaction terms for bilateral legal review.
