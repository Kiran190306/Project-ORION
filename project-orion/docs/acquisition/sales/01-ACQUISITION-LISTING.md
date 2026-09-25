# Project ORION — Acquisition Marketplace Listing Specification

**Classification:** Buyer Acquisition Information Memorandum
**Asset Category:** Pre-Revenue Quantitative Software & Intellectual Property Asset
**Document Reference:** `docs/acquisition/sales/01-ACQUISITION-LISTING.md`

---

## 1. Title
**Project ORION — Quantitative FX Research & Paper-Trading SaaS**

---

## 2. One-Line Positioning
A software platform for quantitative FX research, historical backtesting, parameter optimization, walk-forward analysis, strategy deployment governance, simulated paper execution, risk controls, multi-tenant organization management, and role-based access control.

---

## 3. Asking Price
**ASKING PRICE: $24,900 USD**

> **Price Disclosure Notice**: This is the seller's asking price for the proposed software/IP asset transaction. It is not a valuation, independent appraisal, revenue multiple, or SaaS subscription price. The asset is offered as an outright software and intellectual property acquisition subject to executed transaction agreements.

---

## 4. Executive Summary
Project ORION is an existing implemented software platform engineered to take foreign exchange algorithmic strategies from mathematical formulation through historical backtesting and Walk-Forward Analysis (WFA) to simulated paper execution. Built upon Domain-Driven Design (DDD) and Hexagonal Architecture principles, the platform decouples pure algorithmic logic from external infrastructure.

The asset is offered as a pure software and intellectual property asset acquisition. The buyer is acquiring an implemented software foundation rather than starting from a blank project. The repository includes a complete FastAPI ASGI backend, a React 19 / TypeScript / Vite Single-Page Application (SPA), a PostgreSQL 16 schema with 15 linear forward migrations across 29 tables, a declarative PaaS deployment blueprint for Render, an automated test harness with historical development evidence of 4,260 automated tests and 99.4% documented historical test coverage, and a complete technical diligence data room.

---

## 5. What the Buyer Receives
Subject to definitive executed transaction agreements, the proposed transferable scope includes:
* **Project ORION Software Repository:** Project ORION source code, tests, migrations, deployment configuration, and documented acquisition assets where audited repository history shows a single-author commit history within the reviewed repository scope.
* **Backend API Engine:** 24 modular FastAPI ASGI routers and service orchestration layers (`apps/trading-engine/`).
* **Frontend Web Application:** React 19 Single-Page Application with 20 client routes (`apps/dashboard/`).
* **Domain Libraries:** 21 internal pure Python domain packages (`libraries/domain/`) with zero framework lock-in.
* **Database & Persistence:** 15 linear forward Alembic database schema migrations managing 29 relational tables (`database/`).
* **Automated Test Suite:** 103 test suites containing a documented historical baseline of 4,260 automated tests (`tests/`).
* **Infrastructure as Code:** Declarative Render PaaS blueprint (`render.yaml`), multi-stage production Dockerfiles, and disaster recovery shell scripts.
* **Complete Diligence Data Room:** 18 canonical acquisition dossiers, 8 presentation source documents, 24 visual presentation assets, and 7 operational launch runbooks.

---

## 6. Product Capabilities
* **Market Data Abstraction:** Pluggable provider architecture featuring deterministic internal synthetic data generation (`MockMarketDataProvider`) and external market feed connectivity (`TwelveDataProvider`).
* **Technical Indicators:** High-performance vectorized indicator implementations including Exponential Moving Average (EMA), Relative Strength Index (RSI), Moving Average Convergence Divergence (MACD), and Average True Range (ATR).
* **Quantitative Strategy Framework:** Extensible strategy registry supporting 4 concrete implementations (`EMAStrategy`, `RSIStrategy`, `MACDStrategy`, `ATRStrategy`) and 9 strategy catalogue profiles with typed Pydantic v2 schemas.
* **Historical Backtesting Engine:** Chronological bar-by-bar traversal with simulated execution modeling with documented slippage and commission configuration, generating double-entry trade journals and performance statistics.
* **Temporal Leakage Controls (`LeakageGuard`):** Strict point-in-time timestamp monotonicity checks designed to mitigate temporal leakage and look-ahead bias through chronological data validation and LeakageGuard controls during indicator calculation and backtesting.
* **Parameter Space Optimization:** Multi-parameter grid and random search engines traversing bounded parameter spaces with objective function ranking.
* **Walk-Forward Analysis (WFA):** Rolling In-Sample (IS) training and Out-of-Sample (OOS) validation window slicing; computes Walk-Forward Efficiency (WFE) ratios to measure parameter stability across market regimes.
* **Strategy Deployment Governance:** Programmatic 5-stage lifecycle state machine (`DRAFT` → `BACKTESTED` → `OPTIMIZED` → `INCUBATING` → `PROMOTED`) governing strategy readiness prior to simulation deployment.
* **Simulated Execution Engine:** `PaperExecutionAdapter` modeling resting order queues, spread variance, order volume decay, and adverse execution slippage ($0.00 live capital at risk).
* **Pre-Trade Risk Governance:** Dynamic pre-trade evaluation of margin consumption, leverage limits (1:100 default ceiling), drawdown limits, and daily loss caps.
* **Position & Order Controls:** Support for Market, Limit, and Stop orders, Stop-Loss / Take-Profit enforcement, trailing stop adjustments, and portfolio exposure controls.
* **Multi-Tenant SaaS Architecture:** Tenant-owned application entities are organization-scoped via `organization_id` foreign keys and authorization controls, validated against signed JWT `TenantContext` tokens.
* **Role-Based Access Control (RBAC):** 7 organization roles (`OWNER`, `ADMIN`, `PORTFOLIO_MANAGER`, `TRADER`, `ANALYST`, `AUDITOR`, `VIEWER`) governing 41 granular domain permissions.
* **Immutable Audit Logging:** Append-only operational logging capturing acting user IDs, timestamps, event actions, and structured JSON context.
* **Commercial Billing Integration:** Stripe billing infrastructure configured in Test Mode supporting subscription lifecycle webhooks across 4 distinct tier quotas.
* **User Onboarding Workflow:** Multi-step onboarding state machine guiding users through registration, organization provisioning, and default paper account allocation.
* **System Health & Observability:** Production health probes (`/health/live`, `/health/ready`), Prometheus metric scraping (`/metrics`), and request correlation tracing.

---

## 7. Technical Architecture
* **Architecture Pattern:** Hexagonal Architecture (Ports and Adapters) with Domain-Driven Design (DDD).
* **Backend Runtime:** Python 3.11 with FastAPI (ASGI, asynchronous event loop, Pydantic v2 schemas).
* **Frontend Runtime:** React 19, TypeScript, Vite, Tailwind CSS, Lucide icons.
* **Database & ORM:** PostgreSQL 16 managed via async SQLAlchemy 2.0 with asyncpg driver; 15 Alembic schema migrations across 29 relational tables.
* **Cache & Coordination:** Redis 7 supporting sliding-window API rate limiting, real-time market data caching, and distributed synchronization.
* **Containerization:** Multi-stage Docker container builds with non-root security execution.
* **Cloud Infrastructure:** Infrastructure-as-Code blueprint (`render.yaml`) targeting Render PaaS with automated pre-deploy migrations.
* **Deployment Model:** Single-region containerized PaaS deployment configuration.

---

## 8. Quantitative Research Workflow
ORION implements a disciplined, 5-stage research pipeline designed to enforce mathematical hygiene:
```text
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

## 9. Backtesting, Optimization & Walk-Forward Analysis
* **Deterministic Backtesting:** Eliminates random simulation artifacts by processing historical bar series with fixed decimal mathematical precision.
* **Slippage & Commission Modeling:** Simulated execution modeling with documented slippage and commission configuration rather than assuming frictionless mid-point fills.
* **Parameter Space Engine:** Validates parameter bounds and step sizes, preventing invalid combinatorial explosions during optimization.
* **Overfitting Evaluation:** Walk-Forward Analysis tests whether optimized parameters hold predictive power out-of-sample; WFE ratios below threshold identify parameter decay.

---

## 10. Strategy Deployment Governance
Strategies cannot transition directly from optimization into active simulation. The platform enforces a formal 5-stage lifecycle state machine:
1. `DRAFT`: Strategy formulated and parameters defined.
2. `BACKTESTED`: Initial chronological backtest completed.
3. `OPTIMIZED`: Parameter optimization and WFA completed with quality hurdles met.
4. `INCUBATING`: Strategy deployed to internal paper incubator under live synthetic market data.
5. `PROMOTED`: Final promotion milestone indicating validated paper incubation.

---

## 11. Paper Execution & Safety Boundary
* **Default Paper Balance:** Each newly provisioned account receives an initial virtual balance of **$100,000.00 USD**. Real funds are never accepted.
* **Financial Risk:** Strictly **$0.00 live financial capital at risk** across all demonstrated execution pathways.
* **Order Tagging:** All simulated orders and fills permanently stamp `is_paper=True`.
* **Broker Practice Integration:** Broker connectivity is constrained to OANDA Practice (`https://api-fxpractice.oanda.com`). Production broker clearing endpoints (`api-fxtrade.oanda.com`) fail closed and are blocked by `BrokerEndpointValidator`.
* **Autonomous Worker Invariant:** The background trading worker is disabled by default (`ORION_WORKER_ENABLED=false`).
* **Market Data Safety:** `MockMarketDataProvider` operates internally with deterministic synthetic data; TwelveData external feeds require buyer-provisioned API credentials.

---

## 12. Pre-Trade Risk Controls
Before any simulated order enters the virtual order book, the risk engine evaluates:
* **Account Drawdown Limit:** Rejects orders if account equity has fallen past maximum drawdown thresholds.
* **Daily Loss Limit:** Halts order creation if realized and unrealized losses breach daily loss caps.
* **Leverage Ceiling:** Enforces a maximum leverage ceiling (1:100 default limit).
* **Margin Reservation:** Computes required margin and confirms sufficient free margin prior to submission.
* **Order Sizing Guardrails:** Restricts order lot sizes based on volatility and account balance rules.

---

## 13. Multi-Tenancy & RBAC
* **Tenant Isolation:** Tenant-owned entities enforce `organization_id` foreign key relationships and authorization controls validated against signed JWT `TenantContext` tokens.
* **Organizational Roles:** 7 pre-configured roles (`OWNER`, `ADMIN`, `PORTFOLIO_MANAGER`, `TRADER`, `ANALYST`, `AUDITOR`, `VIEWER`).
* **Granular Permissions:** 41 distinct domain permissions governing administrative, research, and paper-trading functional domains.

---

## 14. Infrastructure & Disaster Recovery
* **PaaS Deployment:** Declarative `render.yaml` orchestrating the FastAPI web service, managed PostgreSQL 16 database, and Redis cache.
* **Disaster Recovery Automation:** Shell backup tooling (`backup/database-backup.sh`, `backup/restore-database.sh`) with documented historical test benchmark of ~7.2 seconds for full database restoration across 29 tables in an isolated container.

---

## 15. Security Controls
* **Authentication:** HS256 JWT tokens with salted bcrypt password hashing and anti-enumeration protections.
* **Credential Protection:** Application encryption utilities using AES-256-GCM for sensitive configuration values.
* **Ingress Controls:** Strict CORS origin whitelisting, HTTP security headers (nosniff, DENY frame options, XSS protection), and sliding-window rate limiting.

---

## 16. Technical Evidence (Historical Development Metrics)
* **Automated Test Suite:** Documented historical baseline of 4,260 automated tests across 103 test suites.
* **Code Coverage:** 99.4% documented historical test coverage across core packages.
* **Database Schema:** 15 forward Alembic migrations managing 29 relational tables.
* **API Surface:** 24 modular FastAPI routers exposing 122 REST endpoints.
* **Code Provenance:** The audited repository history shows a single-author commit history within the reviewed repository scope.

---

## 17. Commercial Status
* **Commercial Model:** Pre-Revenue Technology / Software Asset.
* **Paying Customers:** NOT ESTABLISHED IN REPOSITORY.
* **Active Subscribers:** NOT ESTABLISHED IN REPOSITORY.
* **Annual Recurring Revenue (ARR):** NOT ESTABLISHED IN REPOSITORY.
* **Monthly Recurring Revenue (MRR):** NOT ESTABLISHED IN REPOSITORY.
* **Customer Contracts:** NOT ESTABLISHED IN REPOSITORY.
* **Historical Commercial Revenue:** NOT ESTABLISHED IN REPOSITORY.
* **Billing System Mode:** Stripe Test Mode configured with placeholder test keys.

---

## 18. SaaS Subscription Pricing
The platform enforces a 4-tier commercial subscription quota model in source code (`subscription_service.py`, `pricing.ts`):

| Subscription Tier | Monthly SaaS Fee | Virtual Paper Accounts | Daily Order Cap | Autonomous Workers | FX Pairs & Retention |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Free Sandbox** | **$0 / month** | 1 Account ($100k balance) | 100 orders / day | 0 Workers | 4 Major Pairs │ 30-Day History |
| **Pro Trader** | **$99 / month** | 3 Accounts | 2,500 orders / day | 1 Worker | 12 Liquid Pairs │ 365-Day History |
| **Business Prop Desk** | **$299 / month** | 10 Accounts | 50,000 orders / day | 5 Workers | All Pairs │ 5-Year History |
| **Enterprise** | **Custom Contract** | Unlimited | Unlimited Capacity | Custom Pool | Full Cross-Asset │ 7-Year History |

> **Important Commercial Distinction**: These are documented in-app subscription entitlement tiers. They are separate from the $24,900 software asset asking price.

---

## 19. Acquisition Scope
* **Transaction Structure:** Outright software and intellectual property asset acquisition.
* **Proposed Transferable Scope:** Project ORION software repository and documented acquisition assets, including 21 domain packages, 24 API routers, React SPA, 15 migrations, 103 test suites, Dockerfiles, IaC blueprint, disaster recovery scripts, 18 diligence dossiers, presentation assets, launch runbooks, and sales package.
* **Legal Qualification:** Proposed transferable software / IP scope, subject to executed transaction agreements. Legal title and intellectual property rights do not transfer prior to transaction closing.

---

## 20. Buyer-Provisioned Dependencies
To ensure clean corporate separation and eliminate vendor lock-in, the acquiring entity independently provisions all external services (`BUYER-PROVISIONED`):
* **Cloud Hosting:** Buyer establishes an independent Render PaaS organization (~$14/month documented baseline estimate for the referenced Render configuration; actual buyer operating cost depends on selected resources, region and usage).
* **Payment Gateway:** Buyer establishes an independent Stripe corporate merchant account.
* **Market Data:** Buyer secures a TwelveData API key if live external market data is desired.
* **Broker Practice:** Buyer registers an OANDA Practice account for external sandbox testing.
* **Transactional Email:** Buyer provisions an external SMTP service (SendGrid, Postmark, AWS SES).
* **Custom Domain:** Custom domain and DNS management, if used (buyer provisions independent domain and DNS routing).
* **Production Secrets:** Buyer generates and manages production JWT signing secrets and database passwords.

---

## 21. Known Limitations & Disclaimers
In accordance with full disclosure standards, the following technical and commercial boundaries are registered:
1. **Pre-Revenue Asset:** Commercial revenue, paying customers, and subscriber cohorts are not established in repository evidence.
2. **Paper-Only Execution:** Platform routes virtual orders only; contains no real-money clearing rails ($0.00 capital at risk).
3. **Broker Sandbox:** OANDA integration is restricted strictly to practice sandbox endpoints (`api-fxpractice.oanda.com`).
4. **Autonomous Worker Gated:** Background trading worker loop is disabled by default (`WORKER_ENABLED=false`).
5. **External Credentials Required:** TwelveData API and transactional SMTP require buyer-provisioned credentials.
6. **Demo Verification:** Render demo currently requires external environment verification (`EXTERNAL VERIFICATION PENDING`).
7. **Candlestick Patterns:** OHLCV candle structures exist; pattern recognition algorithms are NOT IMPLEMENTED.
8. **Telegram Adapter:** Domain data structures exist; infrastructure delivery adapter is DOMAIN-ONLY / not an operational delivery channel.
9. **No Formal Certifications:** Software has not undergone third-party penetration testing, SOC 2, ISO 27001, or PCI-DSS certifications.
10. **Not Regulated:** Software holds zero FINRA, FCA, SEC, or ASIC licenses or financial registrations.
11. **Single-Region Deployment:** Deployment configuration targets a single cloud region; multi-region geo-replication is not implemented.
12. **No Financial Guarantees:** Backtests and Walk-Forward Analysis evaluate historical hypotheses only; past simulated performance provides no guarantee of future live market results.

---

## 22. Demo Availability
* **Local Container Demo:** 100% operational offline using `MockMarketDataProvider` for deterministic synthetic data and `PaperExecutionAdapter` for virtual matching.
* **Render Cloud Demo:** External verification pending; cloud deployment blueprint is established in `render.yaml` for immediate deployment into the buyer's Render account.

---

## 23. Due Diligence Package
Prospective buyers are granted access to a comprehensive 18-dossier due diligence data room organized under `docs/acquisition/`:
* **Tier 1 (Executive):** Executive Brief, Product Overview, Architecture Overview.
* **Tier 2 (Technical):** Technical Handover, Deployment SOPs, Operations Runbook, Security Architecture, DR Runbook, API Catalog, Database Migration Guide.
* **Tier 3 (Operational):** Environment Reference, Dependency SBOM, Known Limitations, PaaS Topology Map.
* **Tier 4 (Transaction):** IP Assignment Checklist, Account Ownership Transfer, Domain Transfer, Master Due Diligence Index.

---

## 24. Buyer Profile & Strategic Fit
Project ORION represents a strategic fit for:
* **Fintech & Trading Technology Companies:** Seeking an off-the-shelf quantitative research and backtesting foundation to integrate into existing platforms.
* **Algorithmic Trading Desks & Prop Incubators:** Requiring a paper-trading simulation sandbox and risk-governed deployment pipeline for trader evaluation.
* **Trading Education & Academy Platforms:** Seeking an interactive, safe trading simulator with $100k virtual paper balance and tiered SaaS plans.
* **Technical Founders & Entrepreneurs:** Seeking a clean, tested Python/React codebase with modern architecture to commercialize independently.

---

## 25. Transaction Process
1. **Initial Review:** Review this listing specification, executive summary, and public repository README.
2. **Confidentiality:** Execute standard mutual Non-Disclosure Agreement (NDA).
3. **Data Room Access:** Review 18 canonical due diligence dossiers under `docs/acquisition/`.
4. **Technical Walkthrough:** Conduct a guided technical demonstration following the Demo Operator Sheet.
5. **Indication of Interest (IOI):** Submit proposed transaction terms and consideration structure.
6. **Closing & Handover:** Execute Software Asset Purchase Agreement and IP Assignment Agreement; execute Day-1 handover checklist.

---

## 26. Contact & Next Steps
Request the buyer presentation, technical diligence package, or guided demonstration for further evaluation.
