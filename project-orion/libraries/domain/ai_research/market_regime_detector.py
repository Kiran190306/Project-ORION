"""Market regime detector — unified market regime detection.

Combines all classifiers to produce a single deterministic MarketRegime
classification. This is the primary entry point for market intelligence.

Consumes historical market data only. No execution logic.
"""

from __future__ import annotations

from libraries.domain.ai_research.exceptions import MarketIntelligenceError
from libraries.domain.ai_research.market_classifier import MarketClassifier
from libraries.domain.ai_research.models import (
    MarketClassificationResult,
    MarketRegime,
    ResearchDataset,
)


class MarketRegimeDetector:
    """Detects the current market regime from historical data.

    Delegates to the MarketClassifier for comprehensive analysis,
    then extracts the primary MarketRegime for downstream use.
    """

    def __init__(self, classifier: MarketClassifier | None = None) -> None:
        self._classifier = classifier or MarketClassifier()

    async def detect(self, dataset: ResearchDataset) -> MarketRegime:
        """Detect the current market regime.

        Args:
            dataset: Historical market data.

        Returns:
            MarketRegime classification.

        Raises:
            MarketIntelligenceError: If classification fails.
        """
        try:
            result = await self._classifier.classify(dataset)
            return result.regime
        except (ValueError, TypeError, RuntimeError) as exc:
            raise MarketIntelligenceError(f"regime detection failed: {exc}") from exc

    async def classify(self, dataset: ResearchDataset) -> MarketClassificationResult:
        """Get the full market classification result.

        Args:
            dataset: Historical market data.

        Returns:
            Complete MarketClassificationResult with all sub-classifications.

        Raises:
            MarketIntelligenceError: If classification fails.
        """
        try:
            return await self._classifier.classify(dataset)
        except (ValueError, TypeError, RuntimeError) as exc:
            raise MarketIntelligenceError(f"market classification failed: {exc}") from exc
