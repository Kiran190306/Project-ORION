"""Data models for the strategy framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class StrategyPriority(StrEnum):
    """Priority levels for strategy execution ordering."""

    LOWEST = "lowest"
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def numeric(self) -> int:
        mapping = {
            StrategyPriority.LOWEST: 0,
            StrategyPriority.LOW: 1,
            StrategyPriority.NORMAL: 2,
            StrategyPriority.HIGH: 3,
            StrategyPriority.CRITICAL: 4,
        }
        return mapping[self]


class StrategyStatus(StrEnum):
    """Operational status of a strategy."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    """Configuration for a strategy instance."""

    priority: StrategyPriority = StrategyPriority.NORMAL
    enabled: bool = True
    max_confidence: float = 100.0
    min_confidence: float = 0.0
    params: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
