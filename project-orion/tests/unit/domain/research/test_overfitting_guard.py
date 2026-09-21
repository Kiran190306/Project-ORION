"""Unit tests for OverfittingGuard quant safety warnings (EPIC-023 Phase 16 & 17)."""

from __future__ import annotations

from decimal import Decimal

from libraries.domain.research.models import (
    ResearchPerformanceMetrics,
    WarningSeverity,
)
from libraries.domain.research.overfitting_guard import OverfittingGuard


def _create_metrics(
    total_trades: int = 50,
    sharpe_ratio: float = 1.5,
    win_rate_pct: float = 55.0,
    max_drawdown_pct: float = 12.0,
) -> ResearchPerformanceMetrics:
    return ResearchPerformanceMetrics(
        initial_capital=Decimal(10000),
        final_balance=Decimal(11000),
        net_profit=Decimal(1000),
        total_return_pct=10.0,
        gross_profit=Decimal(2000),
        gross_loss=Decimal(1000),
        profit_factor=2.0,
        win_rate_pct=win_rate_pct,
        loss_rate_pct=100.0 - win_rate_pct,
        total_trades=total_trades,
        winning_trades=int(total_trades * win_rate_pct / 100),
        losing_trades=total_trades - int(total_trades * win_rate_pct / 100),
        avg_trade_pnl=Decimal(20),
        largest_win=Decimal(200),
        largest_loss=Decimal(100),
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=2.0,
        max_drawdown_pct=max_drawdown_pct,
        max_drawdown_duration_seconds=3600.0,
        recovery_factor=1.5,
        expectancy=Decimal(20),
    )


def test_overfitting_guard_clean_baseline() -> None:
    """Standard metrics over 90 days with 2 parameters should produce zero warnings."""
    metrics = _create_metrics(total_trades=50, sharpe_ratio=1.5, win_rate_pct=55.0, max_drawdown_pct=10.0)
    warnings = OverfittingGuard.evaluate(metrics, duration_days=90.0, parameter_count=2)
    assert len(warnings) == 0


def test_overfitting_guard_small_sample_size() -> None:
    """Sample size under 30 trades triggers SMALL_SAMPLE_SIZE warning."""
    metrics = _create_metrics(total_trades=15)
    warnings = OverfittingGuard.evaluate(metrics, duration_days=90.0, parameter_count=2)
    codes = [w.code for w in warnings]
    assert "SMALL_SAMPLE_SIZE" in codes


def test_overfitting_guard_unrealistic_performance() -> None:
    """Extreme Sharpe ratio (>4.0) or win rate (>85%) triggers UNREALISTIC_PERFORMANCE warning."""
    metrics = _create_metrics(total_trades=60, sharpe_ratio=4.5, win_rate_pct=90.0)
    warnings = OverfittingGuard.evaluate(metrics, duration_days=90.0, parameter_count=2)
    codes = [w.code for w in warnings]
    assert "UNREALISTIC_PERFORMANCE" in codes
    critical_warnings = [w for w in warnings if w.severity == WarningSeverity.CRITICAL]
    assert len(critical_warnings) >= 1


def test_overfitting_guard_short_horizon() -> None:
    """Evaluation period under 30 calendar days triggers SHORT_TEST_HORIZON warning."""
    metrics = _create_metrics(total_trades=40)
    warnings = OverfittingGuard.evaluate(metrics, duration_days=14.0, parameter_count=2)
    codes = [w.code for w in warnings]
    assert "SHORT_TEST_HORIZON" in codes


def test_overfitting_guard_high_drawdown() -> None:
    """Drawdown exceeding 25% triggers HIGH_DRAWDOWN warning."""
    metrics = _create_metrics(total_trades=50, max_drawdown_pct=32.5)
    warnings = OverfittingGuard.evaluate(metrics, duration_days=90.0, parameter_count=2)
    codes = [w.code for w in warnings]
    assert "HIGH_DRAWDOWN" in codes


def test_overfitting_guard_parameter_density() -> None:
    """Strategy with >= 6 parameters triggers PARAMETER_DENSITY informational caveat."""
    metrics = _create_metrics(total_trades=50)
    warnings = OverfittingGuard.evaluate(metrics, duration_days=90.0, parameter_count=7)
    codes = [w.code for w in warnings]
    assert "PARAMETER_DENSITY" in codes
