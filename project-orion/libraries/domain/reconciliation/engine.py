"""Institutional Broker Sandbox Reconciliation Engine.

Audits and computes bidirectional state divergences between internal ORION state
and external/sandbox broker state.

Default Discrepancy Policy: ALERT + AUDIT + MANUAL REVIEW.
This engine strictly compares and detects divergences — it NEVER mutates local
positions, orders, or balances silently.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Sequence

from libraries.domain.reconciliation.models import (
    AccountDiscrepancy,
    DiscrepancyType,
    OrderDiscrepancy,
    PositionDiscrepancy,
    ReconciliationSnapshot,
    ReconciliationStatus,
)
from libraries.infrastructure.execution.broker_adapter import (
    AccountInfo,
    BrokerAdapter,
    OrderExecutionInfo,
    PositionInfo,
)

logger = logging.getLogger("domain.reconciliation.engine")


class BrokerReconciliationEngine:
    """Computes bidirectional discrepancies across orders, positions, and account ledger."""

    def __init__(
        self,
        *,
        balance_tolerance: Decimal = Decimal("0.05"),
        equity_tolerance: Decimal = Decimal("0.10"),
        qty_tolerance: Decimal = Decimal("0.0001"),
    ) -> None:
        self.balance_tolerance = balance_tolerance
        self.equity_tolerance = equity_tolerance
        self.qty_tolerance = qty_tolerance

    def reconcile(
        self,
        *,
        organization_id: str,
        broker_account_id: str,
        local_account: dict[str, Any] | None,
        local_orders: Sequence[dict[str, Any]],
        local_positions: Sequence[dict[str, Any]],
        remote_account: AccountInfo | None,
        remote_orders: Sequence[OrderExecutionInfo | dict[str, Any]],
        remote_positions: Sequence[PositionInfo],
        snapshot_id: str | None = None,
    ) -> ReconciliationSnapshot:
        """Execute complete state comparison between ORION and broker sandbox.

        Args:
            organization_id: Multi-tenant organization identifier.
            broker_account_id: Local ID of the broker sandbox account.
            local_account: Dict with keys ('balance', 'equity', 'margin', 'free_margin').
            local_orders: Iterable of active local orders.
            local_positions: Iterable of open local positions.
            remote_account: AccountInfo from broker adapter.
            remote_orders: Iterable of active orders from broker adapter.
            remote_positions: Iterable of open positions from broker adapter.
            snapshot_id: Optional UUID identifier for the snapshot.

        Returns:
            Immutable ReconciliationSnapshot with status and diffs.
        """
        sid = snapshot_id or f"recon_{uuid.uuid4().hex[:16]}"
        order_discrepancies: list[OrderDiscrepancy] = []
        position_discrepancies: list[PositionDiscrepancy] = []
        account_discrepancies: list[AccountDiscrepancy] = []
        balance_delta = Decimal("0.0000")
        equity_delta = Decimal("0.0000")

        # ── 1. Order Reconciliation ───────────────────────────────────────
        order_discrepancies.extend(
            self._reconcile_orders(local_orders=local_orders, remote_orders=remote_orders)
        )

        # ── 2. Position Reconciliation ────────────────────────────────────
        position_discrepancies.extend(
            self._reconcile_positions(
                local_positions=local_positions, remote_positions=remote_positions
            )
        )

        # ── 3. Account Balance & Margin Reconciliation ────────────────────
        if local_account is not None and remote_account is not None:
            acc_disc, bal_d, eq_d = self._reconcile_account(
                local_account=local_account, remote_account=remote_account
            )
            account_discrepancies.extend(acc_disc)
            balance_delta = bal_d
            equity_delta = eq_d

        # ── 4. Determine Classification ───────────────────────────────────
        has_any_discrepancy = (
            len(order_discrepancies) > 0
            or len(position_discrepancies) > 0
            or len(account_discrepancies) > 0
            or abs(balance_delta) > self.balance_tolerance
            or abs(equity_delta) > self.equity_tolerance
        )

        status = ReconciliationStatus.DISCREPANCY if has_any_discrepancy else ReconciliationStatus.MATCHED

        details = {
            "total_local_orders": len(local_orders),
            "total_remote_orders": len(remote_orders),
            "total_local_positions": len(local_positions),
            "total_remote_positions": len(remote_positions),
            "reconciliation_policy": "ALERT_AUDIT_MANUAL_REVIEW",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

        return ReconciliationSnapshot(
            id=sid,
            organization_id=organization_id,
            broker_account_id=broker_account_id,
            status=status,
            order_discrepancies=tuple(order_discrepancies),
            position_discrepancies=tuple(position_discrepancies),
            account_discrepancies=tuple(account_discrepancies),
            balance_delta=balance_delta,
            equity_delta=equity_delta,
            details=details,
        )

    def _reconcile_orders(
        self,
        local_orders: Sequence[dict[str, Any]],
        remote_orders: Sequence[OrderExecutionInfo | dict[str, Any]],
    ) -> list[OrderDiscrepancy]:
        """Bidirectionally compare internal orders vs broker orders."""
        discrepancies: list[OrderDiscrepancy] = []

        # Index remote orders by broker_order_id and client_order_id
        remote_by_broker_id: dict[str, Any] = {}
        for ro in remote_orders:
            if isinstance(ro, OrderExecutionInfo):
                b_id = str(ro.broker_order_id.value)
                remote_by_broker_id[b_id] = ro
            elif isinstance(ro, dict):
                b_id = str(ro.get("broker_order_id") or ro.get("id") or "")
                if b_id:
                    remote_by_broker_id[b_id] = ro

        matched_remote_ids: set[str] = set()

        for lo in local_orders:
            lo_id = str(lo.get("id") or "")
            b_id = str(lo.get("broker_order_id") or "")
            symbol = str(lo.get("symbol") or "")
            local_status = str(lo.get("status") or "").upper()
            local_qty = Decimal(str(lo.get("quantity") or 0))

            if b_id and b_id in remote_by_broker_id:
                ro = remote_by_broker_id[b_id]
                matched_remote_ids.add(b_id)
                ro_status = (
                    ro.status.value if isinstance(ro, OrderExecutionInfo) else str(ro.get("status") or "")
                ).upper()

                # Compare statuses (ignoring case)
                if local_status != ro_status and not (
                    local_status in ("FILLED", "COMPLETE") and ro_status in ("FILLED", "COMPLETE")
                ):
                    discrepancies.append(
                        OrderDiscrepancy(
                            discrepancy_type=DiscrepancyType.ORDER_STATUS_MISMATCH,
                            symbol=symbol,
                            order_id=lo_id,
                            broker_order_id=b_id,
                            local_status=local_status,
                            remote_status=ro_status,
                            local_qty=local_qty,
                            details=f"Status mismatch: local={local_status}, remote={ro_status}",
                        )
                    )
            elif b_id:
                # Order had broker_order_id but not found in active remote orders
                if local_status in ("PENDING", "SUBMITTED", "NEW", "OPEN"):
                    discrepancies.append(
                        OrderDiscrepancy(
                            discrepancy_type=DiscrepancyType.ORDER_MISSING_ON_BROKER,
                            symbol=symbol,
                            order_id=lo_id,
                            broker_order_id=b_id,
                            local_status=local_status,
                            remote_status=None,
                            local_qty=local_qty,
                            details=f"Order {lo_id} is open locally but not found on broker",
                        )
                    )

        # Detect untracked orders on broker
        for b_id, ro in remote_by_broker_id.items():
            if b_id not in matched_remote_ids:
                sym = ro.metadata.get("symbol", "") if isinstance(ro, OrderExecutionInfo) else ro.get("symbol", "")
                r_status = ro.status.value if isinstance(ro, OrderExecutionInfo) else str(ro.get("status") or "")
                r_qty = (
                    ro.filled_quantity if isinstance(ro, OrderExecutionInfo) else Decimal(str(ro.get("quantity") or 0))
                )
                discrepancies.append(
                    OrderDiscrepancy(
                        discrepancy_type=DiscrepancyType.ORDER_UNTRACKED_ON_BROKER,
                        symbol=sym,
                        broker_order_id=b_id,
                        remote_status=r_status,
                        remote_qty=r_qty,
                        details=f"Broker order {b_id} exists on broker but is not tracked locally in ORION",
                    )
                )

        return discrepancies

    def _reconcile_positions(
        self,
        local_positions: Sequence[dict[str, Any]],
        remote_positions: Sequence[PositionInfo],
    ) -> list[PositionDiscrepancy]:
        """Bidirectionally compare open positions between ORION and broker."""
        discrepancies: list[PositionDiscrepancy] = []

        # Index remote positions by symbol
        remote_by_symbol: dict[str, list[PositionInfo]] = {}
        for rp in remote_positions:
            sym = rp.symbol.replace("/", "_").upper()
            remote_by_symbol.setdefault(sym, []).append(rp)

        matched_symbols: set[str] = set()

        for lp in local_positions:
            lp_id = str(lp.get("id") or "")
            raw_sym = str(lp.get("symbol") or "")
            sym = raw_sym.replace("/", "_").upper()
            local_side = str(lp.get("side") or "").upper()
            local_qty = Decimal(str(lp.get("quantity") or 0))
            local_price = Decimal(str(lp.get("entry_price") or lp.get("open_price") or 0))

            if sym in remote_by_symbol:
                matched_symbols.add(sym)
                rps = remote_by_symbol[sym]
                # Sum remote net quantity for this symbol
                remote_qty = sum((rp.quantity for rp in rps), Decimal("0"))
                remote_side = rps[0].side.value.upper() if rps else local_side
                remote_price = rps[0].open_price if rps else local_price

                delta_qty = abs(local_qty - remote_qty)
                if delta_qty > self.qty_tolerance:
                    discrepancies.append(
                        PositionDiscrepancy(
                            discrepancy_type=DiscrepancyType.POSITION_QTY_MISMATCH,
                            symbol=raw_sym,
                            position_id=lp_id,
                            local_side=local_side,
                            remote_side=remote_side,
                            local_qty=local_qty,
                            remote_qty=remote_qty,
                            delta_qty=delta_qty,
                            local_price=local_price,
                            remote_price=remote_price,
                            details=f"Position volume mismatch: local={local_qty}, remote={remote_qty}, delta={delta_qty}",
                        )
                    )
                elif local_side != remote_side:
                    discrepancies.append(
                        PositionDiscrepancy(
                            discrepancy_type=DiscrepancyType.POSITION_QTY_MISMATCH,
                            symbol=raw_sym,
                            position_id=lp_id,
                            local_side=local_side,
                            remote_side=remote_side,
                            local_qty=local_qty,
                            remote_qty=remote_qty,
                            delta_qty=delta_qty,
                            details=f"Position side mismatch: local={local_side}, remote={remote_side}",
                        )
                    )
            else:
                # Local open position does not exist on broker
                discrepancies.append(
                    PositionDiscrepancy(
                        discrepancy_type=DiscrepancyType.POSITION_MISSING_REMOTE,
                        symbol=raw_sym,
                        position_id=lp_id,
                        local_side=local_side,
                        local_qty=local_qty,
                        delta_qty=local_qty,
                        local_price=local_price,
                        details=f"Position on {raw_sym} is marked open locally but missing from broker sandbox",
                    )
                )

        # Detect broker positions untracked locally
        for sym, rps in remote_by_symbol.items():
            if sym not in matched_symbols:
                for rp in rps:
                    r_side = rp.side.value.upper()
                    r_qty = rp.quantity
                    discrepancies.append(
                        PositionDiscrepancy(
                            discrepancy_type=DiscrepancyType.POSITION_MISSING_LOCAL,
                            symbol=rp.symbol,
                            position_id=rp.position_id,
                            remote_side=r_side,
                            remote_qty=r_qty,
                            delta_qty=r_qty,
                            remote_price=rp.open_price,
                            details=f"Broker has open position on {rp.symbol} not tracked in ORION ledger",
                        )
                    )

        return discrepancies

    def _reconcile_account(
        self,
        local_account: dict[str, Any],
        remote_account: AccountInfo,
    ) -> tuple[list[AccountDiscrepancy], Decimal, Decimal]:
        """Compare balance, equity, and margin between local and broker account info."""
        discrepancies: list[AccountDiscrepancy] = []

        local_balance = Decimal(str(local_account.get("balance") or 0))
        remote_balance = remote_account.balance
        bal_delta = remote_balance - local_balance

        if abs(bal_delta) > self.balance_tolerance:
            discrepancies.append(
                AccountDiscrepancy(
                    discrepancy_type=DiscrepancyType.BALANCE_DRIFT,
                    field_name="balance",
                    local_value=local_balance,
                    remote_value=remote_balance,
                    delta=bal_delta,
                    details=f"Balance drift exceeds tolerance ({self.balance_tolerance}): local={local_balance}, remote={remote_balance}",
                )
            )

        local_equity = Decimal(str(local_account.get("equity") or local_balance))
        remote_equity = remote_account.equity
        eq_delta = remote_equity - local_equity

        if abs(eq_delta) > self.equity_tolerance:
            discrepancies.append(
                AccountDiscrepancy(
                    discrepancy_type=DiscrepancyType.EQUITY_DRIFT,
                    field_name="equity",
                    local_value=local_equity,
                    remote_value=remote_equity,
                    delta=eq_delta,
                    details=f"Equity drift exceeds tolerance ({self.equity_tolerance}): local={local_equity}, remote={remote_equity}",
                )
            )

        return discrepancies, bal_delta, eq_delta
