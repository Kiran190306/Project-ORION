"""Indicator context for passing state during calculations.

Provides a thread-safe, dependency-injected context for indicator
calculations with access to market data, settings, and other indicators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IndicatorContext:
    """Context for indicator execution.

    Provides access to:
    - Market data (price, volume)
    - Other indicator values (for derived indicators)
    - Configuration overrides
    - Execution metadata
    """

    symbol: str = ""
    timeframe: str = ""
    indicators: dict[str, Any] = field(default_factory=dict)
    config_overrides: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_indicator(self, name: str) -> Any:
        return self.indicators.get(name)

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.config_overrides.get(key, default)
