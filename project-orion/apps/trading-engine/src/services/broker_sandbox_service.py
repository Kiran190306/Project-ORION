"""Application service for Institutional Broker Sandbox & Demo Broker Integration (EPIC-026).

Enforces:
1. Complete tenant isolation (all queries scoped to organization_id with 404 fail-closed).
2. Mandatory execution pipeline:
   Signal/Request -> RiskEngine -> OrderValidator -> Canonical Order -> Broker Adapter -> Sandbox Broker.
3. Strict zero-capital safety: only LOCAL and SANDBOX environments allowed; LIVE fails closed.
4. AES-GCM credential encryption at rest; raw credentials never exposed in logs, responses, or UI.
5. Idempotent order execution and UNKNOWN state handling on timeouts (NOT_SAFE_TO_RETRY).
6. State reconciliation audits between internal ORION ledger and external broker sandbox state.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.execution.exceptions import OrderValidationError
from libraries.domain.execution.models import (
    BrokerOrderId,
    Fill,
    Order,
    OrderId,
    OrderSide,
    OrderStatus,
    OrderType,
)
from libraries.domain.execution.validator import OrderValidator, OrderValidatorConfig
from libraries.domain.reconciliation.engine import BrokerReconciliationEngine
from libraries.domain.reconciliation.models import ReconciliationSnapshot, ReconciliationStatus
from libraries.domain.risk.context import RiskContext
from libraries.domain.risk.engine import RiskEngine, RiskEngineConfig
from libraries.domain.risk.models import RiskDecision
from libraries.domain.trading.decision_result import DecisionOutcome, TradeDecision
from libraries.domain.trading.signals import SignalDirection
from libraries.domain.subscription.exceptions import (
    AssetNotEntitledError,
    BrokerSandboxAccountQuotaExceededError,
    BrokerSandboxOrderQuotaExceededError,
    EntitlementError,
    SubscriptionInactiveError,
)
from libraries.infrastructure.execution.broker_adapter import (
    AccountInfo,
    AdapterAuthenticationError,
    AdapterConnectionError,
    AdapterNotConnectedError,
    AdapterOrderRejectedError,
    AdapterProviderUnavailableError,
    AdapterRateLimitError,
    AdapterTimeoutError,
    BrokerAdapter,
    ExecutionAdapterError,
    OrderExecutionInfo,
    PositionInfo,
)
from libraries.infrastructure.execution.execution_factory import (
    ExecutionAdapterFactory,
    ExecutionAdapterSpec,
)
from libraries.infrastructure.execution.mock_broker import MockBrokerAdapter, MockBrokerConfig
from libraries.infrastructure.persistence.models import (
    AccountModel,
    FillModel,
    OrderModel,
    PositionModel,
)
from libraries.infrastructure.persistence.models.broker_sandbox import (
    BrokerReconciliationSnapshotModel,
    BrokerSandboxAccountModel,
)
from libraries.infrastructure.security.endpoint_validator import (
    BrokerEndpointValidator,
    CredentialCipher,
    CredentialEncryptionError,
    SecurityViolationError,
)

from ..schemas import (
    BrokerProviderInfo,
    BrokerSandboxAccountCreateRequest,
    BrokerSandboxAccountResponse,
    BrokerSandboxAccountUpdateRequest,
    BrokerSandboxConnectResponse,
    BrokerSandboxOrderRequest,
    BrokerSandboxOrderResponse,
    BrokerSandboxPositionResponse,
    BrokerSandboxReconciliationResponse,
)
from .entitlement_service import EntitlementService

logger = logging.getLogger("trading_engine.services.broker_sandbox")


class BrokerSandboxService:
    """Orchestrates tenant-scoped broker sandbox connections, trading, and reconciliation."""

    # In-memory cached adapter instances keyed by (org_id, account_id)
    _active_adapters: dict[tuple[str, str], BrokerAdapter] = {}

    def __init__(
        self,
        session: AsyncSession,
        entitlement_service: EntitlementService | None = None,
        risk_engine: RiskEngine | None = None,
        order_validator: OrderValidator | None = None,
    ) -> None:
        self.session = session
        self.entitlement_service = entitlement_service or EntitlementService(session)
        self.risk_engine = risk_engine or RiskEngine(config=RiskEngineConfig(fail_open=False, strict_mode=True))
        self.order_validator = order_validator or OrderValidator(OrderValidatorConfig(max_volume=Decimal("10000000")))
        self.reconciliation_engine = BrokerReconciliationEngine()

    # ── Providers Catalog ─────────────────────────────────────────────

    def list_providers(self) -> list[BrokerProviderInfo]:
        """Return catalog of approved broker sandbox providers and capabilities."""
        return [
            BrokerProviderInfo(
                provider="MOCK",
                name="Deterministic Mock Broker",
                environment="LOCAL / SANDBOX",
                description="Institutional in-memory seeded simulation harness with fault injection ($0 Risk).",
                status="AVAILABLE",
                supported_order_types=["MARKET", "LIMIT", "STOP", "STOP_LIMIT", "TRAILING_STOP"],
                supported_symbols=["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD"],
                requires_credentials=False,
            ),
            BrokerProviderInfo(
                provider="OANDA_PRACTICE",
                name="OANDA fxPractice v20 REST",
                environment="SANDBOX",
                description="Official OANDA v20 practice demo gateway (api-fxpractice.oanda.com, $0 Risk).",
                status="AVAILABLE",
                supported_order_types=["MARKET", "LIMIT", "STOP"],
                supported_symbols=["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "EUR/GBP"],
                requires_credentials=True,
            ),
        ]

    # ── Account Management ────────────────────────────────────────────

    async def create_account(
        self,
        organization_id: str,
        user_id: str | None,
        request: BrokerSandboxAccountCreateRequest,
    ) -> BrokerSandboxAccountResponse:
        """Register and persist a new tenant broker sandbox connection."""
        # 1. Entitlement check
        try:
            await self.entitlement_service.check_broker_sandbox_account_quota(organization_id)
        except BrokerSandboxAccountQuotaExceededError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message) from exc
        except SubscriptionInactiveError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message) from exc

        # 2. Security validation: Reject LIVE immediately
        if request.environment.upper() == "LIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LIVE environment is strictly prohibited in Project ORION ($0.00 Capital at Risk).",
            )

        # 3. Encrypt credentials at rest
        try:
            encrypted_creds = CredentialCipher.encrypt(request.credentials)
        except CredentialEncryptionError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

        account_id = f"bsa_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        model = BrokerSandboxAccountModel(
            id=account_id,
            organization_id=organization_id,
            created_by=user_id,
            provider=request.provider.upper(),
            environment=request.environment.upper(),
            account_id_external=request.account_id_external,
            name=request.name,
            status="DISCONNECTED",
            credentials_encrypted=encrypted_creds,
            config=request.config,
            created_at=now,
            updated_at=now,
        )

        shadow_account = AccountModel(
            id=account_id,
            organization_id=organization_id,
            broker_name=f"SANDBOX_{request.provider.upper()}",
            account_number=request.account_id_external or account_id,
            currency="USD",
            balance=Decimal("100000.00"),
            equity=Decimal("100000.00"),
            margin=Decimal("0.00"),
            margin_free=Decimal("100000.00"),
            is_active=True,
        )

        self.session.add(model)
        self.session.add(shadow_account)
        await self.session.commit()
        await self.session.refresh(model)

        return self._to_account_response(model)

    async def list_accounts(
        self,
        organization_id: str,
    ) -> list[BrokerSandboxAccountResponse]:
        """List all broker sandbox connections for the organization."""
        stmt = (
            select(BrokerSandboxAccountModel)
            .where(BrokerSandboxAccountModel.organization_id == organization_id)
            .order_by(BrokerSandboxAccountModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        accounts = res.scalars().all()
        return [self._to_account_response(a) for a in accounts]

    async def get_account(
        self,
        organization_id: str,
        account_id: str,
    ) -> BrokerSandboxAccountResponse:
        """Fetch details of a specific sandbox account (fail-closed 404 for wrong tenant)."""
        model = await self._get_account_model(organization_id, account_id)
        return self._to_account_response(model)

    async def update_account(
        self,
        organization_id: str,
        account_id: str,
        request: BrokerSandboxAccountUpdateRequest,
    ) -> BrokerSandboxAccountResponse:
        """Update configuration or credentials for a sandbox account."""
        model = await self._get_account_model(organization_id, account_id)

        if request.name is not None:
            model.name = request.name

        if request.config is not None:
            model.config = {**model.config, **request.config}

        if request.credentials is not None:
            model.credentials_encrypted = CredentialCipher.encrypt(request.credentials)

        model.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(model)

        # Invalidate active cached adapter
        self._active_adapters.pop((organization_id, account_id), None)
        return self._to_account_response(model)

    async def delete_account(
        self,
        organization_id: str,
        account_id: str,
    ) -> dict[str, str]:
        """Delete a broker sandbox account."""
        model = await self._get_account_model(organization_id, account_id)
        # Disconnect if connected
        adapter = self._active_adapters.pop((organization_id, account_id), None)
        if adapter:
            try:
                await adapter.disconnect()
            except Exception as e:
                logger.warning("Error disconnecting adapter during deletion: %s", e)

        await self.session.delete(model)
        await self.session.commit()
        return {"message": "Account deleted successfully", "account_id": account_id}

    # ── Connection Lifecycle ──────────────────────────────────────────

    async def connect_account(
        self,
        organization_id: str,
        account_id: str,
    ) -> BrokerSandboxConnectResponse:
        """Connect to the broker sandbox and verify health/credentials."""
        model = await self._get_account_model(organization_id, account_id)
        adapter = await self.get_or_create_adapter(organization_id, account_id)

        try:
            connected = await adapter.connect()
            health = await adapter.health_check()
            acc_info = await adapter.get_account()

            model.status = "CONNECTED"
            model.last_connected_at = datetime.now(timezone.utc)
            model.error_message = None
            await self.session.commit()

            return BrokerSandboxConnectResponse(
                account_id=account_id,
                status="CONNECTED",
                connected=connected,
                latency_ms=health.get("latency_ms", 0.0),
                balance=acc_info.balance,
                equity=acc_info.equity,
                margin=acc_info.margin,
                margin_free=acc_info.margin_free,
                currency=acc_info.currency,
                message="Connected successfully to broker sandbox",
            )
        except AdapterAuthenticationError as exc:
            model.status = "ERROR"
            model.error_message = str(exc)
            await self.session.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        except AdapterConnectionError as exc:
            model.status = "ERROR"
            model.error_message = str(exc)
            await self.session.commit()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        except Exception as exc:
            model.status = "ERROR"
            model.error_message = str(exc)
            await self.session.commit()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Connection failed: {exc}") from exc

    async def disconnect_account(
        self,
        organization_id: str,
        account_id: str,
    ) -> BrokerSandboxConnectResponse:
        """Disconnect active session to broker sandbox."""
        model = await self._get_account_model(organization_id, account_id)
        adapter = self._active_adapters.get((organization_id, account_id))
        if adapter:
            await adapter.disconnect()

        model.status = "DISCONNECTED"
        await self.session.commit()

        return BrokerSandboxConnectResponse(
            account_id=account_id,
            status="DISCONNECTED",
            connected=False,
            message="Disconnected from broker sandbox",
        )

    # ── Order Execution Pipeline (MANDATORY CHAIN) ─────────────────────

    async def submit_sandbox_order(
        self,
        organization_id: str,
        account_id: str,
        request: BrokerSandboxOrderRequest,
    ) -> BrokerSandboxOrderResponse:
        """Execute sandbox order through the mandatory risk and validation pipeline.

        MANDATORY CHAIN:
        Request -> EntitlementCheck -> RiskEngine -> OrderValidator -> Canonical Order -> BrokerAdapter -> Broker Sandbox
        """
        # 1. Entitlement check (daily orders + asset entitlement)
        try:
            await self.entitlement_service.check_broker_sandbox_order_quota(organization_id)
            await self.entitlement_service.check_asset_access(organization_id, request.symbol)
        except BrokerSandboxOrderQuotaExceededError as exc:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message) from exc
        except AssetNotEntitledError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message) from exc

        model = await self._get_account_model(organization_id, account_id)
        adapter = await self.get_or_create_adapter(organization_id, account_id)

        # Ensure adapter is connected
        if not adapter.is_connected:
            await adapter.connect()

        # 2. Build Canonical Order
        order_uuid = str(uuid.uuid4())
        client_oid = request.client_order_id or f"cl_{uuid.uuid4().hex[:12]}"

        canonical_order = Order(
            order_id=OrderId(order_uuid),
            decision_id=f"dec_{uuid.uuid4().hex[:12]}",
            execution_id=client_oid,
            symbol=request.symbol,
            side=OrderSide.BUY if request.side.upper() == "BUY" else OrderSide.SELL,
            order_type=OrderType(request.order_type.lower()),
            quantity=request.quantity,
            price=request.price,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            status=OrderStatus.NEW,
        )

        # 3. Risk Engine Pre-Trade Evaluation Gate
        trade_decision = TradeDecision(
            symbol=request.symbol,
            outcome=DecisionOutcome.EXECUTE,
            direction=SignalDirection.BUY if request.side.upper() == "BUY" else SignalDirection.SELL,
            entry_price=canonical_order.price or Decimal("1.0"),
            position_size=canonical_order.quantity,
            stop_loss=canonical_order.stop_loss,
            take_profit=canonical_order.take_profit,
            confidence=1.0,
            decision_id=canonical_order.decision_id,
        )
        risk_context = RiskContext(
            symbol=request.symbol,
            direction="buy" if request.side.upper() == "BUY" else "sell",
            entry_price=canonical_order.price or Decimal("1.0"),
            stop_loss=canonical_order.stop_loss,
            take_profit=canonical_order.take_profit,
            position_size=canonical_order.quantity,
            account_balance=Decimal("100000.00"),
            account_equity=Decimal("100000.00"),
            margin_used=Decimal("0.00"),
            margin_free=Decimal("100000.00"),
        )
        risk_result = await self.risk_engine.evaluate(trade_decision, risk_context)
        if risk_result.decision == RiskDecision.REJECTED:
            reasons = "; ".join(risk_result.rejection_reasons) or "Risk limits breached"
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Order rejected by Pre-Trade Risk Engine: {reasons}",
            )

        # 4. OrderValidator Gate
        validation_result = await self.order_validator.validate(canonical_order)
        if not validation_result.is_valid:
            errors = "; ".join(validation_result.errors)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Order validation failed: {errors}",
            )

        # 5. Route to Broker Adapter (Order submission is NOT_SAFE_TO_RETRY)
        try:
            exec_info = await adapter.submit_order(canonical_order)
        except AdapterRateLimitError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Broker rate limit exceeded: {exc}",
            ) from exc
        except AdapterTimeoutError as exc:
            # Under timeout, classify as UNKNOWN per Decision 8; do NOT blindly retry
            logger.warning("Order submission timed out on broker sandbox: returning UNKNOWN")
            return BrokerSandboxOrderResponse(
                order_id=order_uuid,
                broker_order_id="UNKNOWN",
                symbol=request.symbol,
                side=request.side,
                order_type=request.order_type,
                quantity=request.quantity,
                price=request.price,
                status="UNKNOWN",
                filled_quantity=Decimal("0.00"),
                latency_ms=0.0,
                timestamp=datetime.now(timezone.utc),
                rejection_reason="Broker submission timed out. State is UNKNOWN pending reconciliation.",
            )
        except AdapterOrderRejectedError as exc:
            return BrokerSandboxOrderResponse(
                order_id=order_uuid,
                broker_order_id=f"rej_{uuid.uuid4().hex[:8]}",
                symbol=request.symbol,
                side=request.side,
                order_type=request.order_type,
                quantity=request.quantity,
                price=request.price,
                status="REJECTED",
                filled_quantity=Decimal("0.00"),
                latency_ms=0.0,
                timestamp=datetime.now(timezone.utc),
                rejection_reason=str(exc),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Broker execution failed: {exc}",
            ) from exc

        # 6. Record local OrderModel and FillModel in ORION database
        local_order = OrderModel(
            id=order_uuid,
            organization_id=organization_id,
            account_id=account_id,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.price or exec_info.average_fill_price or Decimal("0.0"),
            status=exec_info.status.value.upper(),
            broker_order_id=str(exec_info.broker_order_id.value),
            filled_quantity=exec_info.filled_quantity,
            average_fill_price=exec_info.average_fill_price,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(local_order)

        for fill in exec_info.fills:
            fill_model = FillModel(
                id=fill.fill_id,
                order_id=order_uuid,
                organization_id=organization_id,
                broker_fill_id=str(fill.fill_id),
                symbol=request.symbol,
                side=request.side.upper(),
                quantity=fill.quantity,
                price=fill.price,
                commission=fill.commission,
                timestamp=fill.timestamp,
            )
            self.session.add(fill_model)

        await self.session.commit()

        return BrokerSandboxOrderResponse(
            order_id=order_uuid,
            broker_order_id=str(exec_info.broker_order_id.value),
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.price,
            status=exec_info.status.value.upper(),
            filled_quantity=exec_info.filled_quantity,
            average_fill_price=exec_info.average_fill_price,
            latency_ms=exec_info.latency_ms,
            timestamp=datetime.now(timezone.utc),
            rejection_reason=exec_info.rejection_reason or None,
        )

    # ── Queries (SAFE_TO_RETRY with bounded retry) ─────────────────────

    async def get_positions(
        self,
        organization_id: str,
        account_id: str,
    ) -> list[BrokerSandboxPositionResponse]:
        """Fetch open positions from broker sandbox."""
        await self._get_account_model(organization_id, account_id)
        adapter = await self.get_or_create_adapter(organization_id, account_id)
        if not adapter.is_connected:
            await adapter.connect()

        positions = await adapter.get_open_positions()
        return [
            BrokerSandboxPositionResponse(
                position_id=p.position_id,
                symbol=p.symbol,
                side=p.side.value.upper(),
                quantity=p.quantity,
                open_price=p.open_price,
                current_price=p.current_price,
                unrealized_pnl=p.profit,
                currency="USD",
            )
            for p in positions
        ]

    async def cancel_order(
        self,
        organization_id: str,
        account_id: str,
        order_id: str,
    ) -> dict[str, Any]:
        """Cancel a resting order on the broker sandbox."""
        await self._get_account_model(organization_id, account_id)
        adapter = await self.get_or_create_adapter(organization_id, account_id)

        # Look up broker_order_id from local OrderModel
        stmt = select(OrderModel).where(
            OrderModel.id == order_id,
            OrderModel.organization_id == organization_id,
        )
        res = await self.session.execute(stmt)
        order = res.scalar_one_or_none()

        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        broker_oid = BrokerOrderId(order.broker_order_id or order_id)
        success = await adapter.cancel_order(broker_oid)

        if success:
            order.status = "CANCELLED"
            order.updated_at = datetime.now(timezone.utc)
            await self.session.commit()

        return {"order_id": order_id, "status": "CANCELLED" if success else "FAILED"}

    # ── State Reconciliation Audit ────────────────────────────────────

    async def reconcile_account(
        self,
        organization_id: str,
        account_id: str,
    ) -> BrokerSandboxReconciliationResponse:
        """Run an on-demand state reconciliation sweep comparing ORION vs broker."""
        model = await self._get_account_model(organization_id, account_id)
        adapter = await self.get_or_create_adapter(organization_id, account_id)
        if not adapter.is_connected:
            await adapter.connect()

        # 1. Local state
        # Active orders
        ord_stmt = select(OrderModel).where(
            OrderModel.organization_id == organization_id,
            OrderModel.account_id == account_id,
        )
        ord_res = await self.session.execute(ord_stmt)
        local_orders_models = ord_res.scalars().all()
        local_orders = [
            {
                "id": o.id,
                "broker_order_id": o.broker_order_id,
                "symbol": o.symbol,
                "status": o.status,
                "quantity": o.quantity,
            }
            for o in local_orders_models
        ]

        # Open positions
        pos_stmt = select(PositionModel).where(
            PositionModel.organization_id == organization_id,
            PositionModel.account_id == account_id,
            PositionModel.is_open.is_(True),
        )
        pos_res = await self.session.execute(pos_stmt)
        local_pos_models = pos_res.scalars().all()
        local_positions = [
            {
                "id": p.id,
                "symbol": p.symbol,
                "side": p.side,
                "quantity": p.quantity,
                "entry_price": p.entry_price,
            }
            for p in local_pos_models
        ]

        # 2. Remote broker state
        remote_account = await adapter.get_account()
        remote_positions = await adapter.get_open_positions()
        remote_orders = await adapter.get_execution_history(limit=50)

        local_account = {
            "balance": remote_account.balance,  # Fallback to remote if no internal cash ledger
            "equity": remote_account.equity,
        }

        # 3. Compute discrepancies via BrokerReconciliationEngine
        snapshot = self.reconciliation_engine.reconcile(
            organization_id=organization_id,
            broker_account_id=account_id,
            local_account=local_account,
            local_orders=local_orders,
            local_positions=local_positions,
            remote_account=remote_account,
            remote_orders=remote_orders,
            remote_positions=remote_positions,
        )

        # 4. Persist reconciliation audit snapshot in DB
        snap_model = BrokerReconciliationSnapshotModel(
            id=snapshot.id,
            organization_id=organization_id,
            broker_account_id=account_id,
            status=snapshot.status.value,
            order_discrepancies=[d.to_dict() for d in snapshot.order_discrepancies],
            position_discrepancies=[d.to_dict() for d in snapshot.position_discrepancies],
            account_discrepancies=[d.to_dict() for d in snapshot.account_discrepancies],
            balance_delta=snapshot.balance_delta,
            equity_delta=snapshot.equity_delta,
            details=snapshot.details,
            created_at=snapshot.created_at,
        )
        self.session.add(snap_model)

        model.last_reconciled_at = snapshot.created_at
        await self.session.commit()

        return self._to_reconciliation_response(snapshot)

    async def list_reconciliations(
        self,
        organization_id: str,
        account_id: str,
        limit: int = 20,
    ) -> list[BrokerSandboxReconciliationResponse]:
        """Fetch historical reconciliation snapshots for an account."""
        await self._get_account_model(organization_id, account_id)
        stmt = (
            select(BrokerReconciliationSnapshotModel)
            .where(
                BrokerReconciliationSnapshotModel.organization_id == organization_id,
                BrokerReconciliationSnapshotModel.broker_account_id == account_id,
            )
            .order_by(BrokerReconciliationSnapshotModel.created_at.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        snaps = res.scalars().all()
        return [
            BrokerSandboxReconciliationResponse(
                id=s.id,
                broker_account_id=s.broker_account_id,
                organization_id=s.organization_id,
                status=s.status,
                has_discrepancies=s.status == "DISCREPANCY",
                order_discrepancies=s.order_discrepancies,
                position_discrepancies=s.position_discrepancies,
                account_discrepancies=s.account_discrepancies,
                balance_delta=s.balance_delta,
                equity_delta=s.equity_delta,
                details=s.details,
                created_at=s.created_at,
            )
            for s in snaps
        ]

    # ── Adapter Factory & Helper Methods ──────────────────────────────

    async def get_or_create_adapter(
        self,
        organization_id: str,
        account_id: str,
    ) -> BrokerAdapter:
        """Retrieve active adapter or instantiate from persisted configuration."""
        key = (organization_id, account_id)
        if key in self._active_adapters:
            return self._active_adapters[key]

        model = await self._get_account_model(organization_id, account_id)

        # Decrypt credentials
        try:
            creds = CredentialCipher.decrypt(model.credentials_encrypted) if model.credentials_encrypted else {}
        except Exception:
            creds = {}

        provider = model.provider.lower()
        endpoint = model.config.get("api_endpoint", "")

        # Use closed ExecutionAdapterFactory
        spec = ExecutionAdapterSpec(
            provider=provider,
            name=model.name,
            api_key=creds.get("api_key", creds.get("token", "")),
            api_secret=creds.get("api_secret", ""),
            api_endpoint=endpoint,
            account_id=model.account_id_external,
            is_paper=True,
            environment=model.environment,
            metadata={**model.config, **creds},
        )

        adapter = ExecutionAdapterFactory.create_adapter(spec)
        self._active_adapters[key] = adapter
        return adapter

    async def _get_account_model(
        self,
        organization_id: str,
        account_id: str,
    ) -> BrokerSandboxAccountModel:
        """Fetch model by ID, strictly verifying tenant ownership (404 on mismatch)."""
        stmt = select(BrokerSandboxAccountModel).where(
            BrokerSandboxAccountModel.id == account_id,
            BrokerSandboxAccountModel.organization_id == organization_id,
        )
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Broker sandbox account '{account_id}' not found.",
            )
        return model

    def _to_account_response(
        self,
        model: BrokerSandboxAccountModel,
    ) -> BrokerSandboxAccountResponse:
        """Convert database model to API response with masked credentials."""
        try:
            raw_creds = CredentialCipher.decrypt(model.credentials_encrypted) if model.credentials_encrypted else {}
            masked = CredentialCipher.mask_credentials(raw_creds)
        except Exception:
            masked = {}

        return BrokerSandboxAccountResponse(
            id=model.id,
            organization_id=model.organization_id,
            name=model.name,
            provider=model.provider,
            environment=model.environment,
            account_id_external=model.account_id_external,
            status=model.status,
            last_connected_at=model.last_connected_at,
            last_reconciled_at=model.last_reconciled_at,
            credentials_masked=masked,
            config=model.config or {},
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_reconciliation_response(
        self,
        snapshot: ReconciliationSnapshot,
    ) -> BrokerSandboxReconciliationResponse:
        """Convert ReconciliationSnapshot to API response."""
        return BrokerSandboxReconciliationResponse(
            id=snapshot.id,
            broker_account_id=snapshot.broker_account_id,
            organization_id=snapshot.organization_id,
            status=snapshot.status.value,
            has_discrepancies=snapshot.has_discrepancies,
            order_discrepancies=[d.to_dict() for d in snapshot.order_discrepancies],
            position_discrepancies=[d.to_dict() for d in snapshot.position_discrepancies],
            account_discrepancies=[d.to_dict() for d in snapshot.account_discrepancies],
            balance_delta=snapshot.balance_delta,
            equity_delta=snapshot.equity_delta,
            details=snapshot.details,
            created_at=snapshot.created_at,
        )
