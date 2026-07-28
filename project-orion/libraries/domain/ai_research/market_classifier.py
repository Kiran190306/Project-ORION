"""Market classifier — aggregates all classifiers into a unified market view.

Combines trend, volatility, and liquidity classifications into a single
comprehensive MarketClassificationResult.

Consumes historical market data only. No execution logic.
"""

from __future__ import annotations

from libraries.domain.ai_research.exceptions import (
    AIResearchError,
    MarketClassificationError,
    MarketIntelligenceError,
)
from libraries.domain.ai_research.liquidity_classifier import LiquidityClassifier
from libraries.domain.ai_research.models import (
    LiquidityClassificationResult,
    MarketClassificationResult,
    MarketCondition,
    MarketRegime,
    ResearchDataset,
    TrendClassificationResult,
    VolatilityClassificationResult,
)
from libraries.domain.ai_research.trend_classifier import TrendClassifier
from libraries.domain.ai_research.volatility_classifier import VolatilityClassifier


class MarketClassifier:
    """Aggregates trend, volatility, and liquidity classifiers.

    Produces a unified MarketClassificationResult with:
    - MarketCondition (BULL, BEAR, SIDEWAYS, HIGH_VOLATILITY, MIXED, etc.)
    - MarketRegime (TRENDING, RANGING, HIGH_VOLATILITY, LOW_LIQUIDITY)
    - Individual classification results from each sub-classifier
    """

    def __init__(
        self,
        trend_classifier: TrendClassifier | None = None,
        volatility_classifier: VolatilityClassifier | None = None,
        liquidity_classifier: LiquidityClassifier | None = None,
    ) -> None:
        self._trend = trend_classifier or TrendClassifier()
        self._volatility = volatility_classifier or VolatilityClassifier()
        self._liquidity = liquidity_classifier or LiquidityClassifier()

    async def classify(self, dataset: ResearchDataset) -> MarketClassificationResult:
        """Perform comprehensive market classification.

        Args:
            dataset: Historical market data.

        Returns:
            MarketClassificationResult with unified classification.

        Raises:
            MarketClassificationError: If any sub-classifier fails.
        """
        try:
            trend_result = await self._trend.classify(dataset)
            volatility_result = await self._volatility.classify(dataset)
            liquidity_result = await self._liquidity.classify(dataset)
        except MarketIntelligenceError:
            raise
        except AIResearchError as exc:
            raise MarketClassificationError(f"classification failed: {exc}") from exc
        except (ValueError, TypeError, RuntimeError) as exc:
            raise MarketClassificationError(f"classification failed: {exc}") from exc

        # Determine unified regime
        regime = self._resolve_regime(trend_result, volatility_result, liquidity_result)

        # Determine market condition
        condition = self._resolve_condition(trend_result, volatility_result, liquidity_result)

        # Confidence is average of sub-classifier confidence indicators
        confidence = (
            trend_result.strength
            + (1.0 - abs(volatility_result.percentile - 0.5) * 2.0)
            + liquidity_result.score
        ) / 3.0
        confidence = max(0.0, min(1.0, confidence))

        return MarketClassificationResult(
            condition=condition,
            regime=regime,
            trend=trend_result,
            volatility=volatility_result,
            liquidity=liquidity_result,
            confidence=round(confidence, 4),
        )

    @staticmethod
    def _resolve_regime(
        trend: TrendClassificationResult,
        volatility: VolatilityClassificationResult,
        liquidity: LiquidityClassificationResult,
    ) -> MarketRegime:
        if trend.direction.value in ("bull", "bear") and volatility.level.value == "normal":
            return MarketRegime.TRENDING
        if volatility.level.value == "high":
            return MarketRegime.HIGH_VOLATILITY
        if liquidity.level.value == "low":
            return MarketRegime.LOW_LIQUIDITY
        if trend.direction.value == "sideways" and volatility.level.value == "low":
            return MarketRegime.RANGING
        return MarketRegime.UNKNOWN

    @staticmethod
    def _resolve_condition(
        trend: TrendClassificationResult,
        volatility: VolatilityClassificationResult,
        liquidity: LiquidityClassificationResult,
    ) -> MarketCondition:
        # Check for mixed conditions first
        conditions = []
        if trend.direction.value in ("bull", "bear"):
            conditions.append(trend.direction.value)
        if volatility.level.value == "high":
            conditions.append("high_volatility")
        if volatility.level.value == "low":
            conditions.append("low_volatility")
        if liquidity.level.value == "high":
            conditions.append("high_liquidity")
        if liquidity.level.value == "low":
            conditions.append("low_liquidity")

        if len(conditions) > 1:
            return MarketCondition.MIXED

        # Single condition
        if trend.direction.value == "bull":
            return MarketCondition.BULL
        if trend.direction.value == "bear":
            return MarketCondition.BEAR
        if trend.direction.value == "sideways":
            return MarketCondition.SIDEWAYS
        if volatility.level.value == "high":
            return MarketCondition.HIGH_VOLATILITY
        if volatility.level.value == "low":
            return MarketCondition.LOW_VOLATILITY
        if liquidity.level.value == "high":
            return MarketCondition.HIGH_LIQUIDITY
        if liquidity.level.value == "low":
            return MarketCondition.LOW_LIQUIDITY
        return MarketCondition.UNKNOWN
