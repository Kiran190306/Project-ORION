"""Parameter stability analysis for AI research strategies.

Analyzes how stable strategy parameters are across different walk-forward windows.
Does NOT execute trades or communicate with brokers.
"""

from __future__ import annotations

from statistics import stdev

from libraries.domain.ai_research.exceptions import ParameterStabilityError
from libraries.domain.ai_research.models import (
    ParameterStabilityReport,
    WalkForwardResult,
)


class ParameterStabilityAnalyzer:
    """Analyzes parameter stability across walk-forward windows.

    A high stability score (close to 1.0) indicates that the strategy's
    optimal parameters are consistent across different market regimes.
    A low stability score indicates parameter sensitivity.
    """

    async def analyze(
        self,
        walk_forward_result: WalkForwardResult,
    ) -> ParameterStabilityReport:
        """Analyze parameter stability from walk-forward windows.

        Args:
            walk_forward_result: Walk-forward validation result.

        Returns:
            ParameterStabilityReport with stability score.

        Raises:
            ParameterStabilityError: If there are no windows to analyze.
        """
        if not walk_forward_result.windows:
            raise ParameterStabilityError("no walk-forward windows to analyze")

        # For each metric, compute the coefficient of variation across windows
        metric_names = set()
        for window in walk_forward_result.windows:
            metric_names.update(window.test_metrics.keys())

        parameter_std: dict[str, float] = {}
        stability_scores: list[float] = []

        for metric_name in sorted(metric_names):
            values = [
                window.test_metrics.get(metric_name, 0.0) for window in walk_forward_result.windows
            ]
            if len(values) > 1:
                mean_val = sum(values) / len(values)
                if abs(mean_val) > 0.0001:
                    try:
                        std_val = stdev(values)
                        cv = std_val / abs(mean_val)
                        stability = max(0.0, min(1.0, 1.0 - cv))
                        parameter_std[metric_name] = std_val
                        stability_scores.append(stability)
                    except Exception:
                        parameter_std[metric_name] = 0.0
                        stability_scores.append(1.0)
                else:
                    # Mean near zero - use absolute values instead
                    abs_values = [abs(v) for v in values]
                    mean_abs = sum(abs_values) / len(abs_values)
                    if mean_abs > 0.0001:
                        try:
                            std_val = stdev(values)
                            cv = std_val / mean_abs
                            stability = max(0.0, min(1.0, 1.0 - cv))
                            parameter_std[metric_name] = std_val
                            stability_scores.append(stability)
                        except Exception:
                            parameter_std[metric_name] = 0.0
                            stability_scores.append(1.0)
                    else:
                        parameter_std[metric_name] = 0.0
                        stability_scores.append(1.0)
            else:
                parameter_std[metric_name] = 0.0
                stability_scores.append(1.0)

        composite_stability = (
            sum(stability_scores) / len(stability_scores) if stability_scores else 1.0
        )
        composite_stability = max(0.0, min(1.0, composite_stability))

        return ParameterStabilityReport(
            strategy_id="unknown",
            stability_score=composite_stability,
            parameter_std=parameter_std,
        )
