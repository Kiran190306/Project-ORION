# Project ORION — Buyer Technical Demonstration Script
## Standardized 15-Minute Operator & Walkthrough Protocol

**Asset Category:** Pre-Revenue Quantitative Software & Intellectual Property Acquisition
**Asking Price:** $24,900 USD
**Document Reference:** `docs/acquisition/sales/07-DEMO-CALL-SCRIPT.md`

---

## 1. Preflight Verification & Environment Setup

### 1.1 Environmental Status & Invariant Verification
* **Demonstration Mode:** Local Docker/Poetry container execution or live PaaS environment.
* **Render Cloud Status:** *External Verification Pending.* Do NOT claim the Render deployment is live unless independently verified immediately prior to the call. If cloud endpoints are dormant, execute the demonstration via the local environment.
* **Paper-Trading Invariant:** Confirm that all order routing connects to `PaperExecutionAdapter` (`is_paper=True`) maintaining **$0.00 live financial capital at risk**.
* **Market Data Feeds:** `MockMarketDataProvider` generates deterministic synthetic FX price action requiring zero external API keys.

---

## 2. 15-Minute Walkthrough Timeline

```text
[00:00 - 01:00]  1. Welcome, Commercial Context & Invariants
[01:00 - 02:00]  2. Registration & User Onboarding Flow
[02:00 - 03:00]  3. Executive Dashboard Overview
[03:00 - 04:30]  4. Strategy Formulation (Strategy Lab)
[04:30 - 06:00]  5. Deterministic Historical Backtesting
[06:00 - 07:30]  6. Parameter Space Optimization
[07:30 - 09:00]  7. Walk-Forward Analysis (WFA) & Overfitting
[09:00 - 10:00]  8. Strategy Deployment Pipeline (Quality Gates)
[10:00 - 11:00]  9. Adverse-Slippage Paper Order Execution
[11:00 - 12:00] 10. Pre-Trade Risk Controls & Position Sizing
[12:00 - 13:00] 11. Multi-Tenant RBAC & Append-Only Audit Trail
[13:00 - 14:00] 12. Codebase Architecture & 18-Dossier Data Room
[14:00 - 15:00] 13. Questions, Acquisition Scope & Next Steps
```

---

## 3. Detailed Step-by-Step Operator Script

### Step 1: Welcome, Commercial Context & Invariants [00:00 – 01:00]
* **Action:** Share screen showing the application login page or local development browser window.
* **Spoken Script:**
  > "Welcome, [BUYER NAME]. Today I’m walking you through Project ORION, a quantitative FX research, backtesting, and simulated paper-trading platform.
  >
  > Before diving in, two foundational context points: First, Project ORION is offered as an outright software and intellectual property asset acquisition at an asking price of $24,900 USD. It is a pre-revenue technology foundation, meaning commercial subscriber traction is unestablished in the repository. Second, the platform operates strictly in simulated paper-trading mode with an initial $100,000 virtual balance and exactly zero live financial capital at risk. Let's walk through the end-to-end research-to-simulation workflow."

---

### Step 2: Registration & User Onboarding Flow [01:00 – 02:00]
* **Action:** Navigate to `/register`. Fill in sample user credentials and submit.
* **Demonstrated Mechanics:**
  * Submits to `POST /api/v1/onboarding/register`.
  * Atomically creates the user record with salted bcrypt password hash.
  * Provisions a new organization entity and assigns the user the `OWNER` role.
  * Assigns the default Free Sandbox subscription plan.
  * Automatically initializes a virtual paper trading account with an initial $100,000.00 USD balance.
* **Spoken Script:**
  > "Registration initiates an automated onboarding workflow. In one transaction, the backend provisions the user, establishes the multi-tenant organization context, assigns the default subscription plan, and allocates an isolated virtual account with a $100,000 starting balance."

---

### Step 3: Executive Dashboard Overview [02:00 – 03:00]
* **Action:** Navigate to `/dashboard`.
* **Demonstrated Mechanics:**
  * Highlights virtual equity, paper balance, open positions count, and daily P&L.
  * Showcases the prominent `SIMULATION / PAPER TRADING ONLY` badge in the UI header.
  * Explains system status widgets displaying API health and market feed state.
* **Spoken Script:**
  > "The dashboard aggregates account equity, simulated margin usage, and open positions. Notice the permanent paper trading safety indicators. All calculations reflect simulated double-entry accounting."

---

### Step 4: Strategy Formulation (Strategy Lab) [03:00 – 04:30]
* **Action:** Navigate to `/strategy-lab`. Select a built-in strategy (e.g., `EMA Cross Strategy`).
* **Demonstrated Mechanics:**
  * Displays typed Pydantic parameter schema (`fast_period`, `slow_period`).
  * Shows the 4 built-in strategy classes (`EMAStrategy`, `RSIStrategy`, `MACDStrategy`, `ATRStrategy`) and 9 parameter catalogue profiles.
  * Explains that strategies are pure domain objects in `libraries/domain/strategy/` with zero web framework dependencies.
* **Spoken Script:**
  > "In the Strategy Lab, quants define or configure strategies using typed parameter schemas. The repository includes 4 concrete strategy implementations and 9 catalogue profiles. Because business logic is decoupled in pure Python domain packages, quants can add new mathematical models without touching the web framework."

---

### Step 5: Deterministic Historical Backtesting [04:30 – 06:00]
* **Action:** Configure backtest parameters (e.g., EUR/USD, 1-Hour bars, date range) and click **Run Backtest**.
* **Demonstrated Mechanics:**
  * Execution of chronological bar-by-bar traversal.
  * Modeling of bid/ask spreads, trading commissions, and execution slippage.
  * Generation of equity curve, drawdown chart, trade journal, and performance statistics (Sharpe, Sortino, Calmar, Max Drawdown).
* **Spoken Script:**
  > "The backtesting engine processes bars chronologically with fixed decimal precision. It explicitly models bid/ask spreads and execution slippage rather than assuming frictionless mid-price fills. Behind the scenes, the `LeakageGuard` utility enforces strict timestamp monotonicity designed to mitigate temporal leakage and look-ahead bias."

---

### Step 6: Parameter Space Optimization [06:00 – 07:30]
* **Action:** Navigate to `/optimization-studio`. Select hyperparameter ranges (e.g., fast period 10–30, slow period 40–100) and run grid search.
* **Demonstrated Mechanics:**
  * Parameter space engine validates bounds and step sizes.
  * Parallel execution across parameter combinations with progress indicators.
  * Results table ranked by objective function (e.g., Sharpe Ratio, Net P&L).
* **Spoken Script:**
  > "The Optimization Studio evaluates bounded parameter spaces. The engine validates parameter combinations to prevent invalid configurations and ranks candidate parameter sets by objective performance metrics."

---

### Step 7: Walk-Forward Analysis (WFA) & Overfitting Detection [07:30 – 09:00]
* **Action:** Switch to the **Walk-Forward Analysis** tab. Display rolling in-sample and out-of-sample slices.
* **Demonstrated Mechanics:**
  * Visual timeline showing rolling training (IS) and validation (OOS) windows.
  * Calculation of Walk-Forward Efficiency (WFE) ratios (OOS performance vs. IS performance).
  * Explanation that a low WFE ratio detects curve-fitting and parameter decay across regime shifts.
* **Spoken Script:**
  > "To detect curve-fitting, ORION provides rolling Walk-Forward Analysis. It tests whether parameters optimized in-sample maintain stability out-of-sample. Strategies with poor Walk-Forward Efficiency ratios are flagged before they can proceed."

---

### Step 8: Strategy Deployment Governance (Quality Gates) [09:00 – 10:00]
* **Action:** Navigate to `/deployment-pipeline`.
* **Demonstrated Mechanics:**
  * Displays the 5-stage lifecycle state machine (`DRAFT` → `BACKTESTED` → `OPTIMIZED` → `INCUBATING` → `PROMOTED`).
  * Shows automated gate evaluations: minimum backtest trade count, maximum allowable drawdown, and minimum WFE ratio.
  * Explains that strategies failing gates cannot be promoted into paper incubation.
* **Spoken Script:**
  > "ORION prevents discretionary deployment errors through a programmatic 5-stage state machine. A strategy must pass objective mathematical hurdles—such as drawdown limits and WFE thresholds—before moving into simulated paper incubation."

---

### Step 9: Adverse-Slippage Paper Order Execution [10:00 – 11:00]
* **Action:** Navigate to `/trading` or `/orders`. Submit a simulated Market Buy order for EUR/USD.
* **Demonstrated Mechanics:**
  * Order is ingested by `POST /api/v1/orders/`.
  * `PaperExecutionAdapter` executes order against simulated liquidity books with adverse slippage modeling.
  * Generates an immediate execution fill and open position stamped `is_paper=True`.
* **Spoken Script:**
  > "When an order is submitted, it routes to `PaperExecutionAdapter`. The adapter models execution delay, volume decay, and adverse slippage. Every simulated trade is permanently stamped as paper trading."

---

### Step 10: Pre-Trade Risk Controls & Position Sizing [11:00 – 12:00]
* **Action:** Demonstrate an order being rejected when exceeding leverage or daily loss limits.
* **Demonstrated Mechanics:**
  * Submitting an order exceeding 1:100 leverage ceiling triggers an immediate pre-trade validation error (`HTTP 400 Limit Breach`).
  * Inspection of stop-loss and take-profit parameters attached to the position.
* **Spoken Script:**
  > "Pre-trade risk controls evaluate every order before submission. If an order breaches margin limits, drawdown thresholds, or the 1:100 leverage ceiling, the engine rejects it immediately and logs the rejection to the audit trail."

---

### Step 11: Multi-Tenant RBAC & Append-Only Audit Trail [12:00 – 13:00]
* **Action:** Navigate to `/settings/team` and `/audit-logs`.
* **Demonstrated Mechanics:**
  * Showcase the 7 organizational roles (`OWNER`, `ADMIN`, `PORTFOLIO_MANAGER`, `TRADER`, `ANALYST`, `AUDITOR`, `VIEWER`).
  * Display append-only audit log rows capturing actor ID, timestamp, action type, and JSON payload.
  * Review pre-wired Stripe subscription tier settings (Free Sandbox — $0/month, Pro Trader — $99/month, Business Prop Desk — $299/month, Enterprise — Custom).
* **Spoken Script:**
  > "The platform includes enterprise administrative infrastructure: 7 pre-configured RBAC roles governing 41 domain permissions, organization-scoped data isolation, append-only operational audit logging, and pre-wired Stripe billing in Test Mode."

---

### Step 12: Codebase Architecture & 18-Dossier Data Room [13:00 – 14:00]
* **Action:** Open the code editor or GitHub repository showing the project structure and `docs/acquisition/`.
* **Demonstrated Mechanics:**
  * Codebase layout: `apps/`, `libraries/domain/`, `database/migrations/` (15 Alembic versions), `render.yaml`.
  * Point out the 18 canonical acquisition dossiers, 8 presentation source docs, and 24 visual assets.
* **Spoken Script:**
  > "Architecturally, the codebase is modular: Python 3.11 FastAPI backend, React 19 frontend, 15 linear database migrations across 29 tables, and documented historical development evidence of 4,260 automated tests. The audited repository history shows a single-author commit history within the reviewed repository scope. The acquisition includes an 18-dossier due diligence data room covering architecture, security, SBOM, and operational runbooks."

---

### Step 13: Questions, Acquisition Scope & Next Steps [14:00 – 15:00]
* **Action:** Open the floor for technical and transaction questions.
* **Spoken Script:**
  > "To summarize: Project ORION is offered as an outright software and intellectual property asset acquisition at an asking price of $24,900 USD. The proposed transaction scope includes the Project ORION software repository and documented acquisition assets (subject to definitive transaction agreements) rather than building from a blank slate. Cloud hosting and vendor accounts are independently buyer-provisioned.
  >
  > Following this call, we can execute a mutual NDA to grant your team full access to the 18-dossier due diligence data room. What questions can I answer about the architecture or transaction scope?"
