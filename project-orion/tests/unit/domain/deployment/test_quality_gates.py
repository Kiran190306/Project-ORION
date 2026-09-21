"""Unit tests for QualityGateEvaluator and institutional 5-gate policies."""

from __future__ import annotations

from libraries.domain.deployment.models import (
    QualityGateVerdict,
)
from libraries.domain.deployment.quality_gates import (
    QualityGateEvaluator,
    QualityGatePolicy,
)


def test_wfe_gate_evaluation():
    """Verify Walk-Forward Efficiency quality gate across 4 verdicts."""
    evaluator = QualityGateEvaluator(QualityGatePolicy(min_wfe_pct=50.0, min_oos_windows=2))

    # 1. Insufficient data: None or too few windows
    r1 = evaluator.evaluate_wfe_gate(None)
    assert r1.verdict == QualityGateVerdict.INSUFFICIENT_DATA

    r2 = evaluator.evaluate_wfe_gate({"windows": [{"window": 1}], "mean_wfe": 70.0})
    assert r2.verdict == QualityGateVerdict.INSUFFICIENT_DATA

    # 2. Fail: Low WFE or OVERFITTED
    r3 = evaluator.evaluate_wfe_gate({
        "windows": [{"w": 1}, {"w": 2}],
        "mean_wfe": 35.0,
        "robustness_verdict": "OVERFITTED",
    })
    assert r3.verdict == QualityGateVerdict.FAIL

    # 3. Inconclusive: Undefined or marginal MODERATE
    r4 = evaluator.evaluate_wfe_gate({
        "windows": [{"w": 1}, {"w": 2}],
        "mean_wfe": 52.0,
        "robustness_verdict": "MODERATE",
    })
    assert r4.verdict == QualityGateVerdict.INCONCLUSIVE

    # 4. Pass: Robust with high WFE
    r5 = evaluator.evaluate_wfe_gate({
        "windows": [{"w": 1}, {"w": 2}, {"w": 3}],
        "mean_wfe": 75.0,
        "robustness_verdict": "ROBUST",
    })
    assert r5.verdict == QualityGateVerdict.PASS
    assert r5.actual_value == 75.0


def test_regime_gate_evaluation():
    """Verify Market Regime Robustness gate."""
    evaluator = QualityGateEvaluator(QualityGatePolicy(min_regimes_covered=2, min_regime_robustness_score=0.4))

    # 1. Insufficient data: None or only 1 regime active
    r1 = evaluator.evaluate_regime_gate(None)
    assert r1.verdict == QualityGateVerdict.INSUFFICIENT_DATA

    r2 = evaluator.evaluate_regime_gate({
        "regimes": {"TRENDING_BULL": {"trade_count": 10}},
        "robustness_score": 0.8,
    })
    assert r2.verdict == QualityGateVerdict.INSUFFICIENT_DATA

    # 2. Fail: Catastrophic performance in one regime
    r3 = evaluator.evaluate_regime_gate({
        "regimes": {
            "TRENDING_BULL": {"trade_count": 10, "profit_factor": 2.0, "win_rate": 60.0},
            "HIGH_VOLATILITY_CHOP": {"trade_count": 8, "profit_factor": 0.1, "win_rate": 10.0},
        },
        "robustness_score": 0.3,
    })
    assert r3.verdict == QualityGateVerdict.FAIL

    # 3. Pass: Good distribution across regimes
    r4 = evaluator.evaluate_regime_gate({
        "regimes": {
            "TRENDING_BULL": {"trade_count": 10, "profit_factor": 1.8, "win_rate": 55.0},
            "RANGING_LOW_VOL": {"trade_count": 8, "profit_factor": 1.4, "win_rate": 50.0},
        },
        "robustness_score": 0.75,
    })
    assert r4.verdict == QualityGateVerdict.PASS


def test_stability_gate_evaluation():
    """Verify Parameter Stability & Cliff Detection gate."""
    evaluator = QualityGateEvaluator(QualityGatePolicy(min_stability_neighbors=2, min_plateau_stability_score=0.4))

    # 1. Insufficient data: No neighbors
    r1 = evaluator.evaluate_stability_gate({"neighbor_count": 1})
    assert r1.verdict == QualityGateVerdict.INSUFFICIENT_DATA

    # 2. Fail: Cliff detected
    r2 = evaluator.evaluate_stability_gate({
        "neighbor_count": 4,
        "is_cliff": True,
        "plateau_stability_score": 0.3,
    })
    assert r2.verdict == QualityGateVerdict.FAIL
    assert "cliff" in r2.details.lower()

    # 3. Pass: Plateau confirmed
    r3 = evaluator.evaluate_stability_gate({
        "neighbor_count": 4,
        "is_cliff": False,
        "plateau_stability_score": 0.8,
    })
    assert r3.verdict == QualityGateVerdict.PASS


def test_trade_count_gate_evaluation():
    """Verify Statistical Trade Sample gate."""
    evaluator = QualityGateEvaluator(QualityGatePolicy(min_total_trades=15, min_trades_for_evaluation=5))

    # Insufficient data: < 5 trades
    r1 = evaluator.evaluate_trade_count_gate({"total_trades": 3})
    assert r1.verdict == QualityGateVerdict.INSUFFICIENT_DATA

    # Fail: 5 to 14 trades
    r2 = evaluator.evaluate_trade_count_gate({"total_trades": 10})
    assert r2.verdict == QualityGateVerdict.FAIL

    # Inconclusive: Borderline 15-19 trades
    r3 = evaluator.evaluate_trade_count_gate({"total_trades": 16})
    assert r3.verdict == QualityGateVerdict.INCONCLUSIVE

    # Pass: >= 20 trades
    r4 = evaluator.evaluate_trade_count_gate({"total_trades": 25})
    assert r4.verdict == QualityGateVerdict.PASS


def test_sharpe_gate_evaluation():
    """Verify Sharpe Ratio hurdle gate."""
    evaluator = QualityGateEvaluator(QualityGatePolicy(min_sharpe_ratio=0.5, sharpe_borderline_buffer=0.15))

    # Insufficient data
    r1 = evaluator.evaluate_sharpe_gate(None)
    assert r1.verdict == QualityGateVerdict.INSUFFICIENT_DATA

    # Fail: Negative or below 0.5
    r2 = evaluator.evaluate_sharpe_gate({"sharpe_ratio": 0.3})
    assert r2.verdict == QualityGateVerdict.FAIL

    # Inconclusive: Borderline [0.50 .. 0.65]
    r3 = evaluator.evaluate_sharpe_gate({"sharpe_ratio": 0.58})
    assert r3.verdict == QualityGateVerdict.INCONCLUSIVE

    # Pass: Sharpe >= 0.65
    r4 = evaluator.evaluate_sharpe_gate({"sharpe_ratio": 1.45})
    assert r4.verdict == QualityGateVerdict.PASS


def test_evaluate_all_aggregate_report():
    """Verify evaluate_all aggregates all 5 gates."""
    evaluator = QualityGateEvaluator()
    report = evaluator.evaluate_all(
        metrics={"total_trades": 30, "sharpe_ratio": 1.5},
        wfa_result={"windows": [{"w": 1}, {"w": 2}], "mean_wfe": 75.0, "robustness_verdict": "ROBUST"},
        regime_breakdown={
            "regimes": {
                "TRENDING_BULL": {"trade_count": 15, "profit_factor": 1.6, "win_rate": 55.0},
                "RANGING_LOW_VOL": {"trade_count": 15, "profit_factor": 1.3, "win_rate": 50.0},
            },
            "robustness_score": 0.7,
        },
        stability_report={"neighbor_count": 4, "is_cliff": False, "plateau_stability_score": 0.8},
    )
    assert len(report.gate_results) == 5
    assert report.all_passed is True
    assert report.summary_verdict == QualityGateVerdict.PASS
