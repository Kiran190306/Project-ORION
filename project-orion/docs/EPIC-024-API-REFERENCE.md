# EPIC-024: Quantitative Strategy Optimization REST API Reference

All endpoints are hosted under `/api/v1/optimization` on the trading engine API router. Every route requires an authenticated tenant bearer token and enforces role-based access control (RBAC) and subscription quota limits.

---

## 1. Endpoints Overview

| Method | Path | Required Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/spaces/{strategy_id}` | `OPTIMIZATION_READ` | Get default parameter ranges and estimated combinations for an archetype |
| `POST` | `/run` | `OPTIMIZATION_EXECUTE` | Launch a Grid Search or Random Search optimization sweep |
| `POST` | `/walk-forward` | `OPTIMIZATION_EXECUTE` | Launch an institutional Walk-Forward Analysis (WFA) run |
| `GET` | `/jobs` | `OPTIMIZATION_READ` | List optimization and walk-forward jobs for the active tenant |
| `GET` | `/jobs/{job_id}` | `OPTIMIZATION_READ` | Get full details, candidates, and metrics for a specific job |
| `POST` | `/jobs/{job_id}/cancel` | `OPTIMIZATION_CANCEL` | Cooperatively signal cancellation for a running job |
| `GET` | `/jobs/{job_id}/heatmap` | `OPTIMIZATION_READ` | Get 2D sensitivity surface data for a completed job |
| `GET` | `/jobs/{job_id}/walk-forward` | `OPTIMIZATION_READ` | Get detailed In-Sample/Out-of-Sample window metrics for a WFA run |
| `GET` | `/jobs/{job_id}/regimes` | `OPTIMIZATION_READ` | Get market regime performance breakdown for a completed job |
| `GET` | `/jobs/{job_id}/export` | `OPTIMIZATION_EXPORT` | Export candidate leaderboard to CSV or JSON format |

---

## 2. Request & Response Schemas

### `POST /api/v1/optimization/run`
Launch a parameter optimization sweep.

#### Request Body:
```json
{
  "strategy_id": "TrendFollowing",
  "symbol": "EUR/USD",
  "timeframe": "H1",
  "start_date": "2025-01-01T00:00:00Z",
  "end_date": "2025-01-31T00:00:00Z",
  "initial_capital": 10000.0,
  "optimization_type": "GRID_SEARCH",
  "fitness_objective": "SHARPE_RATIO",
  "parameter_space": {
    "strategy_id": "TrendFollowing",
    "ranges": [
      {
        "name": "fast_period",
        "param_type": "int",
        "min_value": 5,
        "max_value": 25,
        "step": 5
      },
      {
        "name": "slow_period",
        "param_type": "int",
        "min_value": 30,
        "max_value": 90,
        "step": 15
      }
    ]
  },
  "max_combinations": 100,
  "spread_pips": 1.5,
  "slippage_pips": 0.5,
  "commission": 7.0
}
```

#### Response (201 Created):
```json
{
  "id": "opt-9471abef1234",
  "organization_id": "org_institutional_alpha",
  "strategy_id": "TrendFollowing",
  "symbol": "EUR/USD",
  "timeframe": "H1",
  "status": "COMPLETED",
  "total_combinations": 25,
  "completed_combinations": 25,
  "execution_time_seconds": 1.45,
  "best_parameters": {
    "fast_period": 10,
    "slow_period": 45
  },
  "best_metrics": {
    "sharpe_ratio": 2.15,
    "sortino_ratio": 3.12,
    "total_return": 0.085,
    "max_drawdown": 0.048,
    "win_rate": 0.65,
    "profit_factor": 3.42,
    "total_trades": 20,
    "net_pnl": 850.0
  },
  "top_candidates": [
    {
      "rank": 1,
      "parameters": { "fast_period": 10, "slow_period": 45 },
      "fitness_score": 2.15,
      "total_return": 0.085,
      "sharpe_ratio": 2.15,
      "sortino_ratio": 3.12,
      "calmar_ratio": 1.77,
      "max_drawdown": 0.048,
      "win_rate": 0.65,
      "profit_factor": 3.42,
      "total_trades": 20,
      "net_pnl": 850.0
    }
  ]
}
```

---

## 3. Tenant Isolation & Security Boundary

- **Multi-Tenant Isolation**: Queries strictly filter by `organization_id`. Any request attempting to access a job belonging to a foreign tenant yields an immediate `404 Not Found`, preventing tenant enumeration attacks.
- **Quota Guards**:
  - `DailyOptimizationQuotaExceededError`: Raised when daily optimization sweep count exceeds subscription plan limits.
  - `OptimizationCombinationLimitExceededError`: Raised when requested parameter combinations exceed subscription tier hypervolume limits.
