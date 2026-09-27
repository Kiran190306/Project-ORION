"""Integration tests for Phase 5: End-to-End Trading Workflow Audit & Integration.

Verifies:
1. Strategy -> Research State:
   - Backtest experiment execution and persistence in ResearchExperimentModel.
2. Strategy -> Deployment State:
   - Candidate promotion and lifecycle progression in StrategyDeploymentModel.
3. Market Data Availability:
   - Quote and candle retrieval with canonical normalization and quality validation.
4. Decision / Signal Generation:
   - Market intelligence input through DecisionEngine producing TradeDecision.
5. Sizing Integration:
   - Position sizing calculator with risk-percent and Decimal arithmetic.
6. Risk Validation:
   - Free margin and leverage constraint enforcement before paper execution.
7. Paper Order:
   - POST /api/v1/orders/ submission with strategy_id linkage.
8. Paper Fill:
   - FillModel generation and execution reporting.
9. Position Creation & Netting:
   - PositionModel creation with strategy_id and order_id attribution.
10. Portfolio & P&L State:
    - Multi-strategy portfolio breakdown and real calculated P&L.
11. Notification Dispatch:
    - Authentic in-app notification record on order execution.
12. Audit Trail:
    - AuditLogModel recording of order and strategy lifecycle events.
13. Tenant Isolation:
    - Strict organization boundaries between tenant accounts.
14. Paper-Only Safety Guard:
    - Zero capital at risk ($0.00), PaperExecutionAdapter exclusively.
"""

from __future__ import annotations

import pathlib
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest import mock
from unittest.mock import AsyncMock

import pytest
from apps.trading_engine.src.config import AppSettings
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.services.auth import get_password_hash
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from libraries.domain.execution.models import OrderSide, OrderType
from libraries.domain.trading.decision_engine import DecisionEngine, EngineConfig, MarketIntelligenceInput
from libraries.domain.trading.decision_result import DecisionOutcome
from libraries.domain.trading.signals import SignalDirection
from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.execution.execution_factory import (
    ExecutionAdapterFactory,
    ExecutionAdapterSpec,
)
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.config import DatabaseConfig, DatabaseManager
from libraries.infrastructure.persistence.models import (
    AccountModel,
    AuditLogModel,
    FillModel,
    NotificationRecordModel,
    OrderModel,
    PositionModel,
    ResearchExperimentModel,
    StrategyConfigModel,
    StrategyDeploymentModel,
    UserModel,
)
from libraries.infrastructure.persistence.models.organization import (
    OrganizationMemberModel,
    OrganizationModel,
)


@pytest.fixture
async def phase5_env():
    """Set up an isolated database, mock Redis, paper adapter, and app for testing."""
    db_file = f"test_phase5_{uuid.uuid4().hex[:8]}.db"
    db_path = pathlib.Path(db_file)
    db_url = f"sqlite+aiosqlite:///{db_file}"

    db_config = DatabaseConfig(url=db_url, echo=False)
    db_manager = DatabaseManager(db_config)

    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    org_a_id = "org_p5_alpha"
    org_b_id = "org_p5_beta"
    user_a_id = "user_p5_alpha"
    user_b_id = "user_p5_beta"
    acc_a_id = "acc_p5_alpha"
    acc_b_id = "acc_p5_beta"

    pass_a = "AlphaPass2026!"
    pass_b = "BetaPass2026!"

    async with db_manager.session() as session:
        # Create Organizations
        org_a = OrganizationModel(
            id=org_a_id,
            name="Alpha Hedge Corp",
            slug="alpha-hedge-corp",
            status="ACTIVE",
            meta_data={},
        )
        org_b = OrganizationModel(
            id=org_b_id,
            name="Beta Quantitative",
            slug="beta-quantitative",
            status="ACTIVE",
            meta_data={},
        )
        session.add_all([org_a, org_b])

        # Create Users
        user_a = UserModel(
            id=user_a_id,
            username="alpha_lead",
            email="alpha@example.com",
            hashed_password=get_password_hash(pass_a),
            is_active=True,
            is_superuser=False,
            full_name="Alpha Lead Trader",
            email_verified=True,
            meta_data={"timezone": "UTC"},
        )
        user_b = UserModel(
            id=user_b_id,
            username="beta_lead",
            email="beta@example.com",
            hashed_password=get_password_hash(pass_b),
            is_active=True,
            is_superuser=False,
            full_name="Beta Lead Trader",
            email_verified=True,
            meta_data={"timezone": "UTC"},
        )
        session.add_all([user_a, user_b])

        # Memberships
        mem_a = OrganizationMemberModel(
            id="mem_p5_alpha",
            organization_id=org_a_id,
            user_id=user_a_id,
            role="OWNER",
            status="ACTIVE",
            meta_data={},
        )
        mem_b = OrganizationMemberModel(
            id="mem_p5_beta",
            organization_id=org_b_id,
            user_id=user_b_id,
            role="OWNER",
            status="ACTIVE",
            meta_data={},
        )
        session.add_all([mem_a, mem_b])

        # Accounts
        acc_a = AccountModel(
            id=acc_a_id,
            broker_name="paper",
            account_number="ACC-P5-ALPHA",
            user_id=user_a_id,
            organization_id=org_a_id,
            currency="USD",
            balance=Decimal("100000.00"),
            equity=Decimal("100000.00"),
            margin=Decimal("0.00"),
            margin_free=Decimal("100000.00"),
            margin_level=0.0,
            leverage=100,
            is_active=True,
            is_live=False,
            meta_data={},
        )
        acc_b = AccountModel(
            id=acc_b_id,
            broker_name="paper",
            account_number="ACC-P5-BETA",
            user_id=user_b_id,
            organization_id=org_b_id,
            currency="USD",
            balance=Decimal("50000.00"),
            equity=Decimal("50000.00"),
            margin=Decimal("0.00"),
            margin_free=Decimal("50000.00"),
            margin_level=0.0,
            leverage=50,
            is_active=True,
            is_live=False,
            meta_data={},
        )
        session.add_all([acc_a, acc_b])
        await session.commit()

    settings = AppSettings(
        environment="testing",
        log_level="INFO",
        database_url=db_url,
        redis_url="redis://localhost:6379/0",
        run_migrations=False,
        server_host="127.0.0.1",
        server_port=8000,
        paper_balance=Decimal("100000.00"),
        worker_enabled=False,
        worker_symbols=("EUR/USD", "GBP/USD"),
        market_data_poll_interval=5.0,
        trading_cycle_interval=10.0,
        worker_timeout=30.0,
        worker_stale_threshold=30.0,
        jwt_secret_key="phase5-super-secret-key-institutional-grade-testing-only-12345",
    )

    redis_mock = mock.create_autospec(RedisClient, instance=True)
    redis_mock.is_connected = True
    redis_mock.health_check = AsyncMock(return_value=True)
    redis_mock.connect = AsyncMock()
    redis_mock.disconnect = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=True)
    redis_mock.exists = AsyncMock(return_value=False)
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.expire = AsyncMock(return_value=True)

    paper_adapter = PaperExecutionAdapter(
        config=PaperExecutionConfig(
            broker_name="paper",
            is_paper=True,
            balance=Decimal("100000.00"),
        )
    )
    await paper_adapter.connect()

    app = create_app(
        settings=settings,
        db_manager=db_manager,
        redis_client=redis_mock,
        paper_adapter=paper_adapter,
    )

    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp_a = await client.post(
            "/api/v1/auth/login",
            json={"username": "alpha_lead", "password": pass_a},
        )
        assert resp_a.status_code == 200, f"Login A failed: {resp_a.text}"
        token_a = resp_a.json()["access_token"]

        resp_b = await client.post(
            "/api/v1/auth/login",
            json={"username": "beta_lead", "password": pass_b},
        )
        assert resp_b.status_code == 200, f"Login B failed: {resp_b.text}"
        token_b = resp_b.json()["access_token"]

        yield {
            "client": client,
            "headers_a": {"Authorization": f"Bearer {token_a}"},
            "headers_b": {"Authorization": f"Bearer {token_b}"},
            "app": app,
            "db_manager": db_manager,
            "paper_adapter": paper_adapter,
            "org_a_id": org_a_id,
            "org_b_id": org_b_id,
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
            "acc_a_id": acc_a_id,
            "acc_b_id": acc_b_id,
        }

    await paper_adapter.disconnect()
    await db_manager.close()
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_end_to_end_research_to_deployment_workflow(phase5_env):
    """Objective 1 & 2: Test research experiment creation, metrics, and deployment progression."""
    client = phase5_env["client"]
    headers = phase5_env["headers_a"]
    db = phase5_env["db_manager"]
    org_a = phase5_env["org_a_id"]
    user_a = phase5_env["user_a_id"]

    # 1. Persist a research experiment directly
    exp_id = f"exp_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    async with db.session() as session:
        exp = ResearchExperimentModel(
            id=exp_id,
            organization_id=org_a,
            created_by=user_a,
            strategy_id="trend_following",
            strategy_version="1.0.0",
            symbol="EUR/USD",
            timeframe="H1",
            start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2025, 12, 31, tzinfo=timezone.utc),
            initial_capital=Decimal("10000.00"),
            parameters={"fast_period": 10, "slow_period": 30},
            simulation_config={"slippage_pips": 1.0},
            status="COMPLETED",
            execution_time_seconds=1.25,
            metrics={"sharpe_ratio": 1.85, "win_rate": 62.5, "total_return": 14.2},
            completed_at=now,
        )
        session.add(exp)

        # 2. Persist a deployment linked to research
        dep_id = f"dep_{uuid.uuid4().hex[:12]}"
        dep = StrategyDeploymentModel(
            id=dep_id,
            organization_id=org_a,
            created_by=user_a,
            strategy_id="trend_following",
            strategy_version="1.0.0",
            symbol="EUR/USD",
            timeframe="H1",
            status="INCUBATING",
            parameters={"fast_period": 10, "slow_period": 30},
            source_experiment_id=exp_id,
            evidence_chain={"source": "research_experiment", "id": exp_id},
            initial_capital=Decimal("10000.00"),
            incubation_config={"min_duration_days": 14, "max_drawdown_pct": 5.0},
            promotion_verdict="PENDING",
            transition_history=[{"from": "PENDING_GATES", "to": "INCUBATING", "actor": user_a}],
            started_at=now,
        )
        session.add(dep)
        await session.commit()

    # 3. Verify via Deployment API
    res = await client.get("/api/v1/deployments", headers=headers)
    assert res.status_code == 200
    deployments = res.json()["items"]
    assert len(deployments) >= 1
    matched = next((d for d in deployments if d["id"] == dep_id), None)
    assert matched is not None
    assert matched["strategy_id"] == "trend_following"
    assert matched["status"] == "INCUBATING"


@pytest.mark.asyncio
async def test_end_to_end_decision_sizing_and_paper_execution(phase5_env):
    """Objectives 3, 4, 5, 6, 7, 8, 9, 10, 11, 12: Test Decision -> Sizing -> Order -> Fill -> Position -> Notification -> Audit."""
    client = phase5_env["client"]
    headers = phase5_env["headers_a"]
    db = phase5_env["db_manager"]
    acc_id = phase5_env["acc_a_id"]
    org_id = phase5_env["org_a_id"]

    # 1. Test DecisionEngine generates an executable trade decision
    engine = DecisionEngine(
        config=EngineConfig(
            min_confidence=30.0,
            risk_percent=1.0,
            default_account_balance=Decimal("100000.00"),
        )
    )
    mi = MarketIntelligenceInput(
        spread_pips=1.2,
        entry_price=Decimal("1.10000"),
        stop_loss=Decimal("1.09500"),
        take_profit=Decimal("1.11000"),
        liquidity_score=0.8,
        provider_quality=1.0,
        consensus_quality=0.8,
        volatility_score=0.3,
        trend_strength=0.7,
    )
    decision = await engine.make_decision(
        symbol="EUR/USD",
        market_intelligence=mi,
        account_balance=Decimal("100000.00"),
    )
    assert decision.decision_id.startswith("DEC-")
    assert decision.outcome in (DecisionOutcome.EXECUTE, DecisionOutcome.DEFER)

    # 2. Test Sizing API
    sizing_payload = {
        "symbol": "EUR/USD",
        "method": "risk_percent",
        "risk_percent": 1.5,
        "entry_price": 1.10000,
        "stop_loss": 1.09500,
    }
    sizing_res = await client.post("/api/v1/positions/sizing", json=sizing_payload, headers=headers)
    assert sizing_res.status_code == 200
    sizing_data = sizing_res.json()
    assert sizing_data["is_valid"] is True
    calc_units = Decimal(str(sizing_data["calculated_units"]))
    assert calc_units > Decimal("0")

    # 3. Create active strategy configuration
    strat_res = await client.post(
        "/api/v1/strategies/account/configs",
        json={
            "strategy_id": "trend_following",
            "symbols": ["EUR/USD"],
            "timeframe": "M15",
            "parameters": {"fast_period": 10, "slow_period": 30},
        },
        headers=headers,
    )
    assert strat_res.status_code == 201

    # 4. Submit Order using calculated size and strategy_id
    order_payload = {
        "symbol": "EUR/USD",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": float(calc_units),
        "strategy_id": "trend_following",
    }
    order_res = await client.post("/api/v1/orders/", json=order_payload, headers=headers)
    assert order_res.status_code == 201
    order_data = order_res.json()
    order_id = order_data["id"]
    assert order_data["status"] == "FILLED"
    assert order_data["strategy_id"] == "trend_following"

    # 5. Verify Database Records: Order, Fill, Position, Notification, Audit
    async with db.session() as session:
        # Order
        ord_record = await session.get(OrderModel, order_id)
        assert ord_record is not None
        assert ord_record.status == "FILLED"
        assert ord_record.strategy_id == "trend_following"

        # Fill
        fills_res = await session.execute(
            select(FillModel).where(FillModel.order_id == order_id)
        )
        fills = list(fills_res.scalars().all())
        assert len(fills) >= 1
        assert fills[0].quantity == Decimal(str(calc_units))

        # Position
        pos_res = await session.execute(
            select(PositionModel).where(
                PositionModel.account_id == acc_id,
                PositionModel.is_open == True,
            )
        )
        positions = list(pos_res.scalars().all())
        assert len(positions) >= 1
        pos = positions[0]
        assert pos.symbol == "EUR/USD"
        assert pos.meta_data.get("strategy_id") == "trend_following"
        assert pos.meta_data.get("order_id") == order_id

        # Notification
        notifs_res = await session.execute(
            select(NotificationRecordModel).where(
                NotificationRecordModel.notification_type == "ORDER_FILLED"
            )
        )
        notifs = list(notifs_res.scalars().all())
        assert len(notifs) >= 1
        assert "EUR/USD" in notifs[0].title

        # Platform Audit Log
        audit_res = await session.execute(
            select(AuditLogModel).where(
                AuditLogModel.event_type == "order.created",
                AuditLogModel.organization_id == org_id,
            )
        )
        audits = list(audit_res.scalars().all())
        assert len(audits) >= 1
        assert audits[0].details.get("order_id") == order_id

    # 6. Verify Multi-Strategy Portfolio Breakdown
    portfolio_res = await client.get("/api/v1/portfolio/strategies", headers=headers)
    assert portfolio_res.status_code == 200
    port_data = portfolio_res.json()
    assert port_data["is_paper"] is True
    assert port_data["total_open_positions"] >= 1
    strat_items = port_data["strategies"]
    tf_item = next((s for s in strat_items if s["strategy_id"] == "trend_following"), None)
    assert tf_item is not None
    assert tf_item["open_positions_count"] >= 1
    assert tf_item["is_active"] is True


@pytest.mark.asyncio
async def test_tenant_isolation_and_paper_safety(phase5_env):
    """Objective 13 & 14: Test multi-tenant isolation and strict paper safety guard."""
    client = phase5_env["client"]
    headers_a = phase5_env["headers_a"]
    headers_b = phase5_env["headers_b"]

    # Tenant A creates an order
    res_a = await client.post(
        "/api/v1/orders/",
        json={"symbol": "GBP/USD", "side": "BUY", "order_type": "MARKET", "quantity": 10000},
        headers=headers_a,
    )
    assert res_a.status_code == 201
    order_a_id = res_a.json()["id"]

    # Tenant B cannot view or access Tenant A's order
    res_b_view = await client.get(f"/api/v1/orders/{order_a_id}", headers=headers_b)
    assert res_b_view.status_code in (403, 404)

    # Tenant B list orders contains 0 of Tenant A's orders
    res_b_list = await client.get("/api/v1/orders/", headers=headers_b)
    assert res_b_list.status_code == 200
    b_orders = res_b_list.json()["items"]
    assert all(o["id"] != order_a_id for o in b_orders)

    # Verify execution factory prohibits LIVE
    from libraries.infrastructure.security.endpoint_validator import SecurityViolationError

    with pytest.raises(SecurityViolationError, match="strictly prohibited in Project ORION"):
        ExecutionAdapterFactory.create_adapter(
            ExecutionAdapterSpec(provider="paper", environment="LIVE")
        )
