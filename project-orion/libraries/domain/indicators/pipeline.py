"""Indicator Pipeline.

Provides execution orchestration for indicators with:
- Parallel execution via asyncio.gather
- Dependency graph resolution and topological ordering
- Streaming and batch modes
- Incremental updates

Indicators that depend on other indicators are resolved through
a dependency graph and executed in the correct order.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from libraries.domain.indicators.base import BaseIndicator
from libraries.domain.indicators.cache import IndicatorCache
from libraries.domain.indicators.manager import IndicatorManager
from libraries.domain.indicators.models import Bar, IndicatorResult


@dataclass(frozen=True, slots=True)
class PipelineNode:
    """A node in the indicator pipeline dependency graph."""

    name: str
    dependencies: tuple[str, ...] = ()
    parallel_group: str = "default"

    def __hash__(self) -> int:
        return hash(self.name)


@dataclass(frozen=True, slots=True)
class PipelineStage:
    """A stage in the pipeline execution order.

    All nodes in a stage can be executed in parallel.
    Stages are executed sequentially.
    """

    stage_id: int
    node_names: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class IndicatorPipelineConfig:
    """Configuration for the indicator pipeline."""

    max_concurrency: int = 5
    enable_cache: bool = True
    fail_fast: bool = False
    track_dependencies: bool = True


class IndicatorPipeline:
    """Orchestrates indicator execution with dependency resolution.

    Builds a dependency graph from registered indicators and executes
    them in topological order. Independent indicators run in parallel.

    Supports:
    - Full batch calculation
    - Incremental streaming updates
    - Dependency-aware execution ordering
    - Parallel execution within stages
    """

    def __init__(
        self,
        manager: IndicatorManager,
        cache: IndicatorCache | None = None,
        config: IndicatorPipelineConfig | None = None,
    ) -> None:
        self._manager = manager
        self._cache = cache
        self._config = config or IndicatorPipelineConfig()

        # Dependency graph: {indicator_name: [dependency_names]}
        self._dependencies: dict[str, tuple[str, ...]] = {}
        self._nodes: dict[str, PipelineNode] = {}
        self._lock = asyncio.Lock()

    async def register_node(self, node: PipelineNode) -> None:
        """Register a pipeline node with its dependencies.

        Args:
            node: PipelineNode defining the indicator and its dependencies.
        """
        async with self._lock:
            self._nodes[node.name] = node
            self._dependencies[node.name] = node.dependencies

    async def unregister_node(self, name: str) -> None:
        """Remove a node from the pipeline.

        Args:
            name: Indicator name.
        """
        async with self._lock:
            self._nodes.pop(name, None)
            self._dependencies.pop(name, None)

    async def _resolve_execution_order(self) -> list[PipelineStage]:
        """Resolve the execution order using topological sort.

        Returns:
            List of PipelineStage objects in execution order.
        """
        async with self._lock:
            # Build adjacency list and in-degree count
            in_degree: dict[str, int] = {name: 0 for name in self._nodes}
            adjacency: dict[str, list[str]] = {name: [] for name in self._nodes}

            for name, node in self._nodes.items():
                for dep in node.dependencies:
                    if dep in adjacency:
                        adjacency[dep].append(name)
                        in_degree[name] = in_degree.get(name, 0) + 1

            # Kahn's algorithm for topological sort
            queue: list[str] = [name for name, degree in in_degree.items() if degree == 0]
            stages: list[PipelineStage] = []
            stage_id = 0

            while queue:
                # Current level nodes can run in parallel
                stage_nodes = list(queue)
                stages.append(
                    PipelineStage(
                        stage_id=stage_id,
                        node_names=tuple(stage_nodes),
                    )
                )
                stage_id += 1

                next_queue: list[str] = []
                for node_name in stage_nodes:
                    for neighbor in adjacency.get(node_name, []):
                        in_degree[neighbor] -= 1
                        if in_degree[neighbor] == 0:
                            next_queue.append(neighbor)
                queue = next_queue

            return stages

    async def execute_batch(
        self,
        symbol: str,
        bars: list[Bar],
        indicator_names: list[str] | None = None,
    ) -> dict[str, list[IndicatorResult]]:
        """Execute the pipeline for a batch of bars.

        Respects dependency ordering and runs independent indicators
        in parallel.

        Args:
            symbol: Trading symbol.
            bars: Batch of bars to process.
            indicator_names: Optional subset of indicators to execute.

        Returns:
            Dictionary mapping indicator name to list of results.
        """
        if not indicator_names:
            indicator_names = list(self._nodes.keys())

        final_results: dict[str, list[IndicatorResult]] = {}
        stages = await self._resolve_execution_order()

        for stage in stages:
            # Only include requested indicators in this stage
            stage_names = [n for n in stage.node_names if n in indicator_names]
            if not stage_names:
                continue

            # Execute stage indicators in parallel
            tasks = {
                name: self._manager.batch_calculate(
                    symbol,
                    bars,
                    indicator_names=[name],
                )
                for name in stage_names
            }

            # Limit concurrency
            semaphore = asyncio.Semaphore(self._config.max_concurrency)

            async def _execute_with_limit(
                name: str,
                task: asyncio.Task,
            ) -> tuple[str, list[IndicatorResult]]:
                async with semaphore:
                    result = await task
                    return name, result.get(name, [])

            if tasks:
                task_coros = [
                    _execute_with_limit(name, asyncio.ensure_future(t)) for name, t in tasks.items()
                ]
                results = await asyncio.gather(
                    *task_coros, return_exceptions=not self._config.fail_fast
                )

                for result in results:
                    if isinstance(result, BaseException):
                        if self._config.fail_fast:
                            raise result
                        continue
                    name, indicator_results = result
                    final_results[name] = indicator_results

        return final_results

    async def execute_stream(
        self,
        symbol: str,
        bar: Bar,
        indicator_names: list[str] | None = None,
    ) -> dict[str, IndicatorResult]:
        """Execute the pipeline for a streaming update (single bar).

        Respects dependency ordering and runs independent indicators
        in parallel.

        Args:
            symbol: Trading symbol.
            bar: New bar data.
            indicator_names: Optional subset of indicators to execute.

        Returns:
            Dictionary mapping indicator name to result.
        """
        if not indicator_names:
            indicator_names = list(self._nodes.keys())

        final_results: dict[str, IndicatorResult] = {}
        stages = await self._resolve_execution_order()

        for stage in stages:
            stage_names = [n for n in stage.node_names if n in indicator_names]
            if not stage_names:
                continue

            # Check cache for each indicator
            tasks: dict[str, asyncio.Task] = {}
            for name in stage_names:
                # Check cache first
                if self._config.enable_cache and self._cache:
                    cached = await self._cache.get(name, bar, symbol)
                    if cached is not None:
                        final_results[name] = cached
                        continue

                # Create calculation task
                tasks[name] = asyncio.ensure_future(
                    self._manager.update(symbol, bar, indicator_names=[name])
                )

            # Execute with concurrency limit
            semaphore = asyncio.Semaphore(self._config.max_concurrency)

            async def _execute_with_limit(
                name: str,
                task: asyncio.Task,
            ) -> tuple[str, IndicatorResult]:
                async with semaphore:
                    result = await task
                    return name, result.get(name)

            if tasks:
                task_coros = [_execute_with_limit(name, t) for name, t in tasks.items()]
                results = await asyncio.gather(
                    *task_coros, return_exceptions=not self._config.fail_fast
                )

                for result in results:
                    if isinstance(result, BaseException):
                        if self._config.fail_fast:
                            raise result
                        continue
                    name, indicator_result = result
                    if indicator_result is not None:
                        final_results[name] = indicator_result

        return final_results

    async def get_execution_plan(self) -> list[PipelineStage]:
        """Get the resolved execution plan (for debugging/visualization).

        Returns:
            List of PipelineStage objects showing execution order.
        """
        return await self._resolve_execution_order()

    async def clear(self) -> None:
        """Clear all registered nodes."""
        async with self._lock:
            self._nodes.clear()
            self._dependencies.clear()
