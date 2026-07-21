"""Tests for the Indicator Pipeline."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.indicators.cache import IndicatorCache
from libraries.domain.indicators.ema import EMA
from libraries.domain.indicators.manager import IndicatorManager
from libraries.domain.indicators.models import Bar
from libraries.domain.indicators.pipeline import (
    IndicatorPipeline,
    IndicatorPipelineConfig,
    PipelineNode,
)
from libraries.domain.indicators.registry import IndicatorRegistry
from libraries.domain.indicators.rsi import RSI
from libraries.domain.indicators.statistics import IndicatorStatistics


@pytest.fixture
def registry() -> IndicatorRegistry:
    return IndicatorRegistry()


@pytest.fixture
def manager(registry: IndicatorRegistry) -> IndicatorManager:
    return IndicatorManager(registry=registry)


@pytest.fixture
def cache() -> IndicatorCache:
    return IndicatorCache()


@pytest.fixture
def pipeline(manager: IndicatorManager, cache: IndicatorCache) -> IndicatorPipeline:
    return IndicatorPipeline(
        manager=manager,
        cache=cache,
        config=IndicatorPipelineConfig(max_concurrency=2),
    )


@pytest.fixture
def bar() -> Bar:
    return Bar(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=1000,
    )


class TestIndicatorPipeline:
    async def test_register_node(self, pipeline: IndicatorPipeline) -> None:
        node = PipelineNode(name="ema", dependencies=())
        await pipeline.register_node(node)
        assert "ema" in pipeline._nodes

    async def test_resolve_execution_order_single(self, pipeline: IndicatorPipeline) -> None:
        await pipeline.register_node(PipelineNode(name="ema", dependencies=()))
        stages = await pipeline.get_execution_plan()
        assert len(stages) == 1
        assert "ema" in stages[0].node_names

    async def test_resolve_execution_order_dependency(self, pipeline: IndicatorPipeline) -> None:
        await pipeline.register_node(PipelineNode(name="sma", dependencies=()))
        await pipeline.register_node(PipelineNode(name="ema", dependencies=("sma",)))
        stages = await pipeline.get_execution_plan()
        assert len(stages) >= 2

    async def test_execute_stream(
        self, pipeline: IndicatorPipeline, registry: IndicatorRegistry, bar: Bar
    ) -> None:
        await registry.register(EMA, name="ema")
        await registry.register(RSI, name="rsi")
        await pipeline.register_node(PipelineNode(name="ema", dependencies=()))
        await pipeline.register_node(PipelineNode(name="rsi", dependencies=()))
        await pipeline._manager.create_indicator("ema", "EURUSD")
        await pipeline._manager.create_indicator("rsi", "EURUSD")

        warmup_bars = [
            Bar(
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                open=100.0 + i,
                high=101.0 + i,
                low=99.0 + i,
                close=100.5 + i,
                volume=1000,
            )
            for i in range(20)
        ]

        await pipeline._manager.warmup("EURUSD", warmup_bars)

        results = await pipeline.execute_stream("EURUSD", bar)
        assert "ema" in results
        assert "rsi" in results

    async def test_execute_batch(
        self, pipeline: IndicatorPipeline, registry: IndicatorRegistry
    ) -> None:
        await registry.register(EMA, name="ema")
        await pipeline.register_node(PipelineNode(name="ema", dependencies=()))
        await pipeline._manager.create_indicator("ema", "EURUSD")

        bars = [
            Bar(
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                open=100.0 + i,
                high=101.0 + i,
                low=99.0 + i,
                close=100.5 + i,
                volume=1000,
            )
            for i in range(20)
        ]

        results = await pipeline.execute_batch("EURUSD", bars)
        assert "ema" in results

    async def test_unregister_node(self, pipeline: IndicatorPipeline) -> None:
        await pipeline.register_node(PipelineNode(name="ema", dependencies=()))
        await pipeline.unregister_node("ema")
        assert "ema" not in pipeline._nodes

    async def test_clear(self, pipeline: IndicatorPipeline) -> None:
        await pipeline.register_node(PipelineNode(name="ema", dependencies=()))
        await pipeline.register_node(PipelineNode(name="rsi", dependencies=()))
        await pipeline.clear()
        assert len(pipeline._nodes) == 0

    async def test_independent_nodes_parallel(self, pipeline: IndicatorPipeline) -> None:
        """Test that independent nodes resolve to same stage."""
        await pipeline.register_node(PipelineNode(name="ema", dependencies=()))
        await pipeline.register_node(PipelineNode(name="sma", dependencies=()))
        stages = await pipeline.get_execution_plan()
        # Both have no dependencies, should be in same stage
        assert len(stages) == 1
        assert "ema" in stages[0].node_names
        assert "sma" in stages[0].node_names
