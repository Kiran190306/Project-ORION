"""Unit tests for BrokerSandboxAccountModel and BrokerReconciliationSnapshotModel persistence."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models.broker_sandbox import (
    BrokerReconciliationSnapshotModel,
    BrokerSandboxAccountModel,
)
from libraries.infrastructure.persistence.models.organization import OrganizationModel


@pytest.fixture
async def async_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        # Create base organization
        org = OrganizationModel(
            id="org-test-broker-1",
            name="Test Broker Org",
            slug="test-broker-org",
        )
        session.add(org)
        await session.commit()
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_broker_sandbox_account_crud(async_session: AsyncSession) -> None:
    acc_id = f"bsa_{uuid.uuid4().hex[:12]}"
    account = BrokerSandboxAccountModel(
        id=acc_id,
        organization_id="org-test-broker-1",
        provider="MOCK",
        environment="SANDBOX",
        account_id_external="mock-ext-001",
        name="Primary Mock Sandbox",
        status="DISCONNECTED",
        credentials_encrypted={"ciphertext": "abc", "nonce": "123"},
        config={"leverage": 50},
    )
    async_session.add(account)
    await async_session.commit()

    # Query back
    stmt = select(BrokerSandboxAccountModel).where(BrokerSandboxAccountModel.id == acc_id)
    res = await async_session.execute(stmt)
    retrieved = res.scalar_one_or_none()

    assert retrieved is not None
    assert retrieved.provider == "MOCK"
    assert retrieved.environment == "SANDBOX"
    assert retrieved.name == "Primary Mock Sandbox"
    assert retrieved.status == "DISCONNECTED"

    # Update status
    retrieved.status = "CONNECTED"
    await async_session.commit()

    res_updated = await async_session.execute(stmt)
    assert res_updated.scalar_one().status == "CONNECTED"


@pytest.mark.asyncio
async def test_broker_reconciliation_snapshot_crud(async_session: AsyncSession) -> None:
    acc_id = f"bsa_{uuid.uuid4().hex[:12]}"
    account = BrokerSandboxAccountModel(
        id=acc_id,
        organization_id="org-test-broker-1",
        provider="MOCK",
        account_id_external="mock-ext-002",
        name="Secondary Mock Sandbox",
    )
    async_session.add(account)
    await async_session.commit()

    snap_id = f"snap_{uuid.uuid4().hex[:12]}"
    snapshot = BrokerReconciliationSnapshotModel(
        id=snap_id,
        organization_id="org-test-broker-1",
        broker_account_id=acc_id,
        status="DISCREPANCY",
        order_discrepancies=[{"type": "ORDER_STATUS_MISMATCH"}],
        position_discrepancies=[],
        account_discrepancies=[],
        balance_delta=Decimal("25.5000"),
        equity_delta=Decimal("25.5000"),
        details={"evaluated_by": "test_runner"},
    )
    async_session.add(snapshot)
    await async_session.commit()

    # Query back
    stmt = select(BrokerReconciliationSnapshotModel).where(
        BrokerReconciliationSnapshotModel.id == snap_id
    )
    res = await async_session.execute(stmt)
    retrieved_snap = res.scalar_one_or_none()

    assert retrieved_snap is not None
    assert retrieved_snap.status == "DISCREPANCY"
    assert retrieved_snap.balance_delta == Decimal("25.5000")
    assert len(retrieved_snap.order_discrepancies) == 1
