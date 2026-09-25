# Project ORION — Technical Architecture Sheet

**Document Reference:** `docs/acquisition/presentation/03-TECHNICAL-ARCHITECTURE-SHEET.md`  
**Classification:** Confidential — Acquisition Technical Due Diligence  
**Repository Working Copy:** `project-orion/`  
**Git Baseline Commit:** `d5908d0a0cc2feff99fa02573adb12b8eea33782`  
**Architectural Pattern:** Hexagonal Modular Monorepo (Ports & Adapters)

---

## 1. Architectural Component Map

The Project ORION architecture enforces strict separation between user interfaces, web delivery, application orchestration, pure domain logic, and external infrastructure adapters:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. PRESENTATION LAYER                                                                  │
│    React 18 Single-Page Application (TypeScript, Vite, Tailwind CSS, TanStack Query)   │
│    20 Client Routes (Marketing, Auth, Terminal, Research, Optimization, Deployments)   │
│    Status: [INTERNAL]                                                                  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ HTTPS / JSON REST
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. API & DELIVERY LAYER                                                                │
│    FastAPI ASGI Application Factory (Python 3.11+, Pydantic v2 Schemas)                │
│    ├── 24 Modular Routers (Auth, Orders, Research, Optimization, Deployments, etc.)    │
│    ├── Request Correlation ID Middleware (X-Correlation-ID tracing)                    │
│    ├── HTTP Security Headers Middleware (HSTS, CSP, X-Frame-Options DENY)              │
│    └── Dependency Injection Layer (TenantContext, QuotaGuards, RateLimiting)           │
│    Status: [INTERNAL]                                                                  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Application Calls
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. APPLICATION SERVICES LAYER                                                          │
│    Orchestration and workflow coordination with transactional session management:      │
│    ├── OrderService (Order lifecycle, validation, position creation)                   │
│    ├── ResearchService (Backtest execution, metrics evaluation)                        │
│    ├── OptimizationService (Parameter grid search, walk-forward analysis)              │
│    ├── DeploymentPipelineService (Quality gate evaluation, state transitions)          │
│    ├── EntitlementService (Tier quota enforcement, daily order caps)                   │
│    └── SubscriptionService (Plan management, Stripe webhook handling)                  │
│    Status: [INTERNAL]                                                                  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Domain Invocations
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 4. DOMAIN LOGIC LAYER                                                                  │
│    21 Pure Internal Packages (libraries/domain/) — Zero database/framework imports:   │
│    ├── strategy: StrategyRegistry (4 concrete backtest classes, 9 catalogue profiles)  │
│    ├── research: DeterministicBacktestEngine, LeakageGuard temporal validator          │
│    ├── optimization: OptimizationEngine, WalkForwardEngine (WFE metric scoring)        │
│    ├── deployment: DeploymentLifecycle state machine, QualityGates evaluator           │
│    ├── risk: RiskEngine (pre-trade margin checks, leverage caps, drawdown limits)      │
│    ├── organization: Multi-tenant organization models, 7 RBAC roles, 41 permissions    │
│    ├── subscription: Plan models, quota limits, subscription lifecycle                 │
│    └── execution: Canonical Order, Fill, Position, and Trade value objects             │
│    Status: [INTERNAL]                                                                  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Port & Adapter Interfaces
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 5. INFRASTRUCTURE & ADAPTER LAYER                                                      │
│    Hardware, persistence, caching, and execution adapters:                            │
│    ├── Persistence: SQLAlchemy 2.0 Async ORM + PostgreSQL 16 (29 tables) [INTERNAL]   │
│    ├── Cache & Messaging: RedisClient (session & rate limiting)           [OPTIONAL]   │
│    ├── Execution Adapter: PaperExecutionAdapter (spread, slippage, $0 risk) [SIMULATED] │
│    ├── Broker Sandbox: OandaBrokerAdapter (OANDA Practice integration)     [EXTERNAL]   │
│    ├── Market Data Mock: MockMarketDataProvider (synthetic price bars)    [SIMULATED]  │
│    ├── Market Data Feed: TwelveDataMarketDataProvider (REST quote stream) [EXTERNAL]   │
│    └── Worker: AutonomousWorkerCoordinator (manual trigger; disabled loop) [DISABLED]  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Classification & Operational Status

Every technical component in the platform is strictly classified across five operational states:

| Component Name | Architectural Subsystem | Classification | Implementation Status & Constraints |
|---|---|---|---|
| **React Dashboard SPA** | Presentation (`apps/dashboard/`) | **INTERNAL** | Fully implemented single-page application built with React 18, Vite, and TypeScript across 20 routes. |
| **FastAPI Trading Engine**| API Delivery (`apps/trading-engine/`) | **INTERNAL** | Fully implemented ASGI application factory with 24 routers and typed Pydantic v2 schemas. |
| **Application Services** | Orchestration (`src/services/`) | **INTERNAL** | Fully implemented services managing orders, backtesting, optimization, deployments, and entitlements. |
| **21 Domain Packages** | Business Logic (`libraries/domain/`) | **INTERNAL** | Fully implemented domain logic modules encapsulating strategies, research, risk, and organization models. |
| **SQLAlchemy Persistence**| Storage (`libraries/infrastructure/`) | **INTERNAL** | Fully implemented async repositories managing 29 database tables across 15 linear Alembic migrations. |
| **PostgreSQL 16** | Relational Database | **INTERNAL / HOSTED** | Relational database target; provisioned locally via Docker or in cloud via Render `basic-1gb` tier. |
| **PaperExecutionAdapter**| Execution Matching | **SIMULATED** | Internal simulated broker modeling spread, slippage, latency, and netting. Stamped `is_paper=True` ($0.00 capital). |
| **MockMarketDataProvider**| Market Data Ingestion | **SIMULATED** | Offline synthetic market data generator producing deterministic historical candle bars and spreads. |
| **Redis 7 Client** | Cache & Session Store | **OPTIONAL** | Client implemented with graceful degraded fallback; operates in-memory if Redis is disconnected. |
| **TwelveData Provider** | Market Data Ingestion | **EXTERNAL** | External REST client implemented in source; requires operator-supplied `TWELVE_DATA_API_KEY`. |
| **OandaBrokerAdapter** | Broker Sandbox Integration | **EXTERNAL** | External sandbox adapter implemented in source; requires operator-supplied OANDA practice credentials. |
| **Stripe Billing Client**| Commercial Payment Gateway | **EXTERNAL** | Webhook listeners and tier checkout routes implemented; operates in Stripe Test Mode. |
| **Autonomous Worker** | Strategy Automation Coordinator | **DISABLED BY DESIGN** | Implemented with manual trigger endpoint (`/api/v1/worker/run-once`), but background loop is disabled (`WORKER_ENABLED=false`). |

---

## 3. Major Data Flow & Interface Sequences

### 1. Order Creation & Paper Execution Flow
```
Trader (Browser) 
  ──> POST /api/v1/orders/ (CreateOrderRequest)
  ──> FastAPI Router (Validates JWT & Extracts TenantContext)
  ──> OrderService (Resolves tenant organization & active paper account)
  ──> EntitlementService (Verifies daily order quota for subscription tier)
  ──> RiskService (Evaluates simulated margin, leverage cap, and drawdown ceiling)
  ──> PaperExecutionAdapter (Models spread, adverse slippage, and position netting)
  ──> SQLAlchemy Session (Persists OrderModel, FillModel, and PositionModel)
  ──> AuditService (Writes ORDER_CREATE event to AuditLogModel)
  ──> HTTP 201 Created (OrderResponse with is_paper=True)
```

### 2. Research Backtesting Flow
```
Quant User (Browser)
  ──> POST /api/v1/research/experiments (ExperimentRunRequest)
  ──> ResearchService (Extracts parameters for selected StrategyRegistry class)
  ──> CandleRepository (Loads historical candle bars from cache or mock provider)
  ──> DeterministicBacktestEngine (Traverses bars sequentially)
  ──> LeakageGuard (Validates temporal monotonicity: timestamp[i] <= timestamp[i+1])
  ──> PerformanceCalculator (Computes Sharpe, Sortino, Drawdown, Profit Factor)
  ──> HTTP 201 Created (ExperimentSummaryResponse with equity curve & metrics)
```

### 3. Walk-Forward Analysis Flow
```
Quant User (Browser)
  ──> POST /api/v1/optimization/walk-forward (WalkForwardRunRequest)
  ──> OptimizationService (Slices historical dataset into rolling IS and OOS windows)
  ──> ParameterSpaceEngine (Generates parameter search combinations)
  ──> WalkForwardEngine (Optimizes on IS window; evaluates best candidate on OOS window)
  ──> RobustnessAnalyzer (Computes WFE = Annualized OOS Return / Annualized IS Return)
  ──> HTTP 201 Created (WalkForwardAnalysisResponse with stability surface)
```

---

## 4. Architectural Boundaries & Data Segregation

1. **Strict Multi-Tenant Query Binding:**  
   Every database query across orders, positions, trades, and strategy candidates executes within a dependency-injected session enforcing `WHERE organization_id = :org_id`. Cross-tenant data access fails closed.
2. **Decimal Financial Arithmetic Invariant:**  
   All financial metrics (account balances, trade volume, pip distances, execution prices, and realized/unrealized P&L) are strictly processed using Python `Decimal` data structures, preventing binary floating-point rounding inaccuracy.
3. **Fail-Closed Broker Safety:**  
   The execution layer contains zero code pathways to live real-money brokerage APIs. All live order routing branches raise hard exceptions, ensuring that live financial capital exposure remains exactly $0.00.
