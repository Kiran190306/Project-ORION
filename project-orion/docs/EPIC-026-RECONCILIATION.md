# Project ORION — EPIC-026 State Reconciliation Engine & Audit Specification
# Ledger vs Broker State Auditing, Discrepancy Taxonomy & Zero Silent Mutation Policy

**Document Version:** 1.0.0  
**Date:** 2026-09-21  
**Author:** Quantitative Systems Engineer & Reconciliation Auditor  
**Milestone:** EPIC-026 — Institutional Broker Sandbox & Demo Broker Integration  
**Classification:** Technical Compliance & Audit Manual  

---

## 1. Institutional Purpose of Reconciliation

In financial trading architectures, internal ledger states (orders, positions, cash balance, margin) can diverge from broker states due to:
- Network packet loss and timeout drops.
- Asynchronous partial fills or fee deductions.
- External actions taken directly in the broker console.
- Simulated exchange resets.

The `BrokerReconciliationEngine` performs deterministic periodic and on-demand audits comparing ORION's internal database state with external sandbox broker state.

---

## 2. Inviolable Policy: Zero Silent Local Mutation

> [!IMPORTANT]
> **Resolution Policy: `ALERT + AUDIT + MANUAL REVIEW`**
> Under no circumstances does the State Reconciliation Engine automatically overwrite or mutate internal order records, positions, or ledger balances to force alignment with the broker.
> Automated silent mutations can destroy audit trails, conceal rogue executions, and introduce severe race conditions.

All discrepancies are captured in immutable snapshots (`BrokerReconciliationSnapshotModel`), recorded in the audit trail, and presented to Risk Officers for authorized human review.

---

## 3. Discrepancy Taxonomy

The engine identifies 11 distinct discrepancy types categorized across three entities:

### 3.1 Order Discrepancies
| Discrepancy Code | Severity | Description |
|---|:---:|---|
| `ORDER_MISSING_INTERNALLY` | CRITICAL | An order exists on the broker sandbox that has no corresponding record in ORION's database. |
| `ORDER_MISSING_ON_BROKER` | HIGH | An order is recorded in ORION's database but was never recognized or recorded by the broker. |
| `ORDER_STATUS_MISMATCH` | MEDIUM | Order status diverges (e.g. ORION shows `NEW` while broker shows `FILLED` or `CANCELLED`). |
| `ORDER_QUANTITY_MISMATCH` | HIGH | The filled quantity reported by the broker differs from ORION's recorded fill quantity. |

### 3.2 Position Discrepancies
| Discrepancy Code | Severity | Description |
|---|:---:|---|
| `POSITION_MISSING_INTERNALLY` | CRITICAL | The broker reports an open position for a symbol where ORION has no active position recorded. |
| `POSITION_MISSING_ON_BROKER` | CRITICAL | ORION records an open position that does not exist on the broker (potential phantom exposure). |
| `POSITION_QUANTITY_MISMATCH` | HIGH | Net quantity of units held diverges beyond tolerance limits. |

### 3.3 Account & Balance Discrepancies
| Discrepancy Code | Severity | Description |
|---|:---:|---|
| `CASH_BALANCE_MISMATCH` | MEDIUM | Cash balance diverges beyond the configured tolerance band (default: $0.01). |
| `EQUITY_MISMATCH` | MEDIUM | Total net equity diverges beyond the tolerance band. |
| `MARGIN_MISMATCH` | LOW | Allocated margin diverges between ledger and broker. |
| `UNKNOWN` | HIGH | Uncategorized or unparseable state difference. |

---

## 4. Tolerance Bands & Mathematical Precision

Reconciliation utilizes exact `Decimal` arithmetic to avoid floating-point inaccuracies:
- **Cash & Equity Tolerance:** Configurable threshold (default `Decimal("0.01")`). Differences $\le \$0.01$ resulting from sub-pip rounding are marked as informational warnings rather than hard discrepancies.
- **Position Units:** Absolute unit matching. In institutional FX, position units must match integer quantities.

---

## 5. Audit Snapshot Persistence Schema

Every audit execution generates an immutable database snapshot in `broker_reconciliation_snapshots`:

```sql
CREATE TABLE broker_reconciliation_snapshots (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) REFERENCES organizations(id),
    broker_account_id VARCHAR(64) REFERENCES broker_sandbox_accounts(id),
    status VARCHAR(32) NOT NULL,              -- MATCHED, DISCREPANCY, ERROR, UNKNOWN
    has_discrepancies BOOLEAN NOT NULL,
    order_discrepancies_count INTEGER NOT NULL,
    position_discrepancies_count INTEGER NOT NULL,
    account_discrepancies_count INTEGER NOT NULL,
    discrepancies JSONB NOT NULL,             -- Detailed diff records
    resolution_policy VARCHAR(64) NOT NULL,   -- ALERT_AND_AUDIT
    manual_review_required BOOLEAN NOT NULL,
    internal_state_preserved BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```
