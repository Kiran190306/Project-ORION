# Trading Decision Intelligence Engine (TDIE)
## Phase 3 Architecture Specification

**Document Version:** 1.0  
**Date:** July 2026  
**Classification:** Confidential  
**Status:** Draft  
**Predecessors:** ARCHITECTURE.md (SRS), TRADING_CORE_ARCHITECTURE.md (Core Trading Engine)

---

## Table of Contents

1. [Decision Engine Overview](#1-decision-engine-overview)
2. [Market Context Engine](#2-market-context-engine)
3. [Strategy Selection Framework](#3-strategy-selection-framework)
4. [Signal Scoring Framework](#4-signal-scoring-framework)
5. [Signal Conflict Resolution](#5-signal-conflict-resolution)
6. [Opportunity Ranking Engine](#6-opportunity-ranking-engine)
7. [Position Lifecycle Intelligence](#7-position-lifecycle-intelligence)
8. [Explainability Engine](#8-explainability-engine)
9. [Learning & Evaluation Framework](#9-learning--evaluation-framework)
10. [Safety Layer](#10-safety-layer)
11. [Simulation Compatibility](#11-simulation-compatibility)
12. [Architecture Diagrams](#12-architecture-diagrams)
13. [Engineering Rationale](#13-engineering-rationale)
14. [Extension Points](#14-extension-points)
15. [Risks and Mitigations](#15-risks-and-mitigations)

---

## 1. Decision Engine Overview

### 1.1 Purpose
The Trading Decision Intelligence Engine (TDIE) serves as the central decision-making brain of the platform. It orchestrates the complete decision pipeline from market data ingestion to trade execution, ensuring all decisions are deterministic, explainable, risk-aware, and reproducible.

### 1.2 Decision Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Trading Decision Intelligence Engine                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Market Data                                                               │
│       ↓                                                                     │
│  Market Regime Detection                                                    │
│       ↓                                                                     │
│  Market Context Engine                                                      │
│       ↓                                                                     │
│  Strategy Selection Framework                                               │
│       ↓                                                                     │
│  Signal Generation (from selected strategies)                               │
│       ↓                                                                     │
│  Signal Scoring Framework                                                    │
│       ↓                                                                     │
│  Signal Validation Pipeline                                                 │
│       ↓                                                                     │
│  Risk Validation                                                            │
│       ↓                                                                     │
│  Signal Conflict Resolution                                                  │
│       ↓                                                                     │
│  Opportunity Ranking Engine                                                 │
│       ↓                                                                     │
│  Execution Approval                                                         │
│       ↓                                                                     │
│  Order Execution                                                            │
│       ↓                                                                     │
│  Position Monitoring                                                        │
│       ↓                                                                     │
│  Exit Decision                                                              │
│       ↓                                                                     │
│  Trade Completion                                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Core Responsibilities

**Decision Orchestration:**
- Coordinate all decision-making components
- Ensure decision pipeline execution order
- Manage decision state transitions
- Handle decision pipeline failures

**Context Management:**
- Maintain current market context
- Track context changes over time
- Provide context to all decision components
- Log context transitions

**Strategy Orchestration:**
- Select eligible strategies based on context
- Manage strategy lifecycle
- Coordinate strategy execution
- Track strategy performance

**Signal Management:**
- Collect signals from strategies
- Score and rank signals
- Resolve conflicts between signals
- Validate signals against policies

**Risk Oversight:**
- Ensure all decisions respect risk policies
- Monitor risk exposure in real-time
- Override decisions that violate risk limits
- Trigger emergency procedures when needed

**Explainability:**
- Generate explanations for all decisions
- Maintain decision audit trail
- Provide decision transparency
- Support decision replay and analysis

### 1.4 Inputs

**Real-Time Inputs:**
- Market data (ticks, candles)
- Market regime classifications
- Current positions
- Pending orders
- Account state
- Risk metrics

**Configuration Inputs:**
- Strategy configurations
- Risk policy configurations
- Scoring model configurations
- Context threshold configurations
- Decision rule configurations

**Historical Inputs:**
- Historical market data
- Historical strategy performance
- Historical execution quality
- Historical signal outcomes

### 1.5 Outputs

**Decision Outputs:**
- Trade execution decisions (approve/reject)
- Position modification decisions
- Exit decisions
- No-trade decisions

**State Outputs:**
- Current market context
- Active strategy set
- Signal queue
- Decision audit trail

**Monitoring Outputs:**
- Decision metrics
- Context metrics
- Strategy metrics
- Risk metrics

**Explainability Outputs:**
- Decision explanations
- Rejection reasons
- Confidence scores
- Factor contributions

### 1.6 State Transitions

```
┌─────────────┐
│   Idle      │
└──────┬──────┘
       │
   [Data Available]
       ↓
┌─────────────┐
│  Context    │
│  Analysis   │
└──────┬──────┘
       │
   [Context Ready]
       ↓
┌─────────────┐
│  Strategy   │
│ Selection   │
└──────┬──────┘
       │
   [Strategies Selected]
       ↓
┌─────────────┐
│  Signal     │
│ Generation  │
└──────┬──────┘
       │
   [Signals Available]
       ↓
┌─────────────┐
│  Signal     │
│  Scoring    │
└──────┬──────┘
       │
   [Signals Scored]
       ↓
┌─────────────┐
│  Validation │
└──────┬──────┘
       │
   [Validated]
       ↓
┌─────────────┐
│  Conflict   │
│ Resolution  │
└──────┬──────┘
       │
   [Resolved]
       ↓
┌─────────────┐
│  Ranking    │
└──────┬──────┘
       │
   [Ranked]
       ↓
┌─────────────┐
│  Execution  │
│  Decision   │
└──────┬──────┘
       │
   [Decision Made]
       ↓
┌─────────────┐
│  Monitoring │
└──────┬──────┘
       │
   [Position Active]
       ↓
┌─────────────┐
│  Exit       │
│  Decision   │
└──────┬──────┘
       │
   [Exit Executed]
       ↓
┌─────────────┐
│   Idle      │
└─────────────┘
```

**State Transition Rules:**
- Each state has entry conditions and exit conditions
- State transitions are logged with context
- Invalid transitions trigger error handling
- State can be forced to Idle on critical errors

### 1.7 Decision Boundaries

**Entry Decision Boundaries:**
- Minimum context confidence: 0.60
- Minimum signal score: 0.50
- Maximum spread: 3 pips (configurable)
- Minimum liquidity: configurable
- Risk policy compliance: required

**Exit Decision Boundaries:**
- Stop loss hit: immediate exit
- Take profit hit: immediate exit
- Signal reversal: evaluate context
- Risk limit breach: immediate exit
- Context degradation: evaluate

**No-Trade Boundaries:**
- Context confidence < 0.40
- Signal score < 0.30
- Spread > threshold
- Risk limit near breach
- Abnormal market conditions

### 1.8 Recovery Behavior

**Context Analysis Failure:**
- Use last known context with degrading confidence
- If confidence < 0.30: transition to Idle
- Alert on context analysis failure
- Manual review required if persistent

**Strategy Selection Failure:**
- Use last known strategy set
- If no strategies available: transition to Idle
- Alert on selection failure
- Fallback to conservative strategy if configured

**Signal Generation Failure:**
- If strategy fails: disable strategy, continue with others
- If all strategies fail: transition to Idle
- Alert on strategy failures
- Log detailed error information

**Validation Failure:**
- Reject signal with specific reason
- Continue with other signals
- Alert on validation failures
- Track validation failure rate

**Conflict Resolution Failure:**
- Default to no-trade decision
- Alert on resolution failure
- Log conflict details
- Manual review required

**Execution Decision Failure:**
- Default to no-trade (safety first)
- Alert immediately
- Hold position if already open
- Manual intervention required

---

## 2. Market Context Engine

### 2.1 Overview
The Market Context Engine evaluates multiple dimensions of the market to determine the current trading environment. This context serves as the foundation for all subsequent decisions.

### 2.2 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Market Context Engine                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Trend       │  │  Range       │  │  Volatility  │         │
│  │  Context     │  │  Context     │  │  Context     │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
│         └─────────────────┴─────────────────┘                  │
│                           ↓                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Liquidity   │  │  Session     │  │  HTF/LTF     │         │
│  │  Context     │  │  Context     │  │  Alignment    │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
│         └─────────────────┴─────────────────┘                  │
│                           ↓                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Spread      │  │  Abnormal    │  │  Composite   │         │
│  │  Context     │  │  Behaviour   │  │  Context     │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
│         └─────────────────┴─────────────────┘                  │
│                           ↓                                      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              Context Aggregator                        │      │
│  │  - Weight combination                                 │      │
│  │  - Confidence calculation                             │      │
│  │  - Context classification                            │      │
│  └──────────────────────┬───────────────────────────────┘      │
│                           ↓                                      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              Context Publisher                        │      │
│  │  - Context events                                    │      │
│  │  - State persistence                                 │      │
│  │  - Change detection                                  │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Context Dimensions

#### 2.3.1 Trend Context

**Purpose:** Classify the current trend state

**Required Inputs:**
- OHLCV data (multiple timeframes)
- Moving averages (20, 50, 200 period)
- ADX values
- Directional movement indicators (+DI, -DI)
- Linear regression slope

**Context States:**
- **Strong Up Trend:** Higher highs, higher lows, ADX > 25, +DI > -DI
- **Weak Up Trend:** Upward bias but with pullbacks, ADX 15-25
- **No Trend:** Ranging, ADX < 20
- **Weak Down Trend:** Downward bias with rallies, ADX 15-25
- **Strong Down Trend:** Lower highs, lower lows, ADX > 25, -DI > +DI

**Confidence Estimation:**
```
confidence = (adx_score × 0.4) + (ma_alignment_score × 0.3) + (slope_score × 0.3)

where:
- adx_score: normalized ADX (0-1 based on 0-50 range)
- ma_alignment_score: how well MAs are aligned (0-1)
- slope_score: strength of trend slope (0-1)
```

**Update Frequency:** Every candle (M1 for primary, M5/M15 for confirmation)

**Failure Handling:**
- If indicators unavailable: use price action only
- If conflicting signals: return "No Trend" with low confidence
- If calculation error: return "Unknown" with confidence 0.0

---

#### 2.3.2 Range Context

**Purpose:** Identify ranging vs trending markets

**Required Inputs:**
- OHLCV data
- Bollinger Bands
- Price range statistics
- Support/resistance levels

**Context States:**
- **Tight Range:** Price within narrow band, BB width < threshold
- **Normal Range:** Price oscillating within defined range
- **Wide Range:** Large price swings but no directional trend
- **Breakout:** Price breaking out of range
- **Range Expansion:** Range widening rapidly

**Confidence Estimation:**
```
confidence = (bb_width_score × 0.4) + (range_stability_score × 0.3) + (price_position_score × 0.3)
```

**Update Frequency:** Every candle (M5 for primary)

**Failure Handling:**
- If BB unavailable: use simple range calculation
- If range undefined: return "Unknown"
- If calculation error: use last known range context

---

#### 2.3.3 Volatility Context

**Purpose:** Classify current volatility regime

**Required Inputs:**
- ATR values (multiple periods)
- Bollinger Band width
- Historical volatility
- Realized volatility

**Context States:**
- **Very Low:** ATR < 50% of average
- **Low:** ATR 50-75% of average
- **Normal:** ATR 75-125% of average
- **High:** ATR 125-200% of average
- **Very High:** ATR > 200% of average

**Confidence Estimation:**
```
confidence = (atr_ratio_score × 0.5) + (bb_width_score × 0.3) + (hv_score × 0.2)
```

**Update Frequency:** Every candle (M15 for primary, H1 for trend)

**Failure Handling:**
- If ATR unavailable: use BB width only
- If historical data unavailable: use recent data only
- If calculation error: return "Normal" with low confidence

---

#### 2.3.4 Liquidity Conditions

**Purpose:** Assess current market liquidity

**Required Inputs:**
- Tick frequency
- Bid-ask spread
- Order book depth (if available)
- Trading volume
- Time of day

**Context States:**
- **High Liquidity:** High tick rate, tight spread, high volume
- **Normal Liquidity:** Normal tick rate, normal spread, normal volume
- **Low Liquidity:** Low tick rate, wide spread, low volume
- **Very Low Liquidity:** Very low tick rate, very wide spread, very low volume

**Confidence Estimation:**
```
confidence = (tick_rate_score × 0.3) + (spread_score × 0.3) + (volume_score × 0.2) + (time_score × 0.2)
```

**Update Frequency:** Every 10 seconds (tick-based)

**Failure Handling:**
- If tick rate unavailable: use spread and volume only
- If order book unavailable: use tick rate and spread only
- If calculation error: return "Normal Liquidity" with low confidence

---

#### 2.3.5 Session Context

**Purpose:** Identify current trading session

**Required Inputs:**
- Current UTC time
- Session definitions for instrument
- Day of week
- Holiday calendar

**Context States:**
- **Asian Session:** Tokyo trading hours
- **London Session:** London trading hours
- **New York Session:** New York trading hours
- **Overlap:** London/NY overlap
- **Off-Hours:** Outside major sessions
- **Weekend:** Weekend hours

**Confidence Estimation:**
```
confidence = 1.0 (deterministic based on time)
```

**Update Frequency:** Every minute

**Failure Handling:**
- If session definitions unavailable: use basic UTC time zones
- If holiday calendar unavailable: ignore holidays
- If calculation error: return "Off-Hours"

---

#### 2.3.6 Higher-Timeframe Alignment

**Purpose:** Check alignment across multiple timeframes

**Required Inputs:**
- Trend context from H1, H4, D1 timeframes
- Support/resistance levels across timeframes
- Key levels alignment

**Context States:**
- **Aligned:** All timeframes agree
- **Mostly Aligned:** Majority agree
- **Conflicting:** Timeframes disagree
- **Unknown:** Insufficient data

**Confidence Estimation:**
```
confidence = (agreement_ratio × 1.0)

where agreement_ratio = number of agreeing TFs / total TFs
```

**Update Frequency:** Every H1 candle

**Failure Handling:**
- If higher TF data unavailable: use available TFs only
- If calculation error: return "Unknown"

---

#### 2.3.7 Lower-Timeframe Timing

**Purpose:** Identify optimal entry timing on lower timeframes

**Required Inputs:**
- M1, M5 data
- Short-term momentum
- Intraday patterns
- Volume spikes

**Context States:**
- **Optimal:** Favorable short-term conditions
- **Acceptable:** Normal short-term conditions
- **Suboptimal:** Unfavorable short-term conditions
- **Poor:** Very unfavorable short-term conditions

**Confidence Estimation:**
```
confidence = (momentum_score × 0.4) + (pattern_score × 0.3) + (volume_score × 0.3)
```

**Update Frequency:** Every M1 candle

**Failure Handling:**
- If lower TF data unavailable: return "Acceptable"
- If calculation error: return "Unknown"

---

#### 2.3.8 Spread Conditions

**Purpose:** Evaluate current spread relative to normal

**Required Inputs:**
- Current spread
- Average spread (configurable window)
- Spread statistics
- Time of day

**Context States:**
- **Tight:** Spread < 0.5 × average
- **Normal:** Spread 0.5-1.5 × average
- **Wide:** Spread 1.5-3 × average
- **Very Wide:** Spread > 3 × average

**Confidence Estimation:**
```
confidence = 1.0 - (spread_deviation / max_deviation)
```

**Update Frequency:** Every tick

**Failure Handling:**
- If spread data unavailable: return "Normal"
- If average unavailable: use fixed thresholds
- If calculation error: return "Unknown"

---

#### 2.3.9 Abnormal Market Behaviour

**Purpose:** Detect unusual market conditions

**Required Inputs:**
- Price gaps
- Spike detection
- Volume anomalies
- Correlation breakdowns
- News events

**Context States:**
- **Normal:** No abnormalities detected
- **Minor Anomaly:** Minor unusual behavior
- **Major Anomaly:** Significant unusual behavior
- **Severe Anomaly:** Extreme unusual behavior

**Confidence Estimation:**
```
confidence = (1.0 - anomaly_score) where anomaly_score is 0-1
```

**Update Frequency:** Every candle (M5)

**Failure Handling:**
- If detection unavailable: return "Normal"
- If calculation error: return "Unknown"

---

### 2.4 Composite Context

**Purpose:** Combine all context dimensions into overall market context

**Composite States:**
- **Favorable:** Most dimensions favorable for trading
- **Acceptable:** Some dimensions unfavorable but acceptable
- **Marginal:** Many dimensions unfavorable
- **Unfavorable:** Most dimensions unfavorable
- **Dangerous:** Severe unfavorable conditions

**Composite Confidence:**
```
overall_confidence = Σ(context_confidence × context_weight) / Σ(context_weight)

Default weights:
- Trend Context: 0.20
- Range Context: 0.10
- Volatility Context: 0.15
- Liquidity Context: 0.15
- Session Context: 0.10
- HTF Alignment: 0.10
- LTF Timing: 0.05
- Spread Context: 0.10
- Abnormal Behaviour: 0.05
```

**Context Classification Rules:**
```
if overall_confidence >= 0.75: Favorable
elif overall_confidence >= 0.60: Acceptable
elif overall_confidence >= 0.45: Marginal
elif overall_confidence >= 0.30: Unfavorable
else: Dangerous
```

**Update Frequency:** Every M1 candle (triggered by any context change)

**Failure Handling:**
- If any context unavailable: exclude from composite
- If all contexts unavailable: return "Unknown" with confidence 0.0
- If calculation error: use last known composite context

---

## 3. Strategy Selection Framework

### 3.1 Overview
The Strategy Selection Framework determines which strategies are eligible for execution under current market conditions using rule-based orchestration.

### 3.2 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                Strategy Selection Framework                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐                                               │
│  │  Market      │                                               │
│  │  Context     │                                               │
│  └──────┬───────┘                                               │
│         ↓                                                        │
│  ┌──────────────┐                                               │
│  │  Strategy    │                                               │
│  │  Registry   │                                               │
│  └──────┬───────┘                                               │
│         ↓                                                        │
│  ┌──────────────┐                                               │
│  │  Eligibility │                                               │
│  │  Filter     │                                               │
│  │  - Market conditions                                        │
│  │  - Session compatibility                                     │
│  │  - Symbol support                                          │
│  │  - Volatility range                                         │
│  └──────┬───────┘                                               │
│         ↓                                                        │
│  ┌──────────────┐                                               │
│  │  Dependency  │                                               │
│  │  Manager    │                                               │
│  │  - Strategy dependencies                                    │
│  │  - Resource conflicts                                       │
│  └──────┬───────┘                                               │
│         ↓                                                        │
│  ┌──────────────┐                                               │
│  │  Conflict    │                                               │
│  │  Resolver   │                                               │
│  │  - Priority hierarchy                                       │
│  │  - Mutual exclusion                                         │
│  └──────┬───────┘                                               │
│         ↓                                                        │
│  ┌──────────────┐                                               │
│  │  Health      │                                               │
│  │  Scorer     │                                               │
│  │  - Performance metrics                                      │
│  │  - Error rates                                             │
│  └──────┬───────┘                                               │
│         ↓                                                        │
│  ┌──────────────┐                                               │
│  │  Priority    │                                               │
│  │  Ranker     │                                               │
│  │  - Priority rules                                          │
│  │  - User preferences                                        │
│  └──────┬───────┘                                               │
│         ↓                                                        │
│  ┌──────────────┐                                               │
│  │  Active Set  │                                               │
│  │  Selector   │                                               │
│  │  - Max strategies limit                                     │
│  │  - Diversity requirements                                   │
│  └──────┬───────┘                                               │
│         ↓                                                        │
│  ┌──────────────┐                                               │
│  │  Selected    │                                               │
│  │  Strategies │                                               │
│  └──────────────┘                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Strategy Metadata Schema

```python
@dataclass
class StrategyMetadata:
    # Identification
    id: str
    name: str
    version: str
    category: StrategyCategory
    
    # Market Compatibility
    supported_regimes: List[Regime]  # Trending, Ranging, etc.
    preferred_regimes: List[Regime]
    blocked_regimes: List[Regime]
    
    # Session Compatibility
    supported_sessions: List[Session]  # Asian, London, NY, etc.
    preferred_sessions: List[Session]
    blocked_sessions: List[Session]
    
    # Symbol Support
    supported_symbols: List[str]
    supported_asset_classes: List[AssetClass]
    blocked_symbols: List[str]
    
    # Volatility Compatibility
    min_volatility: Optional[VolatilityLevel]
    max_volatility: Optional[VolatilityLevel]
    preferred_volatility: VolatilityLevel
    
    # Risk Profile
    risk_level: RiskLevel  # low, medium, high, very_high
    max_risk_per_trade: Decimal
    max_position_size: Decimal
    uses_leverage: bool
    max_leverage: Decimal
    
    # Performance
    historical_win_rate: Optional[Decimal]
    historical_sharpe: Optional[Decimal]
    historical_max_dd: Optional[Decimal]
    sample_size: int  # Number of trades in history
    
    # Dependencies
    required_strategies: List[str]  # Strategies that must be active
    conflicting_strategies: List[str]  # Strategies that cannot be active
    required_indicators: List[str]
    
    # Priority
    priority: int  # 1-100, higher = higher priority
    enabled: bool
    
    # Health
    health_score: float  # 0.0-1.0
    error_rate: float  # 0.0-1.0
    last_error: Optional[str]
    last_successful_execution: Optional[datetime]
```

### 3.4 Eligibility Filter

**Filter Rules:**

1. **Market Condition Filter**
   ```
   if current_regime in strategy.blocked_regimes: ineligible
   if current_regime in strategy.supported_regimes: eligible
   if current_regime in strategy.preferred_regimes: boost priority
   ```

2. **Session Filter**
   ```
   if current_session in strategy.blocked_sessions: ineligible
   if current_session in strategy.supported_sessions: eligible
   if current_session in strategy.preferred_sessions: boost priority
   ```

3. **Symbol Filter**
   ```
   if instrument in strategy.blocked_symbols: ineligible
   if instrument in strategy.supported_symbols: eligible
   if asset_class in strategy.supported_asset_classes: eligible
   ```

4. **Volatility Filter**
   ```
   if current_volatility < strategy.min_volatility: ineligible
   if current_volatility > strategy.max_volatility: ineligible
   if current_volatility == strategy.preferred_volatility: boost priority
   ```

5. **Health Filter**
   ```
   if strategy.health_score < 0.30: ineligible
   if strategy.error_rate > 0.50: ineligible
   if not strategy.enabled: ineligible
   ```

**Eligibility Score:**
```
eligibility_score = base_score + priority_boosts - priority_penalties

base_score = 1.0 if all basic filters pass, 0.0 otherwise
priority_boosts = +0.1 for each preferred condition match
priority_penalties = -0.2 for each warning condition
```

### 3.5 Dependency Manager

**Dependency Resolution:**

1. **Required Strategies**
   ```
   if strategy.required_strategies not empty:
       check if all required strategies are eligible
       if any required strategy ineligible: mark strategy as ineligible
   ```

2. **Conflicting Strategies**
   ```
   if strategy.conflicting_strategies not empty:
       check if any conflicting strategy is selected
       if conflict exists: apply conflict resolution
   ```

3. **Resource Conflicts**
   ```
   check resource requirements (CPU, memory)
   check if resources available
   if insufficient resources: deprioritize or exclude
   ```

**Dependency Graph:**
- Build dependency graph from all strategies
- Topological sort to determine execution order
- Detect circular dependencies (error)
- Validate dependency satisfaction before selection

### 3.6 Conflict Resolver

**Conflict Types:**

1. **Mutual Exclusion**
   ```
   if strategy A and strategy B have mutual exclusion:
       select based on priority
       if priorities equal: select based on health score
       if health scores equal: select based on recent performance
   ```

2. **Resource Competition**
   ```
   if strategies compete for limited resources:
       allocate resources to higher priority strategies
       deprioritize lower priority strategies
   ```

3. **Signal Conflict**
   ```
   if strategies generate conflicting signals:
       defer to signal conflict resolution (see Section 5)
   ```

**Resolution Hierarchy:**
1. User-defined priority
2. Health score
3. Historical performance (Sharpe ratio)
4. Recent performance (last 30 trades)
5. Random (last resort)

### 3.7 Health Scorer

**Health Metrics:**

1. **Performance Health**
   ```
   performance_health = (recent_sharpe / max_sharpe) × 0.5 + (recent_win_rate / max_win_rate) × 0.5
   ```

2. **Execution Health**
   ```
   execution_health = 1.0 - error_rate
   ```

3. **Stability Health**
   ```
   stability_health = 1.0 - (recent_drawdown / max_acceptable_drawdown)
   ```

4. **Overall Health**
   ```
   overall_health = (performance_health × 0.4) + (execution_health × 0.3) + (stability_health × 0.3)
   ```

**Health Thresholds:**
- Excellent: > 0.80
- Good: 0.60 - 0.80
- Fair: 0.40 - 0.60
- Poor: 0.20 - 0.40
- Critical: < 0.20

### 3.8 Priority Ranker

**Priority Calculation:**
```
final_priority = (base_priority × 0.4) + (health_score × 0.3) + (context_match × 0.2) + (user_preference × 0.1)

where:
- base_priority: strategy.priority (1-100)
- health_score: overall_health (0.0-1.0)
- context_match: number of preferred conditions / total preferred conditions
- user_preference: user-defined priority modifier (-0.5 to 0.5)
```

**Priority Rules:**
- Strategies with priority < threshold (default 0.30) are excluded
- Top N strategies selected (configurable, default 5)
- Minimum diversity enforced (at least 2 different categories)

### 3.9 Active Set Selector

**Selection Rules:**

1. **Maximum Strategies Limit**
   ```
   if number of eligible strategies > max_strategies:
       select top max_strategies by priority
   ```

2. **Diversity Requirements**
   ```
   ensure at least N different strategy categories
   ensure at least M different timeframes
   ensure at least K different risk levels
   ```

3. **Resource Allocation**
   ```
   allocate CPU/memory to selected strategies
   monitor resource usage
   adjust if resources insufficient
   ```

**Selection Output:**
```python
@dataclass
class ActiveStrategySet:
    strategies: List[StrategyMetadata]
    selection_timestamp: datetime
    context_snapshot: MarketContext
    selection_reasons: Dict[str, str]
    excluded_strategies: List[str]
    exclusion_reasons: Dict[str, str]
```

### 3.10 Historical Performance Tracking

**Tracked Metrics:**
- Total trades
- Win rate
- Average win
- Average loss
- Profit factor
- Sharpe ratio
- Sortino ratio
- Maximum drawdown
- Average holding time
- Signal generation rate
- Signal acceptance rate

**Performance Update Frequency:**
- Real-time: signal generation, acceptance
- Per trade: outcome, P&L
- Daily: aggregated metrics
- Weekly: performance trends

**Performance-Based Adjustments:**
- Strategies with declining performance: deprioritize
- Strategies with improving performance: prioritize
- Strategies with consistent poor performance: disable
- Strategies with consistent excellent performance: maintain priority

---

## 4. Signal Scoring Framework

### 4.1 Overview
The Signal Scoring Framework provides a transparent, explainable scoring system for evaluating trading signals across multiple dimensions.

### 4.2 Scoring Dimensions

#### 4.2.1 Market Alignment Score

**Purpose:** Evaluate how well the signal aligns with current market conditions

**Factors:**
- Regime alignment (signal direction matches regime)
- Trend alignment (signal direction matches trend)
- Session alignment (signal appropriate for current session)
- Volatility alignment (signal appropriate for volatility level)

**Scoring:**
```
market_alignment = (regime_score × 0.3) + (trend_score × 0.3) + (session_score × 0.2) + (volatility_score × 0.2)

where each factor is 0.0-1.0:
- regime_score: 1.0 if perfect match, 0.0 if opposite
- trend_score: 1.0 if with trend, 0.5 if neutral, 0.0 if against
- session_score: 1.0 if preferred session, 0.5 if acceptable, 0.0 if blocked
- volatility_score: 1.0 if preferred volatility, 0.5 if acceptable, 0.0 if outside range
```

---

#### 4.2.2 Structure Quality Score

**Purpose:** Evaluate the technical structure of the signal

**Factors:**
- Pattern quality (how well-defined is the pattern)
- Support/resistance alignment
- Key level proximity
- Multiple timeframe agreement

**Scoring:**
```
structure_quality = (pattern_score × 0.4) + (level_alignment_score × 0.3) + (mtf_agreement_score × 0.3)

where:
- pattern_score: 1.0 for perfect pattern, 0.0 for no pattern
- level_alignment_score: 1.0 at key level, 0.0 far from levels
- mtf_agreement_score: 1.0 if all TFs agree, 0.0 if all disagree
```

---

#### 4.2.3 Trend Agreement Score

**Purpose:** Evaluate signal alignment with overall trend

**Factors:**
- Primary trend direction (H4/D1)
- Secondary trend direction (H1)
- Momentum alignment
- Trend strength

**Scoring:**
```
trend_agreement = (primary_trend_score × 0.4) + (secondary_trend_score × 0.3) + (momentum_score × 0.3)

where:
- primary_trend_score: 1.0 with strong trend, 0.5 with weak trend, 0.0 against
- secondary_trend_score: 1.0 with trend, 0.5 neutral, 0.0 against
- momentum_score: 1.0 if momentum confirms, 0.0 if momentum opposes
```

---

#### 4.2.4 Volatility Suitability Score

**Purpose:** Evaluate if signal is appropriate for current volatility

**Factors:**
- Volatility level match
- ATR suitability
- Spread relative to volatility
- Expected move vs stop distance

**Scoring:**
```
volatility_suitability = (volatility_match_score × 0.4) + (atr_suitability_score × 0.3) + (spread_atr_ratio_score × 0.3)

where:
- volatility_match_score: 1.0 if perfect match, 0.0 if mismatch
- atr_suitability_score: 1.0 if ATR allows proper SL placement, 0.0 if not
- spread_atr_ratio_score: 1.0 if spread is small relative to ATR, 0.0 if large
```

---

#### 4.2.5 Execution Quality Score

**Purpose:** Evaluate expected execution quality

**Factors:**
- Current spread
- Expected slippage
- Liquidity conditions
- Order book depth (if available)

**Scoring:**
```
execution_quality = (spread_score × 0.3) + (slippage_score × 0.3) + (liquidity_score × 0.2) + (depth_score × 0.2)

where:
- spread_score: 1.0 for tight spread, 0.0 for very wide spread
- slippage_score: 1.0 for low expected slippage, 0.0 for high
- liquidity_score: 1.0 for high liquidity, 0.0 for low liquidity
- depth_score: 1.0 for deep order book, 0.0 for shallow
```

---

#### 4.2.6 Historical Reliability Score

**Purpose:** Evaluate historical performance of similar signals

**Factors:**
- Historical win rate for similar signals
- Historical P&L for similar signals
- Sample size
- Recency of similar signals

**Scoring:**
```
historical_reliability = (win_rate_score × 0.4) + (pnl_score × 0.3) + (sample_size_score × 0.2) + (recency_score × 0.1)

where:
- win_rate_score: 1.0 for >60%, 0.0 for <40%
- pnl_score: 1.0 for positive expectancy, 0.0 for negative
- sample_size_score: 1.0 for >100 samples, 0.0 for <10
- recency_score: 1.0 for signals in last 30 days, 0.0 for >1 year ago
```

---

#### 4.2.7 Risk Quality Score

**Purpose:** Evaluate the risk profile of the signal

**Factors:**
- Risk-reward ratio
- Stop loss distance
- Position size relative to account
- Correlation with existing positions

**Scoring:**
```
risk_quality = (rr_ratio_score × 0.4) + (sl_distance_score × 0.2) + (position_size_score × 0.2) + (correlation_score × 0.2)

where:
- rr_ratio_score: 1.0 for R:R > 2:1, 0.0 for R:R < 1:1
- sl_distance_score: 1.0 for reasonable SL, 0.0 for too tight/wide
- position_size_score: 1.0 for appropriate size, 0.0 for oversized
- correlation_score: 1.0 for low correlation, 0.0 for high correlation
```

---

### 4.3 Weighted Scoring

**Overall Signal Score:**
```
overall_score = (market_alignment × 0.20) + 
                (structure_quality × 0.15) + 
                (trend_agreement × 0.15) + 
                (volatility_suitability × 0.10) + 
                (execution_quality × 0.15) + 
                (historical_reliability × 0.15) + 
                (risk_quality × 0.10)
```

**Configurable Weights:**
- Weights can be customized per strategy
- Weights can be customized per market regime
- Weights can be customized per user preference

### 4.4 Score Normalization

**Normalization Method:**
- All component scores are 0.0-1.0
- Overall score is 0.0-1.0
- No additional normalization needed

**Score Buckets:**
- Excellent: 0.80 - 1.00
- Good: 0.60 - 0.79
- Fair: 0.40 - 0.59
- Poor: 0.20 - 0.39
- Very Poor: 0.00 - 0.19

### 4.5 Confidence Computation

**Signal Confidence:**
```
confidence = overall_score × data_quality_factor × strategy_health_factor

where:
- overall_score: weighted score from 4.3
- data_quality_factor: 0.0-1.0 based on data quality
- strategy_health_factor: 0.0-1.0 based on strategy health
```

**Data Quality Factor:**
```
data_quality_factor = (freshness_score × 0.4) + (completeness_score × 0.3) + (accuracy_score × 0.3)

where:
- freshness_score: 1.0 for fresh data, 0.0 for stale data
- completeness_score: 1.0 for complete data, 0.0 for missing data
- accuracy_score: 1.0 for validated data, 0.0 for unvalidated
```

### 4.6 Thresholds

**Execution Thresholds:**
- Minimum score for execution: 0.50 (configurable)
- Minimum score for consideration: 0.30 (configurable)
- Per-strategy thresholds (overrides global)

**Warning Thresholds:**
- Score below 0.40: warning in explanation
- Score below 0.30: flag for review

### 4.7 Auditability

**Score Breakdown Storage:**
```python
@dataclass
class SignalScore:
    signal_id: str
    overall_score: float
    confidence: float
    
    # Component scores
    market_alignment: float
    structure_quality: float
    trend_agreement: float
    volatility_suitability: float
    execution_quality: float
    historical_reliability: float
    risk_quality: float
    
    # Sub-component scores
    regime_score: float
    trend_score: float
    session_score: float
    volatility_score: float
    pattern_score: float
    level_alignment_score: float
    mtf_agreement_score: float
    # ... (all sub-components)
    
    # Factors
    data_quality_factor: float
    strategy_health_factor: float
    
    # Weights used
    weights: Dict[str, float]
    
    # Timestamp
    scored_at: datetime
```

**Score Explanation:**
- Store full score breakdown
- Store weights used
- Store contributing factors
- Enable score reconstruction

---

## 5. Signal Conflict Resolution

### 5.1 Overview
When multiple strategies generate conflicting signals, the Conflict Resolution Engine determines which signal (if any) should be executed.

### 5.2 Conflict Types

**Directional Conflict:**
- Strategy A: Long
- Strategy B: Short
- Same instrument, same timeframe

**Timing Conflict:**
- Strategy A: Enter now
- Strategy B: Wait for better entry
- Same direction, different timing

**Size Conflict:**
- Strategy A: Large position
- Strategy B: Small position
- Same direction, different sizing

**Instrument Conflict:**
- Strategy A: EURUSD
- Strategy B: GBPUSD
- Different instruments, correlated

### 5.3 Resolution Mechanisms

#### 5.3.1 Priority Hierarchy

**Hierarchy:**
```
1. User-defined priority (highest)
2. Strategy priority (from metadata)
3. Signal score
4. Strategy health score
5. Historical performance
6. Random (lowest)
```

**Resolution Logic:**
```
for each conflicting signal:
    calculate priority_score using hierarchy
select signal with highest priority_score
```

---

#### 5.3.2 Weighted Voting

**Voting Schema:**
```
each strategy gets votes based on:
- signal strength (confidence)
- strategy weight (configurable)
- recent performance

weighted_vote = signal_confidence × strategy_weight × performance_factor
```

**Resolution Logic:**
```
sum votes for long signals
sum votes for short signals
if |long_votes - short_votes| < threshold: no-trade
else: select direction with higher votes
```

---

#### 5.3.3 Market Context Preference

**Context-Based Selection:**
```
if current_regime == trending:
    prefer trend-following strategies
if current_regime == ranging:
    prefer mean-reversion strategies
if current_volatility == high:
    prefer volatility-adapted strategies
```

**Resolution Logic:**
```
for each signal:
    calculate context_match_score
select signal with highest context_match
```

---

#### 5.3.4 Confidence Comparison

**Confidence-Based Selection:**
```
compare signal confidences
if confidence difference < threshold:
    apply additional resolution rules
else:
    select signal with higher confidence
```

**Threshold:**
- Default: 0.10 (10% difference)
- Configurable per strategy pair

---

#### 5.3.5 Signal Expiration

**Expiration Rules:**
```
if signal age > max_age:
    signal is expired
    remove from consideration
```

**Max Age:**
- Default: 60 seconds
- Configurable per strategy
- Configurable per signal type

---

#### 5.3.6 Tie-Breaking Rules

**Tie-Breaking Hierarchy:**
```
1. Most recent signal
2. Strategy with higher historical Sharpe
3. Strategy with lower recent drawdown
4. Strategy with higher priority
5. Random selection
```

---

#### 5.3.7 Abstain/No-Trade Decision

**No-Trade Conditions:**
```
if any of the following:
    - confidence difference < 0.05 (too close to call)
    - conflicting signals have equal priority
    - context is unfavorable (confidence < 0.40)
    - risk limits near breach
    - market conditions abnormal
    - insufficient data for resolution
    
then: no-trade decision
```

**No-Trade Rationale:**
- Always explain why no-trade was chosen
- Log all conflicting signals
- Log resolution attempt
- Store for later analysis

### 5.4 Resolution Workflow

```
1. Detect conflicting signals
2. Classify conflict type
3. Apply primary resolution mechanism (priority hierarchy)
4. If tie: apply secondary mechanism (weighted voting)
5. If still tie: apply tertiary mechanism (context preference)
6. If still tie: apply tie-breaking rules
7. If no clear winner: evaluate no-trade conditions
8. Generate resolution decision
9. Log resolution rationale
10. Publish resolution event
```

### 5.5 Resolution Output Schema

```python
@dataclass
class ConflictResolution:
    resolution_id: str
    conflict_type: ConflictType
    conflicting_signals: List[str]
    resolution_mechanism: str
    resolution_decision: ResolutionDecision  # execute_long, execute_short, no_trade
    selected_signal: Optional[str]
    rejected_signals: List[str]
    rationale: str
    confidence: float
    resolution_timestamp: datetime
```

---

## 6. Opportunity Ranking Engine

### 6.1 Overview
When multiple valid trading opportunities exist simultaneously, the Opportunity Ranking Engine prioritizes them for execution based on multiple factors.

### 6.2 Ranking Factors

#### 6.2.1 Overall Quality

**Components:**
- Signal score (from Section 4)
- Market context quality
- Execution quality
- Risk quality

**Scoring:**
```
quality_score = (signal_score × 0.4) + (context_quality × 0.3) + (execution_quality × 0.2) + (risk_quality × 0.1)
```

---

#### 6.2.2 Expected Reward-to-Risk

**Components:**
- Risk-reward ratio
- Expected win rate
- Expected payoff

**Scoring:**
```
rr_score = (rr_ratio × 0.5) + (win_rate × 0.3) + (payoff × 0.2)

where:
- rr_ratio: normalized to 0-1 (1:1 = 0.0, 3:1 = 1.0)
- win_rate: historical win rate (0-1)
- payoff: average win / average loss (normalized)
```

---

#### 6.2.3 Exposure Constraints

**Components:**
- Current portfolio exposure
- Correlation with existing positions
- Diversification benefit
- Margin usage

**Scoring:**
```
exposure_score = (exposure_headroom × 0.4) + (diversification_benefit × 0.3) + (margin_headroom × 0.3)

where:
- exposure_headroom: 1.0 = lots of room, 0.0 = at limit
- diversification_benefit: 1.0 = high diversification, 0.0 = high correlation
- margin_headroom: 1.0 = lots of margin, 0.0 = margin call risk
```

---

#### 6.2.4 Diversification

**Components:**
- Currency diversity
- Asset class diversity
- Strategy diversity
- Timeframe diversity

**Scoring:**
```
diversification_score = (currency_diversity × 0.3) + (asset_diversity × 0.3) + (strategy_diversity × 0.2) + (timeframe_diversity × 0.2)

where:
- each diversity component: 1.0 = highly diverse, 0.0 = no diversity
```

---

#### 6.2.5 Market Conditions

**Components:**
- Market context favorability
- Liquidity conditions
- Spread conditions
- Volatility appropriateness

**Scoring:**
```
conditions_score = (context_favorability × 0.4) + (liquidity × 0.2) + (spread × 0.2) + (volatility × 0.2)
```

---

#### 6.2.6 Strategy Confidence

**Components:**
- Strategy health score
- Strategy recent performance
- Strategy historical reliability
- Strategy error rate

**Scoring:**
```
strategy_confidence = (health_score × 0.4) + (recent_performance × 0.3) + (historical_reliability × 0.2) + (1 - error_rate) × 0.1)
```

---

### 6.3 Overall Ranking Score

**Composite Score:**
```
ranking_score = (quality_score × 0.25) + 
                (rr_score × 0.20) + 
                (exposure_score × 0.20) + 
                (diversification_score × 0.15) + 
                (conditions_score × 0.10) + 
                (strategy_confidence × 0.10)
```

**Configurable Weights:**
- Weights can be customized per user
- Weights can be customized per risk profile
- Weights can be customized per market regime

### 6.4 Ranking Workflow

```
1. Collect all valid opportunities
2. Calculate ranking factors for each opportunity
3. Calculate composite ranking score
4. Sort opportunities by ranking score
5. Apply exposure constraints:
   - Check if top opportunity fits within exposure limits
   - If yes: select for execution
   - If no: move to next opportunity
6. Repeat until:
   - Exposure limit reached, or
   - No more opportunities, or
   - Max concurrent positions reached
7. Generate ranked list
8. Publish ranking event
```

### 6.5 Ranking Output Schema

```python
@dataclass
class OpportunityRanking:
    ranking_id: str
    opportunities: List[RankedOpportunity]
    selected_opportunities: List[str]
    rejected_opportunities: List[str]
    rejection_reasons: Dict[str, str]
    ranking_timestamp: datetime

@dataclass
class RankedOpportunity:
    signal_id: str
    ranking_score: float
    quality_score: float
    rr_score: float
    exposure_score: float
    diversification_score: float
    conditions_score: float
    strategy_confidence: float
    rank: int
    selected: bool
    rejection_reason: Optional[str]
```

---

## 7. Position Lifecycle Intelligence

### 7.1 Overview
Position Lifecycle Intelligence provides decision rules for managing positions throughout their lifecycle, from entry approval to exit.

### 7.2 Entry Approval

**Approval Checklist:**
```
1. Context quality >= threshold (default 0.60)
2. Signal score >= threshold (default 0.50)
3. Risk policies satisfied
4. Exposure limits not breached
5. Margin available
6. No conflicting signals (or resolved)
7. No safety triggers active
8. Strategy healthy
9. Market conditions appropriate
10. Execution quality acceptable
```

**Approval Decision:**
```
if all checklist items pass: APPROVE
else: REJECT with specific reason(s)
```

**Entry Approval Schema:**
```python
@dataclass
class EntryApproval:
    signal_id: str
    approved: bool
    approval_timestamp: datetime
    checklist_results: Dict[str, bool]
    rejection_reasons: List[str]
    confidence: float
```

---

### 7.3 Position Monitoring

**Monitoring Dimensions:**

1. **P&L Monitoring**
   - Real-time unrealized P&L
   - P&L rate of change
   - P&L vs expected

2. **Risk Monitoring**
   - Distance to stop loss
   - Distance to take profit
   - Effective leverage
   - Margin usage

3. **Market Monitoring**
   - Market context changes
   - Regime changes
   - Volatility changes
   - Spread changes

4. **Strategy Monitoring**
   - Strategy health
   - Strategy signal changes
   - Strategy exit signals

**Monitoring Frequency:**
- P&L: Every tick
- Risk: Every M1 candle
- Market: Every M5 candle
- Strategy: Every signal generation

**Monitoring Actions:**
```
if P&L triggers warning: alert
if P&L triggers action: execute action (modify/close)
if risk limit near breach: reduce position or alert
if market context degrades: evaluate exit
if strategy generates exit signal: evaluate exit
```

---

### 7.4 Scaling Decisions

**Scaling-In Rules:**
```
if all of the following:
    - Position is profitable
    - Market context remains favorable
    - Additional signals in same direction
    - Exposure limits allow
    - Risk per additional trade acceptable
    
then: consider scaling in
```

**Scaling-Out Rules:**
```
if any of the following:
    - Position reaches partial profit target
    - Market context degrades
    - Risk limits approached
    - Strategy signals partial exit
    
then: consider scaling out
```

**Scaling Decision Schema:**
```python
@dataclass
class ScalingDecision:
    position_id: str
    scaling_action: ScalingAction  # scale_in, scale_out, none
    scaling_size: Decimal
    scaling_reason: str
    confidence: float
    decision_timestamp: datetime
```

---

### 7.5 Stop Management

**Stop Loss Management:**
```
1. Initial Stop Loss
   - Set at signal generation
   - Based on strategy logic
   - Validated by risk management

2. Trailing Stop
   - Activate when P&L >= trigger
   - Trail by configured distance
   - Never trail against position

3. Break-Even Stop
   - Move to entry when P&L >= trigger
   - Protect profits
   - Optional (configurable)

4. Stop Tightening
   - Tighten stop when near target
   - Lock in profits
   - Optional (configurable)
```

**Stop Modification Workflow:**
```
1. Monitor position P&L
2. Check stop modification conditions
3. Calculate new stop level
4. Validate new stop (not too tight)
5. Submit modification order
6. Confirm modification
7. Update position state
```

---

### 7.6 Take-Profit Management

**Take Profit Options:**
```
1. Fixed Take Profit
   - Single target
   - Close entire position

2. Multiple Take Profits
   - Multiple targets
   - Partial exits at each target
   - Trailing stop for remainder

3. Trailing Take Profit
   - Follow price movement
   - Lock in profits
   - No fixed target

4. No Take Profit
   - Rely on signals
   - Manual exit
   - Stop loss only
```

**Take Profit Execution:**
```
if price >= take_profit:
    submit close order
    if partial TP: close portion only
    if full TP: close entire position
```

---

### 7.7 Early Exit

**Early Exit Conditions:**
```
if any of the following:
    - Market context becomes unfavorable
    - Regime changes against position
    - Strategy generates exit signal
    - Risk limit approached
    - Abnormal market conditions
    - News event (if configured)
    - Technical deterioration
    
then: evaluate early exit
```

**Early Exit Evaluation:**
```
1. Check exit condition severity
2. Calculate unrealized P&L
3. Compare with expected outcome
4. Consider transaction costs
5. Make exit decision
6. If exit: submit close order
7. If hold: continue monitoring
```

---

### 7.8 Emergency Exit

**Emergency Conditions:**
```
if any of the following:
    - Risk limit breached
    - Margin level critical
    - Kill switch activated
    - Broker connection lost
    - Abnormal market conditions
    - System failure
    
then: immediate emergency exit
```

**Emergency Exit Execution:**
```
1. Bypass normal validation
2. Submit market close order
3. Accept any slippage
4. Close entire position
5. Alert immediately
6. Log emergency event
```

---

### 7.9 Position State Machine

```
                    ┌─────────────┐
                    │   None      │
                    └──────┬──────┘
                           │
                    [Entry Approved]
                           ↓
                    ┌─────────────┐
                    │  Entering   │
                    └──────┬──────┘
                           │
                    [Order Submitted]
                           ↓
                    ┌─────────────┐
                    │  Pending    │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
         [Fill]                    [Reject]
              │                         │
              ↓                         ↓
         ┌──────────┐            ┌──────────┐
         │   Open    │            │  Failed  │
         └────┬─────┘            └──────────┘
              │
    ┌─────────┴─────────┐
    │                   │
[Monitoring]       [Scaling]
    │                   │
    │         ┌─────────┴─────────┐
    │         │                   │
[TP Hit]  [SL Hit]        [Early Exit]
    │         │                   │
    └─────────┴───────────────────┘
              │
              ↓
         ┌──────────┐
         │  Closing │
         └────┬─────┘
              │
         [Closed]
              ↓
         ┌──────────┐
         │  Closed   │
         └──────────┘
```

---

## 8. Explainability Engine

### 8.1 Overview
The Explainability Engine generates structured explanations for all decisions, ensuring transparency and auditability.

### 8.2 Decision Explanation Schema

```python
@dataclass
class DecisionExplanation:
    decision_id: str
    decision_type: DecisionType  # entry, exit, modify, no_trade
    decision_timestamp: datetime
    
    # Decision Summary
    summary: str
    decision: str  # APPROVED, REJECTED, NO_TRADE
    confidence: float
    
    # Accepted Conditions
    accepted_conditions: List[str]
    accepted_scores: Dict[str, float]
    
    # Rejected Conditions
    rejected_conditions: List[str]
    rejection_reasons: List[str]
    rejected_scores: Dict[str, float]
    
    # Confidence Contributors
    confidence_contributors: Dict[str, float]
    confidence_breakdown: Dict[str, Any]
    
    # Risk Contributors
    risk_factors: List[str]
    risk_scores: Dict[str, float]
    risk_assessment: str
    
    # Execution Blockers
    execution_blockers: List[str]
    blocking_policies: List[str]
    
    # Applicable Policies
    applicable_policies: List[str]
    policy_compliance: Dict[str, bool]
    
    # Context Snapshot
    market_context: MarketContext
    strategy_context: StrategyContext
    risk_context: RiskContext
    
    # Signal Details
    signal_details: Optional[SignalDetails]
    
    # Alternative Options
    alternatives_considered: List[str]
    alternatives_rejected: List[str]
    
    # Metadata
    explanation_version: str
    generated_by: str  # component/service name
```

### 8.3 Explanation Templates

#### Entry Approval Explanation

```
DECISION: APPROVED entry for {instrument} {direction}

SUMMARY:
Signal {signal_id} from strategy {strategy_name} approved for execution.
Overall confidence: {confidence}%

ACCEPTED CONDITIONS:
✓ Market context favorable (score: {context_score})
✓ Signal score above threshold (score: {signal_score})
✓ Risk policies satisfied
✓ Exposure limits within bounds
✓ Execution quality acceptable

CONFIDENCE BREAKDOWN:
- Market alignment: {market_alignment}%
- Structure quality: {structure_quality}%
- Trend agreement: {trend_agreement}%
- Volatility suitability: {volatility_suitability}%
- Execution quality: {execution_quality}%
- Historical reliability: {historical_reliability}%
- Risk quality: {risk_quality}%

RISK ASSESSMENT:
- Risk per trade: {risk_per_trade}%
- Position size: {position_size}
- Stop loss: {stop_loss} pips
- Take profit: {take_profit} pips
- Risk-reward ratio: {rr_ratio}

APPLICABLE POLICIES:
✓ Position sizing policy
✓ Daily loss limit
✓ Drawdown limit
✓ Correlation limit
```

---

#### Entry Rejection Explanation

```
DECISION: REJECTED entry for {instrument} {direction}

SUMMARY:
Signal {signal_id} from strategy {strategy_name} rejected.
Overall confidence: {confidence}%

REJECTED CONDITIONS:
✗ Market context unfavorable (score: {context_score}, threshold: {threshold})
✗ Signal score below threshold (score: {signal_score}, threshold: {threshold})
✗ Risk limit near breach ({current_risk}% of {limit}%)
✗ Spread too wide ({spread} pips, threshold: {threshold})

REJECTION REASONS:
1. Market context confidence below minimum required
2. Signal score does not meet quality threshold
3. Risk exposure would exceed daily limit
4. Current spread exceeds acceptable range

EXECUTION BLOCKERS:
- Market context blocker: context confidence < 0.40
- Risk blocker: daily loss at 85% of limit
- Execution blocker: spread > 3 pips

ALTERNATIVES CONSIDERED:
- Wait for context improvement
- Reduce position size to meet risk limits
- Wait for spread to narrow
```

---

#### No-Trade Explanation

```
DECISION: NO TRADE for {instrument}

SUMMARY:
No trade decision made due to conflicting signals and unfavorable conditions.
Overall confidence: {confidence}%

REJECTED CONDITIONS:
✗ Conflicting signals (Strategy A: LONG, Strategy B: SHORT)
✗ Market context marginal (score: {context_score})
✗ Insufficient confidence difference ({diff}% < threshold {threshold}%)

REJECTION REASONS:
1. Conflicting directional signals from strategies
2. Market context not sufficiently favorable
3. Unable to resolve conflict with confidence

CONSIDERED SIGNALS:
- Signal A (LONG): confidence {conf_a}%, score {score_a}
- Signal B (SHORT): confidence {conf_b}%, score {score_b}

RESOLUTION ATTEMPT:
- Priority hierarchy: inconclusive
- Weighted voting: tied (long: {votes_long}, short: {votes_short})
- Context preference: no clear preference

RECOMMENDATION:
Wait for market conditions to improve or signals to align.
```

---

### 8.4 Storage Format

**Database Table:**
```sql
CREATE TABLE decision_explanations (
    id UUID PRIMARY KEY,
    decision_id UUID UNIQUE NOT NULL,
    decision_type VARCHAR(50) NOT NULL,
    decision_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    decision VARCHAR(20) NOT NULL,
    confidence DECIMAL(5,4),
    summary TEXT,
    accepted_conditions JSONB,
    rejected_conditions JSONB,
    rejection_reasons TEXT[],
    confidence_contributors JSONB,
    confidence_breakdown JSONB,
    risk_factors TEXT[],
    risk_scores JSONB,
    risk_assessment TEXT,
    execution_blockers TEXT[],
    blocking_policies TEXT[],
    applicable_policies TEXT[],
    policy_compliance JSONB,
    market_context JSONB,
    strategy_context JSONB,
    risk_context JSONB,
    signal_details JSONB,
    alternatives_considered TEXT[],
    alternatives_rejected TEXT[],
    explanation_version VARCHAR(20),
    generated_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_decision_explanations_decision_id ON decision_explanations(decision_id);
CREATE INDEX idx_decision_explanations_timestamp ON decision_explanations(decision_timestamp);
CREATE INDEX idx_decision_explanations_type ON decision_explanations(decision_type);
```

**Retention Policy:**
- Hot storage: 90 days
- Warm storage: 1 year
- Cold storage: 7 years (for compliance)

---

## 9. Learning & Evaluation Framework

### 9.1 Overview
The Learning & Evaluation Framework continuously evaluates system performance without automatically changing live trading behavior. All recommendations require explicit approval.

### 9.2 Tracked Statistics

#### 9.2.1 Strategy Statistics

**Metrics:**
- Total signals generated
- Signals accepted
- Signals rejected
- Acceptance rate
- Total trades executed
- Winning trades
- Losing trades
- Win rate
- Average win
- Average loss
- Profit factor
- Sharpe ratio
- Sortino ratio
- Maximum drawdown
- Average holding time
- Average slippage
- Execution quality score

**Update Frequency:**
- Signal metrics: Per signal
- Trade metrics: Per trade
- Aggregated metrics: Daily

**Storage:**
```sql
CREATE TABLE strategy_statistics (
    id UUID PRIMARY KEY,
    strategy_id UUID NOT NULL,
    strategy_version VARCHAR(20),
    statistic_date DATE NOT NULL,
    total_signals INTEGER,
    signals_accepted INTEGER,
    signals_rejected INTEGER,
    acceptance_rate DECIMAL(5,4),
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate DECIMAL(5,4),
    avg_win DECIMAL(20,8),
    avg_loss DECIMAL(20,8),
    profit_factor DECIMAL(10,4),
    sharpe_ratio DECIMAL(10,4),
    sortino_ratio DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    avg_holding_time_seconds BIGINT,
    avg_slippage_pips DECIMAL(10,4),
    execution_quality_score DECIMAL(5,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(strategy_id, strategy_version, statistic_date)
);
```

---

#### 9.2.2 Market Regime Statistics

**Metrics:**
- Regime distribution (time spent in each regime)
- Regime transition frequency
- Performance by regime
- Signal quality by regime
- Execution quality by regime

**Update Frequency:**
- Regime tracking: Per candle
- Performance metrics: Per trade
- Aggregated: Weekly

**Storage:**
```sql
CREATE TABLE regime_statistics (
    id UUID PRIMARY KEY,
    instrument_id UUID NOT NULL,
    regime VARCHAR(50) NOT NULL,
    statistic_date DATE NOT NULL,
    time_in_regime_seconds BIGINT,
    transitions_in INTEGER,
    transitions_out INTEGER,
    total_signals INTEGER,
    accepted_signals INTEGER,
    win_rate DECIMAL(5,4),
    avg_pnl DECIMAL(20,8),
    sharpe_ratio DECIMAL(10,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(instrument_id, regime, statistic_date)
);
```

---

#### 9.2.3 Execution Quality

**Metrics:**
- Average slippage by order type
- Fill rate
- Rejection rate
- Average execution latency
- Order cancellation rate
- Partial fill rate

**Update Frequency:**
- Per order

**Storage:**
```sql
CREATE TABLE execution_quality (
    id UUID PRIMARY KEY,
    account_id UUID NOT NULL,
    broker_id UUID NOT NULL,
    statistic_date DATE NOT NULL,
    total_orders INTEGER,
    filled_orders INTEGER,
    rejected_orders INTEGER,
    cancelled_orders INTEGER,
    partial_fills INTEGER,
    fill_rate DECIMAL(5,4),
    rejection_rate DECIMAL(5,4),
    cancellation_rate DECIMAL(5,4),
    partial_fill_rate DECIMAL(5,4),
    avg_slippage_pips DECIMAL(10,4),
    avg_execution_latency_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(account_id, broker_id, statistic_date)
);
```

---

#### 9.2.4 Signal Quality

**Metrics:**
- Average signal score by component
- Signal score distribution
- Signal confidence distribution
- Signal outcome correlation
- False positive rate
- False negative rate

**Update Frequency:**
- Per signal
- Aggregated: Weekly

**Storage:**
```sql
CREATE TABLE signal_quality (
    id UUID PRIMARY KEY,
    strategy_id UUID NOT NULL,
    statistic_date DATE NOT NULL,
    total_signals INTEGER,
    avg_overall_score DECIMAL(5,4),
    avg_market_alignment DECIMAL(5,4),
    avg_structure_quality DECIMAL(5,4),
    avg_trend_agreement DECIMAL(5,4),
    avg_volatility_suitability DECIMAL(5,4),
    avg_execution_quality DECIMAL(5,4),
    avg_historical_reliability DECIMAL(5,4),
    avg_risk_quality DECIMAL(5,4),
    avg_confidence DECIMAL(5,4),
    score_distribution JSONB,
    false_positive_rate DECIMAL(5,4),
    false_negative_rate DECIMAL(5,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(strategy_id, statistic_date)
);
```

---

#### 9.2.5 Trade Outcome Distribution

**Metrics:**
- P&L distribution
- Holding time distribution
- Win/loss by regime
- Win/loss by session
- Win/loss by day of week

**Update Frequency:**
- Per trade
- Aggregated: Weekly

**Storage:**
```sql
CREATE TABLE trade_outcome_distribution (
    id UUID PRIMARY KEY,
    account_id UUID NOT NULL,
    statistic_date DATE NOT NULL,
    total_trades INTEGER,
    pnl_distribution JSONB,
    holding_time_distribution JSONB,
    win_by_regime JSONB,
    win_by_session JSONB,
    win_by_day_of_week JSONB,
    avg_pnl DECIMAL(20,8),
    median_pnl DECIMAL(20,8),
    std_pnl DECIMAL(20,8),
    skewness_pnl DECIMAL(10,4),
    kurtosis_pnl DECIMAL(10,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(account_id, statistic_date)
);
```

---

#### 9.2.6 Drawdown Metrics

**Metrics:**
- Current drawdown
- Maximum drawdown (period)
- Average drawdown
- Drawdown duration
- Recovery time
- Drawdown frequency

**Update Frequency:**
- Real-time: current drawdown
- Per trade: drawdown events
- Daily: aggregated

**Storage:**
```sql
CREATE TABLE drawdown_metrics (
    id UUID PRIMARY KEY,
    account_id UUID NOT NULL,
    statistic_date DATE NOT NULL,
    peak_equity DECIMAL(20,8),
    trough_equity DECIMAL(20,8),
    current_drawdown DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    avg_drawdown DECIMAL(10,4),
    drawdown_duration_seconds BIGINT,
    recovery_time_seconds BIGINT,
    drawdown_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(account_id, statistic_date)
);
```

---

### 9.3 Recommendation Generation

**Recommendation Types:**

1. **Strategy Performance Recommendations**
   ```
   if strategy performance declining:
       recommend: review strategy parameters
       recommend: consider disabling strategy
       recommend: investigate error rate
   ```

2. **Parameter Optimization Recommendations**
   ```
   if strategy suboptimal in specific regime:
       recommend: optimize parameters for regime
       recommend: test parameter changes in paper trading
   ```

3. **Risk Policy Recommendations**
   ```
   if risk limits frequently breached:
       recommend: adjust risk limits
       recommend: reduce position sizing
       recommend: review stop loss placement
   ```

4. **Market Condition Recommendations**
   ```
   if performance poor in specific regime:
       recommend: avoid trading in regime
       recommend: adjust strategy selection for regime
   ```

**Recommendation Schema:**
```python
@dataclass
class Recommendation:
    recommendation_id: str
    recommendation_type: RecommendationType
    priority: Priority  # low, medium, high, critical
    title: str
    description: str
    rationale: str
    supporting_data: Dict[str, Any]
    suggested_actions: List[str]
    estimated_impact: str
    requires_approval: bool
    generated_at: datetime
    status: str  # pending, reviewed, approved, rejected, implemented
```

**Recommendation Storage:**
```sql
CREATE TABLE recommendations (
    id UUID PRIMARY KEY,
    recommendation_id UUID UNIQUE NOT NULL,
    recommendation_type VARCHAR(50) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    rationale TEXT,
    supporting_data JSONB,
    suggested_actions TEXT[],
    estimated_impact TEXT,
    requires_approval BOOLEAN DEFAULT TRUE,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) NOT NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by UUID,
    decision TEXT,
    implemented_at TIMESTAMP WITH TIME ZONE
);
```

---

### 9.4 Evaluation Workflow

```
1. Collect performance data
2. Calculate statistics
3. Compare against benchmarks
4. Detect anomalies and trends
5. Generate recommendations
6. Store recommendations
7. Alert for critical recommendations
8. Await user review
9. Implement approved changes
10. Monitor impact of changes
```

**Deterministic Behavior:**
- All recommendations require explicit approval
- No automatic parameter changes
- No automatic strategy enable/disable
- Production decisions remain deterministic

---

## 10. Safety Layer

### 10.1 Overview
The Safety Layer provides protective mechanisms to prevent trading under unsafe conditions. Default behavior always prioritizes safety over taking a trade.

### 10.2 Safety Mechanisms

#### 10.2.1 Conflicting Data

**Detection:**
```
if bid > ask: data conflict
if price change > max_change: data conflict
if volume < 0: data conflict
if timestamp in future: data conflict
if timestamp too old: data conflict
```

**Action:**
```
1. Reject conflicting data
2. Mark data source as suspect
3. Switch to backup data source
4. Alert operations
5. If all sources conflict: halt trading
```

---

#### 10.2.2 Missing Data

**Detection:**
```
if no data received for > timeout: missing data
if required fields null: missing data
if data gaps detected: missing data
```

**Action:**
```
1. Attempt data recovery
2. Use last known data if recent (< 30s)
3. If data stale: halt new entries
4. Maintain existing positions
5. Alert operations
```

---

#### 10.2.3 Stale Market Feeds

**Detection:**
```
if last data timestamp > stale_threshold: stale feed
if data not updating: stale feed
```

**Action:**
```
1. Check connection status
2. Attempt reconnection
3. Switch to backup feed
4. If all feeds stale: halt trading
5. Alert operations
```

---

#### 10.2.4 Excessive Latency

**Detection:**
```
if data latency > threshold: excessive latency
if execution latency > threshold: excessive latency
if decision latency > threshold: excessive latency
```

**Action:**
```
1. Log latency metrics
2. Identify bottleneck
3. If critical path: halt trading
4. If non-critical: continue with warning
5. Alert operations
```

---

#### 10.2.5 Abnormal Spreads

**Detection:**
```
if spread > abnormal_threshold: abnormal spread
if spread > 10 × average: abnormal spread
if spread suddenly widens: abnormal spread
```

**Action:**
```
1. Reject new entries
2. Consider exiting existing positions
3. Alert operations
4. Monitor spread normalization
5. Resume when spread normalizes
```

---

#### 10.2.6 Broker Inconsistencies

**Detection:**
```
if broker position != internal position: inconsistency
if broker balance != internal balance: inconsistency
if broker order status != internal status: inconsistency
```

**Action:**
```
1. Trigger reconciliation
2. Use broker as authoritative
3. Update internal state
4. Alert operations
5. If reconciliation fails: halt trading
```

---

#### 10.2.7 Execution Uncertainty

**Detection:**
```
if order status unknown: uncertainty
if fill not confirmed: uncertainty
if partial fill unexpected: uncertainty
```

**Action:**
```
1. Request order status from broker
2. Reconcile based on actual status
3. If status unknown: assume worst case
4. Alert operations
5. Manual review if persistent
```

---

#### 10.2.8 Abnormal Volatility

**Detection:**
```
if volatility > abnormal_threshold: abnormal volatility
if price gaps > threshold: abnormal volatility
if sudden price spike: abnormal volatility
```

**Action:**
```
1. Halt new entries
2. Consider exiting existing positions
3. Tighten stop losses
4. Alert operations
5. Resume when volatility normalizes
```

---

#### 10.2.9 Unexpected Market Closures

**Detection:**
```
if market outside trading hours: unexpected closure
if exchange closed: unexpected closure
if holiday detected: unexpected closure
```

**Action:**
```
1. Cancel all pending orders
2. Close positions if configured
3. Halt trading
4. Alert operations
5. Resume at market open
```

---

### 10.3 Safety State Machine

```
                    ┌─────────────┐
                    │   Normal    │
                    └──────┬──────┘
                           │
                    [Safety Trigger]
                           ↓
                    ┌─────────────┐
                    │   Warning   │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
         [Resolved]              [Escalated]
              │                         │
              ↓                         ↓
         ┌──────────┐            ┌──────────┐
         │  Normal  │            │  Caution │
         └──────────┘            └────┬─────┘
                                    │
                         [Further Escalation]
                                    │
                                    ↓
                            ┌─────────────┐
                            │ Restricted  │
                            └──────┬──────┘
                                   │
                        [Critical Escalation]
                                   │
                                   ↓
                            ┌─────────────┐
                            │   Halted    │
                            └─────────────┘
```

**State Definitions:**
- **Normal:** All systems operational, no safety concerns
- **Warning:** Minor safety issue, monitoring increased
- **Caution:** Moderate safety issue, some restrictions
- **Restricted:** Major safety issue, significant restrictions
- **Halted:** Critical safety issue, all trading halted

**State Transitions:**
- Normal → Warning: Single safety trigger
- Warning → Normal: Trigger resolved
- Warning → Caution: Multiple triggers or escalation
- Caution → Warning: Triggers resolved
- Caution → Restricted: Further escalation
- Restricted → Caution: Issues resolved
- Restricted → Halted: Critical escalation
- Halted → Restricted: Issues resolved (manual approval required)

---

### 10.4 Safety Configuration

```python
@dataclass
class SafetyConfiguration:
    # Data Safety
    max_data_age_ms: int = 5000
    max_price_change_percent: Decimal = Decimal("1.0")
    stale_feed_threshold_ms: int = 30000
    
    # Latency Safety
    max_data_latency_ms: int = 100
    max_execution_latency_ms: int = 500
    max_decision_latency_ms: int = 200
    
    # Spread Safety
    max_spread_pips: Decimal = Decimal("5.0")
    spread_multiplier_threshold: Decimal = Decimal("10.0")
    
    # Volatility Safety
    max_volatility_multiplier: Decimal = Decimal("3.0")
    max_gap_pips: Decimal = Decimal("50.0")
    
    # Reconciliation Safety
    reconciliation_interval_ms: int = 60000
    max_reconciliation_attempts: int = 3
    
    # Escalation Rules
    warning_trigger_count: int = 1
    caution_trigger_count: int = 3
    restricted_trigger_count: int = 5
    halt_trigger_count: int = 10
    
    # Auto-Actions
    auto_cancel_on_halt: bool = True
    auto_close_on_halt: bool = False
    auto_reduce_on_caution: bool = True
```

---

## 11. Simulation Compatibility

### 11.1 Overview
Every decision made by the TDIE must be exactly reproducible in historical backtests, paper trading, and production logs.

### 11.2 Determinism Requirements

**Deterministic Components:**
- All decision rules must be deterministic
- No random number generation in decision path
- All external data must be timestamped and versioned
- All configuration must be versioned

**Non-Deterministic Components:**
- Market data (external, but timestamped)
- Network latency (logged, not used in decisions)
- Broker execution (logged, not used in decisions)

### 11.3 State Snapshot

**Snapshot Schema:**
```python
@dataclass
class DecisionStateSnapshot:
    snapshot_id: str
    snapshot_timestamp: datetime
    
    # Market State
    market_data: MarketDataSnapshot
    market_context: MarketContext
    regime: str
    
    # Strategy State
    active_strategies: List[str]
    strategy_states: Dict[str, Any]
    
    # Position State
    open_positions: List[PositionState]
    pending_orders: List[OrderState]
    
    # Account State
    account_state: AccountState
    
    # Risk State
    risk_metrics: RiskMetrics
    risk_limits: RiskLimits
    
    # Configuration State
    configuration_version: str
    decision_rules_version: str
    scoring_model_version: str
    
    # Decision State
    pending_signals: List[SignalState]
    decision_queue: List[DecisionState]
```

### 11.4 Replay Mechanism

**Replay Workflow:**
```
1. Load historical data for period
2. Load configuration versions for period
3. Load state snapshot at start of period
4. Process data in timestamp order
5. For each timestamp:
   - Update market state
   - Update context
   - Run decision pipeline
   - Record decision
   - Update state
6. Compare replay decisions with original decisions
7. Report any discrepancies
```

**Replay Validation:**
```
if replay_decision != original_decision:
    log discrepancy
    investigate cause:
        - configuration difference?
        - data difference?
        - bug in replay?
        - non-deterministic component?
```

### 11.5 Decision Logging

**Decision Log Schema:**
```python
@dataclass
class DecisionLog:
    log_id: str
    decision_timestamp: datetime
    
    # Input State
    input_state: DecisionStateSnapshot
    
    # Decision Process
    decision_pipeline_steps: List[PipelineStep]
    
    # Decision Output
    decision: str
    decision_confidence: float
    
    # Explanation
    explanation: DecisionExplanation
    
    # Metadata
    configuration_version: str
    data_version: str
    engine_version: str
```

**Pipeline Step:**
```python
@dataclass
class PipelineStep:
    step_name: str
    step_timestamp: datetime
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    processing_time_ms: int
    configuration_used: Dict[str, Any]
```

### 11.6 Backtest Compatibility

**Backtest Mode:**
```
1. Load historical data
2. Set engine to backtest mode
3. Disable real-time features (WebSocket, live API calls)
4. Use historical data for all inputs
5. Process in timestamp order
6. Record all decisions
7. Generate backtest report
8. Validate against production decisions (if available)
```

**Backtest Validation:**
```
if backtest_decision != production_decision:
    investigate:
        - data difference (tick vs candle)?
        - timing difference (real-time vs historical)?
        - configuration difference?
        - known backtest limitation?
```

### 11.7 Paper Trading Compatibility

**Paper Trading Mode:**
```
1. Use real-time market data
2. Use virtual execution (no real orders)
3. Simulate execution with realistic delays
4. Simulate slippage and spread
5. Record all decisions
6. Compare with live trading (if running)
7. Generate paper trading report
```

**Paper Trading Validation:**
```
if paper_decision != live_decision:
    investigate:
        - execution simulation difference?
        - timing difference?
        - data source difference?
```

---

## 12. Architecture Diagrams

### 12.1 TDIE Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Trading Decision Intelligence Engine                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐                                                            │
│  │ Market Data  │                                                            │
│  └──────┬───────┘                                                            │
│         ↓                                                                    │
│  ┌──────────────┐                                                            │
│  │ Market       │                                                            │
│  │ Regime       │                                                            │
│  └──────┬───────┘                                                            │
│         ↓                                                                    │
│  ┌──────────────┐                                                            │
│  │ Market       │                                                            │
│  │ Context      │──────────────────────────────────────────────────────┐    │
│  │   Engine     │                                                            │    │
│  └──────┬───────┘                                                            │    │
│         ↓                                                                    │    │
│  ┌──────────────┐                                                            │    │
│  │ Strategy     │                                                            │    │
│  │ Selection    │                                                            │    │
│  └──────┬───────┘                                                            │    │
│         ↓                                                                    │    │
│  ┌──────────────┐                                                            │    │
│  │ Signal       │                                                            │    │
│  │ Generation   │                                                            │    │
│  └──────┬───────┘                                                            │    │
│         ↓                                                                    │    │
│  ┌──────────────┐                                                            │    │
│  │ Signal       │                                                            │    │
│  │ Scoring      │                                                            │    │
│  └──────┬───────┘                                                            │    │
│         ↓                                                                    │    │
│  ┌──────────────┐                                                            │    │
│  │ Signal       │                                                            │    │
│  │ Validation   │                                                            │    │
│  └──────┬───────┘                                                            │    │
│         ↓                                                                    │    │
│  ┌──────────────┐                                                            │    │
│  │ Risk         │                                                            │    │
│  │ Validation   │                                                            │    │
│  └──────┬───────┘                                                            │    │
│         ↓                                                                    │    │
│  ┌──────────────┐                                                            │    │
│  │ Conflict     │                                                            │    │
│  │ Resolution   │                                                            │    │
│  └──────┬───────┘                                                            │    │
│         ↓                                                                    │    │
│  ┌──────────────┐                                                            │    │
│  │ Opportunity   │                                                            │    │
│  │ Ranking      │                                                            │    │
│  └──────┬───────┘                                                            │    │
│         ↓                                                                    │    │
│  ┌──────────────┐                                                            │    │
│  │ Execution    │                                                            │    │
│  │ Approval    │                                                            │    │
│  └──────┬───────┘                                                            │    │
│         ↓                                                                    │    │
│  ┌──────────────┐                                                            │    │
│  │ Order        │                                                            │    │
│  │ Execution    │                                                            │    │
│  └──────┬───────┘                                                            │    │
│         ↓                                                                    │    │
│  ┌──────────────┐                                                            │    │
│  │ Position     │                                                            │    │
│  │ Monitoring   │──────────────────────────────────────────────────────┘    │
│  └──────┬───────┘                                                            │
│         ↓                                                                    │
│  ┌──────────────┐                                                            │
│  │ Exit         │                                                            │
│  │ Decision    │                                                            │
│  └──────┬───────┘                                                            │
│         ↓                                                                    │
│  ┌──────────────┐                                                            │
│  │ Trade        │                                                            │
│  │ Completion   │                                                            │
│  └──────────────┘                                                            │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                      Supporting Components                            │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │    │
│  │  │ Explain  │  │ Learning │  │  Safety  │  │ Decision │             │    │
│  │  │ ability  │  │ & Eval  │  │  Layer   │  │ Logging  │             │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘             │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 12.2 Decision Pipeline Sequence Diagram

```
Market Data    Context Engine    Strategy Sel    Signal Gen    Signal Score    Validation    Risk    Conflict    Ranking    Execution    Position
    │                 │                │               │               │              │         │          │          │           │          │
    │─Data───────────▶│                │               │               │              │         │          │          │           │          │
    │                 │─Context───────▶│               │               │              │         │          │          │           │          │
    │                 │                │─Select───────▶│               │              │         │          │          │           │          │
    │                 │                │               │─Signal───────▶│              │         │          │          │           │          │
    │                 │                │               │               │─Score───────▶│         │          │          │           │          │
    │                 │                │               │               │              │─Valid──▶│          │          │           │          │
    │                 │                │               │               │              │         │─Risk────▶│          │           │          │
    │                 │                │               │               │              │         │          │─Conf────▶│           │          │
    │                 │                │               │               │              │         │          │          │─Rank────▶│          │          │
    │                 │                │               │               │              │         │          │          │           │─Approve──▶│          │
    │                 │                │               │               │              │         │          │          │           │           │─Monitor──▶│
```

### 12.3 Safety Layer State Diagram

```
                    ┌─────────────┐
                    │   Normal    │
                    └──────┬──────┘
                           │
                    [1 Trigger]
                           ↓
                    ┌─────────────┐
                    │   Warning   │
                    └──────┬──────┘
                           │
                    [Resolved]
                           │
                    ┌─────────────┐
                    │   Normal    │
                    └─────────────┘
                           
                    [3 Triggers]
                           │
                    ┌─────────────┐
                    │   Caution   │
                    └──────┬──────┘
                           │
                    [Resolved]
                           │
                    ┌─────────────┐
                    │   Normal    │
                    └─────────────┘
                           
                    [5 Triggers]
                           │
                    ┌─────────────┐
                    │  Restricted │
                    └──────┬──────┘
                           │
                    [Resolved]
                           │
                    ┌─────────────┐
                    │   Normal    │
                    └─────────────┘
                           
                    [10 Triggers]
                           │
                    ┌─────────────┐
                    │   Halted    │
                    └──────┬──────┘
                           │
                    [Manual Approval]
                           │
                    ┌─────────────┐
                    │   Normal    │
                    └─────────────┘
```

---

## 13. Engineering Rationale

### 13.1 Deterministic Decision Making

**Rationale:**
- Enables reproducible backtesting
- Facilitates debugging and analysis
- Required for regulatory compliance
- Builds trust in system behavior

**Implementation:**
- All decision rules are deterministic
- No random components in decision path
- All inputs are timestamped and versioned
- Full decision logging for replay

---

### 13.2 Explainability First

**Rationale:**
- Regulatory requirement for audit trails
- Essential for trust and transparency
- Required for debugging and improvement
- Enables human oversight

**Implementation:**
- Every decision generates explanation
- Full score breakdown stored
- Decision audit trail maintained
- Natural language explanations

---

### 13.3 Safety Over Profit

**Rationale:**
- Protects capital from catastrophic loss
- Required for responsible trading
- Builds user trust
- Regulatory expectation

**Implementation:**
- Safety layer overrides all other decisions
- Default behavior is no-trade
- Multiple safety mechanisms
- Conservative thresholds

---

### 13.4 Modular Scoring

**Rationale:**
- Enables customization per strategy
- Allows tuning without code changes
- Facilitates A/B testing
- Improves maintainability

**Implementation:**
- Component-based scoring
- Configurable weights
- Pluggable scoring factors
- Versioned scoring models

---

### 13.5 Context-Aware Decision Making

**Rationale:**
- Different strategies work in different conditions
- Market conditions change over time
- One-size-fits-all doesn't work
- Improves overall performance

**Implementation:**
- Multi-dimensional context evaluation
- Strategy-context matching
- Context-based strategy selection
- Context-aware signal validation

---

### 13.6 Conflict Resolution Hierarchy

**Rationale:**
- Multiple strategies may disagree
- Need systematic way to resolve
- Prevents arbitrary decisions
- Enables customization

**Implementation:**
- Multiple resolution mechanisms
- Configurable hierarchy
- No-trade as valid option
- Full resolution logging

---

### 13.7 Learning Without Auto-Change

**Rationale:**
- Prevents runaway optimization
- Maintains human control
- Avoids overfitting to recent data
- Required for regulatory compliance

**Implementation:**
- Recommendations require approval
- No automatic parameter changes
- Deterministic production behavior
- Evaluation in sandbox first

---

## 14. Extension Points

### 14.1 Additional Context Dimensions

**Extension Points:**
- Sentiment analysis (news, social media)
- Order flow analysis
- Macro economic indicators
- Correlation analysis
- Seasonality patterns

**Implementation:**
- Plugin architecture for context providers
- Standardized context interface
- Configurable context weights
- Context versioning

---

### 14.2 Advanced Scoring Models

**Extension Points:**
- Machine learning scoring models
- Ensemble scoring
- Adaptive scoring weights
- Real-time weight optimization

**Implementation:**
- Scoring model interface
- Model versioning
- A/B testing framework
- Rollback capability

---

### 14.3 Additional Resolution Mechanisms

**Extension Points:**
- Game-theoretic resolution
- Reinforcement learning resolution
- User-defined resolution rules
- External resolution services

**Implementation:**
- Resolution mechanism interface
- Mechanism registration
- Priority configuration
- Fallback mechanism

---

### 14.4 Advanced Exit Strategies

**Extension Points:**
- Portfolio-level exits
- Correlation-based exits
- Volatility-based exits
- Time-based exits

**Implementation:**
- Exit strategy interface
- Strategy composition
- Priority hierarchy
- Backtesting support

---

### 14.5 Enhanced Explainability

**Extension Points:**
- Visual explanations
- Interactive explanations
- Natural language generation
- Explanation customization

**Implementation:**
- Explanation template system
- Multi-language support
- Visualization hooks
- User preference integration

---

## 15. Risks and Mitigations

### 15.1 Technical Risks

**Risk: Decision Pipeline Latency**
- **Impact:** Missed trading opportunities
- **Mitigation:** Performance monitoring, optimization, caching
- **Monitoring:** Latency percentiles, timeout alerts

**Risk: State Synchronization Failure**
- **Impact:** Incorrect decisions
- **Mitigation:** State snapshots, reconciliation, validation
- **Monitoring:** State mismatch alerts

**Risk: Configuration Drift**
- **Impact:** Unexpected behavior changes
- **Mitigation:** Configuration versioning, approval workflow
- **Monitoring:** Configuration change alerts

---

### 15.2 Decision Quality Risks

**Risk: Over-Optimization**
- **Impact:** Poor out-of-sample performance
- **Mitigation:** Walk-forward testing, regularization, constraints
- **Monitoring:** Performance degradation alerts

**Risk: Context Misclassification**
- **Impact:** Wrong strategies selected
- **Mitigation:** Multiple context models, confidence thresholds
- **Monitoring:** Context accuracy metrics

**Risk: Scoring Model Bias**
- **Impact:** Biased signal selection
- **Mitigation:** Regular validation, diverse training data
- **Monitoring:** Score distribution monitoring

---

### 15.3 Operational Risks

**Risk: Human Error in Configuration**
- **Impact:** Incorrect decisions
- **Mitigation:** Configuration validation, approval workflow, rollback
- **Monitoring:** Configuration change audit

**Risk: Insufficient Explainability**
- **Impact:** Cannot debug or audit decisions
- **Mitigation:** Mandatory explanation generation, explanation validation
- **Monitoring:** Explanation completeness checks

**Risk: Safety Layer Too Restrictive**
- **Impact:** Missed opportunities
- **Mitigation:** Tunable thresholds, gradual relaxation
- **Monitoring:** Safety trigger rate, opportunity cost

---

### 15.4 Financial Risks

**Risk: Simultaneous Signal Failure**
- **Impact:** Multiple losing positions
- **Mitigation:** Diversification, correlation limits, position sizing
- **Monitoring:** Correlation monitoring, drawdown alerts

**Risk: Regime Change Detection Lag**
- **Impact:** Trading in wrong regime
- **Mitigation:** Multiple detection methods, fast detection, conservative transitions
- **Monitoring:** Regime change latency, performance by regime

**Risk: Execution Quality Degradation**
- **Impact:** Slippage, poor fills
- **Mitigation:** Execution quality monitoring, broker diversification
- **Monitoring:** Slippage metrics, fill rate

---

### 15.5 Compliance Risks

**Risk: Insufficient Audit Trail**
- **Impact:** Regulatory non-compliance
- **Mitigation:** Comprehensive logging, immutable storage
- **Monitoring:** Log completeness checks

**Risk: Non-Deterministic Behavior**
- **Impact:** Cannot reproduce decisions
- **Mitigation:** Determinism requirements, replay validation
- **Monitoring:** Replay validation results

**Risk: Inadequate Risk Controls**
- **Impact:** Excessive losses
- **Mitigation:** Multiple risk layers, independent validation
- **Monitoring:** Risk limit breaches, stress testing

---

**Document Status:** Draft  
**Next Review:** August 2026  
**Approved By:** [Pending]
