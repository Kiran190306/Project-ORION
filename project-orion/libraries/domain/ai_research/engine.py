"""Pure orchestration engine for the AI Research Platform.

The engine coordinates the research pipeline only.
It does NOT perform calculations, optimization, or broker communication.
"""

from __future__ import annotations

from datetime import datetime, timezone

from libraries.domain.ai_research.context import ResearchContext
from libraries.domain.ai_research.exceptions import AIResearchError, ExperimentError
from libraries.domain.ai_research.models import (
    Experiment,
    ExperimentResult,
    ExperimentStatus,
    LeaderboardEntry,
    ResearchResult,
    StrategyEvaluation,
    ValidationResult,
)


class AIResearchEngine:
    """Pure orchestrator for AI research workflows.

    Responsibilities:
        - Load dataset from context
        - Invoke feature engineering
        - Evaluate each strategy
        - Validate each evaluation
        - Rank evaluated strategies
        - Store experiment result
        - Return ResearchResult

    Every external dependency is injected through the constructor.
    No calculations, optimization algorithms, or broker communication.
    """

    def __init__(
        self,
        feature_engineer=None,
        strategy_evaluator=None,
        strategy_ranker=None,
        validation_engine=None,
        experiment_tracker=None,
        strategy_repository=None,
        dataset_builder=None,
    ) -> None:
        self._feature_engineer = feature_engineer
        self._strategy_evaluator = strategy_evaluator
        self._strategy_ranker = strategy_ranker
        self._validation_engine = validation_engine
        self._experiment_tracker = experiment_tracker
        self._strategy_repository = strategy_repository
        self._dataset_builder = dataset_builder

    @property
    def feature_engineer(self):
        return self._feature_engineer

    @property
    def strategy_evaluator(self):
        return self._strategy_evaluator

    @property
    def strategy_ranker(self):
        return self._strategy_ranker

    @property
    def validation_engine(self):
        return self._validation_engine

    @property
    def experiment_tracker(self):
        return self._experiment_tracker

    @property
    def strategy_repository(self):
        return self._strategy_repository

    @property
    def dataset_builder(self):
        return self._dataset_builder

    async def run(self, context: ResearchContext) -> ResearchResult:
        """Execute one deterministic research run.

        Pipeline:
            1. (Optional) Build dataset via dataset_builder
            2. (Optional) Engineer feature vectors
            3. Evaluate each strategy
            4. (Optional) Validate each evaluation
            5. Rank strategies
            6. (Optional) Persist experiment
            7. Return ResearchResult
        """
        dataset = context.dataset

        # Step 2: Feature engineering
        feature_vectors = None
        if self._feature_engineer is not None and context.feature_definitions:
            feature_vectors = await self._feature_engineer.engineer(
                dataset, context.feature_definitions
            )

        # Step 3: Evaluate each strategy
        evaluations: list[StrategyEvaluation] = []
        for strategy in context.strategies:
            evaluation = await self._strategy_evaluator.evaluate(strategy, dataset)
            evaluations.append(evaluation)

        # Step 4: Validate
        validation_results: dict[str, ValidationResult] = {}
        if self._validation_engine is not None:
            for evaluation in evaluations:
                strategy = await self._strategy_repository.get_by_id(evaluation.strategy_id)
                if strategy is not None:
                    validation = await self._validation_engine.validate(strategy, evaluation)
                    validation_results[evaluation.strategy_id] = validation

        # Step 5: Rank
        leaderboard = await self._strategy_ranker.rank(evaluations)

        # Step 6: Persist experiment
        experiment_result = None
        if self._experiment_tracker is not None:
            experiment = Experiment(
                experiment_id=_generate_experiment_id(),
                name="research-run",
                version=context.configuration.version,
                metadata=dict(context.experiment_metadata),
            )
            await self._experiment_tracker.create(experiment)
            try:
                experiment_result = ExperimentResult(
                    experiment_id=experiment.experiment_id,
                    status=ExperimentStatus.COMPLETED,
                )
                await self._experiment_tracker.finish(experiment_result)
            except Exception as exc:
                await self._experiment_tracker.update_status(
                    experiment.experiment_id, ExperimentStatus.FAILED
                )
                raise ExperimentError(f"experiment tracking failed: {exc}") from exc

        # Step 7: Return result
        return ResearchResult(
            dataset_id=dataset.dataset_id,
            evaluations=tuple(evaluations),
            leaderboard=leaderboard,
            experiment=experiment_result,
        )

    async def run_single(
        self,
        context: ResearchContext,
        strategy_id: str,
    ) -> StrategyEvaluation | None:
        """Evaluate a single strategy by ID.

        Args:
            context: Research context.
            strategy_id: Strategy identifier.

        Returns:
            Evaluation result, or None if strategy not found.
        """
        strategy = next(
            (s for s in context.strategies if s.strategy_id == strategy_id),
            None,
        )
        if strategy is None:
            return None
        return await self._strategy_evaluator.evaluate(strategy, context.dataset)


def _generate_experiment_id() -> str:
    """Generate a deterministic experiment ID based on current UTC timestamp."""
    return f"exp-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
