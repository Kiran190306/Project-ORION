# Project ORION — Strategic Buyer Pitch Memorandum

**Asset Category:** Pre-Revenue Quantitative Software & Intellectual Property Acquisition
**Asking Price:** $24,900 USD
**Document Reference:** `docs/acquisition/sales/03-BUYER-PITCH.md`

---

## 1. The Strategic Problem in Quantitative Trading Software
Building algorithmic trading infrastructure from scratch is complex, time-consuming, and operationally hazardous. Engineering teams frequently encounter recurring structural challenges:
* **Fragmented Research Workflows:** Disconnected toolchains where strategy development in Python scripts fails to translate cleanly to backtesting, parameter optimization, and order execution.
* **Look-Ahead Leakage:** Insidious timestamp leakage in backtesting code where calculations inadvertently consume future data bars, producing artificial performance metrics that collapse out-of-sample.
* **Overfitting & Curve-Fitting:** Traditional optimization methods often over-tune hyperparameters to historical noise, failing to test parameter robustness across rolling market regimes.
* **Frictionless Simulation Assumptions:** Paper trading simulators that assume perfect mid-market fills, ignoring bid/ask spreads, adverse execution slippage, and resting order queues.
* **Lack of Promotion Governance:** Informal strategy management where unvalidated algorithms are deployed directly into simulation without passing objective quality gate hurdles.
* **SaaS Multi-Tenancy Complexity:** Building secure organization data partitioning, granular role-based access controls, and subscription billing funnels requires extensive non-trading infrastructure engineering.

---

## 2. The Current Software Foundation
**Project ORION** provides an implemented, tested software foundation designed to resolve these structural challenges within a unified, domain-driven architecture.

The buyer is acquiring an implemented software foundation rather than starting from a blank project. The platform implements an end-to-end quantitative research, walk-forward optimization, and adverse-slippage paper-trading pipeline wrapped in a multi-tenant SaaS framework.

---

## 3. The Technical Asset
Project ORION represents a complete, cohesive codebase built with modern, maintainable technologies:
* **Backend Tier:** Python 3.11 with FastAPI (ASGI), async SQLAlchemy 2.0 with asyncpg driver, and Pydantic v2 schemas.
* **Frontend Tier:** React 19 Single-Page Application built with TypeScript, Vite, Tailwind CSS, and Lucide icons.
* **Persistence Tier:** Managed PostgreSQL 16 relational store with 15 linear forward Alembic database schema migrations managing 29 tables.
* **Cache & Coordination:** Redis 7 in-memory cache supporting sliding-window API rate limiting, real-time market data caching, and distributed synchronization.
* **Cloud Infrastructure:** Declarative Render PaaS blueprint (`render.yaml`), multi-stage Docker container builds, and shell-based disaster recovery automation.
* **Documented Verification Metrics:** Historical development evidence records 4,260 automated tests across 103 test suites, 99.4% documented historical test coverage, and a documented ~7.2-second physical database restoration benchmark.

---

## 4. The Quantitative Research Workflow
The platform implements a structured, 5-stage research pipeline designed to enforce mathematical hygiene:
1. **Strategy Formulation:** Typed parameter schemas supporting 4 built-in strategy classes (`EMAStrategy`, `RSIStrategy`, `MACDStrategy`, `ATRStrategy`) and 9 parameter catalogue profiles.
2. **Deterministic Backtesting Engine:** Chronological bar traversal processing spreads, commissions, and execution slippage with reproducible trade journals.
3. **Temporal Leakage Controls (`LeakageGuard`):** Strict point-in-time timestamp monotonicity checks designed to mitigate temporal leakage and look-ahead bias through chronological data validation and LeakageGuard controls during feature generation and backtesting.
4. **Walk-Forward Analysis (WFA):** Rolling In-Sample (IS) optimization and Out-of-Sample (OOS) validation window slicing; computes Walk-Forward Efficiency (WFE) ratios to measure parameter stability across market regimes.
5. **Quality Gate Evaluation:** Programmatic hurdle validation (e.g., minimum WFE $\ge 0.50$, maximum drawdown $\le 15\%$) required before strategy incubation.

---

## 5. Execution & Safety Boundary
Project ORION is engineered with strict safeguards to isolate simulated trading operations:
* **Virtual Account Balance:** Default virtual paper balance of **$100,000.00 USD**. Real funds are never accepted.
* **Zero Financial Risk:** Enforces exactly **$0.00 live financial capital at risk** across all demonstrated execution pathways.
* **Order Tagging:** All simulated orders and fills permanently stamp `is_paper=True`.
* **Broker Connectivity:** Restricted exclusively to OANDA Practice sandbox endpoints (`api-fxpractice.oanda.com`). Production live endpoints fail closed and are blocked by `BrokerEndpointValidator`.
* **Autonomous Worker Invariant:** Background trading worker is disabled by default (`ORION_WORKER_ENABLED=false`).
* **Market Data Feeds:** `MockMarketDataProvider` operates internally with deterministic synthetic data; TwelveData external feeds require buyer-provisioned API credentials.

---

## 6. Pre-Trade Risk Governance & Order Controls
Before any simulated order enters the virtual order book, the risk engine evaluates:
* **Account Drawdown Limits:** Rejects orders if account equity falls past maximum drawdown thresholds.
* **Daily Loss Limits:** Halts order creation if realized and unrealized losses breach daily loss caps.
* **Leverage Ceilings:** Enforces a maximum leverage ceiling (1:100 default limit).
* **Margin Reservation:** Computes required margin and confirms sufficient free margin prior to submission.
* **Order Types & Sizing:** Supports Market, Limit, and Stop orders, Stop-Loss / Take-Profit enforcement, trailing stop adjustments, and portfolio exposure controls.

---

## 7. Platform Architecture & Multi-Tenancy
* **Multi-Tenant Isolation:** Tenant-owned entities enforce `organization_id` foreign key relationships and authorization controls validated against signed JWT `TenantContext` tokens.
* **Role-Based Access Control (RBAC):** 7 organization roles (`OWNER`, `ADMIN`, `PORTFOLIO_MANAGER`, `TRADER`, `ANALYST`, `AUDITOR`, `VIEWER`) governing 41 granular domain permissions.
* **Immutable Audit Logging:** Append-only operational logging capturing acting user IDs, timestamps, event actions, and structured JSON context.
* **Commercial Billing Integration:** Pre-wired Stripe billing infrastructure configured in Test Mode supporting subscription lifecycle webhooks across 4 distinct tier quotas.

---

## 8. Strategic Buyer Use Cases
* **Fintech & Trading Technology Firms:** Integrate an off-the-shelf quantitative research, backtesting, and paper-trading module into existing client portals or brokerage services.
* **Algorithmic Trading Desks & Prop Firms:** Deploy a structured research and incubation pipeline to evaluate candidate trading algorithms under rigorous risk limits and simulated slippage.
* **Trading Academies & Educational Portals:** Provide students with an interactive, safe trading simulator ($100k virtual balance, $0 live risk) backed by professional research tools.
* **Technical Founders & Software Operators:** Acquire a complete, tested Python/React codebase with modern architecture to launch and commercialize independently.

---

## 9. Proposed Acquisition Scope
Subject to executed transaction agreements, the proposed transferable scope includes:
* Project ORION software repository and documented acquisition assets where audited repository history shows a single-author commit history within the reviewed repository scope.
* All 21 internal pure Python domain logic packages (`libraries/domain/`).
* All 24 modular FastAPI backend API routers and service orchestrators.
* Complete React 19 / TypeScript / Vite Single-Page Application (`apps/dashboard/`).
* 15 linear forward Alembic database schema migrations managing 29 relational tables.
* Automated test harness with documented historical baseline of 4,260 tests across 103 test suites.
* Declarative Render PaaS blueprint (`render.yaml`), Dockerfiles, and disaster recovery scripts.
* Complete 18-dossier due diligence data room, 8 presentation source docs, and 24 visual presentation assets.

*Buyer-Provisioned External Services:* Cloud hosting (Render), payment gateway (Stripe), market data (TwelveData), broker sandbox (OANDA Practice), transactional SMTP, and custom domain and DNS management, if used, are independently provisioned by the acquiring entity.

---

## 10. Commercial Status
* **Commercial Model:** Pre-Revenue Technology / Software Asset.
* **Paying Customers:** NOT ESTABLISHED IN REPOSITORY.
* **Active Subscribers:** NOT ESTABLISHED IN REPOSITORY.
* **Annual Recurring Revenue (ARR):** NOT ESTABLISHED IN REPOSITORY.
* **Monthly Recurring Revenue (MRR):** NOT ESTABLISHED IN REPOSITORY.
* **Customer Contracts:** NOT ESTABLISHED IN REPOSITORY.
* **Historical Commercial Revenue:** NOT ESTABLISHED IN REPOSITORY.
* **Billing System Mode:** Stripe Test Mode configured with placeholder test keys.
* **Documented In-App SaaS Subscription Pricing:** Free Sandbox — $0/month, Pro Trader — $99/month, Business Prop Desk — $299/month, Enterprise — Custom. *(Note: These are documented in-app subscription entitlement tiers. They are separate from the $24,900 software asset asking price).*
* **Hosting Overhead:** ~$14/month documented baseline estimate for the referenced Render configuration; actual buyer operating cost depends on selected resources, region and usage.

---

## 11. Known Limitations & Disclaimers
In accordance with full disclosure standards, the following technical and commercial boundaries are registered:
* **Pre-Revenue Asset:** Commercial revenue, paying customers, and subscriber cohorts are not established in repository evidence.
* **Paper-Only Execution:** Platform routes virtual orders only; contains no real-money clearing rails ($0.00 capital at risk).
* **Broker Sandbox:** OANDA integration is restricted strictly to practice sandbox endpoints (`api-fxpractice.oanda.com`).
* **Autonomous Worker Gated:** Background trading worker loop is disabled by default (`WORKER_ENABLED=false`).
* **External Credentials Required:** TwelveData API and transactional SMTP require buyer-provisioned credentials.
* **Demo Verification:** Render demo currently requires external environment verification (`EXTERNAL VERIFICATION PENDING`).
* **Candlestick Patterns:** OHLCV candle structures exist; pattern recognition algorithms are NOT IMPLEMENTED.
* **Telegram Adapter:** Domain data structures exist; infrastructure delivery adapter is DOMAIN-ONLY / not an operational delivery channel.
* **No Formal Certifications:** Software has not undergone third-party penetration testing, SOC 2, ISO 27001, or PCI-DSS certifications.
* **Not Regulated:** Software holds zero FINRA, FCA, SEC, or ASIC licenses or financial registrations.
* **Single-Region Deployment:** Deployment configuration targets a single cloud region; multi-region geo-replication is not implemented.
* **No Financial Guarantees:** Backtests and Walk-Forward Analysis evaluate historical hypotheses only; past simulated performance provides no guarantee of future live market results.

---

## 12. Asking Price
**ASKING PRICE: $24,900 USD**

> **Price Disclosure Notice**: This is the seller's asking price for the proposed software/IP asset transaction. It is not a valuation, independent appraisal, revenue multiple, or SaaS subscription price. The asset is offered as an outright software and intellectual property acquisition subject to executed transaction agreements.

---

## 13. Due Diligence Data Room
Prospective buyers are granted access to a comprehensive 18-dossier technical due diligence data room organized under `docs/acquisition/` across 4 tiers:
* **Tier 1 (Executive):** Dossiers 01–03 (Executive Brief, Product Overview, Architecture Overview).
* **Tier 2 (Technical):** Dossiers 04–10 (Handover Guide, Deployment SOPs, Operations Runbook, Security, DR, API Catalog, Migrations).
* **Tier 3 (Operational):** Dossiers 11–14 (Environment Reference, SBOM, Known Limitations, PaaS Topology).
* **Tier 4 (Transaction):** Dossiers 15–18 (IP Checklist, Account Transfer, Domain Transfer, Master Index).

---

## 14. Next Steps
Request the buyer presentation, technical diligence package, or guided demonstration for further evaluation.
