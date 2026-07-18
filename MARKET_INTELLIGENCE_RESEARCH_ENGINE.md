# Market Intelligence Research Engine (MIRE)
## Phase 4 Architecture Specification

**Document Version:** 1.0  
**Date:** July 2026  
**Classification:** Confidential  
**Status:** Draft  
**Predecessors:** ARCHITECTURE.md (SRS), TRADING_CORE_ARCHITECTURE.md (Core Trading Engine), TRADING_DECISION_INTELLIGENCE_ENGINE.md (TDIE)

---

## Table of Contents

1. [Market Structure Intelligence](#1-market-structure-intelligence)
2. [Liquidity Intelligence](#2-liquidity-intelligence)
3. [Institutional Price Delivery Concepts](#3-institutional-price-delivery-concepts)
4. [Market Regime Behaviour](#4-market-regime-behaviour)
5. [Session Intelligence](#5-session-intelligence)
6. [Volatility Intelligence](#6-volatility-intelligence)
7. [Market Context Scoring](#7-market-context-scoring)
8. [Explainability](#8-explainability)
9. [Historical Validation Framework](#9-historical-validation-framework)
10. [Architecture Diagrams](#10-architecture-diagrams)
11. [Extension Points](#11-extension-points)
12. [Risks and Assumptions](#12-risks-and-assumptions)

---

## 1. Market Structure Intelligence

### 1.1 Overview
Market Structure Intelligence identifies and describes the structural framework of price action, providing the foundation for all subsequent market analysis.

### 1.2 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              Market Structure Intelligence Engine                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Swing      │  │  Internal    │  │  External    │         │
│  │  Structure   │  │  Structure   │  │  Structure   │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
│         └─────────────────┴─────────────────┘                  │
│                           ↓                                      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              Structure Aggregator                        │      │
│  │  - HH/HL/LH/LL detection                              │      │
│  │  - Break of structure                                  │      │
│  │  - Change of character                                 │      │
│  └──────────────────────┬───────────────────────────────┘      │
│                           ↓                                      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              Structure Classifier                      │      │
│  │  - Trend continuation                                  │      │
│  │  - Trend transition                                    │      │
│  │  - Consolidation/Expansion/Contraction                │      │
│  └──────────────────────┬───────────────────────────────┘      │
│                           ↓                                      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              Structure Publisher                        │      │
│  │  - Structure events                                    │      │
│  │  - State persistence                                   │      │
│  │  - Confidence reporting                                │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Structure Modules

#### 1.3.1 Swing Structure

**Definition:**
Swing structure identifies the major price pivots that define the overall market direction. Swings are typically identified on higher timeframes (H4, D1, W1) and represent significant turning points in price action.

**Required Inputs:**
- OHLCV data (H4, D1, W1 timeframes)
- Swing detection parameters:
  - Minimum swing size (pips or percentage)
  - Minimum swing duration (candles)
  - Swing detection method (fractal, zigzag, swing high/low)
- Current price

**Detection Algorithm:**
```
1. Identify potential swing highs:
   - Price is higher than N candles before and after
   - Minimum swing size requirement met
   - Minimum duration requirement met

2. Identify potential swing lows:
   - Price is lower than N candles before and after
   - Minimum swing size requirement met
   - Minimum duration requirement met

3. Validate swings:
   - Confirm swing is not broken by subsequent price
   - Check swing significance (volume, volatility context)

4. Link swings:
   - Connect swing highs to swing lows
   - Identify swing sequences
   - Calculate swing relationships

5. Classify swing structure:
   - Higher Highs (HH): Each swing high higher than previous
   - Higher Lows (HL): Each swing low higher than previous
   - Lower Highs (LH): Each swing high lower than previous
   - Lower Lows (LL): Each swing low lower than previous
```

**Confidence Estimation:**
```
swing_confidence = (size_score × 0.4) + (duration_score × 0.3) + (volume_score × 0.2) + (clarity_score × 0.1)

where:
- size_score: swing size relative to average (0-1)
- duration_score: swing duration relative to average (0-1)
- volume_score: volume at swing point relative to average (0-1)
- clarity_score: how clearly defined the swing is (0-1)
```

**Edge Cases:**
- **Flat market:** No significant swings detected → return "No Structure"
- **Choppy market:** Many small swings → filter by minimum size/duration
- **Gap at swing:** Price gap at swing point → mark as "Gap Swing"
- **News event swing:** Spike due to news → mark as "Event-Driven"

**Invalidation Rules:**
- Swing high invalidated when price closes above it
- Swing low invalidated when price closes below it
- Invalidation threshold: close beyond swing level (not just wick)
- Time-based invalidation: if not confirmed within X candles

**Historical Validation Approach:**
- Backtest swing detection on historical data
- Compare detected swings with manually labeled swings
- Measure precision/recall of swing detection
- Validate that swing points align with significant turning points
- Test robustness across different market conditions

---

#### 1.3.2 Internal Structure

**Definition:**
Internal structure refers to the smaller-scale price movements within the broader swing structure. Typically analyzed on lower timeframes (M15, H1) to identify the immediate market structure.

**Required Inputs:**
- OHLCV data (M15, H1 timeframes)
- Swing structure context (from 1.3.1)
- Internal structure parameters:
  - Pivot lookback period (default: 5 candles)
  - Minimum internal move size
  - Internal structure timeframe

**Detection Algorithm:**
```
1. Identify internal pivot points:
   - Local highs/low within swing structure
   - Use shorter lookback than swing detection
   - Filter by minimum move size

2. Classify internal structure:
   - Within uptrend: HH/HL or LH/LL patterns
   - Within downtrend: LH/LL or HH/HL patterns
   - Within range: alternating highs/lows

3. Validate internal structure:
   - Ensure internal structure aligns with swing direction
   - Check for structure breaks
   - Identify structure weakening/strengthening

4. Detect internal structure breaks:
   - Break of internal swing high/low
   - Change of internal structure pattern
   - Early warning of potential swing change
```

**Confidence Estimation:**
```
internal_confidence = (alignment_score × 0.4) + (clarity_score × 0.3) + (consistency_score × 0.3)

where:
- alignment_score: alignment with swing structure (0-1)
- clarity_score: how clearly defined internal pivots are (0-1)
- consistency_score: consistency of internal pattern (0-1)
```

**Edge Cases:**
- **No internal structure:** Price moves in straight line → return "No Internal Structure"
- **Conflicting internal structure:** Internal structure conflicts with swing → flag for review
- **Rapid internal changes:** Many structure changes in short time → mark as "Choppy"

**Invalidation Rules:**
- Internal structure invalidated more frequently than swing structure
- Invalidation on close beyond internal pivot
- Time-based invalidation: if not confirmed within shorter timeframe

**Historical Validation Approach:**
- Validate internal structure predicts swing changes
- Measure lead time of internal structure breaks before swing breaks
- Test internal structure reliability across different volatility regimes

---

#### 1.3.3 External Structure

**Definition:**
External structure refers to the broader market context beyond the immediate instrument, including correlated instruments, index movements, and macro-level structure.

**Required Inputs:**
- OHLCV data for correlated instruments
- Index data (if applicable)
- Currency index data
- Correlation matrix
- External structure parameters:
  - Correlation threshold
  - Index weight
  - External timeframe

**Detection Algorithm:**
```
1. Identify correlated instrument structure:
   - Detect swing structure on correlated pairs
   - Detect swing structure on currency index
   - Detect swing structure on broader index

2. Classify external structure:
   - Correlated structures: aligned or diverging
   - Index structure: bullish or bearish
   - Currency strength: strong or weak

3. Compare with target instrument structure:
   - Is target structure aligned with external structure?
   - Is target structure leading or lagging?
   - Is there divergence developing?

4. Generate external structure assessment:
   - Alignment score with external structure
   - Divergence warnings
   - Confluence/conflict indicators
```

**Confidence Estimation:**
```
external_confidence = (correlation_score × 0.4) + (alignment_score × 0.3) + (consistency_score × 0.3)

where:
- correlation_score: strength of correlation (0-1)
- alignment_score: alignment of structures (0-1)
- consistency_score: consistency across external sources (0-1)
```

**Edge Cases:**
- **Low correlation:** No meaningful external structure → return "No External Context"
- **Divergent external signals:** External sources disagree → flag for review
- **Changing correlations:** Correlations shifting over time → use rolling correlation

**Invalidation Rules:**
- External structure invalidated when correlated instruments break structure
- Time-based invalidation: external structure has shorter validity
- Correlation threshold: invalidate if correlation drops below threshold

**Historical Validation Approach:**
- Validate external structure leads target structure
- Measure predictive value of external alignment
- Test correlation stability over time
- Validate divergence warnings precede reversals

---

#### 1.3.4 Higher Highs (HH)

**Definition:**
A higher high occurs when a swing high exceeds the previous swing high, indicating bullish momentum continuation.

**Required Inputs:**
- Swing structure data
- Current price
- Previous swing high level

**Detection Algorithm:**
```
1. Identify new swing high candidate
2. Compare with previous swing high:
   - If new > previous: Higher High confirmed
   - If new <= previous: Not a Higher High
3. Validate HH significance:
   - Is the difference meaningful (above minimum threshold)?
   - Is volume supportive?
   - Is time since previous HH reasonable?
4. Classify HH strength:
   - Strong HH: significant exceedance with volume
   - Weak HH: marginal exceedance with low volume
```

**Confidence Estimation:**
```
hh_confidence = (exceedance_score × 0.5) + (volume_score × 0.3) + (timing_score × 0.2)

where:
- exceedance_score: how much higher than previous HH (normalized 0-1)
- volume_score: volume at new HH relative to average (0-1)
- timing_score: time since previous HH (not too fast/slow) (0-1)
```

**Edge Cases:**
- **Marginal HH:** Only slightly higher → mark as "Weak HH"
- **HH with no HL:** HH without corresponding HL → potential weakness
- **HH after long consolidation:** First HH after range → mark as "Breakout HH"

**Invalidation Rules:**
- HH invalidated when price closes below previous HH
- Time-based invalidation: if not confirmed within X candles
- Volume-based invalidation: if volume too low

**Historical Validation Approach:**
- Validate HH leads to continuation more often than reversal
- Measure success rate of HH as continuation signal
- Test HH significance thresholds

---

#### 1.3.5 Higher Lows (HL)

**Definition:**
A higher low occurs when a swing low is higher than the previous swing low, indicating buying pressure and potential trend continuation.

**Required Inputs:**
- Swing structure data
- Current price
- Previous swing low level

**Detection Algorithm:**
```
1. Identify new swing low candidate
2. Compare with previous swing low:
   - If new > previous: Higher Low confirmed
   - If new <= previous: Not a Higher Low
3. Validate HL significance:
   - Is the difference meaningful?
   - Is buying pressure evident (volume, candle patterns)?
   - Is HL at support level?
4. Classify HL strength:
   - Strong HL: significant elevation with support
   - Weak HL: marginal elevation
```

**Confidence Estimation:**
```
hl_confidence = (elevation_score × 0.5) + (support_score × 0.3) + (buying_pressure_score × 0.2)

where:
- elevation_score: how much higher than previous HL (normalized 0-1)
- support_score: proximity to known support level (0-1)
- buying_pressure_score: evidence of buying pressure (0-1)
```

**Edge Cases:**
- **Marginal HL:** Only slightly higher → mark as "Weak HL"
- **HL with no HH:** HL without corresponding HH → potential weakness
- **HL at key support:** HL at major support → mark as "Key Support HL"

**Invalidation Rules:**
- HL invalidated when price closes below previous HL
- Time-based invalidation: if not confirmed within X candles
- Support-based invalidation: if support broken

**Historical Validation Approach:**
- Validate HL leads to trend continuation
- Measure success rate of HL as support signal
- Test HL at key support levels

---

#### 1.3.6 Lower Highs (LH)

**Definition:**
A lower high occurs when a swing high is lower than the previous swing high, indicating selling pressure and potential trend reversal or weakening.

**Required Inputs:**
- Swing structure data
- Current price
- Previous swing high level

**Detection Algorithm:**
```
1. Identify new swing high candidate
2. Compare with previous swing high:
   - If new < previous: Lower High confirmed
   - If new >= previous: Not a Lower High
3. Validate LH significance:
   - Is the difference meaningful?
   - Is selling pressure evident?
   - Is LH at resistance level?
4. Classify LH strength:
   - Strong LH: significant decline with resistance
   - Weak LH: marginal decline
```

**Confidence Estimation:**
```
lh_confidence = (decline_score × 0.5) + (resistance_score × 0.3) + (selling_pressure_score × 0.2)

where:
- decline_score: how much lower than previous LH (normalized 0-1)
- resistance_score: proximity to known resistance level (0-1)
- selling_pressure_score: evidence of selling pressure (0-1)
```

**Edge Cases:**
- **Marginal LH:** Only slightly lower → mark as "Weak LH"
- **LH with no LL:** LH without corresponding LL → potential weakness
- **LH at key resistance:** LH at major resistance → mark as "Key Resistance LH"

**Invalidation Rules:**
- LH invalidated when price closes above previous LH
- Time-based invalidation: if not confirmed within X candles
- Resistance-based invalidation: if resistance broken

**Historical Validation Approach:**
- Validate LH leads to reversal or continuation
- Measure success rate of LH as reversal signal
- Test LH at key resistance levels

---

#### 1.3.7 Lower Lows (LL)

**Definition:**
A lower low occurs when a swing low is lower than the previous swing low, indicating bearish momentum continuation.

**Required Inputs:**
- Swing structure data
- Current price
- Previous swing low level

**Detection Algorithm:**
```
1. Identify new swing low candidate
2. Compare with previous swing low:
   - If new < previous: Lower Low confirmed
   - If new >= previous: Not a Lower Low
3. Validate LL significance:
   - Is the difference meaningful?
   - Is selling pressure evident?
   - Is LL at support level?
4. Classify LL strength:
   - Strong LL: significant decline with support break
   - Weak LL: marginal decline
```

**Confidence Estimation:**
```
ll_confidence = (decline_score × 0.5) + (support_break_score × 0.3) + (selling_pressure_score × 0.2)

where:
- decline_score: how much lower than previous LL (normalized 0-1)
- support_break_score: significance of support break (0-1)
- selling_pressure_score: evidence of selling pressure (0-1)
```

**Edge Cases:**
- **Marginal LL:** Only slightly lower → mark as "Weak LL"
- **LL with no LH:** LL without corresponding LH → potential weakness
- **LL at key support:** LL breaking major support → mark as "Key Support Break LL"

**Invalidation Rules:**
- LL invalidated when price closes above previous LL
- Time-based invalidation: if not confirmed within X candles
- Support-based invalidation: if support holds

**Historical Validation Approach:**
- Validate LL leads to continuation more often than reversal
- Measure success rate of LL as continuation signal
- Test LL at key support breaks

---

#### 1.3.8 Break of Structure (BOS)

**Definition:**
A break of structure occurs when price moves beyond a significant swing point, signaling potential trend continuation or reversal.

**Required Inputs:**
- Swing structure data
- Current price
- Structure level to break (swing high or low)
- Break confirmation parameters

**Detection Algorithm:**
```
1. Identify structure level to break:
   - Bullish BOS: break of swing high
   - Bearish BOS: break of swing low

2. Detect break attempt:
   - Price moves beyond structure level
   - Wick break vs close break
   - Break magnitude

3. Validate break:
   - Is break confirmed on close?
   - Is volume supportive?
   - Is break meaningful (not just wick)?
   - Is there retest?

4. Classify BOS type:
   - Confirmed BOS: close beyond level with volume
   - Failed BOS: broke but couldn't hold
   - Retested BOS: broke, retested, held
   - Wick BOS: only wick broke, close didn't
```

**Confidence Estimation:**
```
bos_confidence = (close_confirmation × 0.4) + (volume_score × 0.3) + (break_magnitude × 0.2) + (retest_score × 0.1)

where:
- close_confirmation: close beyond level (1.0) vs wick only (0.3)
- volume_score: volume at break relative to average (0-1)
- break_magnitude: how far beyond level (normalized 0-1)
- retest_score: if retest occurred and held (1.0) or not (0.5)
```

**Edge Cases:**
- **Wick BOS:** Only wick broke → mark as "Unconfirmed BOS"
- **Failed BOS:** Broke but couldn't hold → mark as "Failed BOS"
- **Gap BOS:** Gap beyond structure level → mark as "Gap BOS"
- **News BOS:** Break due to news event → mark as "Event-Driven BOS"

**Invalidation Rules:**
- BOS invalidated when price moves back through structure level
- Time-based invalidation: if not confirmed within X candles
- Volume-based invalidation: if volume too low

**Historical Validation Approach:**
- Validate BOS leads to continuation
- Measure success rate of BOS as continuation signal
- Test different BOS confirmation methods (close vs wick)
- Validate retest significance

---

#### 1.3.9 Change of Character (CHoCH)

**Definition:**
Change of Character occurs when market structure shifts from bullish to bearish or vice versa, typically indicated by a break of a significant swing point in the opposite direction of the current trend.

**Required Inputs:**
- Current market structure (HH/HL or LH/LL)
- Swing structure data
- Current price
- CHoCH detection parameters

**Detection Algorithm:**
```
1. Determine current structure:
   - Bullish structure: HH + HL pattern
   - Bearish structure: LH + LL pattern

2. Detect potential CHoCH:
   - In bullish structure: break of significant swing low
   - In bearish structure: break of significant swing high

3. Validate CHoCH:
   - Is the broken swing point significant?
   - Is break confirmed on close?
   - Is there follow-through?
   - Is volume supportive?

4. Classify CHoCH type:
   - Bullish CHoCH: bearish to bullish shift
   - Bearish CHoCH: bullish to bearish shift
   - Potential CHoCH: break not yet confirmed
   - Failed CHoCH: break but structure reverted
```

**Confidence Estimation:**
```
choch_confidence = (structure_significance × 0.4) + (break_confirmation × 0.3) + (follow_through × 0.2) + (volume_score × 0.1)

where:
- structure_significance: significance of broken swing point (0-1)
- break_confirmation: close confirmation (1.0) vs wick (0.3)
- follow_through: price continued in new direction (0-1)
- volume_score: volume at break relative to average (0-1)
```

**Edge Cases:**
- **Premature CHoCH:** Break of minor swing → mark as "Potential CHoCH"
- **Failed CHoCH:** Structure reverted after break → mark as "Failed CHoCH"
- **CHoCH in range:** Structure change within range → mark as "Range CHoCH"
- **Multiple CHoCH:** Rapid structure changes → mark as "Choppy Structure"

**Invalidation Rules:**
- CHoCH invalidated when structure reverts to previous pattern
- Time-based invalidation: if not confirmed within X candles
- Follow-through required: price must continue in new direction

**Historical Validation Approach:**
- Validate CHoCH predicts trend change
- Measure success rate of CHoCH as reversal signal
- Test CHoCH significance thresholds
- Validate follow-through requirements

---

#### 1.3.10 Market Structure Shift

**Definition:**
Market structure shift refers to a broader change in market behavior, encompassing multiple structural changes and indicating a fundamental shift in market dynamics.

**Required Inputs:**
- Market structure history
- Multiple CHoCH events
- Structure shift parameters:
  - Minimum number of structural changes
  - Time window for shift detection
  - Shift significance threshold

**Detection Algorithm:**
```
1. Monitor structural changes over time window:
   - Count CHoCH events
   - Count BOS events
   - Track structure pattern changes

2. Detect structure shift:
   - If multiple structural changes in short time
   - If structure pattern fundamentally changes
   - If volatility regime changes with structure

3. Validate structure shift:
   - Is shift significant (not just noise)?
   - Is shift confirmed across timeframes?
   - Is shift supported by volume/volatility?

4. Classify shift type:
   - Trend to Range: trending structure becomes ranging
   - Range to Trend: ranging structure becomes trending
   - Volatility Expansion: structure shift with volatility increase
   - Volatility Contraction: structure shift with volatility decrease
```

**Confidence Estimation:**
```
shift_confidence = (change_count × 0.3) + (pattern_change × 0.3) + (multi_tf_confirmation × 0.2) + (volatility_support × 0.2)

where:
- change_count: number of structural changes (normalized 0-1)
- pattern_change: significance of pattern change (0-1)
- multi_tf_confirmation: confirmation across timeframes (0-1)
- volatility_support: volatility change supports shift (0-1)
```

**Edge Cases:**
- **Gradual shift:** Slow structural evolution → mark as "Gradual Shift"
- **Sudden shift:** Rapid structural change → mark as "Sudden Shift"
- **False shift:** Temporary structural change → mark as "Failed Shift"
- **Partial shift:** Only some aspects change → mark as "Partial Shift"

**Invalidation Rules:**
- Structure shift invalidated if structure reverts
- Time-based invalidation: if not sustained over longer period
- Multi-timeframe validation: must be confirmed on higher timeframe

**Historical Validation Approach:**
- Validate structure shift predicts regime change
- Measure duration of structure shifts
- Test shift significance thresholds
- Validate multi-timeframe confirmation

---

#### 1.3.11 Trend Continuation

**Definition:**
Trend continuation occurs when market structure confirms the existing trend is likely to continue, typically through BOS in the direction of the trend.

**Required Inputs:**
- Current trend direction
- Market structure (HH/HL or LH/LL)
- Recent BOS events
- Trend continuation parameters

**Detection Algorithm:**
```
1. Determine current trend:
   - Uptrend: HH + HL structure
   - Downtrend: LH + LL structure

2. Detect continuation signals:
   - BOS in trend direction
   - Structure pattern maintained
   - No CHoCH against trend

3. Validate continuation:
   - Is continuation confirmed on higher timeframe?
   - Is volume supportive?
   - Is there follow-through?

4. Classify continuation strength:
   - Strong continuation: clear BOS with volume and follow-through
   - Weak continuation: marginal BOS with low volume
   - Potential continuation: structure suggests but not confirmed
```

**Confidence Estimation:**
```
continuation_confidence = (structure_alignment × 0.4) + (bos_quality × 0.3) + (volume_score × 0.2) + (follow_through × 0.1)

where:
- structure_alignment: alignment of structure with trend (0-1)
- bos_quality: quality of BOS signal (0-1)
- volume_score: volume at BOS relative to average (0-1)
- follow_through: price continued in trend direction (0-1)
```

**Edge Cases:**
- **Weak continuation:** Structure aligned but weak BOS → mark as "Weak Continuation"
- **Mixed signals:** Some continuation, some reversal signals → mark as "Mixed Signals"
- **Exhaustion:** Extended trend with weakening continuation → mark as "Potential Exhaustion"

**Invalidation Rules:**
- Continuation invalidated by CHoCH against trend
- Time-based invalidation: if no follow-through within X candles
- Structure-based invalidation: if structure pattern breaks

**Historical Validation Approach:**
- Validate continuation signals predict trend continuation
- Measure success rate of continuation signals
- Test continuation strength thresholds
- Validate follow-through requirements

---

#### 1.3.12 Trend Transition

**Definition:**
Trend transition occurs when market structure indicates a trend is ending and a new trend (or range) is beginning, typically through CHoCH.

**Required Inputs:**
- Current trend direction
- Market structure
- CHoCH events
- Trend transition parameters

**Detection Algorithm:**
```
1. Detect trend weakening:
   - Structure pattern weakening (HH/HL becoming marginal)
   - Decreasing momentum
   - Increasing volatility against trend

2. Detect trend transition:
   - CHoCH against current trend
   - Structure pattern change
   - BOS in opposite direction

3. Validate transition:
   - Is transition confirmed on higher timeframe?
   - Is there follow-through?
   - Is volume supportive?

4. Classify transition type:
   - Trend to Range: trend becomes ranging
   - Trend to Reversal: trend reverses direction
   - Trend Acceleration: trend strengthens (not a transition)
   - Trend Exhaustion: trend ends, unclear what follows
```

**Confidence Estimation:**
```
transition_confidence = (choch_quality × 0.4) + (pattern_change × 0.3) + (follow_through × 0.2) + (volume_score × 0.1)

where:
- choch_quality: quality of CHoCH signal (0-1)
- pattern_change: significance of pattern change (0-1)
- follow_through: price continued in new direction (0-1)
- volume_score: volume at transition relative to average (0-1)
```

**Edge Cases:**
- **Premature transition:** CHoCH but structure reverts → mark as "Failed Transition"
- **Gradual transition:** Slow structural evolution → mark as "Gradual Transition"
- **Whipsaw transition:** Rapid trend changes → mark as "Choppy Transition"

**Invalidation Rules:**
- Transition invalidated if structure reverts to previous trend
- Time-based invalidation: if not sustained over longer period
- Follow-through required: must continue in new direction

**Historical Validation Approach:**
- Validate transition signals predict trend change
- Measure success rate of transition signals
- Test transition quality thresholds
- Validate follow-through requirements

---

#### 1.3.13 Consolidation

**Definition:**
Consolidation occurs when price moves within a defined range with no clear directional bias, characterized by alternating highs and lows within the range.

**Required Inputs:**
- OHLCV data
- Range detection parameters:
  - Range definition (percentage or pip-based)
  - Minimum duration
  - Maximum range width
- Current price

**Detection Algorithm:**
```
1. Identify range boundaries:
   - Detect range high (resistance)
   - Detect range low (support)
   - Validate range significance

2. Detect consolidation:
   - Price oscillating within range
   - No clear directional bias
   - Alternating highs and lows

3. Validate consolidation:
   - Is duration sufficient?
   - Is range width within parameters?
   - Is there volume contraction?

4. Classify consolidation type:
   - Tight consolidation: narrow range, low volatility
   - Wide consolidation: wider range, higher volatility
   - Triangle consolidation: converging range boundaries
   - Rectangle consolidation: parallel range boundaries
```

**Confidence Estimation:**
```
consolidation_confidence = (range_stability × 0.4) + (duration_score × 0.3) + (volume_contraction × 0.2) + (boundary_clarity × 0.1)

where:
- range_stability: stability of range boundaries (0-1)
- duration_score: duration relative to minimum (normalized 0-1)
- volume_contraction: volume decrease during consolidation (0-1)
- boundary_clarity: clarity of support/resistance levels (0-1)
```

**Edge Cases:**
- **Breaking consolidation:** Price approaching range boundary → mark as "Potential Breakout"
- **Failed consolidation:** Range breaks and reverts → mark as "False Range"
- **Expanding consolidation:** Range widening over time → mark as "Expanding Range"

**Invalidation Rules:**
- Consolidation invalidated when price breaks range boundary
- Time-based invalidation: if duration too short
- Volume-based invalidation: if volume not contracting

**Historical Validation Approach:**
- Validate consolidation precedes breakout
- Measure success rate of consolidation as continuation signal
- Test consolidation duration thresholds
- Validate breakout direction prediction

---

#### 1.3.14 Expansion

**Definition:**
Expansion occurs when price breaks out of a consolidation range with increased volatility and range, indicating potential trend development.

**Required Inputs:**
- Consolidation data
- Current price
- Expansion detection parameters:
  - Breakout threshold
  - Volume increase threshold
  - Volatility increase threshold

**Detection Algorithm:**
```
1. Detect breakout from consolidation:
   - Price breaks range boundary
   - Break confirmed on close
   - Volume increase

2. Detect expansion:
   - Range width increases
   - Volatility increases
   - Price moves away from range

3. Validate expansion:
   - Is breakout significant?
   - Is follow-through present?
   - Is volume/volatility increase confirmed?

4. Classify expansion type:
   - True expansion: breakout with follow-through
   - False expansion: breakout without follow-through
   - Partial expansion: breakout but range not fully left
```

**Confidence Estimation:**
```
expansion_confidence = (breakout_quality × 0.4) + (follow_through × 0.3) + (volume_increase × 0.2) + (volatility_increase × 0.1)

where:
- breakout_quality: quality of breakout signal (0-1)
- follow_through: price moved away from range (0-1)
- volume_increase: volume increase relative to average (0-1)
- volatility_increase: volatility increase relative to average (0-1)
```

**Edge Cases:**
- **False expansion:** Breakout without follow-through → mark as "False Breakout"
- **Gradual expansion:** Slow range expansion → mark as "Gradual Expansion"
- **Gap expansion:** Gap breakout → mark as "Gap Expansion"

**Invalidation Rules:**
- Expansion invalidated if price returns to range
- Time-based invalidation: if not sustained within X candles
- Follow-through required: must move away from range

**Historical Validation Approach:**
- Validate expansion leads to trend development
- Measure success rate of expansion as trend signal
- Test expansion quality thresholds
- Validate follow-through requirements

---

#### 1.3.15 Contraction

**Definition:**
Contraction occurs when volatility decreases and price range narrows, often preceding a breakout or indicating market indecision.

**Required Inputs:**
- OHLCV data
- Volatility data
- Contraction detection parameters:
  - Volatility decrease threshold
  - Range width decrease threshold
  - Minimum duration

**Detection Algorithm:**
```
1. Detect volatility decrease:
   - Compare current volatility to recent average
   - Detect significant decrease
   - Validate decrease is sustained

2. Detect range contraction:
   - Range width decreasing
   - Highs getting lower
   - Lows getting higher

3. Validate contraction:
   - Is duration sufficient?
   - Is contraction significant?
   - Is volume decreasing?

4. Classify contraction type:
   - Volatility contraction: volatility decrease primary
   - Range contraction: range decrease primary
   - Full contraction: both volatility and range decrease
```

**Confidence Estimation:**
```
contraction_confidence = (volatility_decrease × 0.4) + (range_decrease × 0.3) + (duration_score × 0.2) + (volume_decrease × 0.1)

where:
- volatility_decrease: volatility decrease relative to average (0-1)
- range_decrease: range width decrease (0-1)
- duration_score: duration relative to minimum (normalized 0-1)
- volume_decrease: volume decrease relative to average (0-1)
```

**Edge Cases:**
- **Temporary contraction:** Short-term decrease → mark as "Temporary Contraction"
- **Asymmetric contraction:** One side contracting more than other → mark as "Asymmetric Contraction"
- **Failed contraction:** Contraction followed by immediate expansion → mark as "Failed Contraction"

**Invalidation Rules:**
- Contraction invalidated when volatility increases
- Time-based invalidation: if duration too short
- Breakout invalidation: if breakout occurs

**Historical Validation Approach:**
- Validate contraction precedes breakout
- Measure success rate of contraction as breakout precursor
- Test contraction significance thresholds
- Validate breakout direction prediction

---

### 1.4 Structure Output Schema

```python
@dataclass
class MarketStructure:
    structure_id: str
    instrument_id: str
    timestamp: datetime
    
    # Swing Structure
    swing_structure: SwingStructure
    swing_confidence: float
    
    # Internal Structure
    internal_structure: InternalStructure
    internal_confidence: float
    
    # External Structure
    external_structure: ExternalStructure
    external_confidence: float
    
    # Current Pattern
    current_pattern: str  # HH/HL, LH/LL, Range, etc.
    pattern_strength: float
    
    # Recent Events
    recent_events: List[StructureEvent]
    
    # Structure State
    structure_state: StructureState  # trending, ranging, transitioning
    state_confidence: float
    
    # Key Levels
    key_levels: List[KeyLevel]
    
    # Metadata
    timeframe: str
    version: str
```

---

## 2. Liquidity Intelligence

### 2.1 Overview
Liquidity Intelligence analyzes the availability and distribution of liquidity in the market, identifying areas where significant buying or selling pressure exists.

### 2.2 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Liquidity Intelligence Engine                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Buy-Side    │  │  Sell-Side   │  │  Equal       │         │
│  │  Liquidity    │  │  Liquidity    │  │  Highs/Lows  │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
│         └─────────────────┴─────────────────┘                  │
│                           ↓                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Liquidity   │  │  Stop Runs   │  │  Liquidity   │         │
│  │  Pools       │  │              │  │  Sweeps      │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
│         └─────────────────┴─────────────────┘                  │
│                           ↓                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Engineered  │  │  Resting     │  │  Trapped     │         │
│  │  Liquidity   │  │  Liquidity   │  │ Participants│         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
│         └─────────────────┴─────────────────┘                  │
│                           ↓                                      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              Liquidity Aggregator                        │      │
│  │  - Liquidity profile                                   │      │
│  │  - Liquidity distribution                              │      │
│  │  - Liquidity quality                                   │      │
│  └──────────────────────┬───────────────────────────────┘      │
│                           ↓                                      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              Liquidity Publisher                        │      │
│  │  - Liquidity events                                    │      │
│  │  - State persistence                                   │      │
│  │  - Confidence reporting                                │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Liquidity Modules

#### 2.3.1 Buy-Side Liquidity

**Definition:**
Buy-side liquidity refers to the availability of buy orders at various price levels, typically concentrated below current price (limit buy orders, stop loss buy orders).

**Observable Characteristics:**
- Order book depth at bid levels
- Concentration of limit buy orders at specific levels
- Buy stop clusters
- Absorption of selling pressure at specific levels
- Price reaction when hitting buy liquidity

**Required Inputs:**
- Order book data (if available)
- Price action data
- Volume profile
- Buy-side liquidity parameters:
  - Liquidity threshold
  - Cluster detection parameters
  - Absorption detection parameters

**Detection Algorithm:**
```
1. Detect buy-side liquidity clusters:
   - Identify price levels with high buy order concentration
   - Detect buy stop clusters
   - Identify areas of repeated buying interest

2. Validate buy-side liquidity:
   - Is liquidity concentration significant?
   - Has price reacted at this level before?
   - Is there absorption evidence?

3. Classify buy-side liquidity:
   - Strong buy-side: high concentration, proven absorption
   - Moderate buy-side: moderate concentration, some absorption
   - Weak buy-side: low concentration, no absorption
```

**Confidence Metrics:**
```
buy_liquidity_confidence = (concentration_score × 0.4) + (absorption_score × 0.3) + (repeatability × 0.2) + (depth_score × 0.1)

where:
- concentration_score: concentration of buy orders (0-1)
- absorption_score: evidence of selling absorption (0-1)
- repeatability: price has reacted at this level before (0-1)
- depth_score: depth of liquidity at level (0-1)
```

**Failure Scenarios:**
- **No order book data:** Cannot detect liquidity clusters → use price action proxy
- **Thin order book:** Insufficient depth → mark as "Low Liquidity"
- **Rapidly changing order book:** Liquidity moving quickly → mark as "Transient Liquidity"

**Ambiguity Handling:**
- If multiple liquidity levels close together: mark as "Clustered Liquidity"
- If liquidity detected but not confirmed: mark as "Potential Liquidity"
- If conflicting signals: mark as "Ambiguous Liquidity"

---

#### 2.3.2 Sell-Side Liquidity

**Definition:**
Sell-side liquidity refers to the availability of sell orders at various price levels, typically concentrated above current price (limit sell orders, stop loss sell orders).

**Observable Characteristics:**
- Order book depth at ask levels
- Concentration of limit sell orders at specific levels
- Sell stop clusters
- Absorption of buying pressure at specific levels
- Price reaction when hitting sell liquidity

**Required Inputs:**
- Order book data (if available)
- Price action data
- Volume profile
- Sell-side liquidity parameters

**Detection Algorithm:**
```
1. Detect sell-side liquidity clusters:
   - Identify price levels with high sell order concentration
   - Detect sell stop clusters
   - Identify areas of repeated selling interest

2. Validate sell-side liquidity:
   - Is liquidity concentration significant?
   - Has price reacted at this level before?
   - Is there absorption evidence?

3. Classify sell-side liquidity:
   - Strong sell-side: high concentration, proven absorption
   - Moderate sell-side: moderate concentration, some absorption
   - Weak sell-side: low concentration, no absorption
```

**Confidence Metrics:**
```
sell_liquidity_confidence = (concentration_score × 0.4) + (absorption_score × 0.3) + (repeatability × 0.2) + (depth_score × 0.1)
```

**Failure Scenarios:**
- **No order book data:** Use price action proxy
- **Thin order book:** Mark as "Low Liquidity"
- **Rapidly changing order book:** Mark as "Transient Liquidity"

**Ambiguity Handling:**
- Multiple liquidity levels close: "Clustered Liquidity"
- Liquidity detected but not confirmed: "Potential Liquidity"
- Conflicting signals: "Ambiguous Liquidity"

---

#### 2.3.3 Equal Highs

**Definition:**
Equal highs occur when price reaches the same high level multiple times, indicating significant sell-side liquidity at that level.

**Observable Characteristics:**
- Multiple swing highs at same price level
- Rejection at same level
- Volume at each equal high
- Time between equal highs

**Required Inputs:**
- Swing structure data
- Price data
- Volume data
- Equal highs parameters:
  - Price tolerance (pips)
  - Time window
  - Minimum occurrences

**Detection Algorithm:**
```
1. Identify swing highs
2. Group highs by price level (within tolerance)
3. Detect equal highs:
   - At least N occurrences at same level
   - Within time window
   - Rejection at each occurrence
4. Validate equal highs:
   - Is rejection clear?
   - Is volume consistent?
   - Is time between occurrences reasonable?
5. Classify equal highs:
   - Strong equal highs: clear rejection, consistent volume
   - Weak equal highs: marginal rejection, low volume
```

**Confidence Metrics:**
```
equal_highs_confidence = (precision_score × 0.4) + (rejection_clarity × 0.3) + (volume_consistency × 0.2) + (temporal_pattern × 0.1)

where:
- precision_score: how closely highs match (0-1)
- rejection_clarity: clarity of rejection at level (0-1)
- volume_consistency: volume consistency across highs (0-1)
- temporal_pattern: time pattern between highs (0-1)
```

**Failure Scenarios:**
- **Insufficient data:** Not enough swing highs → mark as "Insufficient Data"
- **Wide tolerance:** High tolerance leads to false positives → tighten tolerance
- **Long time window:** Too wide time window → not meaningful equal highs

**Ambiguity Handling:**
- Marginal equal highs: mark as "Potential Equal Highs"
- Equal highs with break: mark as "Broken Equal Highs"
- Equal highs in strong trend: mark as "Trend Equal Highs"

---

#### 2.3.4 Equal Lows

**Definition:**
Equal lows occur when price reaches the same low level multiple times, indicating significant buy-side liquidity at that level.

**Observable Characteristics:**
- Multiple swing lows at same price level
- Rejection at same level
- Volume at each equal low
- Time between equal lows

**Required Inputs:**
- Swing structure data
- Price data
- Volume data
- Equal lows parameters

**Detection Algorithm:**
```
1. Identify swing lows
2. Group lows by price level (within tolerance)
3. Detect equal lows:
   - At least N occurrences at same level
   - Within time window
   - Rejection at each occurrence
4. Validate equal lows
5. Classify equal lows:
   - Strong equal lows: clear rejection, consistent volume
   - Weak equal lows: marginal rejection, low volume
```

**Confidence Metrics:**
```
equal_lows_confidence = (precision_score × 0.4) + (rejection_clarity × 0.3) + (volume_consistency × 0.2) + (temporal_pattern × 0.1)
```

**Failure Scenarios:**
- **Insufficient data:** Not enough swing lows → mark as "Insufficient Data"
- **Wide tolerance:** Tighten tolerance
- **Long time window:** Not meaningful equal lows

**Ambiguity Handling:**
- Marginal equal lows: mark as "Potential Equal Lows"
- Equal lows with break: mark as "Broken Equal Lows"
- Equal lows in strong trend: mark as "Trend Equal Lows"

---

#### 2.3.5 Liquidity Pools

**Definition:**
Liquidity pools are areas where significant liquidity is concentrated, either buy-side or sell-side, often at key price levels.

**Observable Characteristics:**
- High order book concentration
- Volume profile nodes
- Repeated price reaction at level
- Time at level

**Required Inputs:**
- Order book data (if available)
- Volume profile data
- Price data
- Liquidity pool parameters:
  - Concentration threshold
  - Volume threshold
  - Time threshold

**Detection Algorithm:**
```
1. Detect potential liquidity pools:
   - Order book concentration
   - Volume profile nodes
   - Price reaction areas

2. Validate liquidity pools:
   - Is concentration significant?
   - Is there volume support?
   - Has price reacted before?

3. Classify liquidity pools:
   - Buy-side pool: buy liquidity concentration
   - Sell-side pool: sell liquidity concentration
   - Balanced pool: both buy and sell liquidity
```

**Confidence Metrics:**
```
pool_confidence = (concentration_score × 0.4) + (volume_score × 0.3) + (reaction_score × 0.2) + (time_score × 0.1)

where:
- concentration_score: liquidity concentration (0-1)
- volume_score: volume at level (0-1)
- reaction_score: price reaction history (0-1)
- time_score: time spent at level (0-1)
```

**Failure Scenarios:**
- **No order book data:** Use volume profile only
- **Low volume:** Insufficient volume → mark as "Weak Pool"
- **No reaction:** No price reaction → mark as "Untested Pool"

**Ambiguity Handling:**
- Multiple pools close: mark as "Clustered Pools"
- Pool not tested: mark as "Untested Pool"
- Conflicting signals: mark as "Ambiguous Pool"

---

#### 2.3.6 Stop Runs

**Definition:**
Stop runs occur when price rapidly moves through areas where stop loss orders are clustered, triggering those stops and often reversing direction.

**Observable Characteristics:**
- Rapid price movement
- Volume spike
- Quick reversal after stop run
- Liquidity sweep
- Price moving through obvious levels

**Required Inputs:**
- Price data
- Volume data
- Liquidity data
- Stop run parameters:
  - Speed threshold
  - Volume spike threshold
  - Reversal threshold
  - Level identification

**Detection Algorithm:**
```
1. Identify potential stop levels:
   - Below recent lows (buy stops)
   - Above recent highs (sell stops)
   - At obvious technical levels
   - At equal highs/lows

2. Detect stop run:
   - Rapid movement through level
   - Volume spike at level
   - Quick reversal after level
   - Liquidity sweep

3. Validate stop run:
   - Was movement rapid enough?
   - Was there volume spike?
   - Did reversal occur?
   - Was liquidity swept?

4. Classify stop run:
   - Confirmed stop run: all criteria met
   - Potential stop run: some criteria met
   - Failed stop run: no reversal
```

**Confidence Metrics:**
```
stop_run_confidence = (speed_score × 0.3) + (volume_spike × 0.3) + (reversal_score × 0.2) + (level_clarity × 0.2)

where:
- speed_score: speed of movement (0-1)
- volume_spike: volume increase relative to average (0-1)
- reversal_score: quick reversal after level (0-1)
- level_clarity: clarity of stop level (0-1)
```

**Failure Scenarios:**
- **No clear level:** Cannot identify stop level → mark as "Unclear Stop Run"
- **No reversal:** Movement continued → mark as "Breakout, Not Stop Run"
- **Low volume:** No volume spike → mark as "Low Volume Move"

**Ambiguity Handling:**
- Partial stop run: mark as "Partial Stop Run"
- Stop run in strong trend: mark as "Trend Stop Run"
- Multiple stop levels: mark as "Multiple Stop Run"

---

#### 2.3.7 Liquidity Sweeps

**Definition:**
Liquidity sweeps occur when price briefly moves through a liquidity area to trigger orders, then reverses, indicating institutional order filling.

**Observable Characteristics:**
- Quick move through level
- Wick penetration
- Quick reversal
- Volume at level
- Time at level

**Required Inputs:**
- Price data
- Volume data
- Liquidity data
- Sweep parameters:
  - Penetration threshold
  - Reversal speed
  - Time at level

**Detection Algorithm:**
```
1. Identify liquidity areas
2. Detect sweep:
   - Price moves through liquidity area
   - Wick penetration (close doesn't hold)
   - Quick reversal
   - Volume at liquidity area

3. Validate sweep:
   - Was penetration significant?
   - Was reversal quick?
   - Was there volume?
   - Did price return?

4. Classify sweep:
   - Confirmed sweep: all criteria met
   - Failed sweep: no reversal
   - Partial sweep: partial penetration
```

**Confidence Metrics:**
```
sweep_confidence = (penetration_score × 0.3) + (reversal_speed × 0.3) + (volume_score × 0.2) + (return_score × 0.2)

where:
- penetration_score: depth of penetration (0-1)
- reversal_speed: speed of reversal (0-1)
- volume_score: volume at level (0-1)
- return_score: price returned to original side (0-1)
```

**Failure Scenarios:**
- **No liquidity area:** Cannot identify liquidity → mark as "Unclear Sweep"
- **Full penetration:** Price held beyond level → mark as "Breakout, Not Sweep"
- **Slow reversal:** Reversal too slow → mark as "Slow Reversal"

**Ambiguity Handling:**
- Partial sweep: mark as "Partial Sweep"
- Sweep with no volume: mark as "Low Volume Sweep"
- Multiple sweeps: mark as "Multiple Sweeps"

---

#### 2.3.8 Engineered Liquidity

**Definition:**
Engineered liquidity refers to liquidity that appears to be deliberately placed or manipulated, often visible as unusual order book patterns or price action.

**Observable Characteristics:**
- Unusual order book patterns
- Large orders appearing/disappearing
- Spoofing patterns
- Layered orders
- Unusual price action at levels

**Required Inputs:**
- Order book data
- Price data
- Engineered liquidity parameters:
  - Pattern recognition rules
  - Unusual behavior thresholds
  - Time patterns

**Detection Algorithm:**
```
1. Detect unusual order book patterns:
   - Large orders appearing/disappearing
   - Layered orders at specific levels
   - Asymmetric order placement
   - Order timing patterns

2. Detect unusual price action:
   - Unusual price behavior at levels
   - Repeated patterns
   - Timing anomalies

3. Validate engineered liquidity:
   - Is pattern unusual?
   - Is it repeatable?
   - Does it deviate from normal?

4. Classify engineered liquidity:
   - Confirmed engineered: clear unusual patterns
   - Potential engineered: some unusual patterns
   - Natural: no unusual patterns
```

**Confidence Metrics:**
```
engineered_confidence = (pattern_unusualness × 0.4) + (repeatability × 0.3) + (deviation_score × 0.2) + (timing_anomaly × 0.1)

where:
- pattern_unusualness: how unusual the pattern is (0-1)
- repeatability: pattern repeats (0-1)
- deviation_score: deviation from normal (0-1)
- timing_anomaly: unusual timing (0-1)
```

**Failure Scenarios:**
- **No order book data:** Cannot detect → mark as "No Data"
- **Normal patterns:** No unusual patterns → mark as "Natural Liquidity"
- **Insufficient history:** Not enough data → mark as "Insufficient Data"

**Ambiguity Handling:**
- Some unusual patterns: mark as "Potential Engineered"
- Conflicting signals: mark as "Ambiguous"
- Low confidence: mark as "Uncertain"

---

#### 2.3.9 Resting Liquidity

**Definition:**
Resting liquidity refers to orders that remain in the order book for extended periods, indicating genuine interest rather than short-term manipulation.

**Observable Characteristics:**
- Orders persisting in book
- Stable order sizes
- Limited order modifications
- Consistent with market activity

**Required Inputs:**
- Order book data
- Resting liquidity parameters:
  - Time threshold
  - Stability threshold
  - Modification threshold

**Detection Algorithm:**
```
1. Track order book over time
2. Identify resting orders:
   - Orders persisting beyond time threshold
   - Orders with stable sizes
   - Orders with limited modifications

3. Validate resting liquidity:
   - Is persistence significant?
   - Is stability confirmed?
   - Is it consistent with market?

4. Classify resting liquidity:
   - Strong resting: long persistence, high stability
   - Moderate resting: moderate persistence, some stability
   - Weak resting: short persistence, low stability
```

**Confidence Metrics:**
```
resting_confidence = (persistence_score × 0.4) + (stability_score × 0.3) + (consistency_score × 0.2) + (size_score × 0.1)

where:
- persistence_score: time order persisted (normalized 0-1)
- stability_score: stability of order size (0-1)
- consistency_score: consistency with market (0-1)
- size_score: significance of order size (0-1)
```

**Failure Scenarios:**
- **No order book data:** Cannot detect → mark as "No Data"
- **Highly dynamic book:** Orders changing rapidly → mark as "Dynamic Book"
- **Short history:** Not enough time → mark as "Insufficient Data"

**Ambiguity Handling:**
- Some resting, some dynamic: mark as "Mixed Liquidity"
- Moderate persistence: mark as "Moderate Resting"
- Low confidence: mark as "Uncertain"

---

#### 2.3.10 Trapped Participants

**Definition:**
Trapped participants refer to traders who entered positions at unfavorable levels and are likely to be forced out when price moves against them, creating liquidity in the opposite direction.

**Observable Characteristics:**
- Price moves against recent entries
- Volume at trap levels
- Rapid movement against trapped positions
- Reversal after trap completion

**Required Inputs:**
- Price data
- Volume data
- Entry point analysis
- Trap detection parameters:
  - Entry identification
  - Trap level identification
  - Movement threshold

**Detection Algorithm:**
```
1. Identify potential entry points:
   - Breakout entries
   - Breakdown entries
   - Reversal entries
   - Range entries

2. Detect trapped participants:
   - Price moves against entries
   - Movement through entry levels
   - Volume at trap levels
   - Forced exit behavior

3. Validate trapped participants:
   - Are entries clearly identified?
   - Is movement against entries significant?
   - Is there volume support?
   - Is there reversal after trap?

4. Classify trapped participants:
   - Confirmed trap: clear trap and reversal
   - Potential trap: some evidence
   - No trap: no evidence
```

**Confidence Metrics:**
```
trap_confidence = (entry_clarity × 0.3) + (movement_against × 0.3) + (volume_support × 0.2) + (reversal_evidence × 0.2)

where:
- entry_clarity: clarity of entry points (0-1)
- movement_against: movement against entries (0-1)
- volume_support: volume at trap level (0-1)
- reversal_evidence: reversal after trap (0-1)
```

**Failure Scenarios:**
- **No clear entries:** Cannot identify → mark as "Unclear Entries"
- **No movement against:** Price moved with entries → mark as "No Trap"
- **No reversal:** No reversal after trap → mark as "Failed Trap"

**Ambiguity Handling:**
- Partial trap: mark as "Partial Trap"
- Multiple trap levels: mark as "Multiple Traps"
- Low confidence: mark as "Uncertain"

---

### 2.4 Liquidity Output Schema

```python
@dataclass
class LiquidityIntelligence:
    liquidity_id: str
    instrument_id: str
    timestamp: datetime
    
    # Buy-Side Liquidity
    buy_liquidity: BuySideLiquidity
    buy_confidence: float
    
    # Sell-Side Liquidity
    sell_liquidity: SellSideLiquidity
    sell_confidence: float
    
    # Key Levels
    equal_highs: List[EqualHighs]
    equal_lows: List[EqualLows]
    liquidity_pools: List[LiquidityPool]
    
    # Recent Events
    stop_runs: List[StopRun]
    liquidity_sweeps: List[LiquiditySweep]
    
    # Liquidity State
    liquidity_state: LiquidityState  # balanced, skewed, thin
    state_confidence: float
    
    # Engineered Liquidity
    engineered_liquidity: List[EngineeredLiquidity]
    
    # Resting Liquidity
    resting_liquidity: List[RestingLiquidity]
    
    # Trapped Participants
    trapped_participants: List[TrappedParticipants]
    
    # Metadata
    timeframe: str
    version: str
```

---

## 3. Institutional Price Delivery Concepts

### 3.1 Overview
Institutional Price Delivery Concepts identify patterns that suggest institutional order flow and execution, providing insight into where large market participants may have entered or exited positions.

### 3.2 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│          Institutional Price Delivery Engine                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Order      │  │  Mitigation  │  │  Breaker     │         │
│  │  Blocks     │  │  Blocks      │  │  Blocks      │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
│         └─────────────────┴─────────────────┘                  │
│                           ↓                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Rejection   │  │  Fair Value  │  │  Inverse     │         │
│  │  Blocks      │  │  Gaps        │  │  FVG         │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
│         └─────────────────┴─────────────────┘                  │
│                           ↓                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Balanced    │  │ Displacement │  │  Market      │         │
│  │  Price Ranges│  │              │  │  Inefficiency│         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
│         └─────────────────┴─────────────────┘                  │
│                           ↓                                      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              IPD Aggregator                             │      │
│  │  - Pattern recognition                              │      │
│  │  - Quality scoring                                   │      │
│  │  - Lifecycle tracking                                │      │
│  └──────────────────────┬───────────────────────────────┘      │
│                           ↓                                      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              IPD Publisher                              │      │
│  │  - IPD events                                        │      │
│  │  - State persistence                                 │      │
│  │  - Confidence reporting                                │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 IPD Modules

#### 3.3.1 Order Blocks

**Definition:**
Order blocks are the last opposing candle before a significant move, representing institutional order execution that caused the move.

**Identification Rules:**
```
1. Identify significant move:
   - Large bullish move: look for last bearish candle before move
   - Large bearish move: look for last bullish candle before move

2. Validate order block:
   - Is the move significant (size, speed)?
   - Is the opposing candle clear?
   - Is there volume at the order block?
   - Is the order block not yet breached?

3. Classify order block:
   - Bullish OB: bearish candle before bullish move
   - Bearish OB: bullish candle before bearish move
```

**Quality Scoring:**
```
ob_quality = (move_significance × 0.4) + (ob_clarity × 0.3) + (volume_score × 0.2) + (unbreached × 0.1)

where:
- move_significance: significance of the move (0-1)
- ob_clarity: clarity of the OB candle (0-1)
- volume_score: volume at OB (0-1)
- unbreached: OB not yet breached (1.0) or breached (0.0)
```

**Invalidation:**
- Order block invalidated when price closes beyond it
- Retest of OB is common before invalidation
- Time-based invalidation: if not retested within X candles

**Lifecycle:**
1. Formation: OB created
2. Untested: OB not yet retested
3. Retested: price returns to OB
4. Mitigated: OB respected and price moves away
5. Broken: OB breached and closes beyond

**Historical Validation:**
- Validate OB acts as support/resistance
- Measure success rate of OB as reversal signal
- Test OB significance thresholds
- Validate retest behavior

---

#### 3.3.2 Mitigation Blocks

**Definition:**
Mitigation blocks are order blocks that have been mitigated (price returned to them and respected), indicating institutional positions were defended.

**Identification Rules:**
```
1. Identify order blocks (as above)
2. Detect mitigation:
   - Price returns to OB
   - Price respects OB (doesn't close beyond)
   - Price moves away from OB
3. Validate mitigation:
   - Is retest clear?
   - Is respect clear?
   - Is there follow-through?
4. Classify mitigation:
   - Strong mitigation: clear retest, respect, follow-through
   - Weak mitigation: marginal retest/respect
```

**Quality Scoring:**
```
mitigation_quality = (retest_clarity × 0.4) + (respect_clarity × 0.3) + (follow_through × 0.2) + (volume_score × 0.1)
```

**Invalidation:**
- Mitigation invalidated when OB is subsequently broken
- Time-based invalidation: if follow-through doesn't sustain

**Lifecycle:**
1. OB formation
2. Retest
3. Mitigation
4. Sustained (follow-through continues)
5. Failed (OB broken later)

**Historical Validation:**
- Validate mitigated OBs act as stronger support/resistance
- Measure success rate after mitigation
- Test mitigation quality thresholds

---

#### 3.3.3 Breaker Blocks

**Definition:**
Breaker blocks are order blocks that have been broken, indicating institutional positions were likely stopped out or the market moved against them.

**Identification Rules:**
```
1. Identify order blocks (as above)
2. Detect break:
   - Price closes beyond OB
   - Break is significant
3. Validate break:
   - Is break confirmed on close?
   - Is there volume?
   - Is there follow-through?
4. Classify breaker:
   - Strong breaker: clear break with volume and follow-through
   - Weak breaker: marginal break with low volume
```

**Quality Scoring:**
```
breaker_quality = (break_clarity × 0.4) + (volume_score × 0.3) + (follow_through × 0.2) + (significance × 0.1)
```

**Invalidation:**
- Once broken, OB remains broken
- Can become new OB in opposite direction
- Time-based: significance decreases over time

**Lifecycle:**
1. OB formation
2. Break
3. Follow-through (or failed)
4. New OB formation (possible)

**Historical Validation:**
- Validate broken OBs lead to continuation
- Measure success rate of break signals
- Test break significance thresholds

---

#### 3.3.4 Rejection Blocks

**Definition:**
Rejection blocks are candles that show strong rejection of a price level, indicating institutional defense of that level.

**Identification Rules:**
```
1. Identify potential rejection level:
   - Previous highs/lows
   - Order block levels
   - Liquidity pool levels

2. Detect rejection:
   - Strong candle rejection at level
   - Long wicks rejecting level
   - Volume at rejection
   - Quick reversal from level

3. Validate rejection:
   - Is rejection clear?
   - Is there volume?
   - Is reversal quick?
   - Is level significant?

4. Classify rejection:
   - Strong rejection: clear rejection with volume and reversal
   - Weak rejection: marginal rejection
```

**Quality Scoring:**
```
rejection_quality = (rejection_clarity × 0.4) + (wick_size × 0.3) + (volume_score × 0.2) + (reversal_speed × 0.1)
```

**Invalidation:**
- Rejection invalidated when level is broken
- Time-based: significance decreases if not retested

**Lifecycle:**
1. Level identification
2. Rejection
3. Follow-through (or failed)
4. Retest (possible)
5. Break (possible)

**Historical Validation:**
- Validate rejected levels act as support/resistance
- Measure success rate of rejection signals
- Test rejection quality thresholds

---

#### 3.3.5 Fair Value Gaps (FVG)

**Definition:**
Fair Value Gaps are price imbalances that occur when there is a large gap between the wicks of two candles, indicating inefficiency that price often returns to fill.

**Identification Rules:**
```
1. Detect FVG:
   - Bullish FVG: gap between candle 1 high and candle 2 low
   - Bearish FVG: gap between candle 1 low and candle 2 high
   - Gap must be significant (size threshold)

2. Validate FVG:
   - Is gap size significant?
   - Is there volume at gap formation?
   - Is gap not yet filled?

3. Classify FVG:
   - Strong FVG: large gap with volume
   - Weak FVG: small gap with low volume
```

**Quality Scoring:**
```
fvg_quality = (gap_size × 0.4) + (volume_score × 0.3) + (unfilled × 0.2) + (freshness × 0.1)

where:
- gap_size: size of gap relative to ATR (0-1)
- volume_score: volume at formation (0-1)
- unfilled: gap not yet filled (1.0) or filled (0.0)
- freshness: how recent the gap is (0-1)
```

**Invalidation:**
- FVG invalidated when filled (price trades through gap)
- Time-based: significance decreases over time

**Lifecycle:**
1. Formation
2. Unfilled
3. Partial fill
4. Filled
5. Retest (possible after fill)

**Historical Validation:**
- Validate FVGs get filled
- Measure fill rate and time to fill
- Test FVG significance thresholds
- Validate fill behavior

---

#### 3.3.6 Inverse Fair Value Gaps (iFVG)

**Definition:**
Inverse Fair Value Gaps are gaps that occur in the opposite direction of the current trend, often indicating a counter-trend move that may be reversed.

**Identification Rules:**
```
1. Detect iFVG:
   - Same detection as FVG
   - Must be opposite to current trend
   - Must occur after trend move

2. Validate iFVG:
   - Is gap significant?
   - Is it truly inverse to trend?
   - Is it not yet filled?

3. Classify iFVG:
   - Strong iFVG: large gap, clearly inverse
   - Weak iFVG: small gap, ambiguous
```

**Quality Scoring:**
```
ifvg_quality = (gap_size × 0.3) + (trend_inverse × 0.4) + (volume_score × 0.2) + (unfilled × 0.1)
```

**Invalidation:**
- Same as FVG

**Lifecycle:**
- Same as FVG

**Historical Validation:**
- Validate iFVGs get filled
- Measure if iFVGs predict trend resumption
- Test iFVG significance thresholds

---

#### 3.3.7 Balanced Price Ranges (BPR)

**Definition:**
Balanced Price Ranges are ranges where price has moved sideways with equal buying and selling pressure, indicating equilibrium that may break in either direction.

**Identification Rules:**
```
1. Detect range:
   - Price oscillating between support and resistance
   - Range duration sufficient
   - Range width within parameters

2. Validate balance:
   - Are moves up and down equal?
   - Is volume balanced?
   - Is there no clear direction?

3. Classify BPR:
   - Strong BPR: clear range, balanced moves
   - Weak BPR: marginal range, imbalanced moves
```

**Quality Scoring:**
```
bpr_quality = (range_clarity × 0.3) + (balance_score × 0.4) + (volume_balance × 0.2) + (duration_score × 0.1)
```

**Invalidation:**
- BPR invalidated when range breaks
- Time-based: significance decreases if too long

**Lifecycle:**
1. Formation
2. Balanced
3. Imbalance (possible)
4. Breakout

**Historical Validation:**
- Validate BPRs break out
- Measure breakout direction prediction
- Test BPR quality thresholds

---

#### 3.3.8 Displacement

**Definition:**
Displacement is a strong, impulsive move that breaks structure and indicates institutional order flow entering the market.

**Identification Rules:**
```
1. Detect displacement:
   - Strong directional move
   - Breaks structure
   - High volume
   - Large candle(s)

2. Validate displacement:
   - Is move strong enough?
   - Does it break structure?
   - Is there volume?
   - Is it impulsive?

3. Classify displacement:
   - Bullish displacement: strong up move
   - Bearish displacement: strong down move
```

**Quality Scoring:**
```
displacement_quality = (strength × 0.4) + (structure_break × 0.3) + (volume_score × 0.2) + (impulsiveness × 0.1)
```

**Invalidation:**
- Displacement invalidated if structure reverts
- Time-based: significance decreases over time

**Lifecycle:**
1. Formation
2. Follow-through (or failed)
3. Retest (possible)
4. Continuation or reversal

**Historical Validation:**
- Validate displacements lead to trend
- Measure success rate of displacement signals
- Test displacement quality thresholds

---

#### 3.3.9 Market Inefficiencies

**Definition:**
Market inefficiencies are price anomalies that don't reflect normal market behavior, often caused by temporary imbalances, news events, or institutional flows.

**Identification Rules:**
```
1. Detect inefficiency:
   - Price deviates from expected behavior
   - Unusual volatility
   - Unusual correlation breakdown
   - Gap formation

2. Validate inefficiency:
   - Is deviation significant?
   - Is it temporary?
   - Is there a cause?

3. Classify inefficiency:
   - Temporary: short-lived anomaly
   - Structural: longer-term anomaly
   - Event-driven: caused by specific event
```

**Quality Scoring:**
```
inefficiency_quality = (deviation × 0.4) + (temporariness × 0.3) + (clarity × 0.2) + (cause_identification × 0.1)
```

**Invalidation:**
- Inefficiency invalidated when price normalizes
- Time-based: significance decreases over time

**Lifecycle:**
1. Detection
2. Active
3. Normalization
4. Resolved

**Historical Validation:**
- Validate inefficiencies normalize
- Measure time to normalization
- Test inefficiency significance thresholds

---

### 3.4 IPD Output Schema

```python
@dataclass
class InstitutionalPriceDelivery:
    ipd_id: str
    instrument_id: str
    timestamp: datetime
    
    # Order Blocks
    order_blocks: List[OrderBlock]
    mitigation_blocks: List[MitigationBlock]
    breaker_blocks: List[BreakerBlock]
    
    # Rejection Blocks
    rejection_blocks: List[RejectionBlock]
    
    # Fair Value Gaps
    fvgs: List[FairValueGap]
    ifvgs: List[InverseFVG]
    
    # Ranges
    balanced_price_ranges: List[BalancedPriceRange]
    
    # Displacement
    displacements:	List[Displacement]
    
    # Inefficiencies
    inefficiencies: List[MarketInefficiency]
    
    # IPD State
    ipd_state: IPDState
    state_confidence: float
    
    # Metadata
    timeframe: str
    version: str
```

---

## 4. Market Regime Behaviour

### 4.1 Overview
Market Regime Behaviour describes how markets behave under different conditions, providing context for strategy selection and risk management.

### 4.2 Regime Definitions

#### 4.2.1 Strong Trend

**Defining Characteristics:**
- Clear directional bias
- HH/HL (uptrend) or LH/LL (downtrend)
- Momentum indicators confirming trend
- Pullbacks are shallow and short-lived
- Volume supports trend direction
- Low volatility relative to trend strength

**Transition Indicators:**
- Structure weakening (marginal HH/HL or LH/LL)
- Decreasing momentum
- Increasing volatility against trend
- CHoCH against trend
- Failed BOS in trend direction

**Confidence:**
```
strong_trend_confidence = (structure_clarity × 0.4) + (momentum_strength × 0.3) + (volatility_alignment × 0.2) + (volume_alignment × 0.1)
```

**Limitations:**
- May not persist in volatile markets
- Can transition quickly in news-driven markets
- May be difficult to identify in real-time
- Subject to false signals during corrections

---

#### 4.2.2 Weak Trend

**Defining Characteristics:**
- Directional bias present but weak
- Marginal HH/HL or LH/LL
- Momentum indicators weak
- Deeper pullbacks
- Volume less supportive
- Higher volatility relative to trend

**Transition Indicators:**
- Structure breakdown
- Momentum reversal
- Range formation
- CHoCH
- BOS failure

**Confidence:**
```
weak_trend_confidence = (structure_marginality × 0.4) + (momentum_weakness × 0.3) + (pullback_depth × 0.2) + (volume_weakness × 0.1)
```

**Limitations:**
- Difficult to distinguish from range
- May transition to range or reversal
- Higher false signal rate
- Requires careful monitoring

---

#### 4.2.3 Range

**Defining Characteristics:**
- No clear directional bias
- Price oscillating between support and resistance
- Alternating highs and lows
- Momentum indicators neutral
- Volume typically low
- Low volatility

**Transition Indicators:**
- Range break with volume
- Volatility expansion
- Structure shift
- BOS from range

**Confidence:**
```
range_confidence = (range_stability × 0.4) + (neutrality_score × 0.3) + (volume_contraction × 0.2) + (volatility_low × 0.1)
```

**Limitations:**
- May be difficult to identify boundaries
- False breakouts common
- Can persist for extended periods
- Breakout direction unpredictable

---

#### 4.2.4 Breakout

**Defining Characteristics:**
- Price breaks range or structure
- Increased volume
- Increased volatility
- Momentum shift
- Follow-through expected

**Transition Indicators:**
- Failed breakout (revert to range)
- Continuation (trend development)
- Reversal (false breakout)

**Confidence:**
```
breakout_confidence = (break_quality × 0.4) + (volume_increase × 0.3) + (volatility_increase × 0.2) + (follow_through × 0.1)
```

**Limitations:**
- High false breakout rate
- Difficult to distinguish true vs false
- Requires quick decision making
- High risk if wrong

---

#### 4.2.5 Failed Breakout

**Defining Characteristics:**
- Initial breakout signal
- Price reverts to range
- Volume spike then drop
- False follow-through
- Structure reverts

**Transition Indicators:**
- Return to range
- Range re-establishment
- Opposite breakout (possible)

**Confidence:**
```
failed_breakout_confidence = (initial_break × 0.3) + (reversion_clarity × 0.4) + (volume_pattern × 0.2) + (structure_revert × 0.1)
```

**Limitations:**
- Can only be identified in hindsight
- May be confused with pullback
- High uncertainty during failure
- Requires quick position management

---

#### 4.2.6 Reversal

**Defining Characteristics:**
- Trend direction changes
- CHoCH confirmed
- Structure shift
- Momentum reversal
- Volume supports reversal

**Transition Indicators:**
- Trend continuation (reversal was false)
- Range formation
- New trend development

**Confidence:**
```
reversal_confidence = (choch_quality × 0.4) + (structure_shift × 0.3) + (momentum_reversal × 0.2) + (volume_support × 0.1)
```

**Limitations:**
- Difficult to distinguish from pullback
- High false signal rate
- May be partial or complete
- Requires confirmation

---

#### 4.2.7 Pullback

**Defining Characteristics:**
- Temporary move against trend
- Shallow depth relative to trend
- Short duration
- Volume decreases during pullback
- Structure maintained (HH/HL or LH/LL)

**Transition Indicators:**
- Trend continuation (pullback ends)
- Deeper pullback (becomes correction)
- Reversal (pullback becomes reversal)

**Confidence:**
```
pullback_confidence = (depth_shallow × 0.4) + (duration_short × 0.3) + (structure_maintained × 0.2) + (volume_decrease × 0.1)
```

**Limitations:**
- Difficult to distinguish from reversal
- May become deeper than expected
- Timing of continuation uncertain
- Requires active management

---

#### 4.2.8 Accumulation

**Defining Characteristics:**
- Price consolidates after downtrend
- Buying pressure evident (absorption)
- Volume patterns suggest accumulation
- Range formation with bullish bias
- Potential reversal to uptrend

**Transition Indicators:**
- Breakout to upside
- Failed accumulation (continues downtrend)
- Extended accumulation (becomes distribution)

**Confidence:**
```
accumulation_confidence = (absorption_evidence × 0.4) + (volume_pattern × 0.3) + (range_bias × 0.2) + (context_alignment × 0.1)
```

**Limitations:**
- Can only be confirmed in hindsight
- May be confused with range
- Duration uncertain
- False accumulation common

---

#### 4.2.9 Distribution

**Defining Characteristics:**
- Price consolidates after uptrend
- Selling pressure evident (absorption)
- Volume patterns suggest distribution
- Range formation with bearish bias
- Potential reversal to downtrend

**Transition Indicators:**
- Breakout to downside
- Failed distribution (continues uptrend)
- Extended distribution (becomes accumulation)

**Confidence:**
```
distribution_confidence = (absorption_evidence × 0.4) + (volume_pattern × 0.3) + (range_bias × 0.2) + (context_alignment × 0.1)
```

**Limitations:**
- Can only be confirmed in hindsight
- May be confused with range
- Duration uncertain
- False distribution common

---

#### 4.2.10 Re-Accumulation

**Defining Characteristics:**
- Accumulation after uptrend pullback
- Higher low structure
- Buying pressure at higher levels
- Continuation pattern

**Transition Indicators:**
- Breakout to new highs
- Failed re-accumulation (reversal)
- Extended re-accumulation

**Confidence:**
```
re_accumulation_confidence = (hl_structure × 0.4) + (absorption_at_higher_levels × 0.3) + (volume_pattern × 0.2) + (trend_context × 0.1)
```

**Limitations:**
- May be confused with distribution
- Higher low may fail
- Duration uncertain
- False re-accumulation possible

---

#### 4.2.11 Re-Distribution

**Defining Characteristics:**
- Distribution after downtrend pullback
- Lower high structure
- Selling pressure at lower levels
- Continuation pattern

**Transition Indicators:**
- Breakout to new lows
- Failed re-distribution (reversal)
- Extended re-distribution

**Confidence:**
```
re_distribution_confidence = (lh_structure × 0.4) + (absorption_at_lower_levels × 0.3) + (volume_pattern × 0.2) + (trend_context × 0.1)
```

**Limitations:**
- May be confused with accumulation
- Lower high may fail
- Duration uncertain
- False re-distribution possible

---

### 4.3 Regime Output Schema

```python
@dataclass
class MarketRegime:
    regime_id: str
    instrument_id: str
    timestamp: datetime
    
    # Current Regime
    current_regime: str
    regime_confidence: float
    
    # Regime Characteristics
    trend_strength: str
    volatility_state: str
    momentum_state: str
    
    # Transition Indicators
    transition_signals: List[TransitionSignal]
    transition_probability: float
    
    # Regime History
    regime_history: List[RegimeState]
    current_duration: timedelta
    
    # Limitations
    limitations: List[str]
    uncertainty_notes: List[str]
    
    # Metadata
    timeframe: str
    version: str
```

---

## 5. Session Intelligence

### 5.1 Overview
Session Intelligence models the behavioral characteristics of different trading sessions, providing context for strategy selection and risk management.

### 5.2 Session Models

#### 5.2.1 Asian Session

**Volatility Expectations:**
- Generally lower volatility
- Can be volatile during news events
- Ranges often tighter
- Spreads may be wider (lower liquidity)

**Liquidity Expectations:**
- Lower liquidity overall
- Thinner order books
- Wider spreads
- Potential for larger moves on lower volume

**Common Behaviour:**
- Range-bound trading common
- Trend development possible but slower
- Often sets up London session
- Can be influenced by other regional markets

**Risk Considerations:**
- Wider spreads increase costs
- Lower liquidity increases slippage risk
- Overnight gap risk
- News events can cause large moves

---

#### 5.2.2 London Session

**Volatility Expectations:**
- Moderate to high volatility
- Most volatile session for many pairs
- Breakouts common
- Trend development likely

**Liquidity Expectations:**
- High liquidity
- Tight spreads
- Deep order books
- Efficient execution

**Common Behaviour:**
- Trend initiation common
- Breakouts from Asian range
- Strong directional moves
- Volume increases

**Risk Considerations:**
- Fast moves require quick decisions
- Breakout false signals possible
- Overlap with NY can be volatile
- News events have high impact

---

#### 5.2.3 New York Session

**Volatility Expectations:**
- High volatility (especially overlap)
- Can be volatile post-overlap
- Trend continuation or reversal
- Late session can quiet down

**Liquidity Expectations:**
- Very high liquidity during overlap
- High liquidity post-overlap
- Tight spreads
- Deep order books

**Common Behaviour:**
- Overlap: high volatility, trend continuation or reversal
- Post-overlap: trend continuation or range
- Late session: quiet, range-bound
- Profit taking common late session

**Risk Considerations:**
- Overlap volatility requires tight risk management
- Reversals common during overlap
- Late session liquidity decreases
- Overnight gap risk into Asian session

---

#### 5.2.4 Session Overlaps

**London/NY Overlap:**
- Highest volatility
- Highest liquidity
- Most trading volume
- Trend continuation or reversal
- Highest risk and opportunity

**Asian/London Overlap:**
- Moderate volatility increase
- Liquidity increasing
- Breakouts from Asian range
- Trend initiation possible

**Other Overlaps:**
- Lower significance
- Regional considerations
- Currency-specific behavior

---

#### 5.2.5 Session Transitions

**Asian to London:**
- Volatility increase
- Liquidity increase
- Breakout from Asian range
- Trend initiation possible

**London to NY:**
- Volatility peak (overlap)
- Liquidity peak
- Trend continuation or reversal
- High activity

**NY to Asian:**
- Volatility decrease
- Liquidity decrease
- Range formation
- Profit taking

---

### 5.3 Session Output Schema

```python
@dataclass
class SessionIntelligence:
    session_id: str
    instrument_id: str
    timestamp: datetime
    
    # Current Session
    current_session: str
    session_phase: str  # early, mid, late, overlap
    
    # Session Characteristics
    volatility_expectation: str
    liquidity_expectation: str
    typical_behavior: str
    
    # Transition Information
    next_session: str
    time_to_transition: timedelta
    transition_probability: float
    
    # Risk Considerations
    risk_level: str
    risk_factors: List[str]
    
    # Historical Performance
    session_performance: SessionPerformance
    
    # Metadata
    timezone: str
    version: str
```

---

## 6. Volatility Intelligence

### 6.1 Overview
Volatility Intelligence classifies and tracks volatility states, providing context for position sizing, risk management, and strategy selection.

### 6.2 Volatility States

#### 6.2.1 Volatility States

**States:**
- **Very Low:** ATR < 50% of average
- **Low:** ATR 50-75% of average
- **Normal:** ATR 75-125% of average
- **High:** ATR 125-200% of average
- **Very High:** ATR > 200% of average

**Measurements:**
- ATR (Average True Range)
- Realized volatility
- Implied volatility (if available)
- Bollinger Band width
- Standard deviation of returns

**Classification:**
```
current_atr = calculate_atr(period)
avg_atr = calculate_average_atr(lookback)
atr_ratio = current_atr / avg_atr

if atr_ratio < 0.5: Very Low
elif atr_ratio < 0.75: Low
elif atr_ratio < 1.25: Normal
elif atr_ratio < 2.0: High
else: Very High
```

**Transition Logic:**
```
if volatility_state changes:
    confirm with multiple measurements
    check persistence over time
    validate with other volatility measures
    update state only if confirmed
```

---

#### 6.2.2 Compression

**Definition:**
Volatility compression occurs when volatility decreases significantly, often preceding a breakout.

**Detection:**
```
1. Calculate current volatility
2. Compare to historical average
3. Detect significant decrease
4. Validate decrease is sustained
5. Classify compression strength
```

**Classification:**
- Strong compression: >50% decrease, sustained
- Moderate compression: 25-50% decrease
- Weak compression: 10-25% decrease

---

#### 6.2.3 Expansion

**Definition:**
Volatility expansion occurs when volatility increases significantly, often after a breakout or news event.

**Detection:**
```
1. Calculate current volatility
2. Compare to historical average
3. Detect significant increase
4. Validate increase is sustained
5. Classify expansion strength
```

**Classification:**
- Strong expansion: >100% increase, sustained
- Moderate expansion: 50-100% increase
- Weak expansion: 25-50% increase

---

#### 6.2.4 Abnormal Volatility

**Definition:**
Abnormal volatility occurs when volatility is outside normal statistical range, indicating unusual market conditions.

**Detection:**
```
1. Calculate volatility statistics
2. Detect outliers (e.g., >3 standard deviations)
3. Validate outlier is significant
4. Identify cause if possible (news, event)
5. Classify abnormality type
```

**Classification:**
- Statistical abnormality: outside normal range
- Event-driven: caused by specific event
- Structural: new volatility regime

---

#### 6.2.5 Quiet Markets

**Definition:**
Quiet markets have very low volatility and range, often indicating consolidation or lack of interest.

**Detection:**
```
1. Detect low volatility state
2. Detect narrow range
3. Validate low volume
4. Check for lack of catalysts
5. Classify quiet market type
```

**Classification:**
- Consolidation quiet: range-bound, low volatility
- Dead market: no activity, very low volatility
- Pre-news quiet: waiting for catalyst

---

#### 6.2.6 Explosive Moves

**Definition:**
Explosive moves are sudden, large volatility increases often caused by news events or liquidity shocks.

**Detection:**
```
1. Detect sudden volatility spike
2. Detect large price movement
3. Validate volume spike
4. Identify cause if possible
5. Classify move type
```

**Classification:**
- News-driven: caused by news event
- Liquidity shock: caused by liquidity imbalance
- Breakout-driven: caused by technical breakout

---

### 6.3 Volatility Output Schema

```python
@dataclass
class VolatilityIntelligence:
    volatility_id: str
    instrument_id: str
    timestamp: datetime
    
    # Current State
    current_state: str
    state_confidence: float
    
    # Measurements
    current_atr: Decimal
    avg_atr: Decimal
    realized_volatility: Decimal
    implied_volatility: Optional[Decimal]
    
    # Compression/Expansion
    compression_active: bool
    expansion_active: bool
    compression_strength: Optional[float]
    expansion_strength: Optional[float]
    
    # Abnormality
    is_abnormal: bool
    abnormality_type: Optional[str]
    abnormality_cause: Optional[str]
    
    # Market Type
    is_quiet_market: bool
    quiet_market_type: Optional[str]
    
    # Explosive Moves
    explosive_move_active: bool
    explosive_move_type: Optional[str]
    
    # Historical Context
    volatility_history: List[VolatilityState]
    
    # Metadata
    timeframe: str
    version: str
```

---

## 7. Market Context Scoring

### 7.1 Overview
Market Context Scoring combines all intelligence modules into a single explainable market context score, providing a unified view of market conditions.

### 7.2 Scoring Framework

#### 7.2.1 Score Components

**Structure Score:**
```
structure_score = (trend_clarity × 0.4) + (structure_quality × 0.3) + (pattern_strength × 0.2) + (multi_tf_alignment × 0.1)
```

**Liquidity Score:**
```
liquidity_score = (liquidity_depth × 0.4) + (liquidity_quality × 0.3) + (spread_tightness × 0.2) + (stability × 0.1)
```

**IPD Score:**
```
ipd_score = (ipd_clarity × 0.4) + (ipd_quality × 0.3) + (ipd_freshness × 0.2) + (ipd_significance × 0.1)
```

**Regime Score:**
```
regime_score = (regime_clarity × 0.4) + (regime_stability × 0.3) + (regime_favorability × 0.2) + (regime_confidence × 0.1)
```

**Session Score:**
```
session_score = (session_favorability × 0.5) + (liquidity_expectation × 0.3) + (volatility_expectation × 0.2)
```

**Volatility Score:**
```
volatility_score = (volatility_appropriateness × 0.5) + (volatility_stability × 0.3) + (volatility_predictability × 0.2)
```

---

#### 7.2.2 Overall Context Score

**Composite Score:**
```
context_score = (structure_score × 0.25) + 
                 (liquidity_score × 0.20) + 
                 (ipd_score × 0.15) + 
                 (regime_score × 0.15) + 
                 (session_score × 0.15) + 
                 (volatility_score × 0.10)
```

**Score Buckets:**
- Excellent: 0.80 - 1.00
- Good: 0.60 - 0.79
- Fair: 0.40 - 0.59
- Poor: 0.20 - 0.39
- Very Poor: 0.00 - 0.19

---

#### 7.2.3 Determinism

**Requirements:**
- All scoring formulas are deterministic
- No random components
- All inputs are timestamped
- All configurations are versioned
- Full score breakdown stored

**Reproducibility:**
- Score can be recalculated from stored inputs
- Same inputs produce same score
- Score version tracked
- Configuration version tracked

---

#### 7.2.4 Configurability

**Configurable Elements:**
- Component weights
- Score thresholds
- Sub-component formulas
- Timeframes used
- Data sources

**Configuration Schema:**
```python
@dataclass
class ContextScoringConfig:
    component_weights: Dict[str, float]
    score_thresholds: Dict[str, float]
    sub_component_configs: Dict[str, Any]
    timeframes: Dict[str, str]
    data_sources: Dict[str, str]
    version: str
```

---

#### 7.2.5 Explainability

**Score Breakdown:**
```
For each component:
- Component score
- Sub-component scores
- Weights used
- Contributing factors
- Limitations
```

**Explanation Template:**
```
MARKET CONTEXT SCORE: {overall_score} ({bucket})

COMPONENT BREAKDOWN:
- Structure: {structure_score} ({weight}%)
  - Trend clarity: {trend_clarity}
  - Structure quality: {structure_quality}
  - Pattern strength: {pattern_strength}
  - Multi-TF alignment: {multi_tf_alignment}

- Liquidity: {liquidity_score} ({weight}%)
  - Liquidity depth: {liquidity_depth}
  - Liquidity quality: {liquidity_quality}
  - Spread tightness: {spread_tightness}
  - Stability: {stability}

[... other components ...]

LIMITATIONS:
- [List of limitations]

UNCERTAINTY:
- [List of uncertainty notes]
```

---

### 7.3 Context Output Schema

```python
@dataclass
class MarketContextScore:
    score_id: str
    instrument_id: str
    timestamp: datetime
    
    # Overall Score
    overall_score: float
    score_bucket: str
    
    # Component Scores
    structure_score: float
    liquidity_score: float
    ipd_score: float
    regime_score: float
    session_score: float
    volatility_score: float
    
    # Score Breakdown
    score_breakdown: Dict[str, Any]
    
    # Weights Used
    weights: Dict[str, float]
    
    # Configuration
    config_version: str
    
    # Explainability
    explanation: str
    limitations: List[str]
    uncertainty_notes: List[str]
    
    # Metadata
    version: str
```

---

## 8. Explainability

### 8.1 Overview
Every market classification must produce a structured explanation ensuring transparency and auditability.

### 8.2 Explanation Schema

```python
@dataclass
class MarketExplanation:
    explanation_id: str
    classification_type: str
    instrument_id: str
    timestamp: datetime
    
    # Summary
    summary: str
    
    # Supporting Evidence
    supporting_evidence: List[str]
    evidence_strength: Dict[str, float]
    
    # Conflicting Evidence
    conflicting_evidence: List[str]
    conflict_strength: Dict[str, float]
    
    # Confidence
    confidence: float
    confidence_breakdown: Dict[str, float]
    
    # Limitations
    limitations: List[str]
    
    # Uncertainty Notes
    uncertainty_notes: List[str]
    
    # Data Quality
    data_quality: float
    data_freshness: float
    
    # Metadata
    explanation_version: str
    generated_by: str
```

### 8.3 Explanation Templates

#### 8.3.1 Structure Explanation

```
MARKET STRUCTURE: {structure_type}

SUMMARY:
{summary of current structure}

SUPPORTING EVIDENCE:
✓ {evidence 1} (strength: {strength})
✓ {evidence 2} (strength: {strength})
✓ {evidence 3} (strength: {strength})

CONFLICTING EVIDENCE:
✗ {conflict 1} (strength: {strength})
✗ {conflict 2} (strength: {strength})

CONFIDENCE: {confidence}%

CONFIDENCE BREAKDOWN:
- Structure clarity: {score}
- Pattern strength: {score}
- Multi-TF alignment: {score}

LIMITATIONS:
- {limitation 1}
- {limitation 2}

UNCERTAINTY:
- {uncertainty note 1}
- {uncertainty note 2}
```

---

#### 8.3.2 Liquidity Explanation

```
LIQUIDITY ANALYSIS: {liquidity_state}

SUMMARY:
{summary of liquidity conditions}

BUY-SIDE LIQUIDITY:
- Level: {level}
- Confidence: {confidence}
- Key areas: {areas}

SELL-SIDE LIQUIDITY:
- Level: {level}
- Confidence: {confidence}
- Key areas: {areas}

KEY LEVELS:
- Equal highs: {count} at {level}
- Equal lows: {count} at {level}
- Liquidity pools: {count} identified

RECENT EVENTS:
- Stop run at {level}
- Liquidity sweep at {level}

LIMITATIONS:
- {limitation 1}
- {limitation 2}
```

---

#### 8.3.3 Regime Explanation

```
MARKET REGIME: {regime}

SUMMARY:
{summary of current regime}

REGIME CHARACTERISTICS:
- Trend strength: {strength}
- Volatility state: {state}
- Momentum: {momentum}

TRANSITION INDICATORS:
- {signal 1}: {probability}
- {signal 2}: {probability}

CONFIDENCE: {confidence}%

LIMITATIONS:
- {limitation 1}
- {limitation 2}

UNCERTAINTY:
- Regime may be transitioning
- Low confidence in {aspect}
```

---

## 9. Historical Validation Framework

### 9.1 Overview
The Historical Validation Framework ensures every intelligence module is validated using historical data to ensure reliability and accuracy.

### 9.2 Validation Datasets

**Dataset Requirements:**
- Minimum 5 years of historical data
- Multiple market conditions (trending, ranging, volatile)
- Multiple instruments
- Tick data where possible
- Event data (news, holidays)

**Dataset Composition:**
- Training set: 60% (for parameter tuning)
- Validation set: 20% (for threshold validation)
- Test set: 20% (for final validation)

**Data Quality:**
- Data completeness checks
- Data quality validation
- Gap handling
- Outlier detection

---

### 9.3 Reproducibility

**Requirements:**
- All validation results must be reproducible
- Random seed fixed for any stochastic components
- Configuration versioning
- Data versioning

**Reproducibility Process:**
```
1. Store configuration version
2. Store data version (hash)
3. Store random seed
4. Run validation
5. Store results with metadata
6. Re-run to validate reproducibility
```

---

### 9.4 Confidence Tracking

**Confidence Calibration:**
- Compare predicted confidence with actual outcomes
- Calibrate confidence scores
- Track confidence accuracy over time
- Adjust confidence models if needed

**Confidence Metrics:**
- Calibration curve
- Brier score
- Reliability diagram
- Confidence intervals

---

### 9.5 Regression Testing

**Test Suite:**
- Unit tests for each module
- Integration tests for module interactions
- End-to-end tests for complete pipeline
- Performance tests

**Regression Detection:**
- Compare current results with baseline
- Detect performance degradation
- Alert on significant changes
- Rollback if needed

---

### 9.6 Benchmark Comparisons

**Benchmarks:**
- Random baseline
- Simple technical indicators
- Commercial services (if available)
- Academic models

**Comparison Metrics:**
- Accuracy
- Precision
- Recall
- F1 score
- Profitability (for trading-related modules)

---

### 9.7 Validation Output Schema

```python
@dataclass
class ValidationResults:
    validation_id: str
    module_name: str
    validation_timestamp: datetime
    
    # Dataset
    dataset_version: str
    data_period: DateRange
    instrument_count: int
    
    # Results
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    
    # Confidence Calibration
    calibration_score: float
    brier_score: float
    
    # Benchmark Comparison
    baseline_comparison: Dict[str, float]
    
    # Regression Test
    regression_passed: bool
    performance_delta: float
    
    # Configuration
    config_version: str
    random_seed: int
    
    # Reproducibility
    is_reproducible: bool
    reproducibility_check: str
    
    # Metadata
    version: str
```

---

## 10. Architecture Diagrams

### 10.1 MIRE Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Market Intelligence Research Engine                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐                                                            │
│  │ Market Data  │                                                            │
│  └──────┬───────┘                                                            │
│         ↓                                                                    │
│  ┌──────────────┐                                                            │
│  │ Structure    │                                                            │
│  │ Intelligence │                                                            │
│  └──────┬───────┘                                                            │
│         ↓                                                                    │
│  ┌──────────────┐                                                            │
│  │ Liquidity    │                                                            │
│  │ Intelligence │                                                            │
│  └──────┬───────┘                                                            │
│         ↓                                                                    │
│  ┌──────────────┐                                                            │
│  │ IPD Engine   │                                                            │
│  └──────┬───────┘                                                            │
│         ↓                                                                    │
│  ┌──────────────┐                                                            │
│  │ Regime       │                                                            │
│  │ Intelligence │                                                            │
│  └──────┬───────┘                                                            │
│         ↓                                                                    │
│  ┌──────────────┐                                                            │
│  │ Session      │                                                            │
│  │ Intelligence │                                                            │
│  └──────┬───────┘                                                            │
│         ↓                                                                    │
│  ┌──────────────┐                                                            │
│  │ Volatility   │                                                            │
│  │ Intelligence │                                                            │
│  └──────┬───────┘                                                            │
│         ↓                                                                    │
│  ┌──────────────┐                                                            │
│  │ Context      │                                                            │
│  │ Scoring     │                                                            │
│  └──────┬───────┘                                                            │
│         ↓                                                                    │
│  ┌──────────────┐                                                            │
│  │ Explainability│                                                            │
│  │ Engine       │                                                            │
│  └──────┬───────┘                                                            │
│         ↓                                                                    │
│  ┌──────────────┐                                                            │
│  │ Validation   │                                                            │
│  │ Framework    │                                                            │
│  └──────────────┘                                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Data Flow Diagram

```
Market Data → Structure Intelligence → Liquidity Intelligence → IPD Engine
                                                              ↓
Market Data → Regime Intelligence → Session Intelligence → Volatility Intelligence
                                                              ↓
                                                             Context Scoring
                                                              ↓
                                                          Explainability Engine
                                                              ↓
                                                          Validation Framework
```

### 10.3 State Diagram - Market Structure

```
                    ┌─────────────┐
                    │   Unknown    │
                    └──────┬──────┘
                           │
                    [Structure Detected]
                           ↓
                    ┌─────────────┐
                    │  Trending    │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
         [Continuation]              [Transition]
              │                         │
              ↓                         ↓
         ┌──────────┐              ┌──────────┐
         │  Strong  │              │  Weakening│
         └────┬─────┘              └────┬─────┘
              │                         │
         [CHoCH]                  [CHoCH]
              │                         │
              ↓                         ↓
         ┌──────────┐              ┌──────────┐
         │ Reversal │              │  Ranging  │
         └──────────┘              └────┬─────┘
                                      │
                              [Breakout]
                                      │
                                      ↓
                                 ┌──────────┐
                                 │ Expansion│
                                 └──────────┘
```

---

## 11. Extension Points

### 11.1 Additional Structure Modules
- Fibonacci structure levels
- Harmonic patterns
- Elliott Wave analysis
- Wyckoff methodology

### 11.2 Advanced Liquidity Analysis
- Order flow analysis
- Footprint charts
- Delta analysis
- Volume profile advanced

### 11.3 Additional IPD Concepts
- Volume profile analysis
- VWAP bands
- Market profile
- Delta footprint

### 11.4 Machine Learning Integration
- ML-based structure detection
- ML-based regime classification
- Anomaly detection
- Pattern recognition

### 11.5 Multi-Asset Analysis
- Cross-asset correlation
- Currency strength analysis
- Commodity analysis
- Equity index analysis

---

## 12. Risks and Assumptions

### 12.1 Technical Risks

**Risk: Data Quality Issues**
- Impact: Incorrect classifications
- Mitigation: Data validation, quality scoring, fallback mechanisms

**Risk: Latency Issues**
- Impact: Stale classifications
- Mitigation: Timestamp validation, freshness tracking

**Risk: Computational Complexity**
- Impact: Slow processing
- Mitigation: Optimization, caching, parallel processing

---

### 12.2 Model Risks

**Risk: Overfitting**
- Impact: Poor out-of-sample performance
- Mitigation: Cross-validation, regularization, walk-forward testing

**Risk: Concept Ambiguity**
- Impact: Inconsistent classifications
- Mitigation: Clear definitions, confidence scoring, explainability

**Risk: False Signals**
- Impact: Incorrect trading decisions
- Mitigation: Confidence thresholds, validation, historical testing

---

### 12.3 Market Risks

**Risk: Regime Changes**
- Impact: Models become invalid
- Mitigation: Continuous monitoring, regime detection, model adaptation

**Risk: Black Swan Events**
- Impact: Extreme market behavior
- Mitigation: Safety layer, abnormality detection, conservative thresholds

**Risk: Structural Changes**
- Impact: Market structure changes
- Mitigation: Continuous validation, adaptation mechanisms

---

### 12.4 Assumptions

**Assumption: Order Book Availability**
- Not all brokers provide order book data
- Mitigation: Price action proxies, volume analysis

**Assumption: Historical Patterns Repeat**
- Past patterns may not predict future
- Mitigation: Confidence scoring, continuous validation

**Assumption: Markets Are Efficient**
- Markets may not always be efficient
- Mitigation: Inefficiency detection, anomaly detection

**Assumption: Timeframe Independence**
- Patterns may not work across all timeframes
- Mitigation: Multi-timeframe analysis, timeframe-specific models

---

**Document Status:** Draft  
**Next Review:** August 2026  
**Approved By:** [Pending]
