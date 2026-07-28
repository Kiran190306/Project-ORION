"""Exception hierarchy for the AI research domain."""


class AIResearchError(Exception):
    """Base error for every AI research operation."""


class ConfigurationError(AIResearchError):
    """Invalid platform configuration or dependency graph."""


class DatasetError(AIResearchError):
    """Invalid or unavailable research dataset."""


class FeatureEngineeringError(AIResearchError):
    """Feature calculation or registration failed."""


class ValidationError(AIResearchError):
    """Validation could not be completed."""


class StrategyError(AIResearchError):
    """Invalid strategy candidate or evaluation."""


class OptimizationError(AIResearchError):
    """Optimization operation failed."""


class ExperimentError(AIResearchError):
    """Experiment lifecycle operation failed."""


class RepositoryError(AIResearchError):
    """Strategy repository operation failed."""


class RankingError(AIResearchError):
    """Strategy ranking operation failed."""


class ParameterSpaceError(AIResearchError):
    """Invalid parameter space definition."""


class FitnessError(AIResearchError):
    """Fitness calculation failed."""


class WalkForwardError(AIResearchError):
    """Walk-forward validation failed."""


class CrossValidationError(AIResearchError):
    """Cross-validation failed."""


class RobustnessError(AIResearchError):
    """Robustness analysis failed."""


class OverfittingError(AIResearchError):
    """Overfitting detection failed."""


class ParameterStabilityError(AIResearchError):
    """Parameter stability analysis failed."""


class ExperimentDatabaseError(AIResearchError):
    """Experiment database operation failed."""


class VersionError(AIResearchError):
    """Version management operation failed."""


class RecommendationError(AIResearchError):
    """Recommendation generation failed."""


class ParallelExecutionError(AIResearchError):
    """Parallel execution operation failed."""


class MarketIntelligenceError(AIResearchError):
    """Market intelligence operation failed."""


class TrendClassificationError(AIResearchError):
    """Trend classification failed."""


class VolatilityClassificationError(AIResearchError):
    """Volatility classification failed."""


class LiquidityClassificationError(AIResearchError):
    """Liquidity classification failed."""


class MarketClassificationError(AIResearchError):
    """Market classification failed."""


class LeaderboardError(AIResearchError):
    """Leaderboard operation failed."""
