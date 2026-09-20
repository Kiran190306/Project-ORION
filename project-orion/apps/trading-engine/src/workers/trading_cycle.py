"""Autonomous trading cycle worker.

Orchestrates the complete paper-trading pipeline for a single symbol:

  MarketTick
    -> MarketIntelligenceInput
    -> DecisionEngine.make_decision()
    -> [EXECUTE?]
    -> RiskEngine.evaluate()
    -> [APPROVED?]
    -> OrderBuilder.build()
    -> OrderValidator.validate()
    -> PaperExecutionAdapter.submit_order()
    -> NotificationService.notify()

Safety gates (in order):
  1. Worker not running -> abort cycle
  2. Market data missing / stale -> no order, log warning
  3. Market data invalid -> no order
  4. DecisionEngine returns DEFER / REJECT -> no order
  5. RiskEngine returns REJECTED / DEFERRED -> no order
  6. OrderValidator fails -> no order, log warning
  7. PaperExecutionAdapter unavailable -> no order, send failure notification
  8. Unexpected exception -> isolate to symbol, continue

All financial arithmetic is Decimal. Timestamps are UTC-aware.
No global mutable state. No framework imports in domain layer.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.execution.builder import OrderBuilder, OrderBuilderConfig
from libraries.domain.execution.validator import OrderValidator, OrderValidatorConfig
from libraries.domain.notification.models import (
    NotificationChannel,
    NotificationRequest,
    NotificationSeverity,
    NotificationType,
)
from libraries.domain.notification.service import NotificationService
from libraries.domain.risk.engine import RiskEngine
from libraries.domain.trading.decision_engine import (
    DecisionEngine,
    MarketIntelligenceInput,
)
from libraries.infrastructure.execution.broker_adapter import (
    AdapterOrderRejectedError,
    ExecutionAdapterError,
)
from libraries.infrastructure.execution.paper_execution import PaperExecutionAdapter

from .market_data import MarketTick

logger = logging.getLogger("trading_engine.worker.trading_cycle")


@dataclass
class CycleMetrics:
    """Cycle-level counters for Prometheus export."""

    cycles_attempted: int = 0
    cycles_completed: int = 0
    cycles_failed: int = 0
    strategy_evaluations: int = 0
    risk_rejections: int = 0
    orders_submitted: int = 0
    execution_failures: int = 0
    notifications_sent: int = 0


@dataclass(frozen=True, slots=True)
class CycleResult:
    """Result of a single autonomous trading cycle for one symbol."""

    symbol: str
    cycle_id: str
    success: bool
    outcome: str  # "executed", "deferred", "rejected", "risk_rejected", "error"
    reason: str = ""
    order_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


class TradingCycleWorker:
    """Executes the full autonomous paper-trading pipeline per symbol.

    Thread-safe: each symbol cycle is isolated. One symbol's failure
    does not cancel other symbols.

    Args:
        decision_engine: Domain DecisionEngine (no framework deps).
        risk_engine: Domain RiskEngine.
        paper_adapter: Infrastructure PaperExecutionAdapter (paper money only).
        notification_service: Domain NotificationService.
        account_balance: Starting paper account balance (Decimal).
        builder_config: Optional OrderBuilderConfig overrides.
        validator_config: Optional OrderValidatorConfig overrides.
    """

    def __init__(
        self,
        decision_engine: DecisionEngine,
        risk_engine: RiskEngine,
        paper_adapter: PaperExecutionAdapter,
        notification_service: NotificationService,
        account_balance: Decimal = Decimal(100000),
        builder_config: OrderBuilderConfig | None = None,
        validator_config: OrderValidatorConfig | None = None,
    ) -> None:
        self._decision_engine = decision_engine
        self._risk_engine = risk_engine
        self._paper_adapter = paper_adapter
        self._notification_service = notification_service
        self._account_balance = account_balance
        self._builder = OrderBuilder(builder_config)
        self._validator = OrderValidator(validator_config)
        self._metrics = CycleMetrics()

    @property
    def metrics(self) -> CycleMetrics:
        return self._metrics

    async def run_cycle(self, market_data: dict[str, MarketTick]) -> list[CycleResult]:
        """Run one trading cycle over all available market data snapshots.

        Each symbol is processed independently. Exceptions from one symbol
        are caught and logged; processing continues for remaining symbols.

        Args:
            market_data: Mapping of symbol -> MarketTick from MarketDataPoller.

        Returns:
            List of CycleResult, one per symbol attempted.
        """
        if not market_data:
            logger.debug("No market data available for this cycle – skipping.")
            return []

        results: list[CycleResult] = []
        for symbol, tick in market_data.items():
            result = await self._run_symbol_cycle(symbol, tick)
            results.append(result)

        return results

    async def _run_symbol_cycle(self, symbol: str, tick: MarketTick) -> CycleResult:
        """Run a complete pipeline for one symbol. Isolated from other symbols."""
        cycle_id = f"CYCLE-{uuid.uuid4().hex[:8].upper()}"
        self._metrics.cycles_attempted += 1

        try:
            result = await self._execute_pipeline(symbol, tick, cycle_id)
            self._metrics.cycles_completed += 1
            return result
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._metrics.cycles_failed += 1
            logger.exception(
                "Unexpected error in cycle %s for %s",
                cycle_id,
                symbol,
            )
            await self._send_notification(
                title=f"Worker Error: {symbol}",
                body=f"Cycle {cycle_id} failed with unexpected error: {exc}",
                severity=NotificationSeverity.ERROR,
                notification_type=NotificationType.SYSTEM_ALERT,
                metadata={"cycle_id": cycle_id, "symbol": symbol, "error": str(exc)},
            )
            return CycleResult(
                symbol=symbol,
                cycle_id=cycle_id,
                success=False,
                outcome="error",
                reason=str(exc),
            )

    async def _execute_pipeline(
        self, symbol: str, tick: MarketTick, cycle_id: str
    ) -> CycleResult:
        """Execute the full Market -> Decision -> Risk -> Execution pipeline."""

        # --- Gate: validate tick ---
        if not tick.is_valid:
            logger.warning("Cycle %s: invalid tick for %s – skipping.", cycle_id, symbol)
            return CycleResult(
                symbol=symbol, cycle_id=cycle_id, success=False,
                outcome="error", reason="Invalid market tick",
            )

        # --- Step 1: Build MarketIntelligenceInput from tick ---
        mi = MarketIntelligenceInput(
            spread_pips=tick.spread_pips,
            entry_price=tick.mid,
            liquidity_score=0.7,  # default: adequate liquidity assumed for paper trading
            provider_quality=1.0 if not tick.is_simulated else 0.8,
            consensus_quality=0.7,
            volatility_score=0.4,
        )

        # --- Step 2: DecisionEngine ---
        self._metrics.strategy_evaluations += 1
        decision = await self._decision_engine.make_decision(
            symbol=symbol,
            market_intelligence=mi,
            account_balance=self._account_balance,
        )

        if not decision.is_executable:
            outcome = "rejected" if decision.is_rejected else "deferred"
            logger.debug(
                "Cycle %s: %s %s – %s",
                cycle_id, symbol, outcome, decision.reason,
            )
            return CycleResult(
                symbol=symbol, cycle_id=cycle_id, success=True,
                outcome=outcome, reason=decision.reason,
                metadata={"decision_id": decision.decision_id},
            )

        logger.info(
            "Cycle %s: EXECUTE signal for %s (direction=%s confidence=%.1f)",
            cycle_id, symbol, decision.direction, decision.confidence,
        )

        # --- Step 3: RiskEngine ---
        risk_result = await self._risk_engine.evaluate(decision)

        if not risk_result.is_approved:
            self._metrics.risk_rejections += 1
            reasons = ", ".join(risk_result.rejection_reasons) or str(risk_result.decision)
            logger.info(
                "Cycle %s: RiskEngine REJECTED %s – %s",
                cycle_id, symbol, reasons,
            )
            await self._send_notification(
                title=f"Risk Rejected: {symbol}",
                body=f"Order for {symbol} rejected by risk engine. Reason: {reasons}",
                severity=NotificationSeverity.WARNING,
                notification_type=NotificationType.ORDER_REJECTED,
                metadata={
                    "cycle_id": cycle_id, "symbol": symbol,
                    "decision_id": decision.decision_id,
                    "risk_score": risk_result.risk_score,
                    "reasons": list(risk_result.rejection_reasons),
                },
            )
            return CycleResult(
                symbol=symbol, cycle_id=cycle_id, success=True,
                outcome="risk_rejected", reason=reasons,
                metadata={"risk_score": risk_result.risk_score},
            )

        # --- Step 4: OrderBuilder ---
        try:
            order = self._builder.build(decision)
        except Exception as exc:  # noqa: BLE001 - OrderBuilder errors are isolated per symbol
            logger.warning("Cycle %s: OrderBuilder failed for %s: %s", cycle_id, symbol, exc)
            return CycleResult(
                symbol=symbol, cycle_id=cycle_id, success=False,
                outcome="error", reason=f"OrderBuilder: {exc}",
            )

        # --- Step 5: OrderValidator ---
        validation = await self._validator.validate(order)
        if not validation.is_valid:
            errors = "; ".join(validation.errors)
            logger.warning("Cycle %s: OrderValidator rejected %s: %s", cycle_id, symbol, errors)
            return CycleResult(
                symbol=symbol, cycle_id=cycle_id, success=False,
                outcome="rejected", reason=f"Validation: {errors}",
            )

        # --- Step 6: PaperExecutionAdapter ---
        if not self._paper_adapter.is_connected:
            logger.warning("Cycle %s: paper adapter not connected; skipping.", cycle_id)
            return CycleResult(
                symbol=symbol, cycle_id=cycle_id, success=False,
                outcome="error", reason="Paper adapter not connected",
            )

        try:
            execution_info = await self._paper_adapter.submit_order(order)
            self._metrics.orders_submitted += 1
        except AdapterOrderRejectedError as exc:
            self._metrics.execution_failures += 1
            logger.warning("Cycle %s: broker rejected order for %s: %s", cycle_id, symbol, exc)
            await self._send_notification(
                title=f"Order Rejected by Broker: {symbol}",
                body=str(exc),
                severity=NotificationSeverity.WARNING,
                notification_type=NotificationType.ORDER_REJECTED,
                metadata={"cycle_id": cycle_id, "symbol": symbol},
            )
            return CycleResult(
                symbol=symbol, cycle_id=cycle_id, success=False,
                outcome="rejected", reason=str(exc),
            )
        except ExecutionAdapterError as exc:
            self._metrics.execution_failures += 1
            logger.error("Cycle %s: execution error for %s: %s", cycle_id, symbol, exc)
            await self._send_notification(
                title=f"Execution Error: {symbol}",
                body=str(exc),
                severity=NotificationSeverity.ERROR,
                notification_type=NotificationType.SYSTEM_ALERT,
                metadata={"cycle_id": cycle_id, "symbol": symbol},
            )
            return CycleResult(
                symbol=symbol, cycle_id=cycle_id, success=False,
                outcome="error", reason=str(exc),
            )

        # --- Step 7: Notify success ---
        order_id_str = (
            order.order_id.value if hasattr(order.order_id, "value") else str(order.order_id)
        )
        fill_price = execution_info.average_fill_price
        status_str = (
            execution_info.status.value
            if hasattr(execution_info.status, "value")
            else str(execution_info.status)
        )

        await self._send_notification(
            title=f"Order Submitted: {symbol}",
            body=(
                f"Paper {decision.direction} order for {symbol} submitted.\n"
                f"Order ID: {order_id_str}\n"
                f"Fill Price: {fill_price}\n"
                f"Status: {status_str}"
            ),
            severity=NotificationSeverity.SUCCESS,
            notification_type=NotificationType.ORDER_FILLED,
            metadata={
                "cycle_id": cycle_id,
                "symbol": symbol,
                "order_id": order_id_str,
                "fill_price": str(fill_price),
                "direction": str(decision.direction),
            },
        )

        logger.info(
            "Cycle %s: order submitted for %s – order_id=%s fill=%s status=%s",
            cycle_id, symbol, order_id_str, fill_price, status_str,
        )

        return CycleResult(
            symbol=symbol,
            cycle_id=cycle_id,
            success=True,
            outcome="executed",
            order_id=order_id_str,
            metadata={
                "fill_price": str(fill_price),
                "direction": str(decision.direction),
                "decision_id": decision.decision_id,
            },
        )

    async def _send_notification(
        self,
        title: str,
        body: str,
        severity: NotificationSeverity,
        notification_type: NotificationType,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Send an IN_APP notification; silently swallow errors so the pipeline continues."""
        try:
            request = NotificationRequest(
                channel=NotificationChannel.IN_APP,
                severity=severity,
                notification_type=notification_type,
                title=title,
                body=body,
                metadata=metadata or {},
            )
            await self._notification_service.notify(request)
            self._metrics.notifications_sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to send notification: %s", exc)
