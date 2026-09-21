"""Unit tests for IncubationPolicy and IncubationPolicyEvaluator."""

from __future__ import annotations

from decimal import Decimal

from libraries.domain.deployment.incubation_policy import (
    IncubationPolicyEvaluator,
)
from libraries.domain.deployment.models import (
    IncubationConfig,
    IncubationMetrics,
)


def test_incubation_insufficient_duration_or_trades():
    """Verify incubation cannot validate before duration and trade hurdles."""
    evaluator = IncubationPolicyEvaluator()
    config = IncubationConfig(min_duration_days=7, min_trade_count=10)

    # 3 days, 5 trades -> cannot validate
    metrics = IncubationMetrics(
        net_pnl=Decimal("100.00"),
        total_trades=5,
        sharpe_ratio=1.5,
    )
    res = evaluator.evaluate(
        metrics=metrics,
        config=config,
        benchmark={"total_return_pct": 5.0, "sharpe_ratio": 1.2},
        elapsed_days=3,
    )
    assert res.can_validate is False
    assert res.is_passed is False
    assert res.is_failed is False
    assert any(v.rule_name == "MINIMUM_DURATION" for v in res.violations)
    assert any(v.rule_name == "MINIMUM_TRADES" for v in res.violations)


def test_incubation_hard_risk_failure():
    """Verify drawdown or risk violation breaches trigger hard incubation failure."""
    evaluator = IncubationPolicyEvaluator()
    config = IncubationConfig(min_duration_days=7, min_trade_count=10, max_drawdown_pct=15.0)

    # Max drawdown was 22.5% (> 15%)
    metrics = IncubationMetrics(
        net_pnl=Decimal("-250.00"),
        total_trades=15,
        max_drawdown_pct=22.5,
        risk_violations=2,
    )
    res = evaluator.evaluate(
        metrics=metrics,
        config=config,
        benchmark={"total_return_pct": 10.0, "sharpe_ratio": 1.5},
        elapsed_days=10,
    )
    assert res.can_validate is True
    assert res.is_failed is True
    assert res.is_passed is False
    critical_rules = {v.rule_name for v in res.violations if v.severity == "CRITICAL"}
    assert "MAXIMUM_DRAWDOWN" in critical_rules


def test_incubation_pass_criteria():
    """Verify successful incubation satisfying all policy hurdles."""
    evaluator = IncubationPolicyEvaluator()
    config = IncubationConfig(min_duration_days=7, min_trade_count=10, max_drawdown_pct=20.0)

    metrics = IncubationMetrics(
        net_pnl=Decimal("350.00"),
        total_return_pct=3.5,
        sharpe_ratio=1.4,
        max_drawdown_pct=4.2,
        win_rate_pct=60.0,
        total_trades=18,
        daily_loss_violations=0,
        risk_violations=0,
        data_quality_score=1.0,
    )
    benchmark = {
        "total_return_pct": 5.0,
        "sharpe_ratio": 1.5,
        "max_drawdown_pct": 6.0,
        "win_rate_pct": 58.0,
        "total_trades": 25,
    }
    res = evaluator.evaluate(
        metrics=metrics,
        config=config,
        benchmark=benchmark,
        elapsed_days=8,
    )
    assert res.can_validate is True
    assert res.is_passed is True
    assert res.is_failed is False
    assert res.benchmark_comparison.return_ratio == 0.7
    assert res.benchmark_comparison.deviation_acceptable is True
