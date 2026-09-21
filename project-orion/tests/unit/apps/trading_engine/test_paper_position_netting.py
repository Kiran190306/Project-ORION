"""Unit tests for position netting and margin accounting in OrderService."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from apps.trading_engine.src.schemas import (
    CreateOrderRequest,
    OrderSideEnum,
    OrderTypeEnum,
)
from apps.trading_engine.src.services.order_service import OrderService
from fastapi import HTTPException

from libraries.domain.execution.models import (
    BrokerOrderId,
    Fill,
    OrderId,
    OrderSide,
    OrderStatus,
)
from libraries.infrastructure.execution.broker_adapter import OrderExecutionInfo
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.persistence.models import (
    AccountModel,
    PositionModel,
)


@pytest.fixture
def mock_account() -> AccountModel:
    account = MagicMock(spec=AccountModel)
    account.id = "acc_netting_001"
    account.organization_id = "org_netting_001"
    account.balance = Decimal("10000.00")
    account.equity = Decimal("10000.00")
    account.margin = Decimal("0.00")
    account.margin_free = Decimal("10000.00")
    account.margin_level = 0.0
    account.leverage = 100
    account.currency = "USD"
    return account


@pytest.fixture
def mock_entitlement_service() -> MagicMock:
    svc = MagicMock()
    svc.check_asset_access = AsyncMock()
    svc.check_daily_order_quota = AsyncMock()
    return svc


@pytest.fixture
def paper_adapter() -> PaperExecutionAdapter:
    cfg = PaperExecutionConfig(
        broker_name="paper",
        is_paper=True,
        deterministic=True,
        latency_ms_mean=0.0,
        latency_ms_std=0.0,
    )
    return PaperExecutionAdapter(config=cfg)


@pytest.mark.asyncio
async def test_pre_trade_margin_check_rejection(
    mock_account: AccountModel, paper_adapter: PaperExecutionAdapter, mock_entitlement_service: MagicMock
) -> None:
    """Pre-trade check must reject order when required margin exceeds free margin."""
    mock_account.margin_free = Decimal("50.00")  # Only $50 free margin
    session = AsyncMock()

    service = OrderService(adapter=paper_adapter, session=session, account=mock_account, entitlement_service=mock_entitlement_service)

    # 1 lot (100,000) at 1.20000 with 1:100 leverage requires $1,200 margin > $50
    req = CreateOrderRequest(
        symbol="EUR/USD",
        side=OrderSideEnum.BUY,
        order_type=OrderTypeEnum.MARKET,
        quantity=Decimal("100000"),
        price=Decimal("1.20000"),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.create_order(req)
    assert exc_info.value.status_code == 400
    assert "insufficient free margin" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_position_creation_and_margin(
    mock_account: AccountModel, paper_adapter: PaperExecutionAdapter, mock_entitlement_service: MagicMock
) -> None:
    """When no position exists, fill creates a new PositionModel and updates margin."""
    await paper_adapter.connect()
    await paper_adapter.set_current_price("EURUSD", Decimal("1.20000"))

    session = AsyncMock()
    # Mock query returning no open position
    exec_res = MagicMock()
    exec_res.scalar_one_or_none.return_value = None
    session.execute.return_value = exec_res

    service = OrderService(adapter=paper_adapter, session=session, account=mock_account, entitlement_service=mock_entitlement_service)

    req = CreateOrderRequest(
        symbol="EUR/USD",
        side=OrderSideEnum.BUY,
        order_type=OrderTypeEnum.MARKET,
        quantity=Decimal("10000"),
        price=Decimal("1.20000"),
    )

    resp = await service.create_order(req)
    assert resp.status == "FILLED"
    assert mock_account.margin > Decimal("0")
    assert mock_account.margin_free < Decimal("10000.00")
    assert session.add.call_count >= 3  # order, fill, execution_report, position


@pytest.mark.asyncio
async def test_position_accumulation_same_direction(
    mock_account: AccountModel, paper_adapter: PaperExecutionAdapter, mock_entitlement_service: MagicMock
) -> None:
    """When open position exists in same direction, accumulates qty with weighted avg entry."""
    await paper_adapter.connect()
    await paper_adapter.set_current_price("EURUSD", Decimal("1.22000"))

    existing_pos = PositionModel(
        id="pos_existing_1",
        account_id=mock_account.id,
        symbol="EUR/USD",
        side="BUY",
        quantity=Decimal("10000"),
        open_price=Decimal("1.20000"),
        current_price=Decimal("1.20000"),
        commission=Decimal("0.70"),
        swap=Decimal("0"),
        is_open=True,
    )

    session = AsyncMock()
    exec_res = MagicMock()
    exec_res.scalar_one_or_none.return_value = existing_pos
    session.execute.return_value = exec_res

    service = OrderService(adapter=paper_adapter, session=session, account=mock_account, entitlement_service=mock_entitlement_service)

    req = CreateOrderRequest(
        symbol="EUR/USD",
        side=OrderSideEnum.BUY,
        order_type=OrderTypeEnum.MARKET,
        quantity=Decimal("10000"),
        price=Decimal("1.22000"),
    )

    await service.create_order(req)
    # Quantity doubled
    assert existing_pos.quantity == Decimal("20000")
    # Weighted average entry price: (1.20*10k + 1.22*10k) / 20k = 1.21000
    assert Decimal("1.209") <= existing_pos.open_price <= Decimal("1.211")


@pytest.mark.asyncio
async def test_position_reduction_and_realized_pnl(
    mock_account: AccountModel, paper_adapter: PaperExecutionAdapter, mock_entitlement_service: MagicMock
) -> None:
    """When order is in opposite direction with smaller qty, reduces position and realizes PnL."""
    await paper_adapter.connect()
    await paper_adapter.set_current_price("EURUSD", Decimal("1.21000"))

    existing_pos = PositionModel(
        id="pos_existing_2",
        account_id=mock_account.id,
        symbol="EUR/USD",
        side="BUY",
        quantity=Decimal("20000"),
        open_price=Decimal("1.20000"),
        current_price=Decimal("1.20000"),
        realized_pnl=Decimal("0"),
        commission=Decimal("1.40"),
        swap=Decimal("0"),
        is_open=True,
    )

    session = AsyncMock()
    exec_res = MagicMock()
    exec_res.scalar_one_or_none.return_value = existing_pos
    session.execute.return_value = exec_res

    initial_balance = mock_account.balance

    service = OrderService(adapter=paper_adapter, session=session, account=mock_account, entitlement_service=mock_entitlement_service)

    # Sell 10,000 at 1.21000 (profit = (1.21 - 1.20)*10,000 = $100)
    req = CreateOrderRequest(
        symbol="EUR/USD",
        side=OrderSideEnum.SELL,
        order_type=OrderTypeEnum.MARKET,
        quantity=Decimal("10000"),
        price=Decimal("1.21000"),
    )

    await service.create_order(req)
    assert existing_pos.quantity == Decimal("10000")
    assert existing_pos.is_open is True
    assert existing_pos.realized_pnl > Decimal("0")
    assert mock_account.balance > initial_balance


@pytest.mark.asyncio
async def test_position_full_closure(
    mock_account: AccountModel, paper_adapter: PaperExecutionAdapter, mock_entitlement_service: MagicMock
) -> None:
    """When opposite order exactly equals open position, closes position and releases margin."""
    await paper_adapter.connect()
    await paper_adapter.set_current_price("EURUSD", Decimal("1.21000"))

    existing_pos = PositionModel(
        id="pos_existing_3",
        account_id=mock_account.id,
        symbol="EUR/USD",
        side="BUY",
        quantity=Decimal("10000"),
        open_price=Decimal("1.20000"),
        current_price=Decimal("1.20000"),
        realized_pnl=Decimal("0"),
        commission=Decimal("0.70"),
        swap=Decimal("0"),
        is_open=True,
    )

    mock_account.margin = Decimal("120.00")
    mock_account.margin_free = Decimal("9880.00")

    session = AsyncMock()
    exec_res = MagicMock()
    exec_res.scalar_one_or_none.return_value = existing_pos
    session.execute.return_value = exec_res

    service = OrderService(adapter=paper_adapter, session=session, account=mock_account, entitlement_service=mock_entitlement_service)

    # Sell full 10,000
    req = CreateOrderRequest(
        symbol="EUR/USD",
        side=OrderSideEnum.SELL,
        order_type=OrderTypeEnum.MARKET,
        quantity=Decimal("10000"),
        price=Decimal("1.21000"),
    )

    await service.create_order(req)
    assert existing_pos.is_open is False
    assert existing_pos.closed_at is not None
    assert mock_account.margin == Decimal("0")
