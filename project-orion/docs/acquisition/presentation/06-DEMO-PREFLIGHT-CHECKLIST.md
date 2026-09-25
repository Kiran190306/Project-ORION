# Project ORION — Demo Preflight & Operator Runbook

**Document Reference:** `docs/acquisition/presentation/06-DEMO-PREFLIGHT-CHECKLIST.md`  
**Classification:** Confidential — Acquisition Technical Due Diligence  
**Repository Working Copy:** `project-orion/`  
**Git Baseline Commit:** `d5908d0a0cc2feff99fa02573adb12b8eea33782`  
**Operational Objective:** Flawless, secure, and reproducible buyer-facing live demonstration execution

---

## 1. Operator Safety Invariants

Before commencing any buyer demonstration, the operator must verify adherence to four absolute safety rules:

1. **Mandatory Dynamic Credential Generation:**  
   The operator must NEVER use a hardcoded password (e.g. `DemoPassword2026!`) or personal credentials. Generate a fresh temporary password immediately prior to the walkthrough.
2. **Fresh Tenant Registration:**  
   Do not rely on static test accounts (e.g. `demo@orion.internal`). Always execute a fresh registration using a unique timestamped email (e.g. `evaluator-${Date.now()}@demo.internal`) to prove live multi-tenant provisioning.
3. **Paper Safety Invariant:**  
   Capital at risk is strictly **$0.00**. Orders route through `PaperExecutionAdapter` (`is_paper=True`).
4. **Historical Benchmark Qualification:**  
   When referencing test metrics, state: *"Documented historical test baseline of 4,260 automated tests with 99.4% coverage."*

---

## 2. Preflight Verification Timeline

### T-24 Hours: Baseline & Environment Integrity
- [ ] **Git Synchronization Check:**  
  Run `git rev-parse HEAD` and `git status --short`. Verify HEAD is `d5908d0a0cc2feff99fa02573adb12b8eea33782` and working tree is clean.
- [ ] **Automated Test Suite Verification:**  
  Run `pytest -m "not slow"` and confirm zero test failures across the test harness.
- [ ] **Database Migration State:**  
  Run `alembic current` and confirm migration head is synchronized across all 15 revisions.
- [ ] **PaaS Infrastructure Check (if cloud staging):**  
  Verify Render dashboard indicates healthy status for `orion-api` and `orion-dashboard`.

### T-1 Hour: Process Initialization & Health Probes
- [ ] **Database & Cache Startup:**  
  Ensure PostgreSQL 16 is accessible on port 5432 and Redis 7 is accessible on port 6379 (or verify cloud connection strings).
- [ ] **API Engine Boot:**  
  Launch FastAPI engine:  
  `uvicorn apps.trading-engine.src.main:app --host 127.0.0.1 --port 8000`
- [ ] **Frontend SPA Boot:**  
  Launch React dashboard:  
  `npm run dev` in `apps/dashboard/` (accessible at `http://localhost:5173/`).
- [ ] **Operational Health Probe Verification:**  
  Execute `curl -f http://127.0.0.1:8000/health/live` (must return HTTP 200).  
  Execute `curl -f http://127.0.0.1:8000/health/ready` (must return HTTP 200).

### T-15 Minutes: Credential & Data Cleanliness
- [ ] **Generate Ephemeral Demo Credentials:**  
  Run `openssl rand -base64 16` to generate a temporary 20-character password.  
  Format registration email: `evaluator-<timestamp>@demo.internal`.
- [ ] **Browser Storage Purge:**  
  Clear cookies, localStorage, and sessionStorage in the demonstration browser profile.  
  Verify opening `http://localhost:5173/` displays the unauthenticated marketing landing page.
- [ ] **Synthetic Candle Smoke Test:**  
  Verify Research Lab executes a EUR/USD H1 backtest in under 2 seconds.

### T-5 Minutes: Screen & Presentation Staging
- [ ] **Display Resolution & Cleanliness:**  
  Set screen resolution to 1080p (1920x1080) at 100% or 125% DPI scaling.  
  Close all email clients, terminal scratch windows, and private chat applications.
- [ ] **Browser Tab Staging:**  
  * Tab 1: `http://localhost:5173/` (Primary trading terminal).
  * Tab 2: `http://127.0.0.1:8000/docs` (FastAPI OpenAPI documentation).
  * Tab 3: Local acquisition data room folder (`docs/acquisition/`).
- [ ] **Audio & Screen Share Check:**  
  Confirm microphone clarity and verify presentation window sharing.

---

## 3. Live Demonstration Script & Action Protocol

```
00:00 - 00:40 │ Marketing Landing Page & Legal Disclaimers
              │ Route: / and /risk-disclosure
              │ Spoken: "Project ORION is a quantitative research and paper-trading platform.
              │ The demo operates with deterministic market data and $0.00 capital at risk."

00:40 - 01:20 │ Self-Service Registration & Multi-Tenant Provisioning
              │ Route: /register
              │ Action: Enter dynamic email and ephemeral password. Submit form.
              │ Spoken: "Submitting creates an isolated organization tenant, assigns the OWNER
              │ role, and initializes a default $100,000 simulated paper trading account."

01:20 - 02:00 │ Trading Terminal Overview
              │ Route: /dashboard
              │ Action: Point out $100,000 virtual balance and 'Paper Trading Only' badges.
              │ Spoken: "The terminal displays our simulated hundred thousand dollar paper
              │ balance. Every financial metric is explicitly badged as paper mode."

02:00 - 03:00 │ Strategy Lab & Deterministic Backtesting
              │ Route: /research
              │ Action: Select Trend Following on EUR/USD H1. Click 'Run Backtest'.
              │ Spoken: "The engine processes historical bars sequentially using LeakageGuard
              │ to prevent look-ahead bias, producing deterministic backtest results."

03:00 - 04:00 │ Optimization Studio & Walk-Forward Analysis
              │ Route: /optimization
              │ Action: Select 2x2 parameter grid. Click 'Run Walk-Forward'.
              │ Spoken: "Optimization evaluates parameter sensitivity. Rolling walk-forward
              │ windows compute Walk-Forward Efficiency to detect curve-fitting."

04:00 - 04:40 │ Strategy Deployment Pipeline & Quality Gates
              │ Route: /deployments
              │ Action: Inspect candidate passing automated quality gates. Click 'Incubate'.
              │ Spoken: "Strategies must pass automated quantitative quality gates before
              │ entering incubation, terminating strictly at paper validation."

04:40 - 05:40 │ Paper Order Execution
              │ Route: /orders
              │ Action: Submit 10,000 EUR/USD BUY Market order with SL/TP.
              │ Spoken: "The demonstrated execution path uses simulated paper capital only,
              │ with $0.00 live financial capital at risk."

05:40 - 06:20 │ Mark-to-Market Positions & Risk Monitoring
              │ Route: /positions and /risk
              │ Action: Show open EUR/USD position and pre-trade leverage ceiling cards.
              │ Spoken: "The position updates with simulated mark-to-market values. The risk
              │ engine monitors leverage caps and account drawdown thresholds."

06:20 - 07:00 │ Organization Governance & Immutable Audit Log
              │ Route: /organization and /audit
              │ Action: Show 7 RBAC roles and filterable audit trail showing ORDER_CREATE.
              │ Spoken: "ORION enforces seven organizational roles across forty-one permissions.
              │ Every action is recorded in an immutable audit log with JSON details."

07:00 - 07:30 │ Architecture & OpenAPI Specifications
              │ Route: /docs (FastAPI Swagger)
              │ Action: Expand router list showing 24 modular routers and Pydantic schemas.
              │ Spoken: "The platform comprises twenty-four FastAPI routers, typed Pydantic v2
              │ schemas, and twenty-one internal domain modules."

07:30 - 08:00 │ Acquisition Handover & Data Room Review
              │ Route: docs/acquisition/ directory listing
              │ Action: Highlight 18 closing dossiers covering architecture, DR, and IP.
              │ Spoken: "The proposed acquisition scope includes complete source code, four
              │ thousand two hundred automated tests, and eighteen closing dossiers."
```

---

## 4. Failure Recovery Protocols

| Failure Event | Immediate Operator Action | Spoken Buyer Explanation | Fallback Screen |
|---|---|---|---|
| **API Connection Lost** | Switch seamlessly to local mirrored instance (`http://127.0.0.1:8000`). | *"Switching to our local mirrored test harness."* | Localhost Dashboard (`:5173`) |
| **Registration Conflict** | Append current millisecond timestamp to email (`evaluator-<ts>@demo.internal`). | *"Registering a second tenant to demonstrate organizational isolation."* | Direct registration retry |
| **Backtest Timeout** | Select standard 3-month window on EUR/USD H1. | *"Focusing on a high-granularity 3-month evaluation window for interactive speed."* | Pre-computed backtest view |
| **Optimization Delay** | Run focused 2x2 grid search (4 combinations). | *"Executing a focused 4-combination parameter grid for rapid interactive evaluation."* | Research Lab studio |
| **Order Rejection** | Reduce lot size to 10,000 units ($0.10 mini lot). | *"Our pre-trade risk engine properly caught an account leverage ceiling breach."* | Orders terminal form |
| **Position Delay** | Click table refresh button or navigate to `/portfolio`. | *"Querying latest mark-to-market position state via the portfolio service."* | Portfolio Overview (`/portfolio`) |
| **Audit Log Blank** | Trigger an immediate order cancellation to emit a fresh event. | *"Generating a fresh operational event to demonstrate real-time audit logging."* | Organization Settings (`/organization`) |
