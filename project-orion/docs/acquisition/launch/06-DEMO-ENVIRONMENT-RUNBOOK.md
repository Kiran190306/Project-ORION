# Project ORION — Demo Environment Runbook
## Standard Operating Procedure for Buyer Product Walkthroughs & Live Demonstrations

```
Document Reference: docs/acquisition/launch/06-DEMO-ENVIRONMENT-RUNBOOK.md
Document Version:   1.0.0
Release Status:     Acquisition Diligence Launch Package
Source Baseline:    Repository Git Commit d5908d0a0cc2feff99fa02573adb12b8eea33782
Canonical System:   Project ORION — Quantitative FX Research & Paper-Trading SaaS
Execution Boundary: Strictly Paper Trading ($100,000 Virtual Starting Balance; $0.00 Live Capital at Risk)
Commercial Status:  Pre-revenue / Commercial Traction Not Established in Repository
```

---

## 1. Executive Summary & Demonstration Philosophy

This runbook establishes the formal, repeatable protocol for conducting technical and product demonstrations of **Project ORION** (Quantitative FX Research & Paper-Trading SaaS) for qualified prospective acquirers, CTOs, product managers, and quantitative researchers.

### Fundamental Operating Rules
1. **Simulation Invariant**: The demonstration highlights quantitative backtesting, optimization, and simulated execution. Presenters must explicitly clarify: *"All trading demonstrated is simulated paper execution (`PaperExecutionAdapter`, `is_paper=True`) managing a $100,000 virtual starting balance with exactly $0.00 live financial capital at risk."*
2. **Two Distinct Execution Paths**:
   - **Path A: Offline / Self-Contained Demo (Primary & Recommended)**: Operates with zero external network calls or vendor dependencies, utilizing deterministic synthetic market feeds (`MockMarketDataProvider`) and internal paper trading adapters.
   - **Path B: External Provider Demo (Optional & Secondary)**: Demonstrates live external data ingestion or practice broker connectivity using buyer-provisioned or dedicated sandbox credentials (TwelveData, OANDA Practice sandbox, Stripe Test Mode). All external vendor accounts are designated as BUYER-PROVISIONED.
3. **No Real Credentials**: This runbook contains zero live production passwords, API tokens, or secrets. All demonstration identifiers are explicitly marked `EXAMPLE / PLACEHOLDER ONLY`.
4. **Pre-Revenue Transparency**: Presenters must never claim active paying subscribers or commercial ARR. Configured tiers ($0/$99/$299/Custom) reflect the platform's multi-tenant billing architecture.

---

## 2. Preflight Checklist & Environment Verification

Before launching a buyer walkthrough, the demonstrator must verify local environment health:

### 2.1 Self-Contained Offline Preflight (Path A)
```bash
# 1. Verify working directory
cd project-orion

# 2. Confirm database and Redis containers are healthy
docker compose ps
# Expected: PostgreSQL 16 (port 5432) and Redis 7 (port 6379) in UP state

# 3. Verify database migrations are current (15 Alembic migrations)
alembic current
# Expected: Head migration matches baseline commit

# 4. Confirm environment configuration enforces offline mocks
# In .env:
# MARKET_DATA_PROVIDER=mock
# EXECUTION_ADAPTER=paper
# WORKER_ENABLED=false
# STRIPE_MODE=test

# 5. Verify Application Health / Liveness Probes
# Note: Application liveness probe verifies web server availability; distinct from live financial trading.
curl -s http://localhost:8000/health/live
# Expected: {"status": "healthy", "service": "trading-engine"}

curl -s http://localhost:8000/health/ready
# Expected: {"status": "ready", "database": "connected", "redis": "connected"}

# 6. Verify Dashboard Development Server
# http://localhost:5173 responds with HTTP 200
```

### 2.2 External-Provider Preflight (Path B — Optional)
If the buyer specifically requests external API verification:
- [ ] TwelveData API key configured in `.env` (`TWELVE_DATA_API_KEY`).
- [ ] OANDA Practice sandbox account ID and developer token configured (`OANDA_API_URL=https://api-fxpractice.oanda.com`, `OANDA_ACCESS_TOKEN`).
- [ ] Stripe Test Mode publishable/secret keys set (`STRIPE_SECRET_KEY=sk_test_...`).
- [ ] Outbound internet connectivity confirmed.

---

## 3. The 16-Step Canonical Demonstration Sequence

The demonstration follows a logical 16-step user journey progressing from platform discovery through research, optimization, simulated execution, governance, and technical architecture. All frontend routes reflect actual verified paths in `apps/dashboard/src/App.tsx`.

```
   [1. / (Landing)] ──> [2. /register] ──> [3. /login & In-App Onboarding] ──> [4. /dashboard]
                                                                  │
   [8. /optimization] <── [7. /research (Backtest)] <── [6. /research] <── [5. /strategies]
          │
          └──> [9. /optimization (WFA)] ──> [10. /deployments] ──> [11. /orders] ──> [12. /risk]
                                                                                        │
   [16. Data Room] <── [15. /audit] <── [14. /organization & /billing] <── [13. /positions & /trades]
```

---

### Step 1: Landing Page & Public Presence
- **URL**: `http://localhost:5173/`
- **Action**: Navigate to the public landing interface. Showcase product positioning: *"Quantitative FX Research & Paper-Trading SaaS"*.
- **Visuals**: Modern responsive landing layout, clear feature highlights (Strategy Lab, Walk-Forward Analysis, Paper Incubator), and transparent pricing tier matrix ($0 Sandbox, $99 Pro Trader, $299 Business Prop, Custom Enterprise).
- **Claim-Safe Speaking Note**: *"The platform is architected as a complete multi-tenant SaaS. The frontend is built on React 18 with TypeScript and Tailwind CSS, presenting a clean, white-labelable interface designed specifically for quant researchers and prop trading candidates."*

---

### Step 2: Self-Serve Registration & Tenant Provisioning Flow
- **URL**: `http://localhost:5173/register`
- **Action**: Demonstrate the self-service registration and institutional tenant creation flow. Enter user credentials, organization name, and accept the mandatory risk and legal disclosures.
- **Backend Mechanism**: Submits to `POST /api/v1/onboarding/register`, which atomically creates the user record (bcrypt salted password hash), provisions the organization entity with `OWNER` role, assigns the default Free Sandbox subscription tier, and initializes the $100,000 USD virtual paper trading account.
- **Claim-Safe Speaking Note**: *"The registration endpoint atomically provisions both the user and the institutional organization boundary in a single transaction, seeding the default paper trading account with $100,000 in virtual capital and zero live financial exposure."*

---

### Step 3: Authentication & In-App Onboarding Wizard
- **URL**: `http://localhost:5173/login` transitioning to authenticated `http://localhost:5173/dashboard` via `AppShell`
- **Action**: Authenticate via the login form using verified credentials to receive stateless HMAC-SHA256 JWT bearer tokens containing the signed `TenantContext`. Upon initial entry into the authenticated shell, showcase the interactive in-app `OnboardingWizard` (managed by `AppShell.tsx` via `GET /api/v1/onboarding/status`), which verifies organizational readiness steps before unlocking full trading terminal views.
- **Visuals**: Inspection of JWT session state, organization context badge in Topbar, automated assignment of $100,000 paper balance, and seamless transition to dashboard upon wizard completion.
- **Claim-Safe Speaking Note**: *"Upon login, the application receives a cryptographic JWT embedding the user's organization context. The in-app onboarding wizard verifies workspace readiness, and once completed, unlocks full terminal navigation under strict paper trading boundaries."*

---

### Step 4: Executive Portfolio Dashboard
- **URL**: `http://localhost:5173/dashboard`
- **Action**: Display the unified portfolio overview. Review virtual equity curves, unrealized P&L, realized P&L, currency exposure breakdowns, and active paper strategies.
- **Visuals**: Interactive equity chart, prominent `"PAPER TRADING — SIMULATION ONLY"` banner, and quick-action navigation cards.
- **Claim-Safe Speaking Note**: *"The dashboard aggregates simulated performance across all active paper trading accounts. The UI consistently reminds users of the paper trading status, satisfying regulatory best practices."*

---

### Step 5: Strategy Catalog & Registry
- **URL**: `http://localhost:5173/strategies`
- **Action**: Browse the Strategy Catalog. Review the 4 core algorithmic strategies and 9 parameterized profiles:
  1. *EMA Crossover* (Fast/Slow Exponential Moving Average trend following).
  2. *RSI Momentum* (Relative Strength Index overbought/oversold mean reversion).
  3. *MACD Confluence* (Moving Average Convergence Divergence signal cross).
  4. *Bollinger Breakout* (Volatility band penetration).
- **Code Reference**: Mention `libraries/domain/strategy/registry.py` and factory instantiation.
- **Claim-Safe Speaking Note**: *"Strategies are registered in a decoupled Python domain registry. New quantitative strategies can be added by implementing the base strategy interface without modifying core engine routes."*

---

### Step 6: Strategy Lab & Parameter Research
- **Frontend Route**: `http://localhost:5173/research` (Strategy Lab page)
- **Backend API Endpoint**: `GET /api/v1/research/experiments`
- **Action**: Navigate to Strategy Lab (`/research`). Select a strategy (e.g., EMA Crossover on EUR/USD), adjust parameters (Fast Period: 12, Slow Period: 26), and select historical timeframes (e.g., 1H, 1D).
- **Visuals**: Clean parameter input forms with validation against schema constraints.
- **Claim-Safe Speaking Note**: *"In the Strategy Lab, researchers define the parameter space for their trading hypotheses. Parameter validation is enforced via Pydantic v2 schemas."*

---

### Step 7: Historical Backtesting Engine Execution
- **Frontend Route**: `http://localhost:5173/research` (Backtest Execution View)
- **Backend API Endpoint**: `POST /api/v1/research/experiments`
- **Action**: Execute a historical backtest from Strategy Lab. Show the progress indicator and resulting metrics report:
  - Total Return, CAGR, Sharpe Ratio, Sortino Ratio, Calmar Ratio, Maximum Drawdown (MDD).
  - Equity curve overlay and trade-by-trade execution log.
- **Architecture Note**: The backtesting architecture is designed to mitigate temporal leakage through sequential bar processing and `LeakageGuard` controls.
- **Claim-Safe Speaking Note**: *"The backtesting engine operates bar-by-bar. Crucially, our backtesting architecture is designed to mitigate temporal leakage through sequential bar processing and LeakageGuard controls, validating point-in-time timestamp monotonicity."*

---

### Step 8: Multi-Dimensional Parameter Optimization
- **Frontend Route**: `http://localhost:5173/optimization` (Optimization Studio page)
- **Backend API Endpoint**: `POST /api/v1/optimization/run`
- **Action**: Run parameter grid optimization. Display top candidate parameter sets, 2D/3D performance surface heatmaps, and parameter stability indicators.
- **Visuals**: Heatmap showing parameter neighborhood sensitivity, identifying fragile spikes versus robust plateaus.
- **Claim-Safe Speaking Note**: *"Rather than simply picking the highest Sharpe ratio, the optimization studio visualizes parameter neighborhoods. If adjacent parameter combinations show steep performance drops, the platform flags the strategy as potentially curve-fitted."*

---

### Step 9: Walk-Forward Analysis (WFA) & Regime Detection
- **Frontend Route**: `http://localhost:5173/optimization` (Walk-Forward Analysis View)
- **Backend API Endpoint**: `POST /api/v1/optimization/walk-forward`
- **Action**: Demonstrate Walk-Forward Analysis with rolling and anchored window splits in Optimization Studio.
- **Visuals**: In-Sample (IS) training windows versus Out-of-Sample (OOS) testing windows. Display the Walk-Forward Efficiency (WFE) score and Market Regime distribution (Trending vs. Ranging).
- **Claim-Safe Speaking Note**: *"Walk-Forward Analysis is our gold standard for robustness testing. Strategies that pass WFA with an acceptable efficiency ratio demonstrate genuine out-of-sample edge rather than historical over-fitting."*

---

### Step 10: Strategy Deployment & Lifecycle Management
- **Frontend Route**: `http://localhost:5173/deployments` (Deployment Pipeline page)
- **Backend API Endpoint**: `POST /api/v1/deployments/promote/optimization` or `POST /api/v1/deployments/promote/experiment`
- **Action**: Navigate to Deployment Pipeline (`/deployments`). Select the validated strategy and promote it through the lifecycle states:
  - `DRAFT` ──> `BACKTESTED` ──> `OPTIMIZED` ──> `DEPLOYED_PAPER`
- **Visuals**: State machine transition visualizer, parameter lock confirmation, and paper instance creation.
- **Claim-Safe Speaking Note**: *"Project ORION implements a formal strategy lifecycle state machine. Strategies cannot jump directly to execution without passing through documented backtesting and validation stages."*

---

### Step 11: Paper Order Submission & Execution Simulation
- **Frontend Route**: `http://localhost:5173/orders` (Orders page)
- **Backend API Endpoint**: `POST /api/v1/orders`
- **Action**: Submit a manual or automated paper order (e.g., BUY 100,000 EUR/USD at Market).
- **Visuals**: Immediate order execution confirmation via `PaperExecutionAdapter`. Show order status transition (`PENDING` ──> `FILLED`) and order response payload stamped `is_paper=True`.
- **Claim-Safe Speaking Note**: *"The paper execution adapter simulates broker order fills with configurable spread and slippage models. Notice the immutable `is_paper=True` flag stamped on every fill record."*

---

### Step 12: Paper-Trading Risk Engine Controls (Simulated Risk & Position Controls)
- **Frontend Route**: `http://localhost:5173/risk` (Risk Controls page)
- **Backend API Endpoint**: `GET /api/v1/risk/limits`
- **Action**: Inspect active simulated risk rules: Max Drawdown limits, maximum position size, leverage caps, and currency concentration checks.
- **Visuals**: Risk status gauges and simulated rule evaluation triggers.
- **Claim-Safe Speaking Note**: *"The risk engine evaluates simulated pre-trade and post-trade risk constraints in the paper-trading environment. If a strategy violates maximum leverage or drawdown limits, the risk manager rejects execution or triggers automated paper liquidation."*

---

### Step 13: Positions, Fills & Trade Blotter
- **Frontend Route**: `http://localhost:5173/positions` and `http://localhost:5173/trades`
- **Backend API Endpoint**: `GET /api/v1/positions` and `GET /api/v1/trades`
- **Action**: View open simulated positions, unrealized P&L tracking against current bid/ask, and the historical trade blotter. Close a position and demonstrate realized P&L settlement.
- **Visuals**: Clean tabular blotter with pagination, symbol filters, and exportable trade records.
- **Claim-Safe Speaking Note**: *"Open positions track simulated unrealized P&L. When closed, realized P&L settlements update virtual account balances through atomic database transactions."*

---

### Step 14: Multi-Tenant Organization, RBAC & Subscriptions
- **Frontend Route**: `http://localhost:5173/organization` and `http://localhost:5173/billing`
- **Backend API Endpoint**: `GET /api/v1/organizations` and `GET /api/v1/billing`
- **Action**: Review user management across 7 pre-configured RBAC roles (SuperAdmin, Admin, Trader, Quant, RiskManager, Viewer, Auditor) and 41 permissions. View Stripe billing portal interface.
- **Visuals**: Role assignment modal, permission inspection matrix, and subscription plan tier selector.
- **Claim-Safe Speaking Note**: *"Multi-tenancy is reinforced with fine-grained RBAC. Quota enforcement is handled by the `EntitlementService`, restricting daily backtests and paper strategies based on the active subscription tier."*

---

### Step 15: Security & Audit Logging
- **Frontend Route**: `http://localhost:5173/audit` (Audit Trail page)
- **Backend API Endpoint**: `GET /api/v1/legal/audit`
- **Action**: Inspect immutable audit log records capturing user logins, parameter changes, strategy deployments, and order submissions.
- **Visuals**: Paginated audit table with IP address, user agent, actor ID, and cryptographic timestamp.
- **Claim-Safe Speaking Note**: *"Every operational state change is recorded in structured audit logs, providing complete administrative traceability for institutional due diligence."*

---

### Step 16: Technical Architecture & Diligence Documentation Room
- **URL**: `http://localhost:5173/docs/acquisition` (or local file presentation)
- **Action**: Conclude the demonstration by introducing the 18 canonical due diligence dossiers and visual presentation package.
- **Artifacts**: Display the Architecture Topology Map (`01-ARCHITECTURE-TOPOLOGY-MAP.svg`) and Database ERD (`02-DATABASE-ERD.svg`).
- **Claim-Safe Speaking Note**: *"The entire software architecture is backed by an 18-dossier technical data room covering everything from database migration scripts to an open-source SBOM audit. We can grant Tier 1 data room access immediately following this session."*

---

## 4. Failure Handling & Contingency Procedures

During a live buyer demonstration, unexpected interruptions must be handled smoothly:

| Potential Issue | Root Cause | Contingency Action |
|:---|:---|:---|
| **API Health / Liveness Probe Fails** | FastAPI process stopped or crashed | Restart trading engine via terminal: `uvicorn apps.trading-engine.src.main:app --port 8000 --reload`. Takes < 3 seconds. |
| **Database Connection Refused** | Local PostgreSQL container stopped | Run `docker compose up -d postgres`. Wait 2 seconds and re-check `/health/ready`. |
| **External Market Data Timeout (Path B)** | TwelveData rate limit reached or network drop | Immediately switch to offline mock mode: Set `MARKET_DATA_PROVIDER=mock` in `.env` and restart API. Informs buyer: *"Switching to local deterministic feed."* |
| **OANDA Practice Rejection (Path B)** | Expired OANDA sandbox token | Fall back immediately to `PaperExecutionAdapter`. Reiterate that simulation is the canonical platform execution mode. |
| **Frontend White Screen** | Vite dev server hot-reload hiccup | Refresh browser window (`Ctrl+F5` / `Cmd+Shift+R`). Vite restores state in < 1 second. |

---

## 5. Summary of Claim Constraints for Presenters

- **NEVER** use the phrase "live trading" — always qualify as "paper trading" or "simulated execution".
- **NEVER** quote historical backtest returns as real-world expectations.
- **NEVER** claim active paying subscribers or commercial ARR (pre-revenue asset sale).
- **NEVER** promise a fixed acquisition valuation during product walkthroughs.
- **ALWAYS** emphasize the 4,260 automated development tests, 99.4% documented historical test coverage, modular Python DDD architecture, and clean IP transferability.
- **ALWAYS** define transaction transfer scope as: "Proposed Transferable Software / IP Scope, subject to executed transaction agreements."

---
*End of Document — Project ORION Acquisition Launch Suite*
