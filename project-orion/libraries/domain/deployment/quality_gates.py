"""Institutional Quality Gate Evaluation Engine.

Evaluates quantitative candidates across five distinct gates:
1. Walk-Forward Efficiency (WFE)
2. Market Regime Robustness
3. Parameter Stability & Cliff Detection
4. Statistical Sample Trade Count
5. Risk-Adjusted Return (Sharpe Ratio)

Each gate produces an explicit four-state verdict:
- PASS: Objective criteria satisfied under policy.
- FAIL: Criteria violated.
- INCONCLUSIVE: Ambiguous or borderline evidence requiring quant review.
- INSUFFICIENT_DATA: Inadequate sample size/observations — blocks auto-advancement.

CRITICAL INVARIANT:
A gate PASS reflects historical quantitative criteria satisfaction under
the specified policy. It MUST NEVER be interpreted as guaranteed future
profitability. All capital remains strictly at $0.00 (Paper/Incubation only).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from libraries.domain.deployment.models import (
    QualityGateReport,
    QualityGateResult,
    QualityGateType,
    QualityGateVerdict,
)


@dataclass(frozen=True, slots=True)
class QualityGatePolicy:
    """Configurable and versioned institutional policy parameters for quality gates."""

    policy_id: str = "institutional_standard_v1"
    version: str = "1.0.0"
    min_wfe_pct: float = 50.0  # Minimum mean Walk-Forward Efficiency percentage
    min_oos_windows: int = 2  # Minimum OOS windows required for statistical validity
    min_regimes_covered: int = 2  # Minimum distinct market regimes with observations
    min_regime_robustness_score: float = 0.40  # Minimum overall regime score [0..1]
    min_plateau_stability_score: float = 0.40  # Minimum plateau stability [0..1]
    min_stability_neighbors: int = 2  # Minimum adjacent parameter coordinates evaluated
    min_total_trades: int = 15  # Minimum statistical trade sample size
    min_trades_for_evaluation: int = 5  # Below this threshold is INSUFFICIENT_DATA
    min_sharpe_ratio: float = 0.50  # Minimum annualized Sharpe ratio
    sharpe_borderline_buffer: float = 0.15  # Buffer within which Sharpe is INCONCLUSIVE
    max_drawdown_pct: float = 30.0  # Maximum backtest drawdown tolerated
    description: str = (
        "Standard institutional quantitative validation policy for strategy deployment."
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize policy to JSON-safe dictionary."""
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "min_wfe_pct": self.min_wfe_pct,
            "min_oos_windows": self.min_oos_windows,
            "min_regimes_covered": self.min_regimes_covered,
            "min_regime_robustness_score": self.min_regime_robustness_score,
            "min_plateau_stability_score": self.min_plateau_stability_score,
            "min_stability_neighbors": self.min_stability_neighbors,
            "min_total_trades": self.min_total_trades,
            "min_trades_for_evaluation": self.min_trades_for_evaluation,
            "min_sharpe_ratio": self.min_sharpe_ratio,
            "sharpe_borderline_buffer": self.sharpe_borderline_buffer,
            "max_drawdown_pct": self.max_drawdown_pct,
            "description": self.description,
        }


class QualityGateEvaluator:
    """Evaluates optimization/research artifacts against an institutional QualityGatePolicy."""

    def __init__(self, policy: QualityGatePolicy | None = None) -> None:
        self.policy = policy or QualityGatePolicy()

    def evaluate_wfe_gate(
        self,
        wfa_result: dict[str, Any] | None,
    ) -> QualityGateResult:
        """Gate 1: Walk-Forward Efficiency (WFE) & Out-of-Sample Robustness."""
        if not wfa_result:
            return QualityGateResult(
                gate_type=QualityGateType.WFE_THRESHOLD,
                verdict=QualityGateVerdict.INSUFFICIENT_DATA,
                actual_value=None,
                threshold=self.policy.min_wfe_pct,
                details="No Walk-Forward Analysis observations available. WFA required for deployment.",
            )

        windows = wfa_result.get("windows", [])
        if len(windows) < self.policy.min_oos_windows:
            return QualityGateResult(
                gate_type=QualityGateType.WFE_THRESHOLD,
                verdict=QualityGateVerdict.INSUFFICIENT_DATA,
                actual_value=float(len(windows)),
                threshold=float(self.policy.min_oos_windows),
                details=f"Insufficient OOS windows: {len(windows)} < required {self.policy.min_oos_windows}",
            )

        robustness_verdict = str(wfa_result.get("robustness_verdict", "UNDEFINED")).upper()
        mean_wfe = wfa_result.get("mean_wfe")

        if mean_wfe is None or robustness_verdict == "UNDEFINED":
            return QualityGateResult(
                gate_type=QualityGateType.WFE_THRESHOLD,
                verdict=QualityGateVerdict.INCONCLUSIVE,
                actual_value=None,
                threshold=self.policy.min_wfe_pct,
                details="Walk-Forward Efficiency is undefined (non-positive in-sample return)",
            )

        actual_wfe = float(mean_wfe)

        if robustness_verdict == "OVERFITTED" or actual_wfe < self.policy.min_wfe_pct:
            return QualityGateResult(
                gate_type=QualityGateType.WFE_THRESHOLD,
                verdict=QualityGateVerdict.FAIL,
                actual_value=round(actual_wfe, 2),
                threshold=self.policy.min_wfe_pct,
                details=f"WFE {actual_wfe:.1f}% below minimum {self.policy.min_wfe_pct}% or marked OVERFITTED",
            )

        if robustness_verdict == "MODERATE" and actual_wfe < (self.policy.min_wfe_pct + 10.0):
            return QualityGateResult(
                gate_type=QualityGateType.WFE_THRESHOLD,
                verdict=QualityGateVerdict.INCONCLUSIVE,
                actual_value=round(actual_wfe, 2),
                threshold=self.policy.min_wfe_pct,
                details=f"WFE {actual_wfe:.1f}% is marginal with MODERATE robustness rating",
            )

        return QualityGateResult(
            gate_type=QualityGateType.WFE_THRESHOLD,
            verdict=QualityGateVerdict.PASS,
            actual_value=round(actual_wfe, 2),
            threshold=self.policy.min_wfe_pct,
            details=f"Robust Walk-Forward Efficiency of {actual_wfe:.1f}% across {len(windows)} OOS windows",
        )

    def evaluate_regime_gate(
        self,
        regime_breakdown: dict[str, Any] | None,
    ) -> QualityGateResult:
        """Gate 2: Market Regime Robustness across distinct market regimes."""
        if not regime_breakdown:
            return QualityGateResult(
                gate_type=QualityGateType.REGIME_ROBUSTNESS,
                verdict=QualityGateVerdict.INSUFFICIENT_DATA,
                actual_value=None,
                threshold=self.policy.min_regime_robustness_score,
                details="No market regime breakdown data available",
            )

        regimes_data = regime_breakdown.get("regimes", {})
        active_regimes = [
            r for r, data in regimes_data.items()
            if isinstance(data, dict) and data.get("trade_count", 0) > 0
        ]

        if len(active_regimes) < self.policy.min_regimes_covered:
            return QualityGateResult(
                gate_type=QualityGateType.REGIME_ROBUSTNESS,
                verdict=QualityGateVerdict.INSUFFICIENT_DATA,
                actual_value=float(len(active_regimes)),
                threshold=float(self.policy.min_regimes_covered),
                details=f"Insufficient regime coverage: trades occurred in only {len(active_regimes)} regime(s)",
            )

        robustness_score = float(regime_breakdown.get("robustness_score", 0.0))

        # Check for catastrophic regime failure (severe loss in any regime)
        catastrophic_regimes = []
        for r_name, r_stats in regimes_data.items():
            if isinstance(r_stats, dict) and r_stats.get("trade_count", 0) >= 3:
                pnl = float(r_stats.get("profit_factor", 1.0))
                win_rate = float(r_stats.get("win_rate", 50.0))
                if pnl < 0.4 or win_rate < 20.0:
                    catastrophic_regimes.append(r_name)

        if catastrophic_regimes:
            return QualityGateResult(
                gate_type=QualityGateType.REGIME_ROBUSTNESS,
                verdict=QualityGateVerdict.FAIL,
                actual_value=round(robustness_score, 2),
                threshold=self.policy.min_regime_robustness_score,
                details=f"Catastrophic failure in regime(s): {', '.join(catastrophic_regimes)}",
            )

        if robustness_score < self.policy.min_regime_robustness_score:
            return QualityGateResult(
                gate_type=QualityGateType.REGIME_ROBUSTNESS,
                verdict=QualityGateVerdict.FAIL,
                actual_value=round(robustness_score, 2),
                threshold=self.policy.min_regime_robustness_score,
                details=f"Regime robustness score {robustness_score:.2f} below threshold {self.policy.min_regime_robustness_score:.2f}",
            )

        if robustness_score < (self.policy.min_regime_robustness_score + 0.15):
            return QualityGateResult(
                gate_type=QualityGateType.REGIME_ROBUSTNESS,
                verdict=QualityGateVerdict.INCONCLUSIVE,
                actual_value=round(robustness_score, 2),
                threshold=self.policy.min_regime_robustness_score,
                details=f"Marginal regime robustness ({robustness_score:.2f}) across {len(active_regimes)} regimes",
            )

        return QualityGateResult(
            gate_type=QualityGateType.REGIME_ROBUSTNESS,
            verdict=QualityGateVerdict.PASS,
            actual_value=round(robustness_score, 2),
            threshold=self.policy.min_regime_robustness_score,
            details=f"Regime robustness score {robustness_score:.2f} verified across {len(active_regimes)} regimes",
        )

    def evaluate_stability_gate(
        self,
        stability_report: dict[str, Any] | None,
    ) -> QualityGateResult:
        """Gate 3: Parameter Stability & Cliff Detection."""
        if not stability_report:
            return QualityGateResult(
                gate_type=QualityGateType.PARAMETER_STABILITY,
                verdict=QualityGateVerdict.INSUFFICIENT_DATA,
                actual_value=None,
                threshold=self.policy.min_plateau_stability_score,
                details="No parameter stability analysis observations available",
            )

        neighbor_count = int(stability_report.get("neighbor_count", 0))
        if neighbor_count < self.policy.min_stability_neighbors:
            return QualityGateResult(
                gate_type=QualityGateType.PARAMETER_STABILITY,
                verdict=QualityGateVerdict.INSUFFICIENT_DATA,
                actual_value=float(neighbor_count),
                threshold=float(self.policy.min_stability_neighbors),
                details=f"Insufficient adjacent parameter neighbors ({neighbor_count} < {self.policy.min_stability_neighbors})",
            )

        is_cliff = bool(stability_report.get("is_cliff", False))
        plateau_score = float(stability_report.get("plateau_stability_score", 0.0))

        if is_cliff:
            return QualityGateResult(
                gate_type=QualityGateType.PARAMETER_STABILITY,
                verdict=QualityGateVerdict.FAIL,
                actual_value=round(plateau_score, 2),
                threshold=self.policy.min_plateau_stability_score,
                details="Parameter cliff detected: Sharp degradation in performance in adjacent configurations",
            )

        if plateau_score < self.policy.min_plateau_stability_score:
            return QualityGateResult(
                gate_type=QualityGateType.PARAMETER_STABILITY,
                verdict=QualityGateVerdict.FAIL,
                actual_value=round(plateau_score, 2),
                threshold=self.policy.min_plateau_stability_score,
                details=f"Plateau stability score {plateau_score:.2f} below required {self.policy.min_plateau_stability_score:.2f}",
            )

        if plateau_score < (self.policy.min_plateau_stability_score + 0.15):
            return QualityGateResult(
                gate_type=QualityGateType.PARAMETER_STABILITY,
                verdict=QualityGateVerdict.INCONCLUSIVE,
                actual_value=round(plateau_score, 2),
                threshold=self.policy.min_plateau_stability_score,
                details=f"Parameter stability {plateau_score:.2f} is acceptable but near sensitivity threshold",
            )

        return QualityGateResult(
            gate_type=QualityGateType.PARAMETER_STABILITY,
            verdict=QualityGateVerdict.PASS,
            actual_value=round(plateau_score, 2),
            threshold=self.policy.min_plateau_stability_score,
            details=f"Robust parameter plateau confirmed (score: {plateau_score:.2f}, neighbors: {neighbor_count})",
        )

    def evaluate_trade_count_gate(
        self,
        metrics: dict[str, Any] | None,
    ) -> QualityGateResult:
        """Gate 4: Statistical Sample Trade Count."""
        if not metrics or "total_trades" not in metrics:
            return QualityGateResult(
                gate_type=QualityGateType.MINIMUM_TRADES,
                verdict=QualityGateVerdict.INSUFFICIENT_DATA,
                actual_value=None,
                threshold=float(self.policy.min_total_trades),
                details="No backtest execution trade metrics available",
            )

        total_trades = int(metrics.get("total_trades", 0))

        if total_trades < self.policy.min_trades_for_evaluation:
            return QualityGateResult(
                gate_type=QualityGateType.MINIMUM_TRADES,
                verdict=QualityGateVerdict.INSUFFICIENT_DATA,
                actual_value=float(total_trades),
                threshold=float(self.policy.min_total_trades),
                details=f"Insufficient trade sample ({total_trades} trades). Cannot establish statistical relevance.",
            )

        if total_trades < self.policy.min_total_trades:
            return QualityGateResult(
                gate_type=QualityGateType.MINIMUM_TRADES,
                verdict=QualityGateVerdict.FAIL,
                actual_value=float(total_trades),
                threshold=float(self.policy.min_total_trades),
                details=f"Trade count {total_trades} below policy minimum {self.policy.min_total_trades}",
            )

        if total_trades < (self.policy.min_total_trades + 5):
            return QualityGateResult(
                gate_type=QualityGateType.MINIMUM_TRADES,
                verdict=QualityGateVerdict.INCONCLUSIVE,
                actual_value=float(total_trades),
                threshold=float(self.policy.min_total_trades),
                details=f"Trade count {total_trades} marginally meets minimum sample requirement",
            )

        return QualityGateResult(
            gate_type=QualityGateType.MINIMUM_TRADES,
            verdict=QualityGateVerdict.PASS,
            actual_value=float(total_trades),
            threshold=float(self.policy.min_total_trades),
            details=f"Adequate statistical sample size of {total_trades} trades",
        )

    def evaluate_sharpe_gate(
        self,
        metrics: dict[str, Any] | None,
    ) -> QualityGateResult:
        """Gate 5: Risk-Adjusted Return (Sharpe Ratio)."""
        if not metrics or "sharpe_ratio" not in metrics:
            return QualityGateResult(
                gate_type=QualityGateType.MINIMUM_SHARPE,
                verdict=QualityGateVerdict.INSUFFICIENT_DATA,
                actual_value=None,
                threshold=self.policy.min_sharpe_ratio,
                details="No Sharpe ratio metric available in candidate backtest",
            )

        raw_sharpe = metrics.get("sharpe_ratio")
        if raw_sharpe is None:
            return QualityGateResult(
                gate_type=QualityGateType.MINIMUM_SHARPE,
                verdict=QualityGateVerdict.INCONCLUSIVE,
                actual_value=None,
                threshold=self.policy.min_sharpe_ratio,
                details="Sharpe ratio could not be computed (zero volatility)",
            )

        sharpe = float(raw_sharpe)

        if sharpe < self.policy.min_sharpe_ratio:
            return QualityGateResult(
                gate_type=QualityGateType.MINIMUM_SHARPE,
                verdict=QualityGateVerdict.FAIL,
                actual_value=round(sharpe, 2),
                threshold=self.policy.min_sharpe_ratio,
                details=f"Sharpe ratio {sharpe:.2f} below required policy threshold {self.policy.min_sharpe_ratio:.2f}",
            )

        if sharpe < (self.policy.min_sharpe_ratio + self.policy.sharpe_borderline_buffer):
            return QualityGateResult(
                gate_type=QualityGateType.MINIMUM_SHARPE,
                verdict=QualityGateVerdict.INCONCLUSIVE,
                actual_value=round(sharpe, 2),
                threshold=self.policy.min_sharpe_ratio,
                details=f"Sharpe ratio {sharpe:.2f} is within borderline zone [{self.policy.min_sharpe_ratio:.2f} .. {self.policy.min_sharpe_ratio + self.policy.sharpe_borderline_buffer:.2f}]",
            )

        return QualityGateResult(
            gate_type=QualityGateType.MINIMUM_SHARPE,
            verdict=QualityGateVerdict.PASS,
            actual_value=round(sharpe, 2),
            threshold=self.policy.min_sharpe_ratio,
            details=f"Sharpe ratio of {sharpe:.2f} satisfies risk-adjusted return hurdle",
        )

    def evaluate_all(
        self,
        *,
        metrics: dict[str, Any] | None,
        wfa_result: dict[str, Any] | None = None,
        regime_breakdown: dict[str, Any] | None = None,
        stability_report: dict[str, Any] | None = None,
    ) -> QualityGateReport:
        """Evaluate all 5 quality gates and assemble an aggregate QualityGateReport."""
        results = (
            self.evaluate_wfe_gate(wfa_result),
            self.evaluate_regime_gate(regime_breakdown),
            self.evaluate_stability_gate(stability_report),
            self.evaluate_trade_count_gate(metrics),
            self.evaluate_sharpe_gate(metrics),
        )
        return QualityGateReport(gate_results=results)
