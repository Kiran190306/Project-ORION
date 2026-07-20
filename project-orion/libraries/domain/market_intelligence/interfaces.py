"""Protocol/port definitions for the Market Intelligence engine."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from libraries.domain.market_intelligence.models import (
    AggregatedProviderData,
    LatencySnapshot,
    ProviderTickData,
)


@runtime_checkable
class ProviderHealthPort(Protocol):
    """Port for querying provider health status."""

    async def is_provider_healthy(self, provider: str) -> bool:
        """Return whether a provider is currently healthy."""
        ...

    async def get_provider_uptime(self, provider: str) -> float:
        """Return provider uptime in seconds."""
        ...

    async def get_connected_providers(self) -> set[str]:
        """Return the set of currently connected providers."""
        ...


@runtime_checkable
class ProviderLatencyTracker(Protocol):
    """Port for recording and querying provider latency."""

    async def record_latency(self, provider: str, latency_ms: float) -> None:
        """Record a latency measurement for a provider."""
        ...

    async def get_latency_snapshot(self, provider: str) -> LatencySnapshot:
        """Return latency statistics for a provider."""
        ...


@runtime_checkable
class IntelligenceSink(Protocol):
    """Consumer of market intelligence output."""

    async def on_aggregated_data(self, data: AggregatedProviderData) -> None:
        """Called when new aggregated data is available."""
        ...


@runtime_checkable
class ConsensusHandler(Protocol):
    """Handler for consensus price updates."""

    async def on_consensus_update(self, symbol: str, consensus: Any) -> None:
        """Called when a new consensus price is produced."""
        ...


@runtime_checkable
class AnomalyHandler(Protocol):
    """Handler for detected anomalies."""

    async def on_anomaly_detected(self, symbol: str, anomaly: Any) -> None:
        """Called when an anomaly is detected."""
        ...


@runtime_checkable
class FailoverHandler(Protocol):
    """Handler for provider failover decisions."""

    async def on_failover(self, symbol: str, decision: Any) -> None:
        """Called when a failover decision is made."""
        ...
