"""Quantitative Research: Overfitting Safeguards and Statistical Advisory Guard.

Emits factual research warnings about sample size limitations, excessive in-sample
performance anomalies, parameter sensitivity, and regime duration.
"""

from __future__ import annotations

from libraries.domain.research.models import (
    ResearchPerformanceMetrics,
    ResearchWarning,
    WarningSeverity,
)


class OverfittingGuard:
    """Evaluates backtest results and emits objective statistical caveats."""

    @staticmethod
    def evaluate(
        metrics: ResearchPerformanceMetrics,
        duration_days: float = 30.0,
        parameter_count: int = 2,
    ) -> list[ResearchWarning]:
        """Generate factual research warnings based on statistical properties."""
        warnings: list[ResearchWarning] = []

        # 1. Sample Size Check
        if metrics.total_trades < 30:
            warnings.append(
                ResearchWarning(
                    code="SMALL_SAMPLE_SIZE",
                    title="Small Trade Sample Size",
                    description=(
                        f"Backtest produced only {metrics.total_trades} trades. "
                        "Statistical validity typically requires at least 30 closed trades "
                        "to mitigate small-sample estimation variance."
                    ),
                    severity=WarningSeverity.WARNING,
                )
            )

        # 2. Performance Anomaly / Overfitting Check
        if metrics.sharpe_ratio > 4.0 or metrics.win_rate_pct > 85.0:
            warnings.append(
                ResearchWarning(
                    code="UNREALISTIC_PERFORMANCE",
                    title="Potential Curve Fitting Anomaly",
                    description=(
                        f"Sharpe ratio ({metrics.sharpe_ratio:.2f}) or win rate ({metrics.win_rate_pct:.1f}%) "
                        "is exceptionally high. In institutional research, this frequently signals "
                        "overfitting to historical data or extreme parameter sensitivity."
                    ),
                    severity=WarningSeverity.CRITICAL,
                )
            )

        # 3. Short Historical Window
        if duration_days < 30.0:
            warnings.append(
                ResearchWarning(
                    code="SHORT_TEST_HORIZON",
                    title="Limited Historical Horizon",
                    description=(
                        f"Backtest period spans only {duration_days:.1f} calendar days. "
                        "Short windows fail to evaluate strategy robustness across different "
                        "macro regimes, trending and ranging cycles, or liquidity shocks."
                    ),
                    severity=WarningSeverity.WARNING,
                )
            )

        # 4. Severe Drawdown
        if metrics.max_drawdown_pct > 25.0:
            warnings.append(
                ResearchWarning(
                    code="HIGH_DRAWDOWN",
                    title="Elevated Capital Drawdown",
                    description=(
                        f"Maximum simulated drawdown reached {metrics.max_drawdown_pct:.1f}%, "
                        "exceeding standard institutional risk budgets (typically 10-20%)."
                    ),
                    severity=WarningSeverity.WARNING,
                )
            )

        # 5. Parameter Count Density
        if parameter_count >= 6:
            warnings.append(
                ResearchWarning(
                    code="PARAMETER_DENSITY",
                    title="High Parameter Dimension",
                    description=(
                        f"Strategy configuration involves {parameter_count} distinct parameters. "
                        "High degrees of freedom increase susceptibility to selection bias."
                    ),
                    severity=WarningSeverity.INFO,
                )
            )

        return warnings
