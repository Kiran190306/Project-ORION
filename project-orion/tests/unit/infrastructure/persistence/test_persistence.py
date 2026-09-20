"""Unit tests for Persistence Infrastructure, DatabaseManager, and ORM models."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from libraries.infrastructure.persistence import (
    AccountModel,
    AuditLogModel,
    Base,
    DatabaseConfig,
    DatabaseManager,
    NotificationRecordModel,
    OrderModel,
    PositionModel,
    StrategyConfigModel,
)


def test_database_metadata_tables() -> None:
    """Verify all expected domain entities are declared in SQLAlchemy Base metadata."""
    expected_tables = {
        "accounts",
        "orders",
        "fills",
        "execution_reports",
        "positions",
        "strategy_configs",
        "risk_limits",
        "risk_breaches",
        "notification_records",
        "audit_logs",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables)


def test_database_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify DatabaseConfig parses environment variables and normalizes URLs."""
    monkeypatch.setenv("ORION_DATABASE_URL", "postgres://user:pass@db.example.com:5432/orion_prod")
    monkeypatch.setenv("ORION_DB_POOL_SIZE", "25")
    monkeypatch.setenv("ORION_DB_MAX_OVERFLOW", "50")

    config = DatabaseConfig.from_env()
    assert config.url.startswith("postgresql+asyncpg://")
    assert config.pool_size == 25
    assert config.max_overflow == 50


@pytest.mark.asyncio
async def test_database_manager_in_memory_lifecycle() -> None:
    """Test DatabaseManager with SQLite in-memory engine, table creation, and queries."""
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:", echo=False)
    manager = DatabaseManager(config)

    # Create tables in memory
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Health check
    assert await manager.health_check() is True

    # Insert Account and Order
    async with manager.session() as session:
        account = AccountModel(
            id="acc_001",
            broker_name="oanda",
            account_number="101-004-12345678-001",
            currency="USD",
            balance=Decimal("50000.00"),
            equity=Decimal("50000.00"),
            margin=Decimal("0.00"),
            margin_free=Decimal("50000.00"),
            margin_level=0.0,
            leverage=100,
            is_live=False,
            is_active=True,
            meta_data={"server": "practice"},
        )
        session.add(account)

        order = OrderModel(
            id="ord_001",
            broker_order_id="b_ord_999",
            account_id="acc_001",
            symbol="EUR/USD",
            side="buy",
            order_type="market",
            quantity=Decimal("1.00"),
            price=Decimal("1.08500"),
            status="filled",
            filled_quantity=Decimal("1.00"),
            average_fill_price=Decimal("1.08502"),
            strategy_id="strat_trend_01",
            meta_data={"slippage_pips": 0.2},
        )
        session.add(order)

        position = PositionModel(
            id="pos_001",
            account_id="acc_001",
            symbol="EUR/USD",
            side="buy",
            quantity=Decimal("1.00"),
            open_price=Decimal("1.08502"),
            current_price=Decimal("1.08600"),
            realized_pnl=Decimal("0.00"),
            unrealized_pnl=Decimal("98.00"),
            is_open=True,
            meta_data={},
        )
        session.add(position)

        strategy = StrategyConfigModel(
            id="strat_trend_01",
            name="Trend Following EMA",
            version="1.0.0",
            is_active=True,
            symbols=["EUR/USD", "GBP/USD"],
            parameters={"fast_period": 9, "slow_period": 21},
            description="EMA Cross Strategy",
        )
        session.add(strategy)

        notification = NotificationRecordModel(
            id="notif_001",
            channel="telegram",
            severity="info",
            notification_type="order_filled",
            title="Order Filled",
            body="EUR/USD BUY 1.00 lot filled at 1.08502",
            status="delivered",
            recipient="chat_12345",
            meta_data={"order_id": "ord_001"},
        )
        session.add(notification)

        audit = AuditLogModel(
            id="aud_001",
            event_type="order_submitted",
            component="execution_engine",
            actor="system",
            details={"order_id": "ord_001"},
        )
        session.add(audit)

        await session.commit()

    # Query back records
    async with manager.session() as session:
        stmt = select(OrderModel).where(OrderModel.id == "ord_001")
        result = await session.execute(stmt)
        saved_order = result.scalar_one()

        assert saved_order.symbol == "EUR/USD"
        assert saved_order.quantity == Decimal("1.00")
        assert saved_order.status == "filled"

        stmt_acc = select(AccountModel).where(AccountModel.id == "acc_001")
        result_acc = await session.execute(stmt_acc)
        saved_acc = result_acc.scalar_one()
        assert saved_acc.balance == Decimal("50000.00")

    await manager.close()
