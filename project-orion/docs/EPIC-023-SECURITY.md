# Project ORION — EPIC-023 Quant & Platform Security Reference

## 1. Zero Live Broker & Capital Protection

Project ORION strictly mandates the following non-negotiable security controls:
- **Capital at Risk**: \$0.00. Under no circumstance may research backtests place orders with a live broker or draw upon real capital.
- **Broker Connections**: 0 live broker credentials, API keys, or FIX/REST connections exist within the research domain.
- **Worker Process**: `ORION_WORKER_ENABLED=false` is enforced across default development, CI/CD, and production runtime environments.

---

## 2. Quantitative Model Integrity & Attack Prevention

### 2.1 Arbitrary Code Execution Prevention
- **Attack Vector**: In unhardened quantitative platforms, users frequently attempt to upload arbitrary Python script files or execute dynamic functions, introducing Remote Code Execution (RCE) vulnerabilities.
- **ORION Defense**:
  - The platform **strictly prohibits** uploading or executing dynamic Python code.
  - All strategies are pre-registered within `StrategyRegistry` as compiled classes (`TrendFollowingStrategy`, `MeanReversionStrategy`, `BreakoutStrategy`, `MomentumStrategy`).
  - Parameter payloads are validated against strict type definitions (`integer`, `float`, `string`, `boolean`) with explicit mathematical bounds.
  - Payloads containing `eval`, `exec`, `__import__`, or arbitrary object references are rejected at the Pydantic schema validation boundary.

### 2.2 Look-Ahead Bias & Data Leakage Prevention (`LeakageGuard`)
- **Attack Vector**: Subtle bugs in backtesting simulators where future information (tomorrow's closing price, future volatility, future economic release) leaks into the strategy's current signal calculation, creating artificially hyper-profitable results.
- **ORION Defense**:
  - `LeakageGuard.filter_visible_candles(candles, current_time)` strictly truncates the visible market series to $[0..T]$.
  - `LeakageGuard.validate_strategy_context(context, current_time)` validates that no timestamp in the context exceeds the simulation clock $T$.
  - Attempting to pass or read forward-dated bars raises `DataLeakageDetectedError`.

### 2.3 Overfitting & Curve Fitting Safeguards (`OverfittingGuard`)
- **Quant Risk**: Excessive in-sample optimization leading to catastrophic out-of-sample drawdowns.
- **ORION Defense**:
  - Automatically calculates and flags `SMALL_SAMPLE_SIZE` (< 30 closed trades).
  - Flags `UNREALISTIC_PERFORMANCE` (Sharpe $> 4.0$ or Win Rate $> 85\%$).
  - Flags `SHORT_TEST_HORIZON` (< 30 calendar days).
  - Flags `HIGH_DRAWDOWN` (> 25% max drawdown).
  - Flags `PARAMETER_DENSITY` ($\ge 6$ tuned parameters).

---

## 3. Multi-Tenant Isolation & IDOR Defense

- **Tenant Key**: All experiments are associated with an authoritative `organization_id`.
- **Query Scoping**: All database reads (`get_experiment`, `list_experiments`, `compare_experiments`, `export_experiment`) include `WHERE organization_id = :org_id`.
- **IDOR Protection**: If an authenticated user from Tenant B requests `/api/v1/research/experiments/{id_belonging_to_tenant_a}`, the service fails closed with HTTP 404 (Not Found), preventing data enumeration and leakage.
- **Export Sanitization**: Experiment CSV and JSON exports only contain data for the requesting tenant.

---

## 4. Role-Based Access Control (RBAC)

The research domain enforces granular permissions mapped directly to institutional roles:

| Permission | Description | Allowed Roles |
|---|---|---|
| `RESEARCH_READ` | Discover catalogue, view experiment metrics & curves | `OWNER`, `ADMINISTRATOR`, `PORTFOLIO_MANAGER`, `TRADER`, `AUDITOR`, `VIEWER` |
| `RESEARCH_EXECUTE` | Run backtest simulations (spends daily quota) | `OWNER`, `ADMINISTRATOR`, `PORTFOLIO_MANAGER`, `TRADER` |
| `RESEARCH_CANCEL` | Terminate running simulations | `OWNER`, `ADMINISTRATOR`, `PORTFOLIO_MANAGER`, `TRADER` |
| `RESEARCH_EXPORT` | Download CSV and JSON simulation reports | `OWNER`, `ADMINISTRATOR`, `PORTFOLIO_MANAGER`, `TRADER`, `AUDITOR` |

---

## 5. Audit Logging & Compliance

Every research operation records an immutable audit log entry in the `audit_logs` table:
- `RESEARCH_EXPERIMENT_STARTED`: Records experiment ID, strategy ID, symbol, timeframe, parameter count, and initiating user ID.
- `RESEARCH_EXPERIMENT_COMPLETED`: Records execution runtime, trade count, net profit, and Sharpe ratio.
- `RESEARCH_EXPERIMENT_CANCELLED`: Records cancellation timestamp and actor ID.
