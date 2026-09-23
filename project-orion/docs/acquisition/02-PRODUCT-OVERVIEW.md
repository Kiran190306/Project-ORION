# Project ORION — Product Overview & Capability Architecture

**Document Version:** 1.0.0<br>
**Target Milestone:** EPIC-027 Phase 7B Acquisition Due Diligence<br>
**Repository Working Copy:** `project-orion/`<br>
**Classification:** Confidential — Due Diligence Technical Data Room (Tier 2 / NDA)<br>
**Safety Mandate:** STRICT PAPER TRADING ONLY ($0.00 Capital at Risk — Zero Live Broker Endpoints)

---

## 1. Product Overview & Market Positioning

Project ORION is a multi-tenant Software-as-a-Service (SaaS) platform engineered for algorithmic Forex quantitative research, combinatorial parameter optimization, Walk-Forward Analysis (WFA), and adverse-slippage paper trading simulation.

The platform provides quantitative traders and development teams with a complete local and cloud simulation environment where algorithmic hypotheses can be authored, backtested against historical tick/candle feeds, rigorously tested for overfitting, and deployed into simulated virtual trading accounts without exposing real financial capital ($0.00 capital at risk).

### Core Quantitative Philosophy
1. **Simulation Isolation:** The platform contains zero facilities for depositing, custodying, or trading real monetary funds.
2. **Realistic Microstructure Simulation:** To prevent the deceptive optimism common in naive backtesting software, Project ORION simulates spread volatility, volume decay, and adverse execution slippage.
3. **Overfitting Diagnostics:** By combining combinatorial Grid/Random search sweeps with Walk-Forward Analysis, the platform actively measures and highlights out-of-sample performance degradation.

---

## 2. Comprehensive Capability Matrix

The following matrix documents the operational implementation status of all primary functional capabilities in Project ORION, verified directly against the underlying codebase:

| Capability Domain | Subsystem / Source Path | Classification | Verification & Evidence | External Dependencies |
|---|---|:---:|---|---|
| **Authentication & Account Lifecycle** | `apps/trading-engine/src/routes/auth.py`, `src/services/auth.py` | **IMPLEMENTED + TESTED** | Salted Bcrypt hashing, stateless HMAC-SHA256 JWTs, password reset with anti-enumeration, single-use SHA-256 tokens, session invalidation via `password_changed_at`. Tested in `test_auth_lifecycle.py`. | None (Internal database & crypto) |
| **Organizations & Multi-Tenancy** | `libraries/domain/organization/`, `apps/trading-engine/src/routes/organization.py` | **IMPLEMENTED + TESTED** | Tenant isolation via `organization_id` foreign keys, membership lifecycle, invitation tokens. Tested in IDOR regression test suites. | None (Relational database) |
| **Role-Based Access Control (RBAC)** | `libraries/domain/organization/permissions.py` | **IMPLEMENTED + TESTED** | 41 granular permissions defined by the current RBAC permission model across 7 organization roles (`OWNER` to `VIEWER`), enforced at route level via `@require_permission`. | None (Pure Python domain logic) |
| **Trading Dashboard SPA** | `apps/dashboard/src/` | **IMPLEMENTED + TESTED** | Modern React 18, TypeScript 5, Vite, TanStack Query, TailwindCSS dark theme, multi-stage Nginx container with SPA fallback routing. Tested in `apps/dashboard/tests/`. | None (Static container build) |
| **Virtual Paper Accounts** | `apps/trading-engine/src/routes/paper.py`, `src/routes/account.py` | **IMPLEMENTED + TESTED** | Virtual equity tracking, free/used margin, leverage configuration, default $100k balance, zero real financial exposure. Tested in `test_paper_trading.py`. | None (Relational database) |
| **Market Data Ingestion** | `libraries/infrastructure/market_data/` | **IMPLEMENTED + EXTERNAL DEPENDENCY** | Mock synthetic Brownian motion generator tested offline; live OHLCV candle ingestion implemented via TwelveData REST API adapter. | TwelveData API subscription key |
| **Technical Indicators** | `libraries/domain/indicators/` | **IMPLEMENTED + TESTED** | Standard indicators (SMA, EMA, RSI, MACD, ATR, Bollinger Bands) computed with arbitrary `Decimal` precision. Tested in unit test suites. | None (Pure Python arithmetic) |
| **Strategy Archetypes** | `libraries/domain/strategies/`, `apps/trading-engine/src/routes/strategies.py` | **IMPLEMENTED + TESTED** | Built-in archetypes (Trend Following, Mean Reversion, Breakout) with JSON schema validation for parameter bounds. Tested in strategy test suites. | None (Pure Python domain models) |
| **Backtesting Engine** | `libraries/domain/backtesting/`, `apps/trading-engine/src/routes/research.py` | **IMPLEMENTED + TESTED** | Bar-by-bar historical replay, Sharpe, Sortino, Calmar ratios, maximum drawdown, equity curve tracking. Tested in `test_backtesting.py`. | Historical market candle data |
| **Walk-Forward Analysis (WFA)** | `libraries/domain/optimization/wfa.py` | **IMPLEMENTED + TESTED** | Rolling In-Sample (IS) training and Out-of-Sample (OOS) testing windows, walk-forward efficiency metrics. Tested in `test_wfa.py`. | Historical market candle data |
| **Combinatorial Optimization** | `libraries/domain/optimization/` | **IMPLEMENTED + TESTED** | Multi-parameter Grid Search and quasi-random parameter sweeps across bounded hyperparameter spaces. Tested in `test_optimization.py`. | Historical market candle data |
| **Strategy Incubator / Pipeline** | `libraries/domain/deployment/`, `apps/trading-engine/src/routes/deployments.py` | **IMPLEMENTED + TESTED** | Formal strategy deployment lifecycle: `DRAFT` -> `BACKTESTED` -> `OPTIMIZED` -> `INCUBATING` -> `ACTIVE` with automated gate criteria. | None (Relational database) |
| **Paper Execution Microstructure**| `libraries/infrastructure/execution/paper_execution.py` | **IMPLEMENTED + TESTED** | Deterministic virtual order matching, spread application (Ask for Buy, Bid for Sell), adverse slippage volume decay model, resting trigger orders. | None (In-memory simulation engine) |
| **Pre-Trade Risk Management** | `libraries/domain/risk/`, `apps/trading-engine/src/routes/risk.py` | **IMPLEMENTED + TESTED** | Pre-trade margin checks, maximum drawdown limits, leverage ceilings, daily loss circuit breakers. Tested in `test_risk_engine.py`. | None (Pure Python domain rules) |
| **Orders, Positions & Trade Logs** | `apps/trading-engine/src/routes/orders.py`, `positions.py`, `trades.py`| **IMPLEMENTED + TESTED** | Order creation/cancellation, FIFO position netting, mark-to-market valuations, append-only audit trail logging in `audit_logs`. | None (Relational database) |
| **Broker Sandbox Integration** | `libraries/infrastructure/execution/oanda_adapter.py` | **IMPLEMENTED + EXTERNAL DEPENDENCY** | OANDA v20 practice REST adapter implemented and tested with mocks; live sandbox validation requires external OANDA practice credentials. | OANDA v20 practice account |
| **Commercial Billing Integration** | `libraries/infrastructure/billing/stripe_adapter.py` | **IMPLEMENTED + EXTERNAL DEPENDENCY** | Stripe Test Mode SDK, webhook HMAC-SHA256 signature verification (300s window), customer mapping; live keys structurally rejected. | Stripe Test Mode account |
| **Transactional Email Delivery** | `libraries/infrastructure/communication/email_service.py` | **IMPLEMENTED + EXTERNAL DEPENDENCY** | SMTP adapter with async thread offloading, anti-enumeration error masking, and paper trading disclosures. Tested in `test_email_service.py`. | External SMTP relay provider |
| **Legal & Risk Disclosures** | `libraries/domain/legal/`, `apps/trading-engine/src/routes/legal.py` | **IMPLEMENTED + TESTED** | Versioned legal documents, user consent receipts, mandatory paper trading risk warnings. Tested in `test_onboarding_legal.py`. | None (Relational database) |
| **User Onboarding Sequence** | `apps/trading-engine/src/services/onboarding_service.py` | **IMPLEMENTED + TESTED** | 5-step guided workflow (`WELCOME`, `EMAIL_VERIFICATION`, `STRATEGY`, `RISK`, `PAPER_TRADING_READY`) persisted in `onboarding_progress`. | None (Relational database) |
| **Autonomous Strategy Worker Loop**| `apps/trading-engine/src/worker.py` | **CONFIGURED / DISABLED BY DEFAULT** | In-process background market polling and signal evaluation loop. Gated by default (`ORION_WORKER_ENABLED: "false"`). | Explicit operator activation |
| **Live Broker Real Money Trading**| N/A | **NOT IMPLEMENTED** | Structurally prohibited by architectural design. Zero live trading execution code exists. | N/A (Intentional exclusion) |
| **Multi-Region Database Clustering**| N/A | **NOT IMPLEMENTED** | Single-region PaaS cloud topology. Geo-replication requires external infrastructure engineering. | Cloud database replication |
| **Third-Party Security Certifications**| N/A | **NOT IMPLEMENTED** | No third-party SOC 2, ISO 27001, or penetration test reports exist. | Independent auditor engagement |

---

## 3. End-to-End Quantitative Workflow

Project ORION structures the quantitative trading process into a rigorous 6-stage lifecycle:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  1. RESEARCH │ ──> │ 2. BACKTEST  │ ──> │ 3. OPTIMIZE  │
│ Parameter &  │     │ Bar-by-Bar   │     │ Grid / Random│
│ Archetype    │     │ Historical   │     │ Parameter    │
│ Definition   │     │ Simulation   │     │ Sweeps       │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                                                 ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│6. PAPER TRADE│ <── │ 5. INCUBATE  │ <── │    4. WFA    │
│ Adverse      │     │ Performance  │     │ Walk-Forward │
│ Slippage &   │     │ Monitoring   │     │ Out-of-Sample│
│ Spread Exec  │     │ Lifecycle    │     │ Validation   │
└──────────────┘     └──────────────┘     └──────────────┘
```

### Stage 1: Strategy Research
The user defines an algorithmic strategy by selecting a validated archetype (e.g., Moving Average Crossover, RSI Mean Reversion, Volatility Breakout) and configuring instrument symbols and parameter bounds.

### Stage 2: Historical Backtesting
The strategy is executed bar-by-bar across historical candle data. The backtesting engine simulates tick execution, tracks cash equity curves, and calculates comprehensive risk-adjusted return ratios (Sharpe, Sortino, Calmar) and maximum drawdown.

### Stage 3: Combinatorial Parameter Optimization
To investigate parameter sensitivity, the user runs Grid Search or Quasi-Random parameter sweeps. The engine evaluates thousands of parameter permutations asynchronously and ranks candidate configurations.

### Stage 4: Walk-Forward Analysis (WFA)
To combat overfitting, the strategy undergoes rolling Walk-Forward Analysis. Historical data is divided into sequential In-Sample (IS) training windows and Out-of-Sample (OOS) testing windows. The engine calculates the Walk-Forward Efficiency (WFE) score to quantify real forward degradation.

### Stage 5: Strategy Incubation & Promotion
Optimized strategies with satisfactory stability metrics are promoted into the Strategy Incubator (`libraries/domain/deployment/`). The deployment state machine tracks strategy health before allowing paper deployment.

### Stage 6: Paper Trading Execution
The strategy is activated in a simulated virtual trading account. Orders are evaluated against live or synthetic feeds by `PaperExecutionAdapter`, applying adverse slippage models, spread costs, and pre-trade margin checks.

---

## 4. Microstructure Simulation & Adverse Slippage Model

To ensure paper simulation results reflect real-world execution friction, `PaperExecutionAdapter` models microstructure dynamics deterministically:

1. **Side-Aware Spread Costs:** Buy orders execute at the simulated Ask price; Sell orders execute at the simulated Bid price.
2. **Adverse Slippage Penalty:** Execution price is dynamically adjusted based on simulated order volume relative to market depth and spread volatility:
   $$\text{Execution Price}_{\text{Buy}} = \text{Ask} + \text{Slippage Penalty}$$
   $$\text{Execution Price}_{\text{Sell}} = \text{Bid} - \text{Slippage Penalty}$$
3. **Resting Trigger Management:** Stop-Loss, Take-Profit, and Limit orders are held in memory and continuously evaluated against incoming quote ticks.
4. **Margin Accounting:** Free margin, used margin, and margin level percentages are computed in real time using `Decimal` arithmetic. Margin breach events trigger simulated liquidation.

---

## 5. Multi-Tenant Governance & User Onboarding

### Guided Onboarding Workflow
Project ORION enforces a structured 5-step onboarding sequence defined in `OnboardingStep` (`libraries/infrastructure/persistence/models/onboarding.py`):
1. `WELCOME`: Initial platform introduction and legal risk disclosure presentation.
2. `EMAIL_VERIFICATION`: Cryptographic confirmation of the user's registered email address.
3. `STRATEGY`: Initial strategy selection and parameter inspection.
4. `RISK`: Pre-trade risk parameter configuration (maximum drawdown, leverage ceiling).
5. `PAPER_TRADING_READY`: Final readiness confirmation and paper balance allocation.

Onboarding progression is tracked via `OnboardingProgressModel` in the `onboarding_progress` table, with state transitions (`NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`) synchronized with the frontend dashboard.

### Fine-Grained Authorization
The system enforces **41 granular permissions defined by the current RBAC permission model** across 7 organization roles:
- `OWNER`: Full administrative, financial, and organizational control.
- `ADMINISTRATOR`: User management, tenant configuration, and strategy oversight.
- `PORTFOLIO_MANAGER`: Strategy deployment, incubator lifecycle, and account management.
- `RISK_OFFICER`: Risk ceiling configuration and drawdown limit enforcement.
- `TRADER`: Order placement, position modification, and paper trading operations.
- `AUDITOR`: Read-only inspection of audit logs and compliance history.
- `VIEWER`: Read-only visibility into dashboard analytics and performance metrics.

---

## 6. External Service Boundaries

| Service Provider | Protocol / Integration | Role in Platform | Boundary Guardrail |
|---|---|---|---|
| **Stripe** | REST API & Webhooks | Subscription billing & checkout sessions | Test Mode only; live production keys raise `LiveCredentialsForbiddenError`. |
| **OANDA** | REST API (v20) | Demo broker connection validation | Practice sandbox only (`api-fxpractice.oanda.com`); live URLs rejected. |
| **TwelveData** | REST API | Historical & live OHLCV candle ingestion | API rate limits respected; falls back to offline synthetic generator. |
| **SMTP Relay** | SMTP (Port 587/465) | Verification emails & password reset | Async thread offloading; anti-enumeration masks transport errors. |
