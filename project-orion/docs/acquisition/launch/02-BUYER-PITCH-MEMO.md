# Project ORION — Prospective Acquirer Executive Pitch Memorandum

**Document Reference:** `docs/acquisition/launch/02-BUYER-PITCH-MEMO.md`  
**Classification:** Confidential / For Executive Due Diligence Evaluators  
**Asset Baseline Commit:** `d5908d0a0cc2feff99fa02573adb12b8eea33782`  
**Execution Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Live Financial Capital at Risk)  

---

## 1. Executive Context
This pitch memorandum provides executive, technical, and corporate development leadership with an objective architectural overview of **Project ORION**. 

Project ORION is presented as a pure software and intellectual property asset acquisition. It provides an established, engineered technical foundation that a buyer can evaluate, adapt, and extend. The system addresses a critical challenge in quantitative algorithmic trading: ensuring mathematical hygiene, preventing indicator look-ahead bias, and enforcing realistic execution modeling before algorithms are deployed to paper incubation.

---

## 2. Product Summary
Project ORION is a multi-tenant quantitative foreign exchange research, Walk-Forward Analysis (WFA), and simulated paper-trading platform. 

The software includes:
* **Quantitative Strategy Lab:** Modular strategy design framework supporting 4 built-in strategy classes and 9 parameter profiles in an API catalogue.
* **Deterministic Backtesting Engine:** Sequential chronological bar traversal with trade-by-trade accounting and Decimal arithmetic.
* **Temporal Leakage Protection (`LeakageGuard`):** Strict point-in-time timestamp monotonicity validation.
* **Combinatorial Optimization & WFA:** Hyperparameter grid search and rolling In-Sample (IS) / Out-of-Sample (OOS) validation slices computing Walk-Forward Efficiency (WFE) ratios.
* **Adverse Slippage Paper Execution:** In-memory order matching simulating market spreads and volume slippage ($0.00 live financial risk).
* **Multi-Tenant SaaS Foundation:** 7 organizational RBAC roles, 41 permissions, row-level tenant partitioning, and Stripe Test Mode billing.

---

## 3. Technology Asset Overview
The codebase is implemented natively in Python 3.11+ and TypeScript / React 18 using Domain-Driven Design (DDD) and Hexagonal Architecture (Ports and Adapters):

```
┌────────────────────────────────────────────────────────────────────────┐
│                              CLIENT TIER                                │
│       React 18 / TypeScript 5 / Vite SPA (Multi-Stage Nginx Container) │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS / RESTful JSON
┌───────────────────────────────────▼────────────────────────────────────┐
│                        API & ORCHESTRATION TIER                         │
│       FastAPI ASGI Application Factory (Python 3.11+, 24 Routers)      │
└──────────────────┬────────────────────────────────┬────────────────────┘
                   │                                │
┌──────────────────▼──────────────┐   ┌─────────────▼────────────────────┐
                   │                                │
┌──────────────────▼──────────────┐   ┌─────────────▼────────────────────┐
│         DOMAIN LAYER            │   │      INFRASTRUCTURE ADAPTERS     │
│   21 Pure Python Domain Packages│   │  SQLAlchemy 2.0 Async / asyncpg  │
│   (Zero Framework Dependencies) │   │  Redis 7 Rate-Limiting & Cache   │
└─────────────────────────────────┘   │  SMTPEmailService (RFC 5321)     │
                                      │  Stripe Test Billing Adapter     │
                                      │  PaperExecutionAdapter           │
                                      │  MockMarketDataProvider          │
                                      └──────────────────────────────────┘
```

* **Core Modularity:** 21 internal domain packages under `libraries/domain/` remain decoupled from web frameworks and databases.
* **Database Layer:** PostgreSQL 16 with 15 linear forward Alembic migrations managing 29 tables.
* **PaaS Blueprint:** Declarative `render.yaml` infrastructure-as-code specification.

---

## 4. Quantitative Research Capability
ORION provides a structured environment for algorithmic strategy modeling:
* **Built-in Strategy Classes (4):** `EMACrossoverStrategy`, `RSIReversalStrategy`, `MACDTrendStrategy`, and `MultiTimeframeConfluenceStrategy` in `StrategyRegistry`.
* **API Catalogue Archetypes (9):** Pre-configured parameter schemas covering trend, momentum, mean-reversion, and breakout configurations.
* **Arbitrary Precision Arithmetic:** All balances, pip calculations, and P&L accounting strictly utilize Python `Decimal` to avoid floating-point inaccuracies.
* **Indicator Pipeline:** Mathematical implementations of EMA, RSI, MACD, ATR, ADX, Bollinger Bands, and Stochastic Oscillators.

---

## 5. Backtesting, Optimization & Walk-Forward Analysis
To protect against the risk of curve-fitting, ORION integrates multi-layer validation tools:
* **Deterministic Backtester:** Bar-by-bar chronological execution simulating bid/ask spreads.
* **LeakageGuard Validation:** Monitors indicator calculations at each time slice to ensure no future bar data influences trading signals.
* **Parameter Space Grid Search:** Evaluates multi-dimensional parameter spaces with Sharpe and Sortino ratio ranking.
* **Rolling Walk-Forward Analysis:** Segments historical data into rolling IS training windows and OOS verification slices, generating objective Walk-Forward Efficiency (WFE) scores.
* **Programmatic Quality Gates:** Enforces hurdle thresholds (e.g. WFE $\ge$ 0.50, Maximum Drawdown $\le$ 15%) before a candidate strategy transitions to incubation.

---

## 6. Paper Execution & Pre-Trade Risk Controls
* **Virtual Execution Adapter:** `PaperExecutionAdapter` simulates realistic order fills, incorporating adverse execution slippage and spread widening based on order volume.
* **Pre-Trade Risk Engine:** Dynamic validation of account margin, leverage ceilings (1:100 default limit), daily loss limits, and maximum drawdown circuit breakers.
* **Capital Boundary:** Operates strictly with a default **$100,000 virtual balance** and **$0.00 live financial capital at risk**. Orders are permanently stamped `is_paper=True`.

---

## 7. Multi-Tenant SaaS Architecture
* **Tenant Isolation:** Tenant-owned application entities are organization-scoped through indexed `organization_id` foreign keys and authorization controls, automatically validated through dependency-injected `TenantContext` (migration metadata tables such as `alembic_version` and global catalog tables are not tenant-owned business entities).
* **Fine-Grained RBAC:** 7 organizational roles (`OWNER`, `ADMINISTRATOR`, `PORTFOLIO_MANAGER`, `RISK_OFFICER`, `TRADER`, `AUDITOR`, `VIEWER`) controlling 41 domain permissions across 14 functional areas.
* **Onboarding State Machine:** 5-step user onboarding flow persisted in the database.

---

## 8. Security, Auditability & Operations
* **Authentication:** Stateless HMAC-SHA256 JWT tokens with 30-minute validity.
* **Password Security:** Salted bcrypt hashing; password modifications update `password_changed_at`, invalidating all active sessions.
* **Anti-Enumeration Protections:** Public authentication routes return uniform response structures and timing regardless of account existence.
* **Immutable Audit Trail:** Sensitive administrative events and order placements generate append-only audit records containing user IDs and JSON context.
* **Container Security:** Non-root container execution (`orion`, `uid=999`).

---

## 9. Deployment & Disaster Recovery
* **Declarative PaaS:** Configured via `render.yaml` spanning FastAPI web service, React SPA, private PostgreSQL 16, and private Redis 7.
* **Hosting Cost:** Approximately $14/month baseline configuration hosting estimate based on the documented Render configuration ($7 DB + $7 API under published 2026 pricing); actual cloud pricing may vary and is buyer-provisioned.
* **Automated Pre-Deployment Migrations:** `preDeployCommand` executes Alembic migrations in an isolated container prior to traffic switching.
* **Disaster Recovery Benchmark:** Tested shell scripts benchmarked at ~7.2 seconds for complete database restoration across 29 tables in an isolated test container (Dossier 08).

---

## 10. Commercial Subscription Model
The platform includes an implemented 4-tier SaaS subscription model:
* **Free Sandbox:** $0 / month (1 account, 100 orders/day, 4 pairs, 30-day history)
* **Pro Trader:** $99 / month (3 accounts, 2,500 orders/day, 12 pairs, 365-day history, WFA)
* **Business Prop:** $299 / month (10 accounts, 50,000 orders/day, all pairs, 5-year history, RBAC)
* **Enterprise:** Custom Contract (unlimited capacity, dedicated worker pool allocation)

*Note: Built-in subscription pricing represents end-user software monetization capability and does not represent an acquisition transaction asking price.*

---

## 11. Current Commercial Status
* **Status:** Pre-revenue technology asset.
* **Repository Evidence:** Customers, subscribers, ARR, MRR, contracts, and historical commercial revenue are **`NOT ESTABLISHED IN REPOSITORY`** (pre-revenue technology asset).
* **Payment Processing:** Integrated with Stripe in **Stripe Test Mode / Developer Sandbox**. Live payment infrastructure is buyer-provisioned.

---

## 12. Proposed Transferable Software / IP Scope
Proposed Transferable Software / IP Scope, subject to executed transaction agreements:
1. Complete Git repository source tree with unbroken single-author commit provenance.
2. 21 internal domain logic packages (`libraries/domain/`).
3. 24 modular FastAPI backend routers.
4. React 18 Single-Page Application (20 routes).
5. 15 linear forward Alembic database migrations.
6. 103 automated test suites (historical development evidence records 4,260 automated tests and 99.4% documented historical test coverage).
7. Declarative Render PaaS blueprint (`render.yaml`) and Dockerfiles.
8. Complete 18-dossier due diligence data room (`docs/acquisition/`).
9. Presentation package (PPTX, publication PDFs, vector SVGs).

---

## 13. Buyer-Provisioned Obligations (BUYER-PROVISIONED)
To ensure clean corporate separation, all third-party services are non-transferable and designated as BUYER-PROVISIONED. The buyer independently provisions:
* Corporate Render PaaS account (`render.yaml` deployed under buyer billing).
* Corporate Stripe merchant account for live payment processing.
* TwelveData API key if live external market data is required.
* OANDA Practice account for external sandbox broker validation.
* RFC 5321 compliant SMTP relay account (SendGrid, Postmark, AWS SES).
* Proprietary web domain and DNS delegation.
* Production environment secrets and encryption keys.

---

## 14. Known Limitations
The following technical limitations are disclosed transparently (Dossier 13):
* **Paper-Only Invariant:** Software does not route live financial capital ($0.00 capital at risk).
* **Worker Execution:** Background strategy event loop is disabled by default in cloud runtime (`WORKER_ENABLED=false`).
* **Single-Process Worker:** Single-process event loop; scaling to high strategy volumes requires Celery/Redis queue adoption.
* **REST Polling:** Client UI updates via HTTP polling; continuous WebSocket push is not implemented.
* **No Third-Party Audits:** Software holds zero SOC 2, ISO 27001, or external penetration testing certifications.
* **Single-Region Deployment:** The Render deployment is configured for a single selected deployment region; the documented configuration can target a supported region such as Oregon or Frankfurt, subject to buyer provisioning.
* **Telegram Adapter:** Defined in domain models; infrastructure delivery adapter is not implemented.
* **Candlestick Patterns:** OHLCV data structures exist; automated pattern recognition algorithms are not implemented.

---

## 15. Due Diligence Path
Prospective acquirers progress through a structured 4-tier due diligence process:
1. **Tier 1 (Executive Overview):** Review Dossiers 01–03 and Executive Brief.
2. **Tier 2 (Technical Deep Dive):** Execute mutual NDA to inspect Dossiers 04–10 (Architecture, Code, DB, DR, Security).
3. **Tier 3 (Operational Diligence):** Inspect Dossiers 11–14 (Settings, SBOM, Limitations, PaaS Topology).
4. **Tier 4 (Transaction Diligence):** Inspect Dossiers 15–18 (IP Assignment, Account Provisioning, Domain Delegation, Master Index).
5. **Technical Demo:** Live operator walkthrough following the Demo Operator Sheet.

---

## 16. Why a Buyer Might Evaluate the Asset
Prospective acquirers typically evaluate Project ORION for the following technical and strategic characteristics:
* **Pre-Engineered Foundation:** Provides an existing, modular codebase featuring hexagonal separation that a buyer can inspect, run locally, adapt, and deploy.
* **Mathematical Hygiene:** Contains built-in implementations of `LeakageGuard`, Walk-Forward Analysis, and Decimal arithmetic, addressing common algorithmic backtesting pitfalls.
* **Multi-Tenant SaaS Infrastructure:** Delivers pre-built RBAC (7 roles, 41 permissions), 5-step onboarding, and Stripe Test Mode billing models.
* **Clean Monorepo Lineage:** Pre-revenue asset with no customer liabilities or real-money execution exposure; the documented dependency audit did not identify copyleft licenses in the reviewed dependency set (MIT/Apache/BSD SBOM; final legal review subject to buyer diligence).
* **Comprehensive Diligence Materials:** Backed by 18 technical dossiers and historical development evidence recording 4,260 automated tests and 99.4% documented test coverage.

---

## 17. Closing / Next Steps
Parties interested in evaluating Project ORION should take the following steps:
1. Review `docs/acquisition/01-EXECUTIVE-BRIEF.md` and `docs/acquisition/presentation/visual/pdf/Project-ORION-Executive-Brief.pdf`.
2. Request a standard bilateral non-disclosure agreement (NDA) to access detailed technical dossiers.
3. Schedule an engineering demonstration walkthrough.
4. Direct transaction inquiries to the authorized seller representative.
