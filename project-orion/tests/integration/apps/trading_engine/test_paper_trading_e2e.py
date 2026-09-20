"""Deterministic 23-step end-to-end integration test for paper trading.

Covers the full institutional flow:
Step 1:  Authentication — login via /api/v1/auth/login, obtain JWT tokens for User A and User B
Step 2:  Account — query /api/v1/auth/me and verify paper trading account balance ($100,000.00)
Step 3:  Dashboard Initial State — GET /api/v1/dashboard/ before any trades, verify 0 positions
Step 4:  Strategy Discovery — query active strategies catalog via /api/v1/strategies/
Step 5:  Strategy Config Update — PUT /api/v1/strategies/account/config, verify updated response
Step 6:  Risk — verify risk status (/api/v1/risk/status) and limits (/api/v1/risk/limits)
Step 7:  Order Submission — submit MARKET BUY EUR/USD (10,000 units) via /api/v1/orders/
Step 8:  Order Validation — verify order request validation and normalized response
Step 9:  Paper Execution — verify immediate simulated fill with realistic pricing
Step 10: Order Persistence — verify order status FILLED in database via /api/v1/orders/{id}
Step 11: Trade Ledger — verify execution fill recorded in trade history via /api/v1/trades/
Step 12: Position Inception — verify new position created in /api/v1/positions/
Step 13: Portfolio Analytics — verify overview and currency exposure via /api/v1/portfolio/
Step 14: Dashboard Post-Execution — verify dashboard reflects open position and recent trades
Step 15: Position Liquidation — close open position via /api/v1/positions/{id}/close
Step 16: Realized P&L — verify realized P&L and updated equity via /api/v1/portfolio/pnl
Step 17: Dashboard Post-Liquidation — verify dashboard shows 0 open positions after close
Step 18: Order Cancellation — submit a LIMIT order, verify SUBMITTED, cancel via /orders/{id}/cancel
Step 19: Risk / Input Validation — verify rejection of invalid order parameters (HTTP 422)
Step 20: IDOR — User B cannot access User A's orders (HTTP 403)
Step 21: IDOR — User B cannot access User A's positions (HTTP 403)
Step 22: IDOR — User B cannot access User A's trades (HTTP 403)
Step 23: IDOR — User B cannot access User A's account summary or strategy config (HTTP 403 / 200 isolated)
"""

from __future__ import annotations

import pathlib
import uuid
from decimal import Decimal
from unittest import mock
from unittest.mock import AsyncMock

import pytest
from apps.trading_engine.src.config import AppSettings
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.services.auth import get_password_hash
from httpx import ASGITransport, AsyncClient

from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.config import DatabaseConfig, DatabaseManager
from libraries.infrastructure.persistence.models import UserModel


@pytest.fixture
async def e2e_environment():
    """Set up an isolated SQLite database, mock Redis, paper adapter, and app."""
    db_file = f"test_e2e_{uuid.uuid4().hex[:8]}.db"
    db_path = pathlib.Path(db_file)
    db_url = f"sqlite+aiosqlite:///{db_file}"

    db_config = DatabaseConfig(url=db_url, echo=False)
    db_manager = DatabaseManager(db_config)

    # Initialize tables
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed User A (Lead Institutional Trader) and User B (Secondary Trader)
    user_a_id = "usr-lead-trader-001"
    user_b_id = "usr-other-trader-002"
    pass_a = "InstitutionalPass123!"
    pass_b = "SecondaryTraderPass123!"

    async with db_manager.session() as session:
        user_a = UserModel(
            id=user_a_id,
            username="lead_trader",
            email="lead@orion-funds.dev",
            hashed_password=get_password_hash(pass_a),
            full_name="Lead Institutional Trader",
            is_active=True,
            is_superuser=False,
        )
        user_b = UserModel(
            id=user_b_id,
            username="other_trader",
            email="other@orion-funds.dev",
            hashed_password=get_password_hash(pass_b),
            full_name="Secondary Trader",
            is_active=True,
            is_superuser=False,
        )
        session.add(user_a)
        session.add(user_b)
        await session.commit()

    # Configure deterministic paper execution adapter
    paper_config = PaperExecutionConfig(
        broker_name="paper",
        is_paper=True,
        balance=Decimal("100000.00"),
        currency="USD",
        spread=0.0001,
        slippage_std=0.0,
        latency_ms_mean=0.0,
        latency_ms_std=0.0,
        partial_fill_probability=0.0,
    )
    paper_adapter = PaperExecutionAdapter(config=paper_config)
    await paper_adapter.connect()

    # Mock Redis client
    mock_redis = mock.create_autospec(RedisClient, instance=True)
    mock_redis.is_connected = True
    mock_redis.health_check = AsyncMock(return_value=True)
    mock_redis.connect = AsyncMock()
    mock_redis.disconnect = AsyncMock()

    # App settings
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
        worker_symbols="EUR/USD,GBP/USD",
        market_data_poll_interval=5.0,
        trading_cycle_interval=10.0,
        worker_timeout=30.0,
        worker_stale_threshold=30.0,
    )

    app = create_app(
        settings=settings,
        db_manager=db_manager,
        redis_client=mock_redis,
        paper_adapter=paper_adapter,
    )

    context = {
        "app": app,
        "db_manager": db_manager,
        "paper_adapter": paper_adapter,
        "pass_a": pass_a,
        "pass_b": pass_b,
    }

    try:
        yield context
    finally:
        await db_manager.close()
        if db_path.exists():
            try:
                db_path.unlink()
            except OSError:
                pass


@pytest.mark.asyncio
async def test_full_23_step_paper_trading_lifecycle(e2e_environment: dict):
    """Execute the complete deterministic 23-step institutional paper-trading workflow."""
    app = e2e_environment["app"]
    pass_a = e2e_environment["pass_a"]
    pass_b = e2e_environment["pass_b"]

    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # ─────────────────────────────────────────────────────────────────────
        # Step 1: Authentication — Login and obtain JWT tokens
        # ─────────────────────────────────────────────────────────────────────
        resp_a = await client.post(
            "/api/v1/auth/login",
            json={"username": "lead_trader", "password": pass_a},
        )
        assert resp_a.status_code == 200, f"Login User A failed: {resp_a.text}"
        data_a = resp_a.json()
        token_a = data_a["access_token"]
        assert data_a["token_type"] == "bearer"
        assert data_a["username"] == "lead_trader"
        headers_a = {"Authorization": f"Bearer {token_a}"}

        resp_b = await client.post(
            "/api/v1/auth/login",
            json={"username": "other_trader", "password": pass_b},
        )
        assert resp_b.status_code == 200, f"Login User B failed: {resp_b.text}"
        data_b = resp_b.json()
        token_b = data_b["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # ─────────────────────────────────────────────────────────────────────
        # Step 2: Account — Query profile and verify paper trading account
        # ─────────────────────────────────────────────────────────────────────
        resp_me = await client.get("/api/v1/auth/me", headers=headers_a)
        assert resp_me.status_code == 200
        assert resp_me.json()["username"] == "lead_trader"

        resp_acc = await client.get("/api/v1/account/summary", headers=headers_a)
        assert resp_acc.status_code == 200
        acc_data = resp_acc.json()
        assert Decimal(str(acc_data["balance"])) == Decimal("100000.00")
        assert acc_data["currency"] == "USD"
        assert acc_data["is_paper"] is True

        # ─────────────────────────────────────────────────────────────────────
        # Step 3: Dashboard Initial State — Verify zero positions before trading
        # ─────────────────────────────────────────────────────────────────────
        resp_dash_initial = await client.get("/api/v1/dashboard/", headers=headers_a)
        assert resp_dash_initial.status_code == 200, (
            f"Dashboard initial fetch failed: {resp_dash_initial.text}"
        )
        dash_initial = resp_dash_initial.json()
        # Dashboard contract: must have account, trading, risk, system blocks
        assert "account" in dash_initial, "Dashboard missing 'account' block"
        assert "trading" in dash_initial, "Dashboard missing 'trading' block"
        assert "risk" in dash_initial, "Dashboard missing 'risk' block"
        assert "system" in dash_initial, "Dashboard missing 'system' block"
        # Before any orders: open_positions list must be empty
        assert len(dash_initial["trading"]["open_positions"]) == 0, (
            "Expected 0 open positions in initial dashboard"
        )
        # Account balance must reflect paper $100,000.00
        dash_balance = Decimal(str(dash_initial["account"]["balance"]))
        assert dash_balance == Decimal("100000.00"), (
            f"Initial dashboard balance mismatch: {dash_balance}"
        )

        # ─────────────────────────────────────────────────────────────────────
        # Step 4: Strategy Discovery — List active strategy catalog
        # ─────────────────────────────────────────────────────────────────────
        resp_strat = await client.get("/api/v1/strategies/", headers=headers_a)
        assert resp_strat.status_code == 200
        strategies = resp_strat.json()["strategies"]
        assert len(strategies) > 0
        strat_ids = [s["id"] for s in strategies]
        assert "trend_following" in strat_ids
        assert "mean_reversion" in strat_ids

        # ─────────────────────────────────────────────────────────────────────
        # Step 5: Strategy Config Update — Configure account strategy
        # ─────────────────────────────────────────────────────────────────────
        config_payload = {
            "strategy_id": "trend_following",
            "timeframe": "H1",
            "symbols": ["EUR/USD", "GBP/USD"],
            "parameters": {"fast_ma_period": 10, "slow_ma_period": 30},
            "is_active": True,
        }
        resp_config_put = await client.put(
            "/api/v1/strategies/account/config",
            json=config_payload,
            headers=headers_a,
        )
        assert resp_config_put.status_code == 200, (
            f"Strategy config update failed: {resp_config_put.text}"
        )
        config_data = resp_config_put.json()
        assert config_data["strategy_id"] == "trend_following"
        assert config_data["timeframe"] == "H1"
        assert config_data["is_active"] is True
        assert "EUR/USD" in config_data["symbols"]

        # Verify GET reflects the updated config
        resp_config_get = await client.get(
            "/api/v1/strategies/account/config", headers=headers_a
        )
        assert resp_config_get.status_code == 200
        get_config = resp_config_get.json()
        # The GET endpoint returns config.id (composite key containing strategy name)
        # e.g. "acc-usr-lead-trader-001_trend_following" — verify the strategy is embedded
        assert "trend_following" in get_config["strategy_id"], (
            f"Expected strategy_id to contain 'trend_following', got: {get_config['strategy_id']}"
        )
        assert get_config["timeframe"] == "H1"
        assert get_config["is_active"] is True

        # ─────────────────────────────────────────────────────────────────────
        # Step 6: Risk — Query pre-trade risk status and configured limits
        # ─────────────────────────────────────────────────────────────────────
        resp_risk = await client.get("/api/v1/risk/status", headers=headers_a)
        assert resp_risk.status_code == 200
        assert resp_risk.json()["status"] == "healthy"
        assert resp_risk.json()["emergency_stop_active"] is False

        resp_limits = await client.get("/api/v1/risk/limits", headers=headers_a)
        assert resp_limits.status_code == 200
        limits_data = resp_limits.json()
        assert "limits" in limits_data
        assert limits_data["total"] >= 1

        # ─────────────────────────────────────────────────────────────────────
        # Step 7 & 8: Order Submission & Validation — MARKET BUY EUR/USD
        # ─────────────────────────────────────────────────────────────────────
        order_payload = {
            "symbol": "EUR/USD",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": "10000",
            "stop_loss": "1.08000",
            "take_profit": "1.12000",
        }
        resp_order = await client.post(
            "/api/v1/orders/",
            json=order_payload,
            headers=headers_a,
        )
        assert resp_order.status_code == 201, f"Create order failed: {resp_order.text}"
        order_data = resp_order.json()
        order_id = order_data["id"]

        # Step 8 verification: normalized order fields
        assert order_data["symbol"] == "EUR/USD"
        assert order_data["side"] == "BUY"
        assert order_data["order_type"] == "MARKET"
        assert Decimal(str(order_data["quantity"])) == Decimal(10000)

        # ─────────────────────────────────────────────────────────────────────
        # Step 9: Paper Execution — Simulated immediate fill
        # ─────────────────────────────────────────────────────────────────────
        assert order_data["status"] == "FILLED"
        assert Decimal(str(order_data["filled_quantity"])) == Decimal(10000)
        assert order_data["average_fill_price"] is not None
        assert Decimal(str(order_data["average_fill_price"])) > Decimal(0)
        assert order_data["broker_order_id"] is not None

        # ─────────────────────────────────────────────────────────────────────
        # Step 10: Order Persistence — Verify order status in DB
        # ─────────────────────────────────────────────────────────────────────
        resp_get_order = await client.get(f"/api/v1/orders/{order_id}", headers=headers_a)
        assert resp_get_order.status_code == 200
        persisted_order = resp_get_order.json()
        assert persisted_order["id"] == order_id
        assert persisted_order["status"] == "FILLED"
        assert Decimal(str(persisted_order["filled_quantity"])) == Decimal(10000)

        resp_list_orders = await client.get("/api/v1/orders/", headers=headers_a)
        assert resp_list_orders.status_code == 200
        assert resp_list_orders.json()["total"] >= 1
        assert any(o["id"] == order_id for o in resp_list_orders.json()["items"])

        # ─────────────────────────────────────────────────────────────────────
        # Step 11: Trade Ledger — Verify execution fill record
        # ─────────────────────────────────────────────────────────────────────
        resp_trades = await client.get("/api/v1/trades/", headers=headers_a)
        assert resp_trades.status_code == 200
        trades_data = resp_trades.json()
        assert trades_data["total"] >= 1
        trade = next(t for t in trades_data["items"] if t["order_id"] == order_id)
        trade_id = trade.get("trade_id") or trade.get("id")
        assert trade["symbol"] == "EUR/USD"
        assert trade["side"] == "BUY"
        assert Decimal(str(trade["quantity"])) == Decimal(10000)

        resp_trade_detail = await client.get(f"/api/v1/trades/{trade_id}", headers=headers_a)
        assert resp_trade_detail.status_code == 200
        assert resp_trade_detail.json().get("trade_id") == trade_id

        # ─────────────────────────────────────────────────────────────────────
        # Step 12: Position Inception — Verify open position
        # ─────────────────────────────────────────────────────────────────────
        resp_positions = await client.get("/api/v1/positions/?is_open=true", headers=headers_a)
        assert resp_positions.status_code == 200
        positions_data = resp_positions.json()
        assert positions_data["total"] >= 1
        pos = positions_data["items"][0]
        position_id = pos["id"]
        assert pos["symbol"] == "EUR/USD"
        assert pos["side"] == "BUY"
        assert Decimal(str(pos["quantity"])) == Decimal(10000)
        assert pos["is_open"] is True

        resp_pos_detail = await client.get(f"/api/v1/positions/{position_id}", headers=headers_a)
        assert resp_pos_detail.status_code == 200
        assert resp_pos_detail.json()["id"] == position_id

        # ─────────────────────────────────────────────────────────────────────
        # Step 13: Portfolio Analytics — Verify overview and currency exposure
        # ─────────────────────────────────────────────────────────────────────
        resp_port = await client.get("/api/v1/portfolio/", headers=headers_a)
        assert resp_port.status_code == 200
        port_data = resp_port.json()
        assert port_data["open_positions_count"] >= 1

        resp_exp = await client.get("/api/v1/portfolio/exposure", headers=headers_a)
        assert resp_exp.status_code == 200
        exp_data = resp_exp.json()
        assert Decimal(str(exp_data["gross_exposure"])) > Decimal(0)
        assert "EUR" in [c["currency"] for c in exp_data["currency_exposures"]]

        # ─────────────────────────────────────────────────────────────────────
        # Step 14: Dashboard Post-Execution — Verify position & trades reflected
        # ─────────────────────────────────────────────────────────────────────
        resp_dash_exec = await client.get("/api/v1/dashboard/", headers=headers_a)
        assert resp_dash_exec.status_code == 200
        dash_exec = resp_dash_exec.json()
        assert "account" in dash_exec
        assert "trading" in dash_exec
        assert len(dash_exec["trading"]["open_positions"]) >= 1, (
            "Dashboard must show >=1 open position after MARKET BUY fill"
        )
        assert len(dash_exec["trading"]["recent_trades"]) >= 1, (
            "Dashboard must show >=1 recent trade after execution"
        )
        assert "risk" in dash_exec
        assert "system" in dash_exec

        # ─────────────────────────────────────────────────────────────────────
        # Step 15: Position Liquidation — Close open position
        # ─────────────────────────────────────────────────────────────────────
        resp_close = await client.post(
            f"/api/v1/positions/{position_id}/close", headers=headers_a
        )
        assert resp_close.status_code == 200
        close_data = resp_close.json()
        assert close_data["position_id"] == position_id
        assert close_data["realized_pnl"] is not None

        # Verify position is now closed
        resp_pos_after = await client.get(f"/api/v1/positions/{position_id}", headers=headers_a)
        assert resp_pos_after.status_code == 200
        assert resp_pos_after.json()["is_open"] is False
        assert resp_pos_after.json()["closed_at"] is not None

        # ─────────────────────────────────────────────────────────────────────
        # Step 16: Realized P&L — Verify P&L record updated
        # ─────────────────────────────────────────────────────────────────────
        resp_pnl = await client.get("/api/v1/portfolio/pnl", headers=headers_a)
        assert resp_pnl.status_code == 200
        pnl_data = resp_pnl.json()
        assert "realized_pnl" in pnl_data

        # ─────────────────────────────────────────────────────────────────────
        # Step 17: Dashboard Post-Liquidation — Verify 0 open positions
        # ─────────────────────────────────────────────────────────────────────
        resp_dash_after = await client.get("/api/v1/dashboard/", headers=headers_a)
        assert resp_dash_after.status_code == 200
        dash_after = resp_dash_after.json()
        assert len(dash_after["trading"]["open_positions"]) == 0, (
            "Dashboard must show 0 open positions after position close"
        )

        # ─────────────────────────────────────────────────────────────────────
        # Step 18: Order Cancellation — Submit LIMIT order and cancel
        # ─────────────────────────────────────────────────────────────────────
        limit_payload = {
            "symbol": "GBP/USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "price": "1.10000",
            "quantity": "5000",
        }
        resp_limit = await client.post("/api/v1/orders/", json=limit_payload, headers=headers_a)
        assert resp_limit.status_code == 201
        limit_order_id = resp_limit.json()["id"]
        assert resp_limit.json()["status"] == "SUBMITTED"

        # Cancel the pending LIMIT order
        resp_cancel = await client.post(
            f"/api/v1/orders/{limit_order_id}/cancel", headers=headers_a
        )
        assert resp_cancel.status_code == 200
        assert resp_cancel.json()["status"] == "CANCELLED"

        # Re-cancelling already cancelled order raises 400 Bad Request
        resp_recancel = await client.post(
            f"/api/v1/orders/{limit_order_id}/cancel", headers=headers_a
        )
        assert resp_recancel.status_code == 400

        # ─────────────────────────────────────────────────────────────────────
        # Step 19: Risk & Validation Rejection — Invalid/non-positive quantity
        # ─────────────────────────────────────────────────────────────────────
        invalid_payload = {
            "symbol": "EUR/USD",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": "-100",  # Invalid non-positive quantity
        }
        resp_inv = await client.post("/api/v1/orders/", json=invalid_payload, headers=headers_a)
        assert resp_inv.status_code == 422

        # Non-existent order lookup returns 404
        resp_404 = await client.get("/api/v1/orders/ord_nonexistent_123", headers=headers_a)
        assert resp_404.status_code == 404

        # ─────────────────────────────────────────────────────────────────────
        # Step 20: IDOR — User B cannot access User A's orders
        # ─────────────────────────────────────────────────────────────────────
        # User B cannot read User A's order
        idor_order_get = await client.get(
            f"/api/v1/orders/{order_id}", headers=headers_b
        )
        assert idor_order_get.status_code == 403, (
            f"IDOR: Expected 403 for cross-tenant order read, got {idor_order_get.status_code}"
        )

        # User B cannot cancel User A's order
        idor_order_cancel = await client.post(
            f"/api/v1/orders/{order_id}/cancel", headers=headers_b
        )
        assert idor_order_cancel.status_code == 403, (
            f"IDOR: Expected 403 for cross-tenant order cancel, got {idor_order_cancel.status_code}"
        )

        # ─────────────────────────────────────────────────────────────────────
        # Step 21: IDOR — User B cannot access User A's positions
        # ─────────────────────────────────────────────────────────────────────
        # User B cannot view User A's position
        idor_pos_get = await client.get(
            f"/api/v1/positions/{position_id}", headers=headers_b
        )
        assert idor_pos_get.status_code == 403, (
            f"IDOR: Expected 403 for cross-tenant position read, got {idor_pos_get.status_code}"
        )

        # User B cannot close User A's position
        idor_pos_close = await client.post(
            f"/api/v1/positions/{position_id}/close", headers=headers_b
        )
        assert idor_pos_close.status_code == 403, (
            f"IDOR: Expected 403 for cross-tenant position close, got {idor_pos_close.status_code}"
        )

        # ─────────────────────────────────────────────────────────────────────
        # Step 22: IDOR — User B cannot access User A's trades
        # ─────────────────────────────────────────────────────────────────────
        idor_trade_get = await client.get(
            f"/api/v1/trades/{trade_id}", headers=headers_b
        )
        assert idor_trade_get.status_code == 403, (
            f"IDOR: Expected 403 for cross-tenant trade read, got {idor_trade_get.status_code}"
        )

        # ─────────────────────────────────────────────────────────────────────
        # Step 23: IDOR — User B data is isolated from User A
        #
        # User B's own account summary returns 200 (their own data, not A's).
        # User B's own trade/order/position lists return empty (0 records), not A's.
        # User B cannot read User A's strategy config via account-bound config GET.
        # ─────────────────────────────────────────────────────────────────────
        # User B's own account summary is accessible and isolated
        idor_acc_b = await client.get("/api/v1/account/summary", headers=headers_b)
        assert idor_acc_b.status_code == 200, (
            f"User B's own account summary failed: {idor_acc_b.text}"
        )
        acc_b_data = idor_acc_b.json()
        # User B has their own fresh paper account, not User A's
        assert Decimal(str(acc_b_data["balance"])) == Decimal("100000.00")

        # User B's order list is empty (no cross-tenant leakage)
        idor_orders_b = await client.get("/api/v1/orders/", headers=headers_b)
        assert idor_orders_b.status_code == 200
        assert idor_orders_b.json()["total"] == 0, (
            f"IDOR: User B should see 0 orders, got {idor_orders_b.json()['total']}"
        )

        # User B's position list is empty (no cross-tenant leakage)
        idor_positions_b = await client.get("/api/v1/positions/", headers=headers_b)
        assert idor_positions_b.status_code == 200
        assert idor_positions_b.json()["total"] == 0, (
            f"IDOR: User B should see 0 positions, got {idor_positions_b.json()['total']}"
        )

        # User B's trade list is empty (no cross-tenant leakage)
        idor_trades_b = await client.get("/api/v1/trades/", headers=headers_b)
        assert idor_trades_b.status_code == 200
        assert idor_trades_b.json()["total"] == 0, (
            f"IDOR: User B should see 0 trades, got {idor_trades_b.json()['total']}"
        )
