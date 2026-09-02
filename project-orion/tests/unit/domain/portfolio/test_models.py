"""Tests for portfolio data models."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.portfolio.models import (
    AccountSnapshot,
    CurrencyPosition,
    DrawdownSnapshot,
    MarginCallThresholds,
    PnLBreakdown,
    PortfolioSnapshot,
    Position,
    PositionSide,
    PositionStatus,
    PositionSummary,
)


class TestPosition:
    """Position model tests."""

    def test_create_long_position(self):
        pos = Position(
            position_id="POS-001",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        assert pos.position_id == "POS-001"
        assert pos.symbol == "EURUSD"
        assert pos.is_long
        assert not pos.is_short
        assert pos.is_active
        assert pos.status == PositionStatus.OPEN
        assert pos.quantity == Decimal("10000")
        assert pos.entry_price == Decimal("1.1000")

    def test_create_short_position(self):
        pos = Position(
            position_id="POS-002",
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.2500"),
        )
        assert pos.is_short
        assert not pos.is_long

    def test_market_value(self):
        pos = Position(
            position_id="POS-003",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
            current_price=Decimal("1.1050"),
        )
        assert pos.market_value == Decimal("11050")  # 10000 * 1.1050

    def test_cost_basis(self):
        pos = Position(
            position_id="POS-004",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        assert pos.cost_basis == Decimal("11000")

    def test_pnl_net(self):
        pos = Position(
            position_id="POS-005",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
            realized_pnl=Decimal("200"),
            unrealized_pnl=Decimal("50"),
            commission=Decimal("10"),
            swap=Decimal("5"),
            fees=Decimal("2"),
        )
        assert pos.pnl_net == Decimal("233")  # 200 + 50 - 10 - 5 - 2

    def test_holding_time_hours_open(self):
        pos = Position(
            position_id="POS-006",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
        )
        assert pos.holding_time_hours >= 0

    def test_return_pct(self):
        pos = Position(
            position_id="POS-007",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
            realized_pnl=Decimal("55"),
        )
        assert pos.return_pct == 5.0  # 55 / 1100 * 100

    def test_with_update(self):
        pos = Position(
            position_id="POS-008",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
        )
        updated = pos.with_update(quantity=Decimal("2000"), stop_loss=Decimal("1.0950"))
        assert updated.quantity == Decimal("2000")
        assert updated.stop_loss == Decimal("1.0950")
        assert updated.position_id == pos.position_id
        assert updated.entry_price == pos.entry_price

    def test_position_status_properties(self):
        assert PositionStatus.OPEN.is_active
        assert not PositionStatus.OPEN.is_closed
        assert PositionStatus.CLOSED.is_closed
        assert not PositionStatus.CLOSED.is_active
        assert PositionStatus.LIQUIDATED.is_closed
        assert PositionStatus.PENDING.is_pending
        assert PositionStatus.FORCED_CLOSE.is_closed

    def test_position_frozen(self):
        pos = Position(
            position_id="POS-009",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
        )
        with pytest.raises(AttributeError):
            pos.quantity = Decimal("2000")  # frozen

    def test_close_time_none_when_open(self):
        pos = Position(
            position_id="POS-010",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
        )
        assert pos.close_time is None
        assert pos.close_reason == ""


class TestAccountSnapshot:
    """AccountSnapshot model tests."""

    def test_create_account_snapshot(self):
        snap = AccountSnapshot(
            balance=Decimal("10000"),
            equity=Decimal("11000"),
            free_margin=Decimal("8000"),
            used_margin=Decimal("2000"),
            margin_level=550.0,
        )
        assert snap.balance == Decimal("10000")
        assert snap.equity == Decimal("11000")

    def test_margin_utilization(self):
        snap = AccountSnapshot(
            equity=Decimal("10000"),
            used_margin=Decimal("2000"),
        )
        assert snap.margin_utilization_pct == 20.0

    def test_margin_call_detection(self):
        snap = AccountSnapshot(
            equity=Decimal("1000"),
            used_margin=Decimal("1100"),
            margin_level=90.9,
        )
        assert snap.is_margin_call

    def test_no_margin_call_when_healthy(self):
        snap = AccountSnapshot(
            equity=Decimal("10000"),
            used_margin=Decimal("2000"),
            margin_level=500.0,
        )
        assert not snap.is_margin_call

    def test_stop_out_detection(self):
        snap = AccountSnapshot(
            equity=Decimal("400"),
            used_margin=Decimal("1000"),
            margin_level=40.0,
        )
        assert snap.is_stop_out

    def test_default_values(self):
        snap = AccountSnapshot()
        assert snap.balance == Decimal("0")
        assert snap.equity == Decimal("0")
        assert snap.margin_level == 0.0


class TestPortfolioSnapshot:
    """PortfolioSnapshot model tests."""

    def test_create_portfolio_snapshot(self):
        snap = PortfolioSnapshot(
            total_realized_pnl=Decimal("500"),
            total_unrealized_pnl=Decimal("200"),
            position_count=5,
            open_position_count=3,
        )
        assert snap.net_profit == Decimal("700")

    def test_empty_portfolio(self):
        snap = PortfolioSnapshot()
        assert snap.position_count == 0
        assert snap.net_profit == Decimal("0")


class TestPnLBreakdown:
    """PnLBreakdown model tests."""

    def test_create_pnl_breakdown(self):
        pnl = PnLBreakdown(
            realized_pnl=Decimal("1000"),
            unrealized_pnl=Decimal("200"),
            commission=Decimal("50"),
            swap=Decimal("10"),
            fees=Decimal("5"),
        )
        assert pnl.total_cost == Decimal("65")
        assert pnl.net_profit == Decimal("1135")

    def test_is_profitable(self):
        pnl = PnLBreakdown(realized_pnl=Decimal("500"))
        assert pnl.is_profitable

    def test_is_not_profitable(self):
        pnl = PnLBreakdown(realized_pnl=Decimal("-100"))
        assert not pnl.is_profitable


class TestPositionSummary:
    """PositionSummary model tests."""

    def test_create_summary(self):
        summary = PositionSummary(
            symbol="EURUSD",
            total_long_quantity=Decimal("10000"),
            total_short_quantity=Decimal("5000"),
            net_quantity=Decimal("5000"),
            position_count=2,
            active_count=2,
        )
        assert summary.symbol == "EURUSD"
        assert summary.net_quantity == Decimal("5000")


class TestCurrencyPosition:
    """CurrencyPosition model tests."""

    def test_create_currency_position(self):
        cp = CurrencyPosition(
            currency="USD",
            long_exposure=Decimal("100000"),
            short_exposure=Decimal("50000"),
            net_exposure=Decimal("50000"),
            position_count=3,
        )
        assert cp.currency == "USD"
        assert cp.position_count == 3


class TestMarginCallThresholds:
    """MarginCallThresholds model tests."""

    def test_default_thresholds(self):
        t = MarginCallThresholds()
        assert t.margin_call_level == 100.0
        assert t.stop_out_level == 50.0
        assert t.warning_level == 200.0

    def test_custom_thresholds(self):
        t = MarginCallThresholds(
            margin_call_level=80.0,
            stop_out_level=30.0,
            warning_level=150.0,
        )
        assert t.margin_call_level == 80.0
        assert t.stop_out_level == 30.0


class TestDrawdownSnapshot:
    """DrawdownSnapshot model tests."""

    def test_create_drawdown(self):
        dd = DrawdownSnapshot(
            current_drawdown=10.5,
            max_drawdown=25.0,
            peak_equity=Decimal("100000"),
            current_equity=Decimal("90000"),
            recovery_factor=0.5,
        )
        assert dd.current_drawdown == 10.5
        assert dd.max_drawdown == 25.0


class TestImmutability:
    """Test that all models are truly immutable."""

    @pytest.mark.parametrize(
        "model_class,kwargs",
        [
            (
                Position,
                dict(
                    position_id="T",
                    symbol="EURUSD",
                    side=PositionSide.LONG,
                    quantity=Decimal("1"),
                    entry_price=Decimal("1.0"),
                ),
            ),
            (AccountSnapshot, dict()),
            (PortfolioSnapshot, dict()),
            (PnLBreakdown, dict()),
            (PositionSummary, dict(symbol="EURUSD")),
            (CurrencyPosition, dict(currency="USD")),
            (MarginCallThresholds, dict()),
            (DrawdownSnapshot, dict()),
        ],
    )
    def test_all_frozen(self, model_class, kwargs):
        instance = model_class(**kwargs)
        with pytest.raises((AttributeError, TypeError)):
            setattr(instance, "dummy", "value")

    def test_position_slots(self):
        pos = Position(
            position_id="T",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1"),
            entry_price=Decimal("1.0"),
        )
        with pytest.raises(AttributeError):
            pos.__dict__  # slots means no __dict__
