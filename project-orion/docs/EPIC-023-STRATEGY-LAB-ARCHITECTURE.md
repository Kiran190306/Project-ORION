# Project ORION — EPIC-023 Strategy Lab & Backtesting Platform Architecture

## 1. Executive Architecture Summary

EPIC-023 implements the **Institutional Strategy Lab & Quantitative Backtesting Platform** for Project ORION. It extends the canonical Strategy, Backtesting, Market Data, Entitlements, RBAC, and Persistence domains to provide an institutional-grade simulation laboratory with zero code duplication, zero live broker connections, zero capital at risk, and mathematical determinism.

```
+---------------------------------------------------------------------------------------------------+
|                                  ORION RESEARCH PLATFORM (EPIC-023)                               |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  [ Institutional React Dashboard ]                                                                |
|     |-- Lab Builder (Archetype discovery, dynamic schema controls, simulation friction config)    |
|     |-- Experiment History (Tenant backtest ledger, status tracking, multi-selection)             |
|     |-- Result Analytics (Key ratios, downsampled SVG equity curve, trade journal, export)        |
|     +-- Comparative Matrix (Side-by-side performance metrics & normalized return % overlays)     |
|                                                                                                   |
|                                         | HTTPS / JSON API                                        |
|                                         v                                                         |
|  [ Trading Engine FastAPI Routing ] (/api/v1/research/*)                                          |
|     |-- require_permission(Permission.RESEARCH_READ / EXECUTE / CANCEL / EXPORT)                  |
|     |-- Multi-tenant boundary isolation (scoped by organization_id)                              |
|     +-- EntitlementService.check_daily_research_quota (Daily bar/day simulation limits)           |
|                                                                                                   |
|                                         | Application Service                                     |
|                                         v                                                         |
|  [ ResearchService ]                                                                              |
|     |-- StrategyRegistry (Validated catalogue, parameter bounds, zero arbitrary Python eval)     |
|     |-- MarketDataServiceHistoricalProvider (Canonical candle bridge & deterministic generator)   |
|     |-- LeakageGuard (Slice [0..T] guarantee, monotonic sequence, zero lookahead)                 |
|     |-- StrategyBacktestAdapter (Decimal accounting, adverse slippage, commissions, netting)      |
|     |-- OverfittingGuard (Small sample, anomaly Sharpe, short horizon, drawdown caveats)          |
|     +-- Downsampling (Min/max extremum-preserving decimation to <= 300 points)                    |
|                                                                                                   |
|                                         | Persistence & Audit                                     |
|                                         v                                                         |
|  [ PostgreSQL / SQLite ]                                                                          |
|     |-- research_experiments (Schema migration 0009_research_experiments.py)                      |
|     +-- audit_logs (RESEARCH_EXPERIMENT_STARTED / COMPLETED / CANCELLED)                          |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Domain Decomposition & Component Responsibilities

### 2.1 Strategy Catalogue & Registry (`libraries/domain/strategy/registry.py`)
- **Single Source of Truth**: Central registry of pre-compiled, deterministic strategies (`TrendFollowingStrategy`, `MeanReversionStrategy`, `BreakoutStrategy`, `MomentumStrategy`).
- **Strict Parameter Schemas**: Every parameter is typed (`integer`, `float`, `string`, `boolean`) with minimum/maximum bounds, defaults, and option sets.
- **Safety**: Complete absence of dynamic Python string execution (`eval`, `exec`, or dynamic imports). All strategies are validated and instantiated via deterministic factories.

### 2.2 Historical Data Provider Bridge (`libraries/domain/backtesting/historical_data.py`)
- **Historical Provider**: Bridges live canonical market data stores or deterministic candle series for backtesting.
- **Continuous Feeds**: Generates deterministic OHLCV series parameterized by symbol and timeframe with continuous price series and authentic volatility.

### 2.3 Data Leakage & Look-Ahead Prevention (`libraries/domain/backtesting/leakage_guard.py`)
- **Time Window Slicing**: Strategies and indicators are strictly restricted to slice $[0..T]$. Any candle or price with $t > T$ is strictly hidden.
- **Monotonicity Verification**: All candle series must possess strictly non-decreasing timestamps. Backward time anomalies raise `DataLeakageDetectedError`.

### 2.4 Accounting & Execution Simulator (`libraries/domain/backtesting/strategy_adapter.py`)
- **High-Performance Replay**: Bypasses `asyncio.sleep` to execute thousands of bars per second deterministically.
- **Authoritative Financial Arithmetic**: All cash balances, margins, equity, gross P&L, fees, and net P&L are computed using `Decimal`.
- **Institutional Friction Models**:
  - **Adverse Slippage**: $Ask + \Delta$ on BUY orders, $Bid - \Delta$ on SELL orders.
  - **Commissions**: Continuous accounting of \$7.00 per standard lot (\$0.00007 per unit).
  - **Netting Execution**: Open positions are netted or reversed with realized P&L written to closed trade records.
- **Equity Curve Downsampling**: Downsamples time-series equity curves while strictly preserving starting balance, terminal balance, and all local extrema (peaks and troughs).

### 2.5 Quantitative Overfitting Safeguards (`libraries/domain/research/overfitting_guard.py`)
- Emits objective, statistical advisories on backtest completions:
  - `SMALL_SAMPLE_SIZE`: Total closed trades $< 30$.
  - `UNREALISTIC_PERFORMANCE`: Sharpe ratio $> 4.0$ or win rate $> 85\%$.
  - `SHORT_TEST_HORIZON`: Backtest duration $< 30$ days.
  - `HIGH_DRAWDOWN`: Max drawdown $> 25\%$.
  - `PARAMETER_DENSITY`: Tuned parameter count $\ge 6$.

---

## 3. Multi-Tenant Governance & Entitlements

- **Tenant Isolation**: All experiment records, curves, and trade ledgers are partitioned by `organization_id`. Any attempt by a tenant to query, inspect, or export another tenant's experiment returns HTTP 404.
- **Subscription Entitlements**:
  - `FREE`: 30 simulation days per day quota, 30 days retention.
  - `PRO`: 365 simulation days per day quota, 180 days retention.
  - `BUSINESS`: 1,825 simulation days per day quota, 365 days retention.
  - `ENTERPRISE`: Unlimited daily simulations, 730 days retention.
- **Granular RBAC**:
  - `RESEARCH_READ`: Discover strategies, list experiments, view equity curves and trade logs.
  - `RESEARCH_EXECUTE`: Initiate backtests and spend daily research simulation quota.
  - `RESEARCH_CANCEL`: Terminate running simulations.
  - `RESEARCH_EXPORT`: Download CSV and JSON datasets.

---

## 4. Database Persistence

Database schema managed via Alembic migration `0009_research_experiments.py`:
- `id`: VARCHAR(36) PK (`exp-<hash>`)
- `organization_id`: VARCHAR(36) NOT NULL (Indexed)
- `created_by`: VARCHAR(36) NULL
- `strategy_id`: VARCHAR(64) NOT NULL
- `strategy_version`: VARCHAR(16) NOT NULL
- `symbol`: VARCHAR(32) NOT NULL
- `timeframe`: VARCHAR(8) NOT NULL
- `start_date`: TIMESTAMPTZ NOT NULL
- `end_date`: TIMESTAMPTZ NOT NULL
- `initial_capital`: NUMERIC(18, 4) NOT NULL
- `parameters`: JSONB / JSON NOT NULL
- `simulation_config`: JSONB / JSON NOT NULL
- `status`: VARCHAR(24) NOT NULL (Indexed)
- `execution_time_seconds`: FLOAT DEFAULT 0.0
- `metrics`: JSONB / JSON NULL
- `equity_curve`: JSONB / JSON NULL
- `trades`: JSONB / JSON NULL
- `warnings`: JSONB / JSON NULL
- `error_message`: TEXT NULL
- `created_at`: TIMESTAMPTZ NOT NULL (Indexed)
- `completed_at`: TIMESTAMPTZ NULL
