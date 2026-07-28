"""Initial strategy evaluation boundary; it does not backtest or optimize."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from libraries.domain.ai_research.exceptions import StrategyError
from libraries.domain.ai_research.models import (
    ResearchDataset,
    StrategyCandidate,
    StrategyEvaluation,
)

MetricProvider = Callable[[StrategyCandidate, ResearchDataset], Mapping[str, float]]


class MetadataStrategyEvaluator:
    """Turns evaluator-supplied metrics into a validated domain evaluation.

    This class deliberately never invokes a strategy or a broker.
    A backtesting adapter can inject a ``MetricProvider`` in a later milestone.
    """

    def __init__(self, metric_provider: MetricProvider | None = None) -> None:
        self._metric_provider = metric_provider or self._metadata_metrics

    async def evaluate(
        self, strategy: StrategyCandidate, dataset: ResearchDataset
    ) -> StrategyEvaluation:
        try:
            metrics = self._metric_provider(strategy, dataset)
            return StrategyEvaluation(
                strategy_id=strategy.strategy_id, dataset_id=dataset.dataset_id, metrics=metrics
            )
        except (TypeError, ValueError) as exc:
            raise StrategyError(f"could not evaluate '{strategy.strategy_id}': {exc}") from exc

    @staticmethod
    def _metadata_metrics(strategy: StrategyCandidate, _: ResearchDataset) -> Mapping[str, float]:
        metrics = strategy.metadata.get("metrics")
        if not isinstance(metrics, Mapping):
            raise ValueError("strategy metadata must provide a metrics mapping")
        return metrics


StrategyEvaluator = MetadataStrategyEvaluator
