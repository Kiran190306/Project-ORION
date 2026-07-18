# Trading Core Architecture - Phase 2
## Engineering Design Document

**Document Version:** 1.0  
**Date:** July 2026  
**Classification:** Confidential  
**Status:** Draft

---

## Table of Contents

1. [Market Data Engine](#1-market-data-engine)
2. [Market Regime Detection Engine](#2-market-regime-detection-engine)
3. [Strategy Plugin Framework](#3-strategy-plugin-framework)
4. [Signal Validation Pipeline](#4-signal-validation-pipeline)
5. [Position Management Engine](#5-position-management-engine)
6. [Risk Management Engine](#6-risk-management-engine)
7. [Execution Engine](#7-execution-engine)
8. [Event Bus](#8-event-bus)
9. [Database Design](#9-database-design)
10. [Reliability](#10-reliability)
11. [Observability](#11-observability)
12. [Architecture Diagrams](#12-architecture-diagrams)
13. [Engineering Decisions](#13-engineering-decisions)
14. [Future Extension Points](#14-future-extension-points)

---

## 1. Market Data Engine

### 1.1 Component Specifications

#### Tick Ingestion
**Inputs:** Raw tick streams, connection parameters, subscription list
**Outputs:** Normalized tick events, connection status, latency metrics
**Workflow:** Connect → Subscribe → Parse → Calculate latency → Publish
**Failure Scenarios:** Connection failure, auth failure, rate limit
**Recovery:** Exponential backoff (1s, 2s, 4s, 8s, 16s, max 60s), circuit breaker after 5 failures

#### Candle Aggregation
**Inputs:** Tick stream, aggregation config, symbol metadata
**Outputs:** OHLCV candles, candle completion events
**Workflow:** Receive tick → Update buckets → Detect completion → Publish → Store
**Failure Scenarios:** Missing ticks, clock drift, session confusion
**Recovery:** Interpolate gaps, NTP sync, session detection with timezone logic

#### Multi-Timeframe Synchronization
**Inputs:** Aggregated candles, symbol list, sync config
**Outputs:** Synchronized candle bundles, alignment events
**Workflow:** Receive candles → Align to grid → Bundle → Validate → Publish
**Failure Scenarios:** Timeframe misalignment, missing timeframe, late data
**Recovery:** Use latest available, mark missing as null, timeout for late data

#### Symbol Management
**Inputs:** Symbol definitions, user subscriptions, metadata
**Outputs:** Active symbol list, metadata cache, status events
**Workflow:** Load definitions → Normalize names → Cache metadata → Track subscriptions
**Failure Scenarios:** Symbol not found, metadata mismatch, delisting
**Recovery:** Validate before subscription, broker-specific normalization, alias mapping

#### Session Detection
**Inputs:** Symbol metadata, current time, session config
**Outputs:** Current session, transition events, calendar
**Workflow:** Load definitions → Convert to UTC → Determine session → Detect transitions
**Failure Scenarios:** Timezone confusion, definition error, clock drift
**Recovery:** Timezone-aware libraries, NTP sync, priority-based selection

#### Spread Monitoring
**Inputs:** Tick data, thresholds, historical spread
**Outputs:** Current spread, statistics, anomaly alerts
**Workflow:** Calculate spread → Update stats → Compare thresholds → Detect spikes → Alert
**Failure Scenarios:** Spread too wide, zero/negative spread, stale spread
**Recovery:** Reject if > threshold, validate bid<ask, use historical average, suspend symbol

#### Latency Monitoring
**Inputs:** Timestamps at each stage
**Outputs:** Latency metrics, percentiles, anomaly alerts
**Workflow:** Record timestamps → Calculate latencies → Update stats → Detect anomalies → Alert
**Failure Scenarios:** Latency spike, negative latency, missing timestamps, drift
**Recovery:** Circuit breaker, NTP sync, default to current time, auto-scaling

#### Data Validation
**Inputs:** Raw data, validation rules, historical stats
**Outputs:** Validated data, validation results, quality score
**Workflow:** Format validation → Range validation → Business rules → Outlier detection → Score
**Failure Scenarios:** Format error, range violation, business rule violation, outlier
**Recovery:** Reject with reason, statistical outlier detection, rule validation, fallback value

#### Missing Candle Recovery
**Inputs:** Detected gaps, historical source, recovery config
**Outputs:** Recovered candles, gap reports, status
**Workflow:** Detect gaps → Check size → Backfill from historical → Validate → Insert → Log
**Failure Scenarios:** Gap too large, historical unavailable, recovered invalid, timeout
**Recovery:** Gap size limits, multiple sources, validate before insert, timeout/abort

#### Data Normalization
**Inputs:** Raw data, normalization rules, symbol mapping
**Outputs:** Normalized data, metadata, mapping events
**Workflow:** Parse schema → Unit conversion → Precision normalization → Timestamp standardization → Field mapping → Validate
**Failure Scenarios:** Schema mismatch, conversion error, precision loss, mapping missing
**Recovery:** Versioned schemas, fallback on conversion error, high-precision internal, default mappings

#### Time Synchronization
**Inputs:** NTP sources, broker timestamps, system clock
**Outputs:** Synced timestamps, offset metrics, quality score
**Workflow:** Query NTP → Calculate offset → Apply correction → Monitor quality → Detect drift → Alert
**Failure Scenarios:** NTP unreachable, large offset, clock drift, conflicting sources
**Recovery:** Multiple NTP with fallback, reject if offset > threshold, periodic resync, median of sources

#### Historical Cache
**Inputs:** Completed candles, queries, cache config
**Outputs:** Historical data, cache statistics, eviction events
**Workflow:** Store candles → Partition by time → Compress old data → Handle queries → Optimize → Retention
**Failure Scenarios:** Write failure, query timeout, storage full, corruption
**Recovery:** Buffer during outages, query optimization, archival, backup restoration

#### Live Cache
**Inputs:** Real-time ticks, in-progress candles, cache config
**Outputs:** Cached real-time data, hit/miss metrics, eviction events
**Workflow:** Store ticks → Store in-progress candles → TTL policies → Evictions → Serve queries → Publish metrics
**Failure Scenarios:** Cache unavailable, memory full, corruption, high miss rate
**Recovery:** Failover Redis, LRU eviction, rebuild, cache warming, fallback to DB

---

## 2. Market Regime Detection Engine

### 2.1 Regime Classifications
- **Trending Up/Down:** Higher highs/lower lows, ADX > 25
- **Ranging:** Price within band, ADX < 20
- **High/Low Volatility:** ATR above/below threshold
- **Breakout:** Volume spike, price outside range
- **Pullback:** Retracement in trending market
- **Consolidation:** Narrow range, low volume
- **News-Driven:** Scheduled news time, volume spike

### 2.2 Classification Workflow
1. Receive market data (OHLCV, indicators)
2. Extract features for each detector (statistical, ML, technical)
3. Run detectors independently
4. Collect outputs with confidence scores
5. Apply detector weights
6. Calculate weighted probabilities
7. Apply consensus threshold
8. Check for regime change (with hysteresis)
9. Update state and publish event

### 2.3 Confidence Scoring
```
overall_confidence = Σ(detector_confidence × detector_weight) / Σ(detector_weight)
```
Levels: High (>0.75), Medium (0.50-0.75), Low (0.25-0.50), Very Low (<0.25)

### 2.4 Required Features
- **Statistical:** Returns, volatility, trend strength, momentum, volume
- **ML:** Normalized price changes, volatility, volume ratios, time features, lagged returns
- **Technical:** Moving averages, Bollinger Bands, RSI, MACD, ATR, support/resistance

### 2.5 State Transitions
```
Unknown → Ranging → Trending/HighVol/LowVol → Consolidation → Breakout
```
Rules: Min hold time 5 candles, confidence threshold >0.60, hysteresis 0.15

### 2.6 Fail-Safe
Default: "Unknown" (insufficient data or detector failure)
Fallback: Secondary detector, last known regime with degrading confidence

---

## 3. Strategy Plugin Framework

### 3.1 Plugin Interface
Every strategy must implement:
- **Metadata:** name, version, author, category, risk level
- **Required Inputs:** data types, symbols, timeframes, fields
- **Timeframe Support:** list of supported timeframes
- **Market Compatibility:** asset classes, volatility regimes, sessions
- **Risk Assumptions:** position size, max risk, leverage, SL/TP requirements
- **Output Schema:** signal types, fields, confidence range
- **Validation Rules:** parameter constraints
- **Versioning:** semantic versioning
- **Health Status:** healthy/degraded/unhealthy

### 3.2 Lifecycle Methods
- **Load:** Load plugin, validate dependencies, register
- **Initialize:** Validate config, load historical data, run init logic
- **Execute:** Process event, generate signals, update state
- **Pause:** Stop processing, persist state
- **Resume:** Load state, resume processing
- **Stop:** Stop processing, cleanup, persist final state
- **Disable:** Stop, clear state, archive, unregister
- **Upgrade:** Backup, stop, load new version, migrate state, start

### 3.3 Lifecycle State Machine
```
Unloaded → Loaded → Initialized → Running ↔ Paused → Stopped → Disabled
```

### 3.4 Plugin Sandbox
- Resource isolation (CPU quota, memory limit)
- Network restrictions (no external calls except approved APIs)
- API access control (whitelist, no direct DB access)
- Security (code signature, dependency validation, static analysis)

---

## 4. Signal Validation Pipeline

### 4.1 Validation Stages

#### Stage 1: Duplicate Detection
Check signal fingerprint against recent signals (5 min window, price tolerance)

#### Stage 2: Data Integrity
Validate required fields, types, ranges, relationships, timestamps

#### Stage 3: Spread Filter
Reject if spread > absolute or relative threshold

#### Stage 4: Session Filter
Check against allowed/blocked sessions, trading hours

#### Stage 5: Risk Policy
Validate position size, risk per trade, leverage against limits

#### Stage 6: Existing Position
Check conflicts, correlation, concurrent positions, per-instrument limits

#### Stage 7: Exposure
Validate total/long/short/net exposure, margin requirements

#### Stage 8: Market State
Check regime compatibility, confidence, volatility, liquidity

#### Stage 9: Signal Expiry
Reject if signal age > threshold (default 60s)

#### Stage 10: Cooldown
Enforce cooldown periods between signals (default 30s)

### 4.2 Validation Result
```python
ValidationResult(is_valid, signal_id, validation_score, rejection_reasons, stage_results)
```

---

## 5. Position Management Engine

### 5.1 Position Lifecycle States
```
None → Pending → Partially Filled → Open ↔ Modified/Reducing → Closing → Closed → Archived
```

### 5.2 Partial Exits
Validate position state, validate exit size, create close order, update state on fill

### 5.3 Break-Even Logic
Monitor P&L, when >= trigger, move SL to entry ± offset, submit modification

### 5.4 Trailing Stop
On favorable movement >= step, calculate new SL = current ± distance, ensure improvement, submit modification

### 5.5 Position Synchronization
Fetch from broker, compare with internal, update on discrepancies, alert on conflicts

### 5.6 Position Recovery
Load persisted state, fetch from broker, reconcile (broker authoritative), restore state machine, alert on discrepancies

---

## 6. Risk Management Engine

### 6.1 Risk Policies (Modular & Configurable)

#### Position Sizing
Methods: Fixed, Percentage of Equity, Volatility-based (ATR), Kelly (capped)

#### Account Risk
Max total risk, max open risk, max pending risk as % of equity

#### Daily Loss
Max daily loss %, reset time, action on breach (block/reduce/close_all/kill_switch)

#### Drawdown
Max drawdown %, calculation method (realized/unrealized/total), recovery threshold

#### Max Simultaneous Trades
Max total, per instrument, per strategy, per direction

#### Correlation Limits
Correlation matrix, max correlated exposure, correlation threshold

#### Margin Protection
Min/critical margin level %, margin buffer, action on critical

#### Equity Protection
Min equity % of initial or absolute, action on breach

#### Kill Switch
Triggers (manual, margin, drawdown, anomalies), auto-enable, manual override

#### Emergency Stop
Close all positions, cancel orders, disable strategies, market orders only

#### Exposure Limits
Max long/short/net exposure %, max per-currency exposure

#### Portfolio Limits
Max portfolio Greeks, VaR at 95%/99%

### 6.2 Policy Hierarchy (Priority)
1. Kill Switch
2. Emergency Stop
3. Margin Protection
4. Daily Loss
5. Drawdown
6. Equity Protection
7. Exposure Limits
8. Portfolio Limits
9. Correlation Limits
10. Max Simultaneous Trades
11. Position Sizing

---

## 7. Execution Engine

### 7.1 Order Lifecycle States
```
None → Created → Validated → Submitted → Pending → Partially Filled/Filled
```
Branches: Rejected, Expired, Cancelled

### 7.2 Pre-Execution Validation
Parameter, account, broker, risk validation

### 7.3 Retry Policy
Max 3 retries, exponential backoff, retry on network/timeout errors, do not retry on invalid parameters/insufficient funds

### 7.4 Idempotency
Unique key per order, check recent orders (24h), return existing if duplicate

### 7.5 Duplicate Prevention
Signal-level (Validation Pipeline Stage 1), order-level (identical in 5 min), idempotency key

### 7.6 Timeout Handling
Submission 5s, acknowledgement 10s, fill 5min, cancellation 5s. On timeout: mark expired, request status, reconcile

### 7.7 Broker Acknowledgement
Wait for ack, extract broker order ID, update state, publish event

### 7.8 Partial Fill Handling
Update state to Partially Filled, continue waiting for remaining, or cancel if all-or-nothing

### 7.9 Slippage Controls
Calculate slippage = |execution - expected|, monitor against thresholds, alert/reject based on severity

### 7.10 Error Recovery
Transient (retry), Permanent (no retry, alert), Ambiguous (request status, reconcile)

### 7.11 Audit Trail
Log: created, validated, submitted, acknowledged, rejected, cancelled, fills, expired, timeout, slippage, errors

---

## 8. Event Bus

### 8.1 Event Schema
```python
Event(event_id, event_type, event_version, timestamp, source, correlation_id, causation_id, data, metadata)
```

### 8.2 Event Catalog

| Event | Publisher | Subscribers | Priority |
|-------|-----------|-------------|----------|
| MarketUpdated | Market Data | Strategy, Regime, Analytics | 1 |
| SignalGenerated | Strategy | Validation, Risk | 2 |
| SignalRejected | Validation | Strategy, Analytics, Alert | 3 |
| SignalValidated | Validation | Risk, Execution | 2 |
| TradeOpened | Position | Risk, Analytics, Journal, Alert | 3 |
| TradeClosed | Position | Risk, Analytics, Journal, Alert | 3 |
| RiskTriggered | Risk | Execution, Alert, Analytics | 1 |
| ExecutionFailed | Execution | Risk, Alert, Analytics | 1 |
| PositionUpdated | Position | Risk, Analytics, Dashboard | 4 |
| ConnectionLost | Data/Execution | Alert, Monitoring, Risk | 1 |
| ConnectionRecovered | Data/Execution | Alert, Monitoring | 2 |
| OrderSubmitted | Execution | Position, Analytics | 3 |
| OrderFilled | Execution | Position, Analytics | 2 |
| OrderCancelled | Execution | Position, Analytics | 3 |
| RegimeChanged | Regime | Strategy, Validation, Risk | 2 |
| StrategyStatusChanged | Strategy | Monitoring, Analytics, Dashboard | 3 |
| KillSwitchActivated | Risk | All Services | 1 |
| DataQualityAlert | Market Data | Monitoring, Alert, Strategy | 2 |

### 8.3 Guarantees
At-least-once delivery, per-partition ordering, dead letter queue for failures

---

## 9. Database Design

### 9.1 Core Tables

**Users:** id, email, username, password_hash, status, mfa_enabled, created_at, updated_at

**Accounts:** id, user_id, broker_id, broker_account_id, account_type, currency, balance, equity, margin, free_margin, margin_level, status

**Brokers:** id, name, display_name, api_type, api_endpoint, supports_demo/live, status

**Broker Connections:** id, account_id, broker_id, connection_type, status, last_connected_at, error_message

**Instruments:** id, symbol, name, asset_class, base/quote_currency, pip_size, tick_size, contract_size, trading_hours, is_active

**Strategies:** id, user_id, name, description, category, risk_level, version, code, parameters, status, health_status

**Strategy Versions:** id, strategy_id, version, code, parameters, is_active

**Signals:** id, strategy_id, instrument_id, signal_type, direction, entry_price, SL/TP, size, confidence, regime, validation_status, rejection_reasons, generated_at, expires_at

**Orders:** id, account_id, broker_id, instrument_id, position_id, signal_id, order_type, direction, size, price, stop_price, filled_size, avg_fill_price, status, broker_order_id, idempotency_key, submitted_at, filled_at

**Fills:** id, order_id, broker_order_id, fill_id, instrument_id, fill_size, fill_price, commission, slippage, fill_timestamp

**Positions:** id, account_id, instrument_id, strategy_id, direction, size, entry_price, current_price, unrealized_pnl, realized_pnl, SL/TP, trailing_stop, break_even_triggered, status, opened_at, closed_at

**Trades:** id, account_id, position_id, order_id, signal_id, strategy_id, instrument_id, direction, size, entry/exit_price, pnl, commission, swap, slippage, duration, regime_at_entry/exit, close_reason, opened/closed_at

**Trade Journal:** id, trade_id, account_id, strategy_id, notes, tags, screenshots, rating, lessons_learned

**Risk Events:** id, account_id, event_type, severity, current_value, limit_value, description, action_taken, resolved_at

**Logs:** id, timestamp, level, service, component, user_id, account_id, message, context, request_id (TimescaleDB hypertable)

**Notifications:** id, user_id, type, title, message, data, priority, status, channels, sent/delivered/read_at

**Licenses:** id, user_id, license_key, plan_type, status, starts/expires_at, features, limits, usage

**Audit Records:** id, timestamp, user_id, action, resource_type/id, ip_address, user_agent, changes, metadata (TimescaleDB hypertable)

### 9.2 Indexing Strategy
- Primary keys on all tables
- Foreign key indexes
- Timestamp indexes for time queries
- Status indexes for filtering
- Composite indexes for common patterns
- TimescaleDB hypertables for logs/audit (time partitioning)
- Partial indexes for active records

---

## 10. Reliability

### 10.1 API Outages
Detection: timeout, consecutive failures, error rate. Mitigation: failover, circuit breaker, queuing, backoff. Recovery: reconnect, process queue, backfill.

### 10.2 Internet Failures
Detection: ping, DNS, connection timeouts. Mitigation: local buffering, graceful degradation, offline mode. Recovery: reconnect, sync, reconcile.

### 10.3 VPS Restart
Detection: startup detection, state validation. Mitigation: state persistence, DB as source of truth. Recovery: load state, reconcile, resume.

### 10.4 Duplicate Requests
Detection: idempotency keys, deduplication, unique constraints. Mitigation: idempotency validation, fingerprinting, optimistic locking. Recovery: return original, log duplicates.

### 10.5 Corrupted Data
Detection: validation, checksums, schema checks. Mitigation: validation before processing, rejection, backups, WAL. Recovery: restore backup, repair tools, manual correction.

### 10.6 Clock Drift
Detection: NTP monitoring, timestamp validation, broker comparison. Mitigation: NTP sync, UTC internal, validation. Recovery: resync, reject invalid timestamps, manual correction.

### 10.7 Database Failures
Detection: health checks, query timeouts, replication lag. Mitigation: primary-replica, connection pooling, circuit breaker, caching. Recovery: failover, retry, replay, manual intervention.

### 10.8 Queue Failures
Detection: health checks, lag monitoring, delivery failures. Mitigation: multiple brokers, DLQ, persistence, buffering. Recovery: reconnect, replay DLQ, replay persistence, consumer catch-up.

### 10.9 Cache Failures
Detection: health checks, hit rate, error rate. Mitigation: cache-aside, multiple layers, graceful degradation. Recovery: reconnect, rebuild from DB, warming, alert.

### 10.10 Service Crashes
Detection: health checks, process monitoring, heartbeat. Mitigation: auto-restart, state persistence, circuit breakers, graceful shutdown. Recovery: restart, restore state, reconcile, alert on repeats.

---

## 11. Observability

### 11.1 Structured Logging
Format: timestamp, level, service, component, user/account/strategy_id, message, context, request/correlation_id. Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL. Aggregation: Loki, retention 30d/90d/1y.

### 11.2 Metrics
Types: Counter, Gauge, Histogram, Summary. Key metrics: system (CPU, memory, disk), application (request rate, error rate, latency), business (orders, positions, P&L, win rate). Labels: service, component, broker, instrument, strategy, status.

### 11.3 Dashboards
System Health (service status, resources, errors, latency), Trading (equity, positions, orders, P&L, risk), Strategy (status, signal rate, performance), Market Data (feed status, latency, spread, quality), Risk (limits, exposure, margin, events).

### 11.4 Alerts
Severity: INFO, WARNING, CRITICAL, EMERGENCY. Conditions: service down, error rate >5%, latency p99 >1s, resource >90%, order failure, execution timeout, position sync failure, broker connection lost, data feed failure, risk breaches, data quality issues. Channels: email, SMS, push, Slack/Teams, PagerDuty. Escalation: Warning→Email, Critical→SMS+PagerDuty, Emergency→Phone+All.

### 11.5 Health Checks
Endpoints: /health, /health/ready, /health/live, /health/dependencies. Components: database, cache, queue, broker API, disk space.

### 11.6 Tracing
OpenTelemetry, Jaeger backend, trace context propagation. Spans: service boundaries, DB queries, API calls, messaging, strategy execution. Sampling: 100% errors, 10% normal.

### 11.7 Diagnostics
Endpoints: /debug/pprof, /debug/vars, /debug/config, /debug/connections. Tools: memory/CPU profiling, thread dumps, connection pool status, cache stats.

### 11.8 Runtime Monitoring
Stack: Prometheus (metrics), Grafana (viz), Loki (logs), Jaeger (traces), AlertManager (alerts).

---

## 12. Architecture Diagrams

### 12.1 Module Interaction
```
Market Data → Regime Detection → Strategy Framework → Signal Validation → Risk Management → Execution → Position Management → Trade Journal
                    ↓                      ↓                      ↓
                 Event Bus ◄─────────────────────────────────────────────────────────────┘
```

### 12.2 Data Flow Sequence
Broker → Market Data → Strategy → Signal Validation → Risk → Execution → Broker → Position → Trade Journal

### 12.3 Error Recovery Sequence
Service A → Service B (Error) → Retry Logic → Circuit Breaker → Alert Service

---

## 13. Engineering Decisions

### 13.1 Technology Choices
- **Python:** Quant finance ecosystem, async support
- **FastAPI:** High performance, auto docs, async
- **gRPC:** High performance, strong typing, streaming
- **PostgreSQL + TimescaleDB:** ACID, time-series optimization
- **Redis:** High performance, rich data structures
- **Kafka:** High throughput, durability, streaming
- **Kubernetes:** Industry standard, self-healing, auto-scaling

### 13.2 Architecture Decisions
- **Microservices:** Independent scaling, fault isolation
- **Event-Driven:** Loose coupling, async processing, audit trail
- **Plugin Architecture:** Extensibility, isolation, versioning
- **Clean Architecture:** Testability, maintainability
- **DDD Bounded Contexts:** Clear boundaries, ubiquitous language

### 13.3 Trade-offs
- **Consistency vs Availability:** Eventual for some, strong for critical
- **Latency vs Throughput:** Optimize latency for trading, throughput for analytics
- **Complexity vs Simplicity:** Accept complexity for flexibility
- **Cost vs Performance:** Cloud-native, reserved for predictable, spot for batch

---

## 14. Future Extension Points

### 14.1 Additional Asset Classes
Crypto, commodities, indices, stocks, options, futures. Extension: instrument schema, broker adapters, order types.

### 14.2 Advanced Order Types
OCO, IF-THEN, trailing stops, iceberg, algo orders. Extension: order schema, execution logic, broker support.

### 14.3 ML-Based Strategies
Deep learning, reinforcement learning, ensemble methods. Extension: strategy framework, model storage, training pipeline.

### 14.4 Social Trading
Copy trading, strategy sharing, leaderboards. Extension: user schema, permission model, social features.

### 14.5 Mobile Applications
iOS, Android apps. Extension: API layer, mobile-specific endpoints, push notifications.

### 14.6 API for Third Parties
Public API, webhooks, integrations. Extension: API gateway, rate limiting, API keys.

### 14.7 Advanced Analytics
Real-time analytics, predictive analytics, custom reports. Extension: analytics engine, data warehouse, BI tools.

### 14.8 Multi-Region Deployment
Global deployment, data locality, compliance. Extension: infrastructure, data replication, compliance.

---

**Document Status:** Draft  
**Next Review:** August 2026  
**Approved By:** [Pending]
