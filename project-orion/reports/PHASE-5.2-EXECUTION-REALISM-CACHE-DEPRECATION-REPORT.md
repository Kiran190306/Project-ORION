# PHASE 5.2 EXECUTION REALISM & CACHE DEPRECATION REPORT
**Project ORION â€” Backtesting Engine Realism & Cache Hardening**
**Date:** 2026-10-03
**Status:** **PASS â€” PHASE 5.2 COMPLETE**

---

## 1. Executive Summary

Phase 5.2 successfully delivers two high-impact enhancements to Project ORION:
1. **TD-002 (Intra-bar Take-Profit Execution):** Implemented deterministic, financially realistic, auditable intra-bar take-profit execution in `StrategyBacktestAdapter` (`libraries/domain/backtesting/strategy_adapter.py`). It mirrors the existing stop-loss execution model, supports take-profit specifications from both `PositionIntent.take_profit` and `Signal.metadata["take_profit"]`, applies bid/ask half-spread and adverse slippage modeling, enforces strict Decimal arithmetic, preserves candlestick pattern attribution, and establishes an institutional conservative risk-first same-candle resolution convention when both SL and TP levels are breached on the same bar.
2. **TD-005 (Legacy Candle Cache Fallback Deprecation):** Completed an audit of all production callers and removed the legacy cache fallback key format (`market:candles:{symbol}:{timeframe}`) from `MarketDataCache.get_candles` (`libraries/infrastructure/market_data/cache.py`). Production services (`MarketDataService`) exclusively use canonical provider-isolated keys (`market:candles:{provider}:{symbol}:{timeframe}`). Verified cross-provider isolation and added regression tests proving legacy keys are never silently consumed.

All 6 required test suites passed completely: 1,513 unit tests passed across backtesting, research, strategies, and market data infrastructure. Zero regressions were introduced to Phase 4 or Phase 5.1. Strict paper-trading invariants ($0 live capital at risk) were rigorously preserved.

---

## 2. Pre-Phase Baseline

- **Phase 4 Freeze:** Phase 4 remains completely frozen and was not reopened.
- **Phase 5.1 Baseline:** Technical debt items TD-001, TD-003, TD-004/007, TD-006, TD-008, TD-009, TD-010, TD-011, TD-012, TD-013, TD-014, and TD-015 were verified resolved in `reports/PHASE-5.1-TECHNICAL-DEBT-REMEDIATION-REPORT.md`.
- **Known Pre-existing Failures:** Two known billing tests remain failing due to an upstream test database schema mismatch:
  - `tests/unit/test_billing.py::test_subscription_cancellation_at_period_end`
  - `tests/unit/test_billing.py::test_entitlement_service_integration`
  These two tests were confirmed pre-existing, were not modified, and remain isolated.
- **Capital Safety Invariant:** Strict paper-trading invariant ($0 live capital) preserved across all adapters and simulation loops.

---

## 3. TD-002 Audit

Before implementing TD-002, the execution pipeline in `StrategyBacktestAdapter` was audited:
1. **PositionIntent Model:** `libraries/domain/strategy/models.py` already defined `take_profit: Decimal | None = None` alongside `stop_loss: Decimal | None = None`.
2. **Signal Metadata:** Strategies occasionally attach `take_profit` as a string or float in `Signal.metadata`.
3. **TradeRecord Model:** `libraries/domain/research/models.py` already included `TAKE_PROFIT` in the documented enumeration for `exit_reason`: `"SIGNAL, STOP_LOSS, TAKE_PROFIT, END_OF_DATA"`.
4. **Validation Conventions:** `libraries/domain/strategy/validation.py` defines `StopLossTakeProfitError` for price inconsistencies (e.g. Long TP below entry price, or Short TP above entry price).
5. **Execution Timing & Causality:** Stop-loss was evaluated at the start of `on_candle` for carried positions (`entry_time < timestamp`). However, take-profit was completely omitted, forcing profitable trades to wait for an opposing close signal (`exit_reason="SIGNAL"`) or backtest termination (`exit_reason="END_OF_DATA"`), misrepresenting strategy performance and win rates.

---

## 4. TD-002 Implementation

In `libraries/domain/backtesting/strategy_adapter.py`:
- **Imports:** Imported `StopLossTakeProfitError` from `libraries.domain.strategy.exceptions`.
- **Extraction & Storage:**
  - Extracted `tp_val` on position opening with canonical priority:
    1. `result.position_intent.take_profit`
    2. `Decimal(str(result.signal.metadata["take_profit"]))`
  - Stored `take_profit: tp_val` in `self._open_position`.
- **Validation:**
  - Positive distance validation: `tp_val <= Decimal(0)` raises `ValueError("Take profit price must be positive")`.
  - Wrong-side & zero-distance validation against `fill_price`:
    - For Long positions (`sig_side == "BUY"`): `tp_val <= fill_price` raises `StopLossTakeProfitError(f"For long positions, take_profit ({tp_val}) must be above entry_price ({fill_price})")`.
    - For Short positions (`sig_side == "SELL"`): `tp_val >= fill_price` raises `StopLossTakeProfitError(f"For short positions, take_profit ({tp_val}) must be below entry_price ({fill_price})")`.
  - Stop-loss validation was symmetrically applied to protect against inverted SL assignments.

---

## 5. TP Execution Semantics

In `StrategyBacktestAdapter.on_candle`:
- **Timing & Eligibility:** Evaluated at the start of `on_candle` across the current bar's `[effective_low, effective_high]` range. Carried positions are strictly filtered by `self._open_position["entry_time"] < timestamp`. Newly opened positions on candle $T$ cannot self-exit intra-bar on candle $T$.
- **Trigger Conditions:**
  - **LONG Position (`pos_side == "BUY"`):** `tp_triggered = (tp is not None and effective_high >= tp)`
  - **SHORT Position (`pos_side == "SELL"`):** `tp_triggered = (tp is not None and effective_low <= tp)`
- **Attribution Preservation:** Exits via take-profit copy `metadata=dict(self._open_position.get("metadata", {}))` to `TradeRecord.metadata`, retaining candlestick pattern IDs, confidence, and strength metrics.

---

## 6. SL/TP Same-Candle Convention

### Conservative Risk-First Resolution
When analyzing historical OHLC candles, intrabar tick sequencing is absent unless tick-level data or order books are replayed. When high volatility causes a candle's extremes to breach **both** the Stop-Loss and Take-Profit thresholds within the same bar:
- **Decision:** The engine deterministically prioritizes **`STOP_LOSS`**.
- **Rationale:** Assuming Take-Profit was hit first without tick path evidence introduces optimistic survivorship bias into quantitative research. Applying the conservative risk-first standard ensures backtested performance is robust and defensible for production capital allocation.
- **Verification:** Both LONG and SHORT same-candle conflict scenarios are explicitly covered and verified in unit tests.

---

## 7. Fill-Price Model

Execution fill pricing mirrors the project's bid/ask spread and adverse slippage cost model:
- **LONG Take-Profit Exit (Sell Order):**
  $$\text{exit\_fill\_price} = \text{take\_profit} - \text{half\_spread} - \text{adverse\_slippage}$$
- **SHORT Take-Profit Exit (Buy Order):**
  $$\text{exit\_fill\_price} = \text{take\_profit} + \text{half\_spread} + \text{adverse\_slippage}$$
- **Commission Fees:**
  $$\text{commission\_rate} = \frac{\text{commission\_per\_lot}}{100{,}000}$$
  $$\text{exit\_fee} = (\text{pos\_q} \times \text{commission\_rate}).\text{quantize}(\text{Decimal}(\text{"0.01"}))$$
  $$\text{total\_fees} = \text{entry\_fee} + \text{exit\_fee}$$
- **PnL Accounting:**
  $$\text{gross\_pnl} = (\text{exit\_fill\_price} - \text{entry\_p}) \times \text{pos\_q} \quad (\text{for LONG})$$
  $$\text{gross\_pnl} = (\text{entry\_p} - \text{exit\_fill\_price}) \times \text{pos\_q} \quad (\text{for SHORT})$$
  $$\text{net\_pnl} = \text{gross\_pnl} - \text{total\_fees}$$
  $$\text{balance} \leftarrow \text{balance} + \text{net\_pnl}$$

All calculations use strict `Decimal` types with zero float approximations.

---

## 8. Exit-Reason Changes

The four canonical exit reasons in `TradeRecord.exit_reason` are now fully operational:
1. `TAKE_PROFIT` â€” Intra-bar exit when candle high/low reaches the take-profit price.
2. `STOP_LOSS` â€” Intra-bar exit when candle low/high breaches the stop-loss price (or when both SL/TP are breached on the same bar).
3. `SIGNAL` â€” Bar-close exit when an opposing strategy signal closes the active position via netting.
4. `END_OF_DATA` â€” Simulation finalization exit at the final candle close.

---

## 9. Attribution Behavior

Candlestick pattern attribution metadata is captured at position entry:
- `pattern_id`
- `pattern_confidence`
- `pattern_strength`

When an intra-bar take-profit triggers, `metadata=dict(self._open_position.get("metadata", {}))` is forwarded to `TradeRecord.metadata`. Unit test `test_pattern_attribution_survives_tp_exit` confirms pattern attribution remains 100% intact through take-profit exits.

---

## 10. Determinism Validation

Unit test `test_deterministic_repeated_execution` instantiates two independent backtest adapters with identical strategy logic, price series, and take-profit levels. Results verified:
- Identical trade counts (1 == 1)
- Identical exit price: `1.08980 == 1.08980`
- Identical gross PnL: `+46.00 == +46.00`
- Identical net PnL: `+44.00 == +44.00`
- Identical fees: `2.00 == 2.00`
- Identical exit reason: `TAKE_PROFIT == TAKE_PROFIT`
- Identical final balance: `10044.00 == 10044.00`

---

## 11. TD-005 Audit

Audit of production codebase for `market:candles:{symbol}:{timeframe}` and `provider="default"`:
1. `apps/trading-engine/src/services/market_data_service.py` (lines 143â€“168):
   - Always invokes `self.cache.get_candles(symbol, timeframe, provider=self.provider_name)`.
   - Never passes `provider="default"`.
   - Keys written and read are strictly `market:candles:{provider}:{symbol}:{timeframe}`.
2. `libraries/infrastructure/market_data/cache.py`:
   - `build_candle_key(symbol, timeframe, provider="default")` generates isolated key when provider is provided.
   - Fallback read in `get_candles()` previously attempted a second lookup using the non-isolated key `market:candles:{symbol}:{timeframe}` if `provider == "default"` and no data was found.
3. No other services or production tasks depend on the legacy key structure.

---

## 12. Legacy Fallback Removal

In `libraries/infrastructure/market_data/cache.py:get_candles`:
- Removed lines:
  ```python
  # Fallback to legacy key without provider for backward compatibility
  if not raw and provider == "default":
      legacy_key = f"market:candles:{symbol.upper()}:{timeframe}"
      raw = await self._redis.get(legacy_key)
  ```
- All lookups now strictly query the canonical provider-isolated key:
  `market:candles:{provider}:{symbol.upper()}:{timeframe}`.

---

## 13. Cache Isolation Validation

Tests in `tests/unit/infrastructure/market_data/test_cache_provider_isolation.py` prove:
1. **Provider Isolation:** Provider A ("provider_a") and Provider B ("provider_b") caching identical symbol/timeframe do not collide or leak data.
2. **Key Format:** Canonical keys adhere to `market:candles:{provider}:{symbol}:{timeframe}`.
3. **Legacy Deprecation Proof:** Test `test_legacy_cache_key_not_consumed_fallback_deprecated` seeds Redis with the legacy key `market:candles:EUR/USD:H1`. Querying `get_candles("EUR/USD", "H1", provider="default")` returns `None`, proving legacy fallback keys are completely ignored and cannot cause silent cache poisoning.

---

## 14. Files Changed

| File Path | Change Summary |
|:---|:---|
| `libraries/domain/backtesting/strategy_adapter.py` | Added `StopLossTakeProfitError` import; implemented intra-bar TP trigger; conservative risk-first SL/TP conflict resolution; TP fill price calculation; TP validation on entry; updated docstrings to document execution realism. |
| `libraries/infrastructure/market_data/cache.py` | Removed legacy fallback key lookup in `get_candles()`. |
| `tests/unit/infrastructure/market_data/test_cache_provider_isolation.py` | Added regression test `test_legacy_cache_key_not_consumed_fallback_deprecated`. |
| `tests/unit/domain/research/test_adapter_take_profit.py` | New comprehensive unit test suite covering requirements A through N (15 test cases). |

---

## 15. Tests Added

In `tests/unit/domain/research/test_adapter_take_profit.py`:
1. `test_long_tp_hit_by_candle_high` (Req A, G)
2. `test_short_tp_hit_by_candle_low` (Req B)
3. `test_long_tp_fill_price_spread_slippage_and_commission` (Req C, D, E, F)
4. `test_short_tp_fill_price_spread_slippage_and_commission` (Req C, D, E, F)
5. `test_same_bar_sl_tp_both_touched_long_triggers_stop_loss` (Req H)
6. `test_same_bar_sl_tp_both_touched_short_triggers_stop_loss` (Req H)
7. `test_newly_opened_position_cannot_self_exit_on_same_candle` (Req I)
8. `test_pattern_attribution_survives_tp_exit` (Req J)
9. `test_tp_via_signal_metadata_fallback` (Req 1)
10. `test_legacy_strategy_without_tp_unchanged` (Req K)
11. `test_deterministic_repeated_execution` (Req L)
12. `test_long_tp_wrong_side_validation_raises` (Req M)
13. `test_short_tp_wrong_side_validation_raises` (Req M)
14. `test_zero_or_negative_tp_raises_value_error` (Req N)
15. `test_zero_distance_tp_raises_stop_loss_take_profit_error` (Req N)

In `tests/unit/infrastructure/market_data/test_cache_provider_isolation.py`:
16. `test_legacy_cache_key_not_consumed_fallback_deprecated` (TD-005 verification)

---

## 16. Full Test Results

| Test Suite | Tests Run | Result | Duration |
|:---|:---:|:---:|:---:|
| `test_adapter_stop_loss_and_attribution.py` | 15 | **15 PASSED** | 0.59s |
| `test_adapter_take_profit.py` | 15 | **15 PASSED** | 0.59s |
| `tests/unit/domain/backtesting/` | 918 | **918 PASSED** | 149.28s |
| `tests/unit/domain/research/` | 299 | **299 PASSED** | 23.29s |
| `tests/unit/domain/strategies/` | 155 | **155 PASSED** | 1.18s |
| `tests/unit/infrastructure/market_data/` | 126 | **126 PASSED** | 3.48s |
| **Total Phase 5.2 Test Footprint** | **1,513** | **1,513 PASSED** | **178.41s** |

---

## 17. Ruff Check

Command:
```bash
poetry run ruff check libraries/domain/backtesting/strategy_adapter.py libraries/infrastructure/market_data/cache.py tests/unit/infrastructure/market_data/test_cache_provider_isolation.py tests/unit/domain/research/test_adapter_take_profit.py
```
Output:
```
All checks passed!
```

---

## 18. Mypy Strict Typing

Command:
```bash
poetry run mypy libraries/domain/backtesting/strategy_adapter.py libraries/infrastructure/market_data/cache.py
```
Output:
```
Success: no issues found in 2 source files
```

---

## 19. Git Diff Check

Command:
```bash
git diff --check libraries/domain/backtesting/strategy_adapter.py libraries/infrastructure/market_data/cache.py tests/unit/infrastructure/market_data/test_cache_provider_isolation.py tests/unit/domain/research/test_adapter_take_profit.py
```
Output:
```
Exit code 0 (clean, no trailing whitespace or CRLF issues)
```

---

## 20. Phase 4 Regression Status

- **Zero Phase 4 Regressions:** All 918 tests in `tests/unit/domain/backtesting/` and all 155 tests in `tests/unit/domain/strategies/` passed without failure.
- **LeakageGuard Integrity:** Re-verified that `LeakageGuard` assertions continue to pass with zero future-candle look-ahead bias across all strategies.

---

## 21. Remaining Pre-Existing Failures

The two known pre-existing billing failures remain identical to the pre-phase baseline:
- `test_subscription_cancellation_at_period_end`
- `test_entitlement_service_integration`
These are unrelated to Phase 5.2 and remain tracked for subsequent billing migrations.

---

## 22. Remaining Technical Debt

From Phase 5.0 audit:
- All core execution realism and cache isolation debt items (TD-001, TD-002, TD-003, TD-004, TD-005, TD-006, TD-007, TD-008, TD-009, TD-010, TD-011, TD-012, TD-013, TD-014, TD-015) are now completely remediated.

---

## 23. Known Limitations & Execution Realism Classification

As required by the Execution Realism audit, repository documentation and docstrings explicitly distinguish:
1. **Intra-bar Stop-Loss Execution:** **YES** (evaluated against bar OHLC extremes: low for BUY, high for SELL).
2. **Intra-bar Take-Profit Execution:** **YES** (evaluated against bar OHLC extremes: high for BUY, low for SELL).
3. **Tick-level Execution / Path Reconstruction:** **NO** (the engine does not reconstruct intra-candle micro-price paths).
4. **OHLC Ambiguity Resolution:** **Deterministic Convention** (when both SL and TP levels fall within the candle range, conservative risk-first standard executes `STOP_LOSS`, rather than claiming historical tick sequence knowledge).

---

## Final Verification Checklist

- [x] Intra-bar Take-Profit Execution implemented (TD-002)
- [x] Legacy Candle Cache Fallback deprecated & removed (TD-005)
- [x] Conservative Risk-First SL/TP Conflict Resolution established & tested
- [x] Strict Decimal financial precision preserved
- [x] Spread, slippage, and commission costs applied to TP fills
- [x] Attribution metadata preserved on TP exits
- [x] Zero-distance, wrong-side, and negative TP validated
- [x] 1,513 unit tests passed across 6 test suites
- [x] Ruff check: All checks passed
- [x] Mypy: Success: no issues found
- [x] Git diff check: Clean (0 warnings/errors)
- [x] $0 live-capital / paper-trading invariant strictly maintained
- [x] No commits, push, stash, or reset performed

**FINAL STATUS: PASS â€” PHASE 5.2 COMPLETE**
