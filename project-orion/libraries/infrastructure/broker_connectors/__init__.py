"""Broker Connector layer (EPIC-005 Sprint-2).

This package provides infrastructure implementations for broker connectivity
and transport/retry/health/metrics concerns.

Domain remains broker-agnostic; domain logic lives under libraries/domain.
"""

from __future__ import annotations

from libraries.infrastructure.broker_connectors.base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorError,
    LoggerLike,
)
from libraries.infrastructure.broker_connectors.connector_manager import (
    ConnectorManager,
    ConnectorManagerResult,
)
from libraries.infrastructure.broker_connectors.connectors import (
    BinanceConnector,
    MT5Connector,
    OANDAConnector,
)
from libraries.infrastructure.broker_connectors.factory import (
    ConnectorFactory,
    ConnectorSpec,
)
from libraries.infrastructure.broker_connectors.health import ConnectorHealth
from libraries.infrastructure.broker_connectors.metrics import (
    MetricSample,
    MetricsCollector,
    NullMetricsCollector,
    RecordingMetricsCollector,
)
from libraries.infrastructure.broker_connectors.parsers import (
    TickParseResult,
    parse_generic_bid_ask_tick,
    parse_provider_dict_tick,
)
from libraries.infrastructure.broker_connectors.retry import (
    RetryError,
    RetryPolicy,
    retry_async,
)
from libraries.infrastructure.broker_connectors.transports import (
    AbstractTransport,
    RESTPollingTransport,
    TransportConnectionError,
    TransportMessage,
    WebSocketTransport,
)

__all__ = [
    "AbstractTransport",
    "BaseConnector",
    "BinanceConnector",
    "ConnectorConfig",
    "ConnectorError",
    "ConnectorFactory",
    "ConnectorHealth",
    "ConnectorManager",
    "ConnectorManagerResult",
    "ConnectorSpec",
    "LoggerLike",
    "MT5Connector",
    "MetricSample",
    "MetricsCollector",
    "NullMetricsCollector",
    "OANDAConnector",
    "RESTPollingTransport",
    "RecordingMetricsCollector",
    "RetryError",
    "RetryPolicy",
    "TickParseResult",
    "TransportConnectionError",
    "TransportMessage",
    "WebSocketTransport",
    "parse_generic_bid_ask_tick",
    "parse_provider_dict_tick",
    "retry_async",
]
