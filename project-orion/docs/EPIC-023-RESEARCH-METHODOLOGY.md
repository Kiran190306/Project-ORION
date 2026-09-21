# Project ORION — EPIC-023 Quantitative Research Methodology Guide

## 1. Quantitative Research Philosophy

The ORION Strategy Lab is built on three institutional principles:
1. **Physical Realism over Theoretical Perfection**: Backtest results must include adverse bid-ask spreads, realistic latency slippage, and explicit broker commission structures.
2. **Determinism and Reproducibility**: Given the same strategy archetype, parameter vector, and historical candle sequence, the simulation must produce the exact same outcome down to the cent, eliminating stochastic ambiguity.
3. **Pessimistic Friction Modeling**: In real institutional execution, slippage is almost never favorable. The simulator systematically penalizes fill prices ($Ask + \Delta$ on BUY, $Bid - \Delta$ on SELL).

---

## 2. Quantitative Metric Formulations

### 2.1 Net Profit & Total Return %
$$\text{Net Profit} = \sum (\text{Realized P&L}) - \sum (\text{Commissions})$$
$$\text{Total Return \%} = \frac{\text{Net Profit}}{\text{Initial Capital}} \times 100$$

### 2.2 Sharpe Ratio
Calculated from closed trade returns scaled to annual frequency:
$$\text{Sharpe Ratio} = \frac{\bar{R} - R_f}{\sigma_R} \times \sqrt{252}$$
Where $R_f = 0.0$ is the standard zero-risk benchmark for intra-year delta-neutral quantitative testing.

### 2.3 Sortino Ratio
Calculated using downside semi-deviation (penalizing only negative returns):
$$\text{Sortino Ratio} = \frac{\bar{R} - R_f}{\sigma_{\text{downside}}} \times \sqrt{252}$$
$$\sigma_{\text{downside}} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (\min(0, R_i))^2}$$

### 2.4 Maximum Drawdown %
Calculated continuously at each bar close $t$:
$$DD_t = \frac{\text{PeakEquity}_t - \text{Equity}_t}{\text{PeakEquity}_t} \times 100$$
$$\text{Max Drawdown \%} = \max_{t} (DD_t)$$

### 2.5 Profit Factor & Expectancy
$$\text{Profit Factor} = \frac{\text{Gross Profit}}{|\text{Gross Loss}|}$$
$$\text{Expectancy} = (\text{Win Rate} \times \text{Avg Win}) - (\text{Loss Rate} \times \text{Avg Loss})$$

---

## 3. Best Practices for Backtesting Research

1. **Adequate Sample Size**: Always target at least 50 to 100 closed trades to establish statistical significance. Backtests with fewer than 30 trades suffer from high sampling variance and trigger `SMALL_SAMPLE_SIZE` advisories.
2. **Multi-Regime Testing**: Ensure the evaluation horizon spans at least 6 to 12 months, encompassing both trending, range-bound, and high-volatility macro regimes.
3. **Beware Curve Fitting**: A Sharpe ratio above 3.5 or a win rate above 80% is statistically suspect in liquid foreign exchange markets. Inspect strategy sensitivity across adjacent parameter values.
4. **Adverse Execution Friction**: Never test with zero spread or zero slippage. In liquid FX majors (e.g. EUR/USD), standard institutional spreads range from 1.0 to 2.0 pips, with 0.3 to 0.8 pips adverse slippage during active sessions.
