# Risk Analytics Domain

> **EPIC-014 · Sprint-4 · v0.14.0-alpha.4**

This document describes the **Risk Analytics** sub-package located at
`libraries/domain/risk/analytics/`. It is the quantitative analytics
foundation that powers the Risk Management Engine (EPIC-007) and the
broader risk domain. It also includes the **Stress Analysis Engine**
introduced in Sprint-4.

## 1. Architecture

The Risk Analytics sub-package is a **pure-domain** layer. It contains no
I/O, no infrastructure code, and no broker integrations. Every engine is
exposed through a **runtime-checkable Protocol** (port), and every result
is an **immutable frozen dataclass**. This keeps the domain testable and
composable with any infrastructure adapter.

```
libraries/domain/risk/analytics/
├── __init__.py       # public exports
├── models.py         # immutable result/model dataclasses + enums
├── interfaces.py     # runtime-checkable Protocol ports
├── validation.py     # shared input validators
├── var.py            # Value at Risk engine
├── cvar.py           # Conditional VaR (expected shortfall) engine
├── kelly.py          # Kelly Criterion engine
├── ratios.py         # Sharpe / Sortino / Calmar engine
├── drawdown.py       # max & rolling drawdown engine
├── volatility.py     # historical / EWMA volatility engine
├── correlation.py    # correlation matrix & beta engine
├── exposure.py       # exposure / allocation / risk budget engine
└── stress.py         # Stress Analysis Engine  (Sprint-4)
```

### Design principles

- **Protocol-based ports** — each engine implements a `@runtime_checkable`
  `Protocol` (e.g. `ValueAtRiskPort`, `StressTestPort`).
- **Immutable dataclasses** — `@dataclass(frozen=True, slots=True)`.
- **`Decimal` for financial values** — currency amounts use `Decimal`.
- **`float` for ratios/percentages** — returns, ratios, weights, shocks.
- **Async-first** — all engine operations are `async`, even when they are
  pure CPU work, to conform to the async domain convention.
- **Timezone-aware timestamps** — all timestamps default to UTC.

## 2. Analytics engines

The package provides the following engines (all confirmed complete):

| Engine | Port | Result model |
| --- | --- | --- |
| `ValueAtRiskEngine` | `ValueAtRiskPort` | `VaRResult` |
| `ConditionalVarEngine` | `ConditionalVarPort` | `CvaRResult` |
| `KellyCriterionEngine` | `KellyCriterionPort` | `KellyResult` |
| `PerformanceMetricsEngine` | `PerformanceMetricsPort` | `PerformanceMetrics` |
| `DrawdownEngine` | `DrawdownPort` | `DrawdownResult` |
| `VolatilityEngine` | `VolatilityPort` | `VolatilityMetrics` |
| `CorrelationEngine` | `CorrelationPort` | `CorrelationResult` |
| `ExposureEngine` | `ExposurePort` | `ExposureMetrics` |
| `ConcentrationEngine` | `ConcentrationPort` | `ConcentrationMetrics` |
| `StressTestEngine` | `StressTestPort` | `StressTestResult` / `StressTestSummary` |

## 3. Stress Analysis Engine

The `StressTestEngine` (Sprint-4) provides deterministic portfolio stress
testing. It implements the `StressTestPort` protocol.

### Methods

| Method | Purpose |
| --- | --- |
| `apply_scenario` | Apply a named user-defined `Scenario` to symbols. |
| `run_historical_stress` | Replay worst historical drawdown windows. |
| `apply_portfolio_shock` | Apply a simultaneous uniform shock to all symbols, scaled by volatility. |
| `simulate_market_crash` | Simulate a crash followed by a mean-reverting recovery path. |
| `apply_volatility_shock` | Scale historical volatility of a returns series. |

### Models

- `StressTestType` — enum classifying scenario / historical / portfolio
  shock / market crash / volatility shock.
- `Scenario` — `name`, `shock_factors` (symbol → fraction), optional
  `volatility_multiplier`.
- `StressTestResult` — per-run result with `portfolio_value`,
  `portfolio_return`, and `symbol_returns`.
- `StressTestSummary` — aggregated summary across a set of runs with
  `worst_case_return`, `best_case_return`, `average_return`, and
  `portfolio_shock_pct`.

### Example

```python
from decimal import Decimal
from libraries.domain.risk.analytics import (
    Scenario,
    StressTestEngine,
)

engine = StressTestEngine()

scenario = Scenario(
    name="2008-style crisis",
    shock_factors={"EURUSD": -0.15, "GBPUSD": -0.10},
)

# Await within an async context
result = await engine.apply_scenario(
    returns_by_symbol={"EURUSD": [...], "GBPUSD": [...]},
    scenario=scenario,
    portfolio_value=Decimal("1000000"),
)
print(result.portfolio_loss_pct)  # e.g. 12.5
```

## 4. Validation layer

Shared validators in `validation.py` are reused across all engines:

- `validate_returns(returns, min_length=2)` — validates a returns series.
- `validate_confidence_level(value)` — enforces `0 < value < 1`.
- `validate_probability(value)` — enforces `0 <= value <= 1`.
- `validate_horizon(days)` — enforces a positive integer.
- `validate_window(window, data_length)` — validates a rolling window.
- `validate_positive_float(value, field)` — enforces a strictly positive
  float.

All validators raise typed exceptions deriving from `RiskAnalyticsError`
(e.g. `InvalidReturnsError`, `InsufficientDataError`,
`InvalidConfidenceLevelError`, `InvalidValueError`).

## 5. Extension guide

To add a new analytics engine:

1. **Model** — add the result dataclass (frozen, slots) to `models.py`.
2. **Port** — add a `@runtime_checkable` Protocol to `interfaces.py`.
3. **Engine** — create `engine.py` implementing the port. Use `async def`
   methods, `Decimal` for money, `float` for ratios.
4. **Validate** — reuse shared validators from `validation.py`.
5. **Export** — add the model, port, and engine to `__init__.py` and
   `__all__`.
6. **Test** — add unit tests under
   `tests/unit/domain/risk/analytics/`.
7. **Document** — extend this document.

## 6. Quality gates

- `ruff check libraries/domain/risk` — 0 issues
- `mypy --strict libraries/domain/risk` — 0 issues
- `pytest tests/unit/domain/risk -v` — all pass

The Risk Management Engine (EPIC-007) is **frozen** and is not modified
by this package; the analytics layer extends it via composition.
