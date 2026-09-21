# EPIC-024: Market Regime Classification & Parameter Stability Surface Analyzer

## 1. Market Regime Classification Engine (`regime_analyzer.py`)

Financial time series exhibit dynamic structural breaks. A strategy that is profitable in strong trends may suffer catastrophic drawdown during high-volatility sideways chop.

The Regime Analyzer segments historical price action into four institutional regimes:

1. **`TRENDING_BULL`**: Close price strictly above Simple Moving Average ($\text{Close} > \text{SMA}_{50}$) with ATR above median ($\text{ATR} \ge \text{Median}(\text{ATR})$).
2. **`TRENDING_BEAR`**: Close price strictly below Simple Moving Average ($\text{Close} < \text{SMA}_{50}$) with ATR above median.
3. **`RANGING_LOW_VOL`**: Price oscillating around SMA with below-median volatility ($\text{ATR} < \text{Median}(\text{ATR})$).
4. **`HIGH_VOLATILITY_CHOP`**: High ATR expansion with rapid oscillations around the moving average.

### Performance Attribution by Regime:
For each regime, the analyzer partitions all closed trade records and computes:
- Total Trade Count ($N$)
- Win Rate (%)
- Profit Factor ($PF$)
- Total Net Return (%)
- Regime Sharpe Ratio ($S$)
- Max Drawdown (%)

---

## 2. Parameter Stability & Cliff Detection (`parameter_stability_analyzer.py`)

An optimal parameter set that lies on a narrow spike ("parameter needle") is dangerous in live trading because small changes in market conditions will cause performance to plummet. Strategies should occupy a wide, stable plateau.

```
Robust Plateau:                        Fragile Cliff / Spike:
      __________                                  /\
     /          \                                /  \
____/   OPTIMAL  \____                     _____/OPT \_____
```

### Plateau Stability Metric:
For the candidate with the highest fitness score $P^* = (p_1^*, p_2^*, \dots, p_k^*)$, the analyzer evaluates all 1-step grid neighbors:

$$\mathcal{N}(P^*) = \{ P \in \text{Grid} \mid \text{dist}(P, P^*) = 1 \text{ step} \}$$

$$\Delta_{\text{drop}}(P) = \max\left(0, \frac{\text{Fitness}(P^*) - \text{Fitness}(P)}{\text{Fitness}(P^*)}\right)$$

$$\text{Plateau Score} = 100 \times \left( 1.0 - \text{Mean}(\Delta_{\text{drop}}) \right)$$

### Parameter Cliff Alert:
A parameter cliff is flagged (`is_cliff = True`) if:
1. Any adjacent neighbor experiences a performance degradation $> 40\%$, OR
2. An adjacent neighbor's Sharpe ratio flips negative while the optimal candidate is positive.

---

## 3. 2D Sensitivity Heatmap Visualization

The engine produces an interactive 2D surface matrix for any two continuous parameters $(x, y)$:
- Automatically scales color gradients from low fitness (rose) to median (yellow) to high fitness (emerald).
- Allows quantitative researchers to immediately visually identify broad stable parameter zones versus steep cliffs.
