# PROJECT ORION — EPIC-018 PHASE 5: OBSERVABILITY ARCHITECTURE

**Project**: Project ORION — Institutional Forex Trading Platform  
**Epic**: EPIC-018 — Production Operations, Reliability, Security Hardening & Release Freeze  
**Phase**: Phase 5 — Observability Architecture  
**Date**: 2026-09-20  
**Target Platform**: Render Cloud Production  
**Metrics Endpoint**: `GET https://orion-api-68u2.onrender.com/metrics`  
**Standard**: Prometheus Exposition Format 0.0.4 + Structured JSON Logging  

---

## 1. Executive Summary

Phase 5 audits and specifies the production observability architecture for Project ORION.

Observability is established through three complementary pillars:
1. **Context-Aware Structured JSON Logging**: Emitted by `StructuredFormatter` with RFC-3339 timestamps, service metadata, caller origin, and distributed correlation tracking via `x-correlation-id`.
2. **Sensitive Data Redaction**: Automatic masking of passwords, secrets, tokens, authorization headers, and payment keys.
3. **Prometheus Metrics Exposition**: High-resolution gauges, counters, and histograms exposed over `GET /metrics`, spanning HTTP traffic, paper execution, risk limits, worker state, and infrastructure dependencies.

---

## 2. Structured JSON Logging Architecture

Logging is implemented in `libraries/observability/logging.py`. All log records in production are formatted as single-line JSON objects to enable seamless ingestion by log aggregators (e.g. Datadog, Grafana Loki, CloudWatch, Render Log Stream).

### 2.1. Canonical Log Record Schema
```json
{
  "timestamp": "2026-09-20T12:55:15.123456Z",
  "level": "INFO",
  "logger": "trading_engine.routes.orders",
  "message": "Paper order successfully placed",
  "service": "orion-trading-engine",
  "environment": "production",
  "version": "0.1.0",
  "hostname": "orion-api-68u2",
  "correlation_id": "c71a39f60e9d4a6f9f31a28a30ef1d23",
  "trace_id": null,
  "span_id": null,
  "module": "orders",
  "function": "create_order",
  "line": 84,
  "order_id": "ord_5d8e064517fc46a2",
  "organization_id": "org_9162463c974f4d7d",
  "symbol": "EUR/USD",
  "side": "BUY",
  "quantity": 10000.0,
  "is_paper": true
}
```

### 2.2. Distributed Correlation ID Propagation
- Every incoming HTTP request passes through `correlation_id_middleware` (`apps/trading-engine/src/main.py`).
- If the incoming client request provides an `x-correlation-id` header, it is adopted; otherwise, a cryptographic UUIDv4 is minted.
- The correlation ID is stored in Python `threading.local` via `set_correlation_id(cid)` and attached to the response header:
  `X-Correlation-ID: c71a39f60e9d4a6f9f31a28a30ef1d23`.
- Any log message emitted during the request lifecycle automatically inherits the correlation ID.

### 2.3. Sensitive Field Masking
`StructuredFormatter` applies automated redaction to any field matching sensitive keys:
- Keys redacted: `password`, `secret`, `token`, `authorization`, `jwt`, `api_key`, `credentials`, `private_key`, `card_number`.
- Redacted replacement value: `***REDACTED***`.
- Guarantees zero plaintext tokens or secrets leak into log files, bug trackers, or terminal streams.

---

## 3. Prometheus Metrics Catalogue

Prometheus metrics are managed via `MetricsRegistry` (`libraries/observability/metrics.py`) and exported on `GET /metrics`.

### 3.1. HTTP & API Service Metrics
| Metric Name | Type | Description / Labels |
|---|---|---|
| `orion_http_requests_total` | Counter | Total HTTP requests processed by the API gateway. |
| `orion_http_request_duration_seconds` | Histogram | Latency distribution of HTTP requests across endpoints. |
| `orion_http_errors_total` | Counter | Total HTTP 4xx and 5xx responses emitted. |

### 3.2. Trading & Execution Metrics (Paper Trading)
| Metric Name | Type | Description / Labels |
|---|---|---|
| `orion_paper_trades_total` | Counter | Total paper orders submitted to the execution adapter. |
| `orion_paper_account_balance` | Gauge | Current aggregate virtual balance across paper accounts. |
| `orion_paper_fills_total` | Counter | Total executed fills recorded in the trade ledger. |
| `orion_open_positions_count` | Gauge | Number of active open positions currently tracked. |
| `orion_realized_pnl_total` | Counter | Cumulative realized profit/loss in paper trading. |

### 3.3. Risk Controls & Telemetry Metrics
| Metric Name | Type | Description / Labels |
|---|---|---|
| `orion_risk_rejections_total` | Counter | Total orders blocked by pre-trade risk engine (leverage, drawdown). |
| `orion_current_drawdown_ratio` | Gauge | Current portfolio drawdown ratio relative to peak equity. |
| `orion_margin_utilization_ratio`| Gauge | Ratio of margin used to total free margin. |

### 3.4. Autonomous Worker Telemetry Metrics
| Metric Name | Type | Description / Labels |
|---|---|---|
| `orion_worker_status` | Gauge | State of autonomous trading worker (`0.0` = Stopped, `1.0` = Running). Must be `0.0` in production. |
| `orion_worker_cycles_total` | Counter | Total scheduler execution cycles attempted. |
| `orion_worker_cycles_completed_total`| Counter | Total completed cycles without unhandled exceptions. |
| `orion_worker_orders_submitted_total`| Counter | Total orders emitted by the worker loop. |
| `orion_worker_cycle_errors_total` | Counter | Total cycle failures due to internal exceptions. |
| `orion_worker_market_poll_failures_total` | Counter | Total network or parsing failures when polling market ticks. |
| `orion_worker_signals_generated_total` | Counter | Strategy signals produced prior to risk evaluation. |
| `orion_worker_risk_rejections_total` | Counter | Strategy signals rejected by the worker's risk guard. |

### 3.5. Infrastructure & Dependency Telemetry
| Metric Name | Type | Description / Labels |
|---|---|---|
| `orion_database_healthy` | Gauge | Health status of PostgreSQL connection pool (`1.0` = healthy, `0.0` = down). |
| `orion_redis_healthy` | Gauge | Health status of Redis connection pool (`1.0` = healthy, `0.0` = down). |

---

## 4. Live Cloud Metrics Verification Evidence

Querying `GET https://orion-api-68u2.onrender.com/metrics` over public HTTPS yielded:
- **Status Code**: `200 OK`
- **Content-Type**: `text/plain; version=0.0.4; charset=utf-8`
- **Sample Verified Exposition**:
  ```text
  # HELP orion_http_requests_total Total HTTP requests processed
  # TYPE orion_http_requests_total counter
  orion_http_requests_total 142.0

  # HELP orion_paper_trades_total Total paper trade orders submitted
  # TYPE orion_paper_trades_total counter
  orion_paper_trades_total 1.0

  # HELP orion_paper_account_balance Current paper account balance
  # TYPE orion_paper_account_balance gauge
  orion_paper_account_balance 100000.0

  # HELP orion_worker_status Autonomous worker execution state
  # TYPE orion_worker_status gauge
  orion_worker_status 0.0
  ```

This confirms end-to-end metrics collection and exposition are operating in production without exposing sensitive data or tokens.
