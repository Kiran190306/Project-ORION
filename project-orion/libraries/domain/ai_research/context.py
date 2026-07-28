"""Immutable request context for one deterministic research run."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from libraries.domain.ai_research.models import (
    FeatureDefinition,
    ResearchDataset,
    ResearchPlatformConfig,
    StrategyCandidate,
)

# ─── Backward-compatible aliases ─────────────────────────────────────────
AIResearchContext = "ResearchContext"


@dataclass(frozen=True, slots=True)
class ResearchContext:
    """All domain inputs required by the research engine."""

    dataset: ResearchDataset
    configuration: ResearchPlatformConfig
    strategies: tuple[StrategyCandidate, ...]
    feature_definitions: tuple[FeatureDefinition, ...] = ()
    experiment_metadata: Mapping[str, Any] = field(default_factory=dict)
    random_seed: int | None = None
    execution_mode: str | None = None

    def __post_init__(self) -> None:
        if not self.strategies:
            raise ValueError("strategies must not be empty")
        if len({strategy.strategy_id for strategy in self.strategies}) != len(self.strategies):
            raise ValueError("strategy identifiers must be unique")
        seed = self.configuration.random_seed if self.random_seed is None else self.random_seed
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("random_seed must be an integer")
        mode = (
            self.configuration.execution_mode
            if self.execution_mode is None
            else self.execution_mode
        )
        if mode not in {"research", "dry_run"}:
            raise ValueError("execution_mode must be 'research' or 'dry_run'")
        object.__setattr__(self, "random_seed", seed)
        object.__setattr__(self, "execution_mode", mode)
        object.__setattr__(
            self, "experiment_metadata", MappingProxyType(dict(self.experiment_metadata))
        )
