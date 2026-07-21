# EPIC-006 Sprint-3: Indicator Engine Implementation Plan

## Information Gathered

### Existing Files (Already Created)
- `interfaces.py` - Indicator protocol, BaseIndicatorABC, IndicatorConfig
- `models.py` - Bar, IndicatorResult, IndicatorMetadata, IndicatorType, IndicatorValue
- `exceptions.py` - IndicatorError hierarchy (6 exception types)
- `base.py` - BaseIndicator with full lifecycle (initialize, warmup, update, batch_calculate, reset, serialize, deserialize)
- `context.py` - IndicatorContext for passing state during calculations
- `__init__.py` - Package exports (all indicators + infrastructure re-exports)

### Existing Indicators (Already Created)
- **Trend**: EMA, SMA, WMA, HMA, SuperTrend, IchimokuCloud
- **Momentum**: RSI, MACD, CCI, ROC, Momentum, Stochastic
- **Volatility**: ATR, BollingerBands, KeltnerChannels, StandardDeviation
- **Volume**: VWAP, OBV, AccumulationDistribution, MoneyFlowIndex
- **Breakout**: DonchianChannel, PivotPoints
- **Market Strength**: ADX (includes DI+, DI-)

### Integration Points (Must Not Change Existing Public Interfaces)
1. **Strategy Framework** (`StrategyContext`): Has `rsi`, `ema_fast`, `ema_slow`, `atr` fields + `extra` dict
2. **Trading Decision Engine** (`SignalGenerator`): Uses `rsi`, `trend_strength`, `volume_ratio`, `price_position`
3. **Market Intelligence**: Protocol-based ports (`ProviderHealthPort`, `IntelligenceSink`, etc.)
4. **Strategy Capabilities**: `required_indicators: FrozenSet[str]` in StrategyCapabilities

## Plan

### Phase 1: Infrastructure Files (5 files)

1. **`registry.py`** - Indicator Registry
   - `IndicatorRegistry` class with register/unregister/discover/metadata
   - Version compatibility checking
   - Thread-safe (asyncio.Lock)
   - Dependency injection friendly

2. **`manager.py`** - Indicator Manager
   - `IndicatorManager` class with lifecycle orchestration
   - `IndicatorManagerConfig` dataclass
   - Batch initialization/warmup/update
   - Symbol-level indicator management

3. **`pipeline.py`** - Indicator Pipeline
   - `IndicatorPipeline` class with dependency graph resolution
   - `PipelineNode` and `PipelineStage` models
   - Parallel execution support
   - Streaming and batch modes
   - Incremental updates

4. **`cache.py`** - Indicator Cache
   - `IndicatorCache` class with rolling window support
   - `IndicatorCacheConfig` dataclass
   - TTL-based expiry
   - Symbol and timeframe scoped caching
   - Incremental reuse (cache-aside pattern)

5. **`statistics.py`** - Indicator Statistics
   - `IndicatorStatistics` class tracking execution metrics
   - Execution count, latency, cache hit ratio
   - Average calculation time, warmup count
   - Last execution timestamp

### Phase 2: Test Suite (target 200+ tests, 96%+ coverage)

Test files to create in `project-orion/tests/unit/domain/indicators/`:

1. **`test_ema.py`** - EMA tests (period, warmup, streaming, edge cases)
2. **`test_rsi.py`** - RSI tests (calculation, boundary values, serialization)
3. **`test_macd.py`** - MACD tests (all three lines, crossovers)
4. **`test_atr.py`** - ATR tests (true range, smoothing)
5. **`test_adx.py`** - ADX tests (DI+, DI-, trend strength)
6. **`test_vwap.py`** - VWAP tests (cumulative, daily reset)
7. **`test_bollinger.py`** - Bollinger Bands tests (bands, bandwidth, %B)
8. **`test_sma.py`** - SMA tests (rolling sum, incremental)
9. **`test_cache.py`** - Cache tests (TTL, symbol scope, incremental reuse)
10. **`test_registry.py`** - Registry tests (register, discover, version compatibility)
11. **`test_pipeline.py`** - Pipeline tests (dependency graph, parallel execution, streaming)
12. **`test_manager.py`** - Manager tests (lifecycle orchestration)
13. **`test_statistics.py`** - Statistics tests (execution tracking)
14. **`test_edge_cases.py`** - Edge cases (NaN, empty, single value, warmup)

### Phase 3: Integration & Quality Gates

1. Update `__init__.py` to ensure all new classes are exported
2. Run `python -m black .` for formatting
3. Run `python -m isort .` for import sorting
4. Run `python -m pytest` for test execution
5. Generate coverage report

### Phase 4: Git Commit

```bash
git add .
git commit -m "Implement EPIC-006 Sprint-3 Production Indicator Engine"
```

## Dependency Graph (Infrastructure)

```
IndicatorCache ──> IndicatorStatistics (for cache hit tracking)
      │
      v
IndicatorRegistry ──> BaseIndicator (version checking)
      │
      v
IndicatorManager ──> IndicatorRegistry, IndicatorCache, IndicatorStatistics
      │
      v
IndicatorPipeline ──> IndicatorManager, IndicatorCache
      │
      v
[Strategy Framework] ──> [Trading Decision Engine] ──> [Market Intelligence]
(via StrategyContext.extra)  (via SignalGenerator)     (via existing ports)
```

## Performance Guarantees

| Indicator | Update | Warmup | Memory |
|-----------|--------|--------|--------|
| EMA       | O(1)   | O(n)   | O(1)   |
| SMA       | O(1)   | O(n)   | O(p)   |
| WMA       | O(p)   | O(n)   | O(p)   |
| RSI       | O(1)   | O(n)   | O(1)   |
| MACD      | O(1)   | O(n)   | O(1)   |
| ATR       | O(1)   | O(n)   | O(1)   |
| ADX       | O(1)   | O(n)   | O(1)   |
| VWAP      | O(1)   | O(n)   | O(1)   |
| BB        | O(p)   | O(n)   | O(p)   |

Where p = period, n = number of bars

