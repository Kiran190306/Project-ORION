"""Reference strategy implementations for the Strategy Abstraction Layer.

These are deterministic example strategies for demonstration and testing.
They contain no broker logic, API calls, or infrastructure code.
"""

from __future__ import annotations

from libraries.domain.strategy.strategies.breakout import BreakoutStrategy
from libraries.domain.strategy.strategies.mean_reversion import MeanReversionStrategy
from libraries.domain.strategy.strategies.momentum import MomentumStrategy
from libraries.domain.strategy.strategies.trend_following import TrendFollowingStrategy

__all__ = [
    "BreakoutStrategy",
    "MeanReversionStrategy",
    "MomentumStrategy",
    "TrendFollowingStrategy",
]