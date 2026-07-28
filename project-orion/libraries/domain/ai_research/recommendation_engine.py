"""Recommendation engine for AI research strategies.

Generates recommendations only — NEVER executes trades or communicates with brokers.
"""

from __future__ import annotations

from libraries.domain.ai_research.exceptions import RecommendationError
from libraries.domain.ai_research.models import (
    LeaderboardEntry,
    MarketRegime,
    Recommendation,
    RecommendationAction,
    ValidationResult,
)


class RecommendationEngine:
    """Generates actionable recommendations for strategies.

    Rules:
    - High confidence: Sharpe > 2.0, drawdown < 10%, profit factor > 2.0
    - Accept: Sharpe > 1.0, drawdown < 20%, profit factor > 1.5
    - Promising: Sharpe > 0.5, reasonable metrics
    - Overfit risk: High Sharpe but low robustness
    - Needs more data: Insufficient evaluation history
    - Low confidence: Below thresholds
    - Reject: Negative Sharpe, high drawdown, poor metrics
    """

    async def recommend(
        self,
        entry: LeaderboardEntry,
        regime: MarketRegime = MarketRegime.UNKNOWN,
        validation_result: ValidationResult | None = None,
    ) -> Recommendation:
        """Generate a recommendation for a leaderboard entry.

        Args:
            entry: Leaderboard entry with evaluation metrics.
            regime: Current market regime (optional).
            validation_result: Validation result (optional).

        Returns:
            Recommendation with action, rationale, reason_codes, supporting_metrics.

        Raises:
            RecommendationError: If evaluation has no metrics.
        """
        evaluation = entry.evaluation
        if not evaluation.metrics:
            raise RecommendationError("evaluation has no metrics to base recommendation on")

        metrics = evaluation.metrics
        sharpe = metrics.get("sharpe", metrics.get("sharpe_ratio", 0.0))
        drawdown = abs(metrics.get("drawdown", metrics.get("max_drawdown", 0.0)))
        profit_factor = metrics.get("profit_factor", 0.0)
        win_rate = metrics.get("win_rate", 0.0)
        normalized_win_rate = win_rate / 100.0 if win_rate > 1.0 else win_rate

        # Determine action and reason codes
        action: RecommendationAction
        confidence: float
        rationale: str
        reason_codes: list[str] = []

        # Check rejection criteria first
        if sharpe <= 0:
            action = RecommendationAction.REJECT
            confidence = 0.1
            rationale = f"Negative or zero Sharpe ratio ({sharpe:.2f})"
            reason_codes = ["NEGATIVE_SHARPE"]
        elif drawdown > 30.0:
            action = RecommendationAction.REJECT
            confidence = 0.1
            rationale = f"Excessive drawdown ({drawdown:.1f}%)"
            reason_codes = ["EXCESSIVE_DRAWDOWN"]
        elif sharpe > 2.0 and drawdown < 10.0 and profit_factor > 2.0:
            action = RecommendationAction.HIGH_CONFIDENCE
            confidence = 0.9
            rationale = (
                f"Exceptional metrics: Sharpe={sharpe:.2f}, "
                f"Drawdown={drawdown:.1f}%, ProfitFactor={profit_factor:.2f}"
            )
            reason_codes = ["HIGH_SHARPE", "LOW_DRAWDOWN", "HIGH_PROFIT_FACTOR"]
        elif sharpe > 1.0 and drawdown < 20.0 and profit_factor > 1.5:
            action = RecommendationAction.ACCEPT
            confidence = 0.7
            rationale = f"Strong performance: Sharpe={sharpe:.2f}, ProfitFactor={profit_factor:.2f}"
            reason_codes = ["GOOD_SHARPE", "GOOD_PROFIT_FACTOR"]
        elif sharpe > 2.0 and drawdown > 20.0:
            action = RecommendationAction.OVERFIT_RISK
            confidence = 0.4
            rationale = (
                f"High Sharpe ({sharpe:.2f}) but significant drawdown ({drawdown:.1f}%)"
                f" -- possible overfitting"
            )
            reason_codes = ["HIGH_SHARPE", "HIGH_DRAWDOWN", "POSSIBLE_OVERFIT"]
        elif sharpe > 0.5 and normalized_win_rate > 0.4:
            action = RecommendationAction.PROMISING
            confidence = 0.5
            rationale = f"Promising metrics: Sharpe={sharpe:.2f}, WinRate={normalized_win_rate:.1%}"
            reason_codes = ["MODERATE_SHARPE", "REASONABLE_WIN_RATE"]
        else:
            action = RecommendationAction.LOW_CONFIDENCE
            confidence = 0.3
            rationale = (
                f"Below thresholds: Sharpe={sharpe:.2f}, "
                f"Drawdown={drawdown:.1f}%, ProfitFactor={profit_factor:.2f}"
            )
            reason_codes = ["BELOW_THRESHOLDS"]

        # Adjust for validation
        validation_summary = ""
        if validation_result is not None:
            if not validation_result.is_valid:
                action = RecommendationAction.REJECT
                confidence = 0.05
                rationale = f"Failed validation: {', '.join(validation_result.reasons)}"
                reason_codes = ["VALIDATION_FAILED"]
                validation_summary = "; ".join(validation_result.reasons)
            else:
                validation_summary = "Validation passed"
                reason_codes.append("VALIDATION_PASSED")

        # Adjust for regime constraint
        if regime == MarketRegime.HIGH_VOLATILITY and drawdown > 15.0:
            confidence *= 0.5
            rationale += " (caution: high volatility regime)"
            reason_codes.append("HIGH_VOLATILITY_CAUTION")

        # Check for insufficient sample
        total_trades = metrics.get("total_trades", 0)
        if total_trades < 30:
            action = RecommendationAction.INSUFFICIENT_SAMPLE
            confidence = 0.2
            rationale = f"Insufficient trade sample: {int(total_trades)} trades (minimum 30)"
            reason_codes = ["INSUFFICIENT_SAMPLE"]

        supporting_metrics = {
            "sharpe": round(sharpe, 4),
            "drawdown": round(drawdown, 4),
            "profit_factor": round(profit_factor, 4),
            "win_rate": round(normalized_win_rate, 4),
            "total_trades": float(total_trades),
        }

        return Recommendation(
            strategy_id=evaluation.strategy_id,
            rationale=rationale,
            confidence=min(1.0, max(0.0, confidence)),
            regime=regime,
            action=action,
            reason_codes=tuple(reason_codes),
            supporting_metrics=supporting_metrics,
            validation_summary=validation_summary,
        )
