"""Unit tests for BrokerSandboxService and order execution pipeline."""

from __future__ import annotations

import uuid
from decimal import Decimal
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models.organization import OrganizationModel
from libraries.infrastructure.execution.mock_broker import MockBrokerAdapter
from apps.trading_engine.src.schemas import (
    BrokerSandboxAccountCreateRequest,
    BrokerSandboxAccountUpdateRequest,
    BrokerSandboxOrderRequest,
)
from apps.trading_engine.src.services.broker_sandbox_service import BrokerSandboxService
from apps.trading_engine.src.services.entitlement_service import EntitlementService


@pytest.fixture
async def async_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        # Create test organizations
        org1 = OrganizationModel(id="org-sandbox-1", name="Alpha Quant Org", slug="alpha-quant")
        org2 = OrganizationModel(id="org-sandbox-2", name="Beta Quant Org", slug="beta-quant")
        session.add_all([org1, org2])
        await session.commit()
        yield session

    await engine.dispose()


@pytest.fixture
def service(async_session: AsyncSession) -> BrokerSandboxService:
    return BrokerSandboxService(session=async_session)


@pytest.mark.asyncio
async def test_create_sandbox_account_and_masking(service: BrokerSandboxService) -> None:
    req = BrokerSandboxAccountCreateRequest(
        name="Primary Mock Adapter",
        provider="MOCK",
        environment="SANDBOX",
        account_id_external="mock-ext-001",
        credentials={"api_key": "secret-token-value-999"},
        config={"leverage": 50},
    )

    acc = await service.create_account(
        organization_id="org-sandbox-1",
        user_id="user-1",
        request=req,
    )

    assert acc.id.startswith("bsa_")
    assert acc.organization_id == "org-sandbox-1"
    assert acc.provider == "MOCK"
    assert acc.environment == "SANDBOX"
    assert acc.status == "DISCONNECTED"

    # Verify credentials are masked in response and never leak plaintext
    assert acc.credentials_masked.get("api_key") == "***"
    assert "secret-token-value-999" not in str(acc.model_dump())


@pytest.mark.asyncio
async def test_tenant_isolation_fail_closed(service: BrokerSandboxService) -> None:
    req = BrokerSandboxAccountCreateRequest(
        name="Org1 Private Sandbox",
        provider="MOCK",
        environment="SANDBOX",
        account_id_external="mock-ext-002",
        credentials={"api_key": "org1-secret"},
    )
    acc = await service.create_account("org-sandbox-1", "user-1", req)

    # Org1 can read it
    acc_read = await service.get_account("org-sandbox-1", acc.id)
    assert acc_read.id == acc.id

    # Org2 CANNOT read it -> strictly returns 404 (IDOR defense)
    with pytest.raises(HTTPException) as exc_info:
        await service.get_account("org-sandbox-2", acc.id)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_connect_and_disconnect_lifecycle(service: BrokerSandboxService) -> None:
    req = BrokerSandboxAccountCreateRequest(
        name="Lifecycle Mock Sandbox",
        provider="MOCK",
        environment="SANDBOX",
        account_id_external="mock-ext-003",
    )
    acc = await service.create_account("org-sandbox-1", "user-1", req)

    # Connect
    conn_res = await service.connect_account("org-sandbox-1", acc.id)
    assert conn_res.status == "CONNECTED"
    assert conn_res.connected is True
    assert conn_res.balance == Decimal("100000.0000")

    # Verify status in DB
    acc_updated = await service.get_account("org-sandbox-1", acc.id)
    assert acc_updated.status == "CONNECTED"
    assert acc_updated.last_connected_at is not None

    # Disconnect
    disc_res = await service.disconnect_account("org-sandbox-1", acc.id)
    assert disc_res.status == "DISCONNECTED"
    assert disc_res.connected is False


@pytest.mark.asyncio
async def test_submit_sandbox_order_pipeline(service: BrokerSandboxService) -> None:
    req = BrokerSandboxAccountCreateRequest(
        name="Order Pipeline Sandbox",
        provider="MOCK",
        environment="SANDBOX",
        account_id_external="mock-ext-004",
    )
    acc = await service.create_account("org-sandbox-1", "user-1", req)
    await service.connect_account("org-sandbox-1", acc.id)

    order_req = BrokerSandboxOrderRequest(
        symbol="EUR/USD",
        side="BUY",
        order_type="MARKET",
        quantity=Decimal("10000"),
        price=Decimal("1.08500"),
    )

    order_res = await service.submit_sandbox_order("org-sandbox-1", acc.id, order_req)
    assert order_res.status == "FILLED"
    assert order_res.filled_quantity == Decimal("10000")
    assert order_res.symbol == "EUR/USD"
    assert order_res.broker_order_id.startswith("mock_b_")

    # Check positions query
    positions = await service.get_positions("org-sandbox-1", acc.id)
    assert len(positions) == 1
    assert positions[0].symbol == "EUR/USD"
    assert positions[0].quantity == Decimal("10000")


@pytest.mark.asyncio
async def test_order_submission_timeout_unknown_handling(service: BrokerSandboxService) -> None:
    req = BrokerSandboxAccountCreateRequest(
        name="Timeout Sandbox",
        provider="MOCK",
        environment="SANDBOX",
        account_id_external="mock-ext-005",
    )
    acc = await service.create_account("org-sandbox-1", "user-1", req)
    adapter = await service.get_or_create_adapter("org-sandbox-1", acc.id)
    await adapter.connect()

    # Set mock adapter to TIMEOUT mode
    if isinstance(adapter, MockBrokerAdapter):
        adapter.set_mode("TIMEOUT")

    order_req = BrokerSandboxOrderRequest(
        symbol="GBP/USD",
        side="BUY",
        order_type="MARKET",
        quantity=Decimal("5000"),
        price=Decimal("1.27500"),
    )

    # Per Decision 8: A timeout after submission must be treated as UNKNOWN without automatic blind resubmission
    order_res = await service.submit_sandbox_order("org-sandbox-1", acc.id, order_req)
    assert order_res.status == "UNKNOWN"
    assert order_res.broker_order_id == "UNKNOWN"


@pytest.mark.asyncio
async def test_on_demand_reconciliation(service: BrokerSandboxService) -> None:
    req = BrokerSandboxAccountCreateRequest(
        name="Reconcile Sandbox",
        provider="MOCK",
        environment="SANDBOX",
        account_id_external="mock-ext-006",
    )
    acc = await service.create_account("org-sandbox-1", "user-1", req)
    await service.connect_account("org-sandbox-1", acc.id)

    # Run on-demand reconciliation
    recon_res = await service.reconcile_account("org-sandbox-1", acc.id)
    assert recon_res.broker_account_id == acc.id
    assert recon_res.status == "MATCHED"
    assert not recon_res.has_discrepancies

    # Check history
    history = await service.list_reconciliations("org-sandbox-1", acc.id)
    assert len(history) == 1
    assert history[0].id == recon_res.id
