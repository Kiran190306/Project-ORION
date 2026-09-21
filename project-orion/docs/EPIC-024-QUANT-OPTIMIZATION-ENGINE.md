# EPIC-024: Quantitative Strategy Optimization Engine Architecture

## 1. Executive Summary

Project ORION's Quantitative Strategy Optimization Engine provides institutional hedge-fund caliber parameter exploration and fitness evaluation for forex trading strategies without look-ahead bias or overfitting.

The engine reuses the battle-tested, deterministic `StrategyBacktestAdapter` and domain-driven design (DDD) entities, ensuring complete fidelity to institutional microstructure modeling—including configurable adverse spread, execution slippage, round-turn commissions, and zero arbitrary user script execution.

---

## 2. Core Architecture & Components

```
+-------------------------------------------------------------+
|                OPTIMIZATION RUN ORCHESTRATION               |
+-------------------------------------------------------------+
                              |
       +----------------------+----------------------+
       |                                             |
       v                                             v
+-----------------------------+       +-----------------------------+
|   PARAMETER SPACE ENGINE    |       |     OPTIMIZATION ENGINE     |
| - StrategyRegistry bounds   |       | - Batch candle replay       |
| - Cartesian grid generation |       | - StrategyBacktestAdapter   |
| - Deterministic seed sampler|       | - Decimal accounting        |
| - Combinatorial safety caps |       | - Multi-objective fitness   |
+-----------------------------+       +-----------------------------+
                                                     |
       +----------------------+----------------------+
       |                      |                      |
       v                      v                      v
+--------------+      +--------------+      +-----------------------+
| SENSITIVITY  |      |   REGIME     |      |      COOPERATIVE      |
| 2D HEATMAP   |      |  ANALYZER    |      |  CANCELLATION TOKEN   |
+--------------+      +--------------+      +-----------------------+
```

### 2.1 Parameter Space Engine (`parameter_space_engine.py`)
- **Metadata Alignment**: Enforces parameter types (`int`, `float`, `choice`) and min/max boundaries as registered in `StrategyRegistry`.
- **Combinatorial Protection**:
  $$\text{Total Combinations} = \prod_{i=1}^{k} N_i$$
  Calculates the total hypervolume before execution. If the combination count exceeds tenant subscription limits (e.g. 50 on Free tier, 300 on Pro tier), raises `OptimizationCombinationLimitExceededError` before allocating memory or compute.
- **Cartesian Grid Search**: Generates every valid point across discrete step increments. Filters invalid parameter invariants (e.g., `fast_period < slow_period`).
- **Deterministic Seeded Random Search**: Replaces unconstrained brute force with deterministic pseudo-random sampling (`random.Random(seed)`), providing exact reproducibility across institutional research audits.

### 2.2 Optimization Engine (`optimization_engine.py`)
- **Friction-Aware Microstructure Modeling**:
  - Spread pips (default 1.5 pips)
  - Adverse slippage pips (default 0.5 pips)
  - Round-turn commission per lot (default \$7.00/lot)
- **Authoritative Decimal Financial Precision**:
  All balance and PnL calculations are computed using Python `Decimal` to eliminate binary floating-point rounding inaccuracies.
- **Cooperative Cancellation**:
  Accepts a `threading.Event` cancellation token. If cancelled by the user mid-sweep, halts further evaluations immediately and records status as `CANCELLED`.

---

## 3. Multi-Objective Fitness Objectives

The optimization engine supports ranking candidates across 8 institutional metrics:

| Objective | Metric | Description |
| :--- | :--- | :--- |
| `SHARPE_RATIO` | $S = \frac{\mu - r_f}{\sigma}$ | Annualized risk-adjusted excess return |
| `SORTINO_RATIO` | $S_{sortino} = \frac{\mu - r_f}{\sigma_d}$ | Downside deviation penalized risk-adjusted return |
| `CALMAR_RATIO` | $CR = \frac{\text{Annualized Return}}{\text{Max Drawdown}}$ | Recovery factor relative to peak-to-valley equity drop |
| `PROFIT_FACTOR` | $PF = \frac{\sum \text{Gross Profit}}{\sum \text{Gross Loss}}$ | Ratio of gross winnings to gross losses |
| `TOTAL_RETURN` | $R = \frac{E_{end} - E_0}{E_0}$ | Total percentage capital growth |
| `WIN_RATE` | $WR = \frac{N_{wins}}{N_{trades}}$ | Fraction of profitable closed trades |
| `MIN_DRAWDOWN` | $1.0 - \text{Max Drawdown}$ | Minimization of capital drawdown |
| `COMPOSITE` | Institutional multi-factor | $0.35 \cdot S + 0.25 \cdot S_{sortino} + 0.25 \cdot PF + 0.15 \cdot (1 - DD)$ |

---

## 4. Zero Arbitrary Code Execution Security Mandate

Under Project ORION's strict quantitative governance:
- **No `eval()` or `exec()`** calls exist anywhere in the codebase.
- **No dynamic Python code uploads** or user scripts are accepted.
- Strategy instantiation is strictly gated through `StrategyRegistry`, ensuring only vetted, compiled strategy archetypes execute within the backtesting harness.
