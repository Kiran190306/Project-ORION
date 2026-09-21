# Project ORION — EPIC-026 Broker Adapter Contract & Execution Pipeline
# Institutional Adapter Interface, Inviolable Execution Chain & Idempotency Guarantees

**Document Version:** 1.0.0  
**Date:** 2026-09-21  
**Author:** Institutional Trading Systems & Broker Integration Engineering  
**Milestone:** EPIC-026 — Institutional Broker Sandbox & Demo Broker Integration  
**Classification:** Technical Architecture Specification  

---

## 1. Broker Adapter Architectural Principles

The broker layer in Project ORION enforces strict decoupling between domain trading logic and external broker communication protocols.

### Architectural Principles
1. **Domain Isolation:** The domain layer is broker-agnostic. No broker-specific SDKs, HTTP schemas, or vendor exception types may enter `libraries/domain/`.
2. **Deterministic In-Memory Sandbox:** `MockBrokerAdapter` serves as the CI/local verification engine with reproducible pseudorandom seeds, simulated latency, partial fills, slippage, and configurable fault injection.
3. **External Provider Integration:** `OANDAExecutionAdapter` handles official v20 REST practice accounts (`api-fxpractice.oanda.com`) only when genuine sandbox credentials are supplied.
4. **Closed Factory Registry:** `ExecutionAdapterFactory` creates adapters strictly from an enumerated closed set (`paper`, `mock`, `sandbox_mock`, `sandbox_oanda`). Any attempt to request a `LIVE` environment fails closed.

---

## 2. Inviolable Order Execution Pipeline

No API endpoint, service, or autonomous cycle may submit an order to an adapter without traversing the complete institutional pre-trade validation chain:

```
User / Strategy Order Request
             │
             ▼
[Step 1: Entitlement & Quota Check]
  ├── check_broker_sandbox_account_quota()
  ├── check_broker_sandbox_order_quota()
  └── check_asset_access(symbol)
             │
             ▼
[Step 2: Canonical Order Construction]
  ├── OrderId(uuid4)
  ├── DecisionId & ExecutionId (client_order_id)
  └── Decimal precision normalized
             │
             ▼
[Step 3: RiskEngine Pre-Trade Gate]
  ├── TradeDecision & RiskContext evaluation
  ├── Drawdown, leverage, and margin limits checked
  └── Reject & fail closed (HTTP 422) if breached
             │
             ▼
[Step 4: OrderValidator Pre-Dispatch Gate]
  ├── Symbol validity, volume thresholds (< 10M units)
  ├── Price and side consistency
  └── Reject & fail closed (HTTP 422) if invalid
             │
             ▼
[Step 5: Broker Adapter Dispatch]
  ├── Adapter connection verification
  ├── Idempotency tracking (client_order_id)
  └── Timeout handled as UNKNOWN (NOT_SAFE_TO_RETRY)
             │
             ▼
[Step 6: Database Persistence & Audit Trail]
  ├── Local OrderModel & FillModel recorded
  └── Latency, slippage, and execution receipts logged
```

---

## 3. Idempotency & Timeout Handling (UNKNOWN State)

Submitting an order to a financial exchange or broker is **NOT SAFE TO RETRY** on network timeout or connection reset:

### The UNKNOWN State Guarantee
- When an adapter encounters a timeout or transport error *after* dispatching an order:
  1. The order status is recorded as `UNKNOWN`.
  2. The system **never** automatically resubmits or retries the order. A blind retry could result in double-fill execution and severe unhedged exposure.
  3. The order is flagged for State Reconciliation or manual review.
  4. The client receives an explicit status `UNKNOWN` with `rejection_reason="Execution timeout after order submission; status UNKNOWN (NOT_SAFE_TO_RETRY)"`.

---

## 4. `MockBrokerAdapter` Deterministic Simulation & Fault Injection

The `MockBrokerAdapter` provides institutional testing fidelity without requiring third-party network connectivity:

- **Seeded Determinism:** Supports deterministic random seeds for unit and integration testing.
- **Configurable Modes:**
  - `NORMAL`: Instant fill at arrival mid price or requested limit price.
  - `REJECT`: Injects broker-level order rejection.
  - `RATE_LIMIT`: Simulates HTTP 429 rate limit errors.
  - `TIMEOUT`: Simulates broker network timeouts to verify `UNKNOWN` handling.
- **Position Netting:** Maintains long/short positions per symbol, updating net quantity, average entry price, and realized PnL on opposite-side trades.
- **Precision:** Uses exact `Decimal` arithmetic for quantities, prices, commissions, and balances.
