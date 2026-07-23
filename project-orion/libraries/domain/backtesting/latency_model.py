"""Latency (broker delay) models for backtesting execution simulation.

Simulates broker/network delays in order transmission and confirmation.
Supports fixed, random, and distribution-based latency models.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class LatencyModelConfig:
    """Configuration for the latency model."""

    base_latency_ms: float = 50.0  # Base round-trip latency in ms
    jitter_ms: float = 20.0  # Random jitter in ms
    min_latency_ms: float = 10.0
    max_latency_ms: float = 500.0
    use_jitter: bool = True
    random_seed: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class LatencyModel:
    """Simulates broker/network latency.

    Thread-safe — uses instance-local random state.
    """

    def __init__(self, config: LatencyModelConfig | None = None) -> None:
        """Initialize latency model.

        Args:
            config: Latency configuration. Uses defaults if None.
        """
        self._config = config or LatencyModelConfig()
        self._random = random.Random(self._config.random_seed)

    @property
    def config(self) -> LatencyModelConfig:
        """Return the current configuration."""
        return self._config

    def calculate_latency_ms(
        self,
        order_type: str = "market",
        volume: float = 0.0,
    ) -> float:
        """Calculate simulated latency in milliseconds.

        Args:
            order_type: Type of order (market, limit, stop).
            volume: Order volume.

        Returns:
            Simulated latency in milliseconds.
        """
        cfg = self._config
        latency = cfg.base_latency_ms

        if cfg.use_jitter:
            jitter = self._random.uniform(-cfg.jitter_ms, cfg.jitter_ms)
            latency += jitter

        # Market orders typically execute faster than limit orders
        if order_type.lower() == "limit":
            latency *= 1.5
        elif order_type.lower() == "stop":
            latency *= 1.3

        # Larger orders may take longer
        if volume > 10.0:
            latency *= 1.0 + (volume - 10.0) * 0.02

        # Clamp to min/max
        if latency < cfg.min_latency_ms:
            latency = cfg.min_latency_ms
        if latency > cfg.max_latency_ms:
            latency = cfg.max_latency_ms

        return round(latency, 1)

    def calculate_confirmation_delay_ms(
        self,
        latency_ms: float | None = None,
    ) -> float:
        """Calculate order confirmation delay.

        Args:
            latency_ms: Optional known latency. Calculated if None.

        Returns:
            Confirmation delay in milliseconds.
        """
        if latency_ms is None:
            latency_ms = self.calculate_latency_ms()
        # Confirmation is typically 1-2x the round-trip latency
        return latency_ms * self._random.uniform(1.0, 2.0)
