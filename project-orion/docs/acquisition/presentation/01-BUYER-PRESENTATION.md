# Project ORION — Buyer Acquisition Presentation

**Document Reference:** `docs/acquisition/presentation/01-BUYER-PRESENTATION.md`  
**Classification:** Confidential — Acquisition Technical Due Diligence  
**Repository Working Copy:** `project-orion/`  
**Git Baseline Commit:** `d5908d0a0cc2feff99fa02573adb12b8eea33782`  
**Software Positioning:** Quantitative FX Research & Paper-Trading SaaS  
**Operational Mandate:** STRICT PAPER TRADING ONLY — $0.00 Live Financial Capital at Risk

---

## Executive Presentation Structure (15 Slides)

```
SLIDE 1  │ Project ORION — Quantitative FX Research & Paper-Trading SaaS
SLIDE 2  │ What the Software Is
SLIDE 3  │ Product Workflow
SLIDE 4  │ Architecture Overview
SLIDE 5  │ Quantitative Research Engine
SLIDE 6  │ Backtesting & Temporal Leakage Controls
SLIDE 7  │ Optimization & Walk-Forward Analysis
SLIDE 8  │ Strategy Deployment Lifecycle
SLIDE 9  │ Paper Trading & Risk Management
SLIDE 10 │ Market Data & Broker Adapter Architecture
SLIDE 11 │ Multi-Tenancy & Organization-Level RBAC
SLIDE 12 │ Security, Auditability & Operations
SLIDE 13 │ Deployment, Backup & Recovery
SLIDE 14 │ Technical Asset / IP Inventory
SLIDE 15 │ Acquisition Scope, Handover & Known Limitations
```

---

### SLIDE 1: Project ORION — Quantitative FX Research & Paper-Trading SaaS

* **Objective:** Establish the platform's core identity, proprietary software asset scope, and foundational paper-trading safety invariants.
* **Buyer-Facing Content:**
  * **Platform Definition:** Institutional-style multi-tenant quantitative research, deterministic backtesting, and simulated paper execution software.
  * **Asset Category:** Pure software and intellectual property technology asset developed in Python 3.11+ (FastAPI) and React 18 (TypeScript).
  * **Capital Safety Invariant:** Strict paper-trading execution model with exactly $0.00 live financial capital at risk.
  * **Delivery Scope:** Complete source repository, full Git commit provenance, automated test harness, and 18 closing due diligence dossiers.
* **Recommended Visual:** Clean dark-mode title slide displaying the Project ORION celestial reticle brand icon, software category badge, and repository commit stamp (`d5908d0a`).
* **Repository Evidence:**
  * Application Branding: [`apps/dashboard/src/pages/MarketingHomePage.tsx`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/dashboard/src/pages/MarketingHomePage.tsx)
  * Executive Overview: [`docs/acquisition/01-EXECUTIVE-BRIEF.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/01-EXECUTIVE-BRIEF.md)
  * Terms & Disclaimers: [`apps/dashboard/src/pages/TermsPage.tsx`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/dashboard/src/pages/TermsPage.tsx)
* **Numeric Claims Used:** $0.00 live financial capital at risk (Current verified invariant).
* **External Dependencies:** None.
* **Speaker Notes:**  
  *"Project ORION is an institutional-style quantitative foreign exchange research and paper-trading platform. Today's walkthrough covers the platform's architectural, mathematical, and operational capabilities. We emphasize that this platform operates strictly in paper-trading simulation mode with deterministic market data and zero live financial capital at risk."*
* **Prohibited Claims:** Do NOT claim Project ORION is a registered broker-dealer, investment fund, licensed RIA, live trading engine, or custodial financial platform.

---

### SLIDE 2: What the Software Is

* **Objective:** Present the concrete capabilities of the software platform and its implemented multi-tier SaaS model.
* **Buyer-Facing Content:**
  * **Algorithmic Engine:** End-to-end quantitative pipeline taking strategies from mathematical formulation through backtesting and walk-forward analysis to paper deployment.
  * **Simulation Matching Engine:** Internal simulated broker adapter (`PaperExecutionAdapter`) calculating realistic spread, adverse slippage, and position netting.
  * **Multi-Tenant SaaS Foundation:** Self-service registration dynamically provisioning isolated tenant organizations, default paper accounts, and role hierarchies.
  * **Authoritative Implemented Subscription Tiers:**
    * **Free Sandbox ($0/mo):** 1 paper account, 100 daily orders, 0 workers, 4 major FX pairs, 30-day retention.
    * **Pro Trader ($99/mo):** 3 paper accounts, 2,500 daily orders, 1 worker, 12 liquid FX pairs, 365-day retention.
    * **Business Prop Desk ($299/mo):** 10 paper accounts, 50,000 daily orders, 5 workers, all FX pairs, 5-year retention.
    * **Enterprise Institutional (Custom):** Unlimited accounts, orders, and workers; 7-year retention.
* **Recommended Visual:** 4-tier SaaS pricing and quota matrix card matching the implemented frontend configuration in `config/pricing.ts`.
* **Repository Evidence:**
  * Pricing Configuration: [`apps/dashboard/src/config/pricing.ts`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/dashboard/src/config/pricing.ts) (Lines 36–134)
  * Subscription Service: [`apps/trading-engine/src/services/subscription_service.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/trading-engine/src/services/subscription_service.py) (Lines 29–99)
* **Numeric Claims Used:** $0, $99, $299, Custom pricing tiers (Current verified invariants).
* **External Dependencies:** Stripe Test Mode for payment checkout simulation (live billing requires buyer-provisioned merchant account).
* **Speaker Notes:**  
  *"ORION delivers a complete SaaS architecture. Subscription plans, quotas, and paper-account entitlements are enforced in code through our EntitlementService across four distinct tiers. Commercial subscriptions operate in Stripe Test Mode with zero customer capital exposed."*
* **Prohibited Claims:** Do NOT use legacy preliminary $49/$149/$399 figures. Do NOT claim active commercial subscribers or recurring revenue exist (NOT ESTABLISHED IN REPOSITORY).

---

### SLIDE 3: Product Workflow

* **Objective:** Map the 5-stage lifecycle from mathematical strategy formulation to paper incubation.
* **Buyer-Facing Content:**
  * **Stage 1 — Specification:** Strategy parameterization across indicators, moving averages, and oscillators via typed schemas.
  * **Stage 2 — Deterministic Backtesting:** Sequential historical bar traversal with temporal leakage protection.
  * **Stage 3 — Optimization & Walk-Forward:** Multi-parameter grid exploration and rolling In-Sample / Out-Of-Sample validation.
  * **Stage 4 — Quality Gate Governance:** Automated validation against Walk-Forward Efficiency ($WFE$), drawdown ceilings, and parameter stability.
  * **Stage 5 — Paper Incubation:** Simulated execution with realistic transaction costs, strictly terminating at Paper Validated or Promotion Candidate status.
* **Recommended Visual:** Horizontal 5-stage workflow chevron diagram showing the progression of strategy candidates through automated validation hurdles.
* **Repository Evidence:**
  * Workflow Architecture: [`docs/acquisition/02-PRODUCT-OVERVIEW.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/02-PRODUCT-OVERVIEW.md) (Section 3)
  * Deployment State Machine: [`libraries/domain/deployment/lifecycle.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/domain/deployment/lifecycle.py)
* **Numeric Claims Used:** 5-stage quantitative workflow.
* **External Dependencies:** None.
* **Speaker Notes:**  
  *"The ORION workflow enforces strict mathematical hygiene. Strategies cannot enter paper trading without passing quantitative quality gates, filtering out overfitted algorithms before they ever touch simulated execution."*
* **Prohibited Claims:** Do NOT claim the pipeline automatically deploys algorithms to live real-money brokerage accounts.

---

### SLIDE 4: Architecture Overview

* **Objective:** Present the clean hexagonal modular architecture and layer decoupling.
* **Buyer-Facing Content:**
  * **Frontend SPA:** Single-Page Application built with React 18, Vite, TypeScript, Tailwind CSS, and TanStack Query across 20 distinct routes.
  * **API Layer:** FastAPI ASGI web service assembling 24 modular routers, Pydantic v2 validation models, and request correlation tracing.
  * **Domain Layer:** 21 pure internal packages under `libraries/domain/` with zero database or framework dependencies.
  * **Infrastructure Adapters:** Decoupled persistence (SQLAlchemy 2.0 Async, PostgreSQL 16), caching (Redis 7 with in-memory degraded fallback), and simulated execution.
* **Recommended Visual:** Hexagonal component architecture diagram from [`docs/acquisition/03-ARCHITECTURE-OVERVIEW.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/03-ARCHITECTURE-OVERVIEW.md) illustrating clean layer separation.
* **Repository Evidence:**
  * FastAPI Entrypoint: [`apps/trading-engine/src/main.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/trading-engine/src/main.py)
  * Router Aggregation: [`apps/trading-engine/src/main.py:163-187`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/trading-engine/src/main.py#L163-L187)
  * Domain Module Tree: [`libraries/domain/`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/domain/) directory listing
* **Numeric Claims Used:** 24 FastAPI routers, 21 internal domain packages (Current verified invariants).
* **External Dependencies:** None.
* **Speaker Notes:**  
  *"Under the hood, Project ORION follows hexagonal architecture principles. The twenty-one domain packages are entirely decoupled from web frameworks and databases, ensuring quantitative algorithms remain mathematically isolated and portable."*
* **Prohibited Claims:** Do NOT claim WebSocket push streaming is active. Do NOT claim the 21 packages are published standalone PyPI libraries.

---

### SLIDE 5: Quantitative Research Engine

* **Objective:** Present the strategy registry pattern, implemented concrete classes, and arbitrary-precision financial math.
* **Buyer-Facing Content:**
  * **Concrete Backtesting Classes:** 4 algorithmic strategy classes registered in `StrategyRegistry`:
    1. `TrendFollowingStrategy`: Dual EMA crossover with ATR dynamic trailing stop.
    2. `MeanReversionStrategy`: Bollinger Bands with RSI oscillator reversion envelopes.
    3. `BreakoutStrategy`: Donchian channel breakout with volume-spread filtering.
    4. `MomentumStrategy`: Multi-period MACD with stochastic momentum confirmation.
  * **API Catalogue Specification:** 9 strategy archetype parameter schemas defined in `_STRATEGY_CATALOGUE` for API configuration and UI generation.
  * **Arbitrary-Precision Arithmetic:** All balances, pip calculations, position lots, and P&L measurements use Python `Decimal` to avoid binary floating-point rounding inaccuracy.
* **Recommended Visual:** Two-column matrix comparing the 4 concrete backtesting classes against the 9 API catalogue schemas.
* **Repository Evidence:**
  * Strategy Registry: [`libraries/domain/strategy/registry.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/domain/strategy/registry.py)
  * Strategy Catalogue: [`apps/trading-engine/src/routes/strategies.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/trading-engine/src/routes/strategies.py)
  * Decimal Arithmetic Invariant: [`docs/acquisition/01-EXECUTIVE-BRIEF.md:90`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/01-EXECUTIVE-BRIEF.md#L90)
* **Numeric Claims Used:** 4 concrete classes, 9 catalogue profiles (Current verified invariants).
* **External Dependencies:** None.
* **Speaker Notes:**  
  *"The research engine implements four concrete algorithmic strategy classes in its core registry, supported by a nine-archetype parameter catalogue in the API. All financial arithmetic uses arbitrary-precision Decimal types, avoiding binary floating-point rounding errors."*
* **Prohibited Claims:** Do NOT claim all 9 catalogue strategies have independent backtest execution classes implemented.

---

### SLIDE 6: Backtesting & Temporal Leakage Controls

* **Objective:** Detail deterministic execution reproducibility and chronological look-ahead bias defenses.
* **Buyer-Facing Content:**
  * **Sequential Processing:** `DeterministicBacktestEngine` traverses historical candle bars in strict chronological order.
  * **Temporal Leakage Guard:** `LeakageGuard.validate_slice()` verifies timestamp monotonicity, architecturally preventing indicators from accessing future bar timestamps.
  * **Deterministic Reproducibility:** Re-running a backtest with identical parameters across identical historical bars produces mathematically identical equity curves and statistics to the exact cent.
  * **Performance Metrics:** Generates Sharpe Ratio, Sortino Ratio, Maximum Drawdown, Profit Factor, Win Rate, and trade-by-trade journals.
* **Recommended Visual:** Chronological timeline diagram illustrating bar-by-bar feeding and the `LeakageGuard` look-ahead barrier.
* **Repository Evidence:**
  * Backtest Engine: [`libraries/domain/research/deterministic_backtest_engine.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/domain/research/deterministic_backtest_engine.py)
  * Leakage Guard: [`libraries/domain/research/leakage_guard.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/domain/research/leakage_guard.py)
  * Backtest Route: [`apps/trading-engine/src/routes/research.py:88`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/trading-engine/src/routes/research.py#L88) (`POST /api/v1/research/experiments`)
* **Numeric Claims Used:** None.
* **External Dependencies:** None.
* **Speaker Notes:**  
  *"Backtesting integrity relies on LeakageGuard, which enforces temporal monotonicity at each step, preventing look-ahead contamination during sequential bar evaluation."*
* **Prohibited Claims:** Do NOT claim the platform 'guarantees zero look-ahead bias across all user-written custom external scripts'.

---

### SLIDE 7: Optimization & Walk-Forward Analysis

* **Objective:** Detail parameter space exploration and out-of-sample robustness validation.
* **Buyer-Facing Content:**
  * **Parameter Optimization:** Multi-parameter grid exploration evaluating candidate robustness across defined parameter bounds (`POST /api/v1/optimization/run`).
  * **Walk-Forward Analysis (WFA):** Slices historical datasets into rolling In-Sample (IS) optimization slices and Out-Of-Sample (OOS) validation slices (`POST /api/v1/optimization/walk-forward`).
  * **Walk-Forward Efficiency ($WFE$):** Calculates the ratio of annualized OOS return to annualized IS return to quantify performance degradation on unseen data.
  * **Robustness Classification:** Classifies parameter surfaces into `ROBUST`, `MODERATE`, or `OVERFITTED` verdicts.
* **Recommended Visual:** Multi-window rolling timeline graphic showing overlapping IS and OOS windows with calculated Walk-Forward Efficiency metrics.
* **Repository Evidence:**
  * Optimization Engine: [`libraries/domain/research/optimization_engine.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/domain/research/optimization_engine.py)
  * Walk-Forward Engine: [`libraries/domain/research/walk_forward_engine.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/domain/research/walk_forward_engine.py)
  * WFA Endpoints: [`apps/trading-engine/src/routes/optimization.py:62,84`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/trading-engine/src/routes/optimization.py#L62)
* **Numeric Claims Used:** None.
* **External Dependencies:** None.
* **Speaker Notes:**  
  *"To combat curve-fitting, ORION provides rolling Walk-Forward Analysis. By comparing optimized parameter performance against out-of-sample data across multiple windows, the system calculates Walk-Forward Efficiency."*
* **Prohibited Claims:** Do NOT claim WFA guarantees live market profitability or eliminates future regime shift risk.

---

### SLIDE 8: Strategy Deployment Lifecycle

* **Objective:** Present the governance state machine and automated quality gate hurdles.
* **Buyer-Facing Content:**
  * **Fail-Closed State Machine:** Managed by `DeploymentLifecycle` enforcing valid transitions:  
    `PENDING_GATES` → `GATES_PASSED` → `INCUBATING` → `PAPER_VALIDATED` → `PROMOTION_CANDIDATE`.
  * **Terminal States:** `GATES_FAILED`, `INCUBATION_FAILED`, `CANCELLED`, `SUSPENDED`, `PROMOTION_CANDIDATE`.
  * **Automated Quality Gates:** Three strict programmatic evaluation checks:
    1. Walk-Forward Efficiency Threshold ($WFE \ge 0.50$).
    2. Maximum Permissible Drawdown Ceiling ($\le 15\%$).
    3. Parameter Stability Surface Variance.
  * **Separation of Duties:** Enforces distinct roles for candidate submission and promotion review.
  * **Paper Termination Invariant:** The deployment pipeline strictly terminates at paper validation; no live brokerage execution transitions exist.
* **Recommended Visual:** State machine transition diagram highlighting quality gate evaluation points.
* **Repository Evidence:**
  * Deployment State Machine: [`libraries/domain/deployment/lifecycle.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/domain/deployment/lifecycle.py)
  * Quality Gates Engine: [`libraries/domain/deployment/quality_gates.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/domain/deployment/quality_gates.py)
  * Promotion Endpoints: [`apps/trading-engine/src/routes/deployments.py:114,137`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/trading-engine/src/routes/deployments.py#L114)
* **Numeric Claims Used:** None.
* **External Dependencies:** None.
* **Speaker Notes:**  
  *"The deployment pipeline enforces institutional governance. Strategies must pass programmatic quality gates before entering incubation, and the pipeline strictly terminates at paper validation with zero live brokerage execution pathways."*
* **Prohibited Claims:** Do NOT claim the pipeline deploys algorithms to live real-money accounts or automated broker execution.

---

### SLIDE 9: Paper Trading & Risk Management

* **Objective:** Detail simulated execution matching, friction modeling, and pre-trade risk controls.
* **Buyer-Facing Content:**
  * **Simulated Execution Core:** `PaperExecutionAdapter` executes market, limit, stop, and trailing stop orders with spread, adverse slippage, and position netting.
  * **Capital Safety Invariant:** All orders are permanently stamped `is_paper=True`. Capital at risk is exactly $0.00.
  * **Pre-Trade Risk Engine:** `RiskService` dynamically evaluates available margin, leverage ceilings (e.g. 1:100 default), position size limits, and daily account drawdown limits.
  * **Simulated Mark-to-Market:** Current simulated position mark-to-market valuations and unrealized P&L are computed synchronously upon request.
* **Recommended Visual:** Sequence flow showing order submission passing through pre-trade risk checks into the paper adapter and database persistence.
* **Repository Evidence:**
  * Paper Adapter: [`libraries/infrastructure/execution/paper_execution.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/infrastructure/execution/paper_execution.py)
  * Risk Engine: [`libraries/domain/risk/`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/domain/risk/)
  * Order Endpoints: [`apps/trading-engine/src/routes/orders.py:32`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/trading-engine/src/routes/orders.py#L32) (`POST /api/v1/orders/`)
* **Numeric Claims Used:** $0.00 live capital at risk (Current verified invariant).
* **External Dependencies:** None.
* **Speaker Notes:**  
  *"The demonstrated execution path uses simulated paper capital only, with $0.00 live financial capital at risk. Pre-trade risk controls dynamically evaluate margin and leverage before any order is accepted."*
* **Prohibited Claims:** Do NOT claim execution is instantaneous zero-latency. Do NOT hardcode fixed mock fill prices or margin estimates.

---

### SLIDE 10: Market Data & Broker Adapter Architecture

* **Objective:** Distinguish internal mock data from external provider integrations.
* **Buyer-Facing Content:**
  * **Default Market Data:** `MockMarketDataProvider` generates deterministic synthetic currency bars and spreads for self-contained offline operation.
  * **External Market Data:** `TwelveDataMarketDataProvider` is implemented in source code to ingest live REST quotes when an operator provisions a `TWELVE_DATA_API_KEY`.
  * **Broker Sandbox Adapter:** `OandaBrokerAdapter` supports connecting to external OANDA Practice sandbox environments (`OANDA_ENVIRONMENT=practice`).
  * **Autonomous Worker State:** `AutonomousWorkerCoordinator` is implemented in source code with manual execution trigger (`/api/v1/worker/run-once`), but is disabled by default in cloud deployments (`WORKER_ENABLED=false`).
* **Recommended Visual:** Component diagram showing market data and broker adapter interface contracts decoupling domain logic from external vendors.
* **Repository Evidence:**
  * Market Data Providers: [`libraries/infrastructure/market_data/`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/infrastructure/market_data/)
  * OANDA Sandbox Adapter: [`libraries/infrastructure/execution/oanda_adapter.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/infrastructure/execution/oanda_adapter.py)
  * Deployment Worker Config: [`render.yaml:52`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/render.yaml#L52) (`ORION_WORKER_ENABLED: "false"`)
* **Numeric Claims Used:** None.
* **External Dependencies:** TwelveData API key (optional), OANDA Practice sandbox token (optional).
* **Speaker Notes:**  
  *"ORION runs self-contained by default using deterministic synthetic market data. Integration adapters for external providers like TwelveData and OANDA Practice are fully implemented and activate when the operator supplies credentials."*
* **Prohibited Claims:** Do NOT describe mock data as 'live market quotes'. Do NOT describe OANDA Practice as live real-money execution.

---

### SLIDE 11: Multi-Tenancy & Organization-Level RBAC

* **Objective:** Present tenant isolation architecture, organization roles, and granular domain permissions.
* **Buyer-Facing Content:**
  * **Relational Multi-Tenancy:** Bounded by `OrganizationModel`; all accounts, orders, and strategies enforce tenant ownership.
  * **Tenant-Scoped Queries:** Database queries bind `WHERE organization_id = :org_id` via dependency-injected session context (`TenantContext`), mitigating cross-tenant data leakage.
  * **7 Organization-Level RBAC Roles:** `OWNER`, `ADMINISTRATOR`, `PORTFOLIO_MANAGER`, `RISK_OFFICER`, `TRADER`, `AUDITOR`, `VIEWER`.
  * **41 Granular Permissions:** Defined in `Permission` enum governing 14 functional platform domains.
* **Recommended Visual:** Role-to-Permission matrix table highlighting separation of duties between Trader, Risk Officer, and Auditor.
* **Repository Evidence:**
  * Organization Models: [`libraries/domain/organization/models.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/domain/organization/models.py)
  * Permissions Matrix: [`libraries/domain/organization/permissions.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/domain/organization/permissions.py)
  * Frontend RBAC Mapping: [`apps/dashboard/src/auth/permissions.ts`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/dashboard/src/auth/permissions.ts)
* **Numeric Claims Used:** 7 RBAC roles, 41 permissions (Current verified invariants).
* **External Dependencies:** None.
* **Speaker Notes:**  
  *"Multi-tenancy is enforced at the database query level. The platform implements seven organization-level RBAC roles governing forty-one granular permissions across all operational endpoints."*
* **Prohibited Claims:** Do NOT claim 'all IDOR vulnerabilities have been eliminated'. Do NOT use 'institutional governance' as an external regulatory certification claim.

---

### SLIDE 12: Security, Auditability & Operations

* **Objective:** Detail security hardening, structured audit logging, and operational observability.
* **Buyer-Facing Content:**
  * **Perimeter Hardening:** Stateless JWT HS256 authentication, bcrypt password hashing, IP rate limiting, and strict HTTP security headers (HSTS, CSP, X-Frame-Options DENY).
  * **Structured Audit Logging:** `AuditLogModel` records operational events (`ORDER_CREATE`, `USER_REGISTER`, `STRATEGY_DEPLOY`) with acting user ID, component, timestamp, and contextual JSON details.
  * **Operational Health Probes:** `/health/live` (liveness), `/health/ready` (database and Redis connectivity), and `/metrics` (Prometheus metrics export).
  * **Secrets Management:** Pydantic Settings ingesting environment variables with zero hardcoded credentials.
* **Recommended Visual:** Security perimeter diagram showing request filtering, middleware headers, and audit log persistence.
* **Repository Evidence:**
  * Security Middleware: [`apps/trading-engine/src/main.py:142`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/trading-engine/src/main.py#L142)
  * Audit Model: [`libraries/infrastructure/persistence/models/audit.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/libraries/infrastructure/persistence/models/audit.py)
  * Health Endpoints: [`apps/trading-engine/src/routes/health.py`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/apps/trading-engine/src/routes/health.py)
* **Numeric Claims Used:** None.
* **External Dependencies:** None.
* **Speaker Notes:**  
  *"Security controls include strict HTTP headers, rate limiting, and an immutable audit trail capturing platform actions with structured contextual JSON details."*
* **Prohibited Claims:** Do NOT claim SOC 2 certification, ISO 27001 certification, or that client IP addresses are systematically indexed in dedicated database columns.

---

### SLIDE 13: Deployment, Backup & Recovery

* **Objective:** Review PaaS infrastructure topology, decoupled migrations, and disaster recovery evidence.
* **Buyer-Facing Content:**
  * **Infrastructure-as-Code Blueprint:** Declarative 4-tier topology defined in `render.yaml` (FastAPI `starter`, React SPA `free`, PostgreSQL `basic-1gb`, Redis `free`).
  * **Base Hosting Estimate:** Baseline cloud hosting configured on Render for approximately $14/month ($7 DB + $7 API under published 2026 pricing).
  * **Decoupled Migrations:** Executed via isolated container job (`preDeployCommand: python scripts/deploy/migrate.py`) before application boot.
  * **Disaster Recovery Evidence:** Documented historical test benchmark demonstrating physical schema and data restoration across 29 tables in ~7.2 seconds in an isolated testing container.
* **Recommended Visual:** PaaS topology diagram showing isolated private networking for database and Redis.
* **Repository Evidence:**
  * PaaS Blueprint: [`render.yaml`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/render.yaml)
  * Infrastructure Map: [`docs/acquisition/14-INFRASTRUCTURE-TOPOLOGY-MAP.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/14-INFRASTRUCTURE-TOPOLOGY-MAP.md)
  * DR Runbook: [`docs/acquisition/08-BACKUP-RESTORE-RUNBOOK.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/08-BACKUP-RESTORE-RUNBOOK.md)
* **Numeric Claims Used:** ~$14/month configuration estimate; ~7.2 second restore across 29 tables (Documented historical evidence).
* **External Dependencies:** Active Render account and payment method.
* **Speaker Notes:**  
  *"ORION deploys declaratively via Render blueprint for an approximately fourteen dollar monthly configuration estimate. In isolated disaster recovery testing, physical database restoration across twenty-nine tables was benchmarked in roughly seven seconds."*
* **Prohibited Claims:** Do NOT claim 'certified disaster recovery' or 'guaranteed 24-hour RPO'.

---

### SLIDE 14: Technical Asset / IP Inventory

* **Objective:** Present the exhaustive codebase inventory, testing metrics, and documentation deliverables.
* **Buyer-Facing Content:**
  * **Modular Source Code:** Complete monorepo comprising FastAPI backend, React dashboard, and 21 internal domain packages.
  * **Automated Test Baseline:** Documented historical test baseline of 4,260 automated tests with 99.4% line coverage across 103 test suites.
  * **Database Evolution:** 15 linear Alembic migration revisions managing 29 database tables.
  * **Due Diligence Data Room:** Complete 18-dossier closing package covering architecture, security, operations, and IP transfer checklists.
* **Recommended Visual:** Dashboard metric grid displaying test suite counts, coverage percentages, and dossier inventory.
* **Repository Evidence:**
  * Launch Audit: [`docs/acquisition/EPIC-028-ACQUISITION-LAUNCH-AUDIT.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/EPIC-028-ACQUISITION-LAUNCH-AUDIT.md)
  * Data Room Index: [`docs/acquisition/18-DUE-DILIGENCE-DATA-ROOM-INDEX.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/18-DUE-DILIGENCE-DATA-ROOM-INDEX.md)
* **Numeric Claims Used:** 4,260 tests, 99.4% coverage (Documented historical evidence); 18 acquisition dossiers, 15 migrations, 29 tables (Current verified invariants).
* **External Dependencies:** None.
* **Speaker Notes:**  
  *"The technical asset includes clean Git commit history, a documented historical baseline of over four thousand two hundred automated tests, and eighteen comprehensive closing dossiers covering every area of due diligence."*
* **Prohibited Claims:** Do NOT present historical test run numbers as real-time guarantees.

---

### SLIDE 15: Acquisition Scope, Handover & Known Limitations

* **Objective:** Transparently establish transaction deliverables, transfer responsibilities, and technical boundaries.
* **Buyer-Facing Content:**
  * **Proposed Acquisition Deliverables:** Transfer of 100% proprietary source code, algorithmic engines, database schemas, and closing documentation, subject to executed transaction documents.
  * **Buyer-Provisioned External Accounts:** Acquirer provisions their own Render PaaS billing, Stripe merchant account, SMTP server, TwelveData API keys, and custom domain DNS.
  * **Transparent Engineering Boundaries:** Documented in `13-KNOWN-LIMITATIONS.md`:
    * Stateless REST architecture (on-demand query polling; no WebSocket push).
    * Single-process execution worker (horizontal worker clustering requires future Celery/Redis queue adoption).
    * Strictly paper trading ($0.00 live financial capital at risk).
  * **Commercial Status:** Pre-revenue technology asset. Paying customers, active subscribers, and recurring revenue are NOT ESTABLISHED IN REPOSITORY.
* **Recommended Visual:** Two-column handover checklist comparing Transferable IP Deliverables against Buyer-Provisioned Accounts.
* **Repository Evidence:**
  * Known Limitations: [`docs/acquisition/13-KNOWN-LIMITATIONS.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/13-KNOWN-LIMITATIONS.md)
  * IP Assignment Checklist: [`docs/acquisition/15-IP-ASSIGNMENT-CHECKLIST.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/15-IP-ASSIGNMENT-CHECKLIST.md)
  * Account Transfer Runbook: [`docs/acquisition/16-ACCOUNT-OWNERSHIP-TRANSFER.md`](file:///c:/Users/Shree/CascadeProjects/forex-trading-platform-architecture/project-orion/docs/acquisition/16-ACCOUNT-OWNERSHIP-TRANSFER.md)
* **Numeric Claims Used:** None.
* **External Dependencies:** Buyer-provisioned vendor accounts.
* **Speaker Notes:**  
  *"The proposed acquisition scope includes complete source code and IP deliverables. Third-party vendor services like Render and Stripe are provisioned directly by the buyer under their corporate identity, ensuring clean vendor separation."*
* **Prohibited Claims:** Do NOT invent ARR, MRR, customer counts, or valuation metrics. Do NOT state legal transfer as already completed.
