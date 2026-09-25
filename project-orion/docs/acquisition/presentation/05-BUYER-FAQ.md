# Project ORION — Technical & Commercial Buyer FAQ

**Document Reference:** `docs/acquisition/presentation/05-BUYER-FAQ.md`  
**Classification:** Confidential — Acquisition Technical Due Diligence  
**Repository Working Copy:** `project-orion/`  
**Git Baseline Commit:** `d5908d0a0cc2feff99fa02573adb12b8eea33782`  
**Target Audience:** Technical Due Diligence Evaluators, CTOs, Quantitative Strategists & M&A Teams

---

## 1. Product & Platform Scope

### Q1: What is Project ORION?
**Answer:** Project ORION is a multi-tenant software platform for quantitative foreign exchange research, algorithmic backtesting, parameter optimization, walk-forward analysis, and simulated paper execution. It provides an institutional-style quantitative workflow from mathematical formulation to incubated paper execution.

### Q2: Is Project ORION a live trading engine?
**Answer:** No. The platform operates strictly in paper-trading simulation mode with exactly $0.00 live financial capital at risk. Live real-money brokerage execution is absent from the software.

### Q3: Is Project ORION a regulated financial platform?
**Answer:** No. ORION is strictly a software technology and intellectual property asset. It possesses no broker-dealer licenses, investment adviser registrations, or regulatory clearances.

---

## 2. Architecture & Technology Stack

### Q4: What is the architectural design pattern?
**Answer:** ORION is built on a clean hexagonal modular monorepo architecture (ports and adapters). Pure business and mathematical logic is isolated within 21 internal packages under `libraries/domain/`, completely decoupled from web delivery and persistence adapters.

### Q5: Why were FastAPI and PostgreSQL selected?
**Answer:** FastAPI delivers asynchronous ASGI performance, native OpenAPI documentation generation, and strict typed request validation via Pydantic v2 schemas. PostgreSQL 16 managed through SQLAlchemy 2.0 async ORM provides relational multi-tenant data isolation and ACID transactional integrity.

### Q6: How does the system behave if Redis is unavailable?
**Answer:** The platform implements a graceful in-memory degraded fallback. If the Redis cache is disconnected, session caching and rate-limiting fall back to process memory without crashing the API.

---

## 3. Quantitative Research & Backtesting

### Q7: How many algorithmic strategy classes are implemented?
**Answer:** Exactly 4 concrete algorithmic backtesting classes are implemented in `StrategyRegistry`: `TrendFollowingStrategy`, `MeanReversionStrategy`, `BreakoutStrategy`, and `MomentumStrategy`. In addition, the API defines a 9-archetype catalogue specification (`_STRATEGY_CATALOGUE`) for UI parameter schema configuration.

### Q8: How does the backtesting engine prevent look-ahead bias?
**Answer:** The `DeterministicBacktestEngine` processes historical bars in strict chronological order. At each step, `LeakageGuard.validate_slice()` verifies timestamp monotonicity, architecturally preventing indicators from accessing future bar data.

### Q9: Are backtest results reproducible?
**Answer:** Yes. Given identical parameters and historical candle datasets, the deterministic engine produces identical trade executions, equity curves, and performance statistics to the exact cent.

### Q10: How is financial arithmetic handled?
**Answer:** All calculations—including account balances, lots, pip values, execution prices, and P&L—strictly use Python `Decimal` arbitrary-precision arithmetic to avoid binary floating-point rounding inaccuracy.

---

## 4. Optimization & Walk-Forward Analysis

### Q11: How does parameter optimization work?
**Answer:** The `OptimizationEngine` performs systematic multi-parameter grid search across user-defined parameter bounds (`POST /api/v1/optimization/run`), evaluating sensitivity surfaces and ranking candidates by Sharpe and Sortino ratios.

### Q12: How does Walk-Forward Analysis (WFA) detect curve-fitting?
**Answer:** The `WalkForwardEngine` slices historical data into rolling In-Sample (IS) optimization windows and Out-Of-Sample (OOS) validation windows (`POST /api/v1/optimization/walk-forward`). It calculates Walk-Forward Efficiency ($WFE = \text{Annualized OOS Return} / \text{Annualized IS Return}$) to quantify performance retention on unseen data.

---

## 5. Strategy Deployment & Lifecycle

### Q13: What is the strategy deployment lifecycle?
**Answer:** The lifecycle is managed by `DeploymentLifecycle`, a fail-closed state machine:  
`PENDING_GATES` → `GATES_PASSED` → `INCUBATING` → `PAPER_VALIDATED` → `PROMOTION_CANDIDATE`.  
The pipeline strictly terminates at paper validation; no live real-money execution transitions exist.

### Q14: What automated quality gates are enforced?
**Answer:** Strategies must pass three programmatic hurdles before entering paper incubation:
1. Walk-Forward Efficiency Threshold ($WFE \ge 0.50$).
2. Maximum Permissible Drawdown Ceiling ($\le 15\%$).
3. Parameter Stability Surface Variance.

---

## 6. Paper Trading & Risk Management

### Q15: How does the paper execution engine work?
**Answer:** Orders execute via `PaperExecutionAdapter`, an internal matching engine that models realistic market spread, adverse slippage, execution latency, and position netting. All orders are stamped with `is_paper=True`.

### Q16: How are pre-trade risk controls enforced?
**Answer:** `RiskService` dynamically evaluates available margin, leverage ceilings (e.g. 1:100 default), position size limits, and daily account drawdown limits before an order is accepted for execution.

### Q17: What is the operational state of the autonomous worker?
**Answer:** The `AutonomousWorkerCoordinator` is implemented in source code with a manual on-demand execution trigger (`/api/v1/worker/run-once`), but is disabled by default in cloud deployments (`WORKER_ENABLED=false`).

---

## 7. Multi-Tenancy & Security

### Q18: How is multi-tenant isolation enforced?
**Answer:** Multi-tenancy is enforced at the organization level (`OrganizationModel`). Database queries systematically bind `WHERE organization_id = :org_id` using dependency-injected session context (`TenantContext`), mitigating cross-tenant data leakage.

### Q19: What RBAC roles and permissions exist?
**Answer:** The platform implements 7 organizational roles (`OWNER`, `ADMINISTRATOR`, `PORTFOLIO_MANAGER`, `RISK_OFFICER`, `TRADER`, `AUDITOR`, `VIEWER`) governing 41 granular permissions defined in the `Permission` enum across 14 functional domains.

### Q20: What is captured in the audit log?
**Answer:** `AuditLogModel` records operational events (`ORDER_CREATE`, `USER_REGISTER`, `STRATEGY_DEPLOY`) with acting user ID, component tags, timestamps, and contextual JSON details.

---

## 8. Deployment, Operations & Disaster Recovery

### Q21: How is the platform deployed to the cloud?
**Answer:** Deployment is specified via a declarative Infrastructure-as-Code blueprint (`render.yaml`) on Render PaaS, orchestrating an ASGI web service, a static SPA web service, managed PostgreSQL 16, and managed Redis 7.

### Q22: What is the baseline cloud hosting cost?
**Answer:** The baseline hosting configuration on Render is estimated at approximately $14/month ($7/mo for PostgreSQL `basic-1gb` + $7/mo for API `starter`), subject to actual cloud provider pricing and workload.

### Q23: What evidence exists for disaster recovery?
**Answer:** In an isolated testing container, physical schema and data restoration across 29 tables was benchmarked in ~7.2 seconds (`docs/acquisition/08-BACKUP-RESTORE-RUNBOOK.md`).

---

## 9. Commercial Status & Acquisition

### Q24: What are the commercial revenue and customer metrics?
**Answer:** **NOT ESTABLISHED IN REPOSITORY**. Project ORION is delivered strictly as a pre-commercial, pre-revenue intellectual property and technology software asset.

### Q25: What is the authoritative subscription pricing model?
**Answer:** Implemented in code as: Free Sandbox ($0/mo), Pro Trader ($99/mo), Business Prop Desk ($299/mo), and Enterprise Institutional (Custom / Contact Enterprise). (Legacy $49/$149/$399 figures were early design proposals superseded during implementation).

### Q26: What does the buyer receive upon transaction closing?
**Answer:** Proposed acquisition scope includes 100% transfer of the Git repository, source code, 4,260 automated test baseline, database models, 15 migrations, and 18 closing due diligence dossiers, subject to executed transaction agreements.
