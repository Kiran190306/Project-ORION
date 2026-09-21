# EPIC-024: Walk-Forward Analysis (WFA) & Out-of-Sample Research Engine

## 1. Quantitative Methodology Overview

Overfitting (curve-fitting) is the primary failure mode of automated trading strategies. Walk-Forward Analysis (WFA) overcomes curve-fitting by evaluating a strategy on chronologically unseen, out-of-sample data following optimization on preceding in-sample data.

Project ORION implements chronological, rolling and anchored walk-forward window partitioning with zero look-ahead bias and strict In-Sample / Out-of-Sample (IS/OOS) separation.

---

## 2. Walk-Forward Window Partitioning

```
Total Historical Dataset
[========================================================================================]

Window 1:
[-------- In-Sample 1 (Optimization) --------][-- Out-of-Sample 1 (Forward Replay) --]

Window 2:
         [-------- In-Sample 2 (Optimization) --------][-- Out-of-Sample 2 (Forward) --]

Window 3:
                  [-------- In-Sample 3 (Optimization) --------][-- Out-of-Sample 3 --]
```

### Partitioning Rules:
- **Rolling Windows**: Fixed duration in-sample window advances forward by the length of the out-of-sample window.
- **Anchored (Expanding) Windows**: In-sample window start remains anchored at $t_0$, expanding with each iteration to incorporate all accumulated history.
- **Chronological Non-Overlap**:
  $$\text{IS}_{\text{end}} \le \text{OOS}_{\text{start}}$$
  Guarantees that no future bar data leaks into the parameter selection process.

---

## 3. Walk-Forward Efficiency (WFE) Calculation

The Walk-Forward Efficiency metric measures the degree to which optimized in-sample returns carry over to out-of-sample performance:

$$\text{Normalized Return}_{\text{IS}} = \frac{R_{\text{IS}}}{N_{\text{IS\_bars}}}$$

$$\text{Normalized Return}_{\text{OOS}} = \frac{R_{\text{OOS}}}{N_{\text{OOS\_bars}}}$$

$$\text{WFE} = \left( \frac{\text{Normalized Return}_{\text{OOS}}}{\text{Normalized Return}_{\text{IS}}} \right) \times 100\%$$

### Robustness Verdict Classification:

| Metric Criteria | Verdict | Description |
| :--- | :--- | :--- |
| $\text{Mean WFE} \ge 60\%$ and $\text{Mean OOS Sharpe} \ge 1.0$ | **`ROBUST`** | Strong forward predictive edge; minimal curve-fitting. |
| $40\% \le \text{Mean WFE} < 60\%$ | **`MODERATE`** | Acceptable forward stability, monitor under regime shifts. |
| $\text{Mean WFE} < 40\%$ or Cumulative OOS Return $< 0$ | **`OVERFITTED`** | Severe curve-fitting; strategy relies on historical noise. |
| $R_{\text{IS}} \le 0$ across windows | **`UNDEFINED`** | In-sample performance insufficient to evaluate efficiency. |

---

## 4. Concatenated Out-of-Sample Equity Trajectory

Unlike standard backtests that simulate an equity curve on in-sample fitted data, the Walk-Forward Engine concatenates exclusively the out-of-sample forward trading segments:

$$E_{\text{OOS}}(t) = E_{\text{window\_1}}(t) \frown E_{\text{window\_2}}(t) \frown \dots \frown E_{\text{window\_n}}(t)$$

This generates the true realistic performance curve that an institutional investor would have experienced as the strategy model was periodically re-optimized over historical time.
