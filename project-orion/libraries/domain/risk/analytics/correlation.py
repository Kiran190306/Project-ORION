"""Correlation and Beta analytics engine.

Computes a Pearson correlation matrix across symbols and optional beta
coefficients against a benchmark. Supports optional rolling correlation
windows.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence

from libraries.domain.risk.analytics.models import CorrelationResult
from libraries.domain.risk.analytics.validation import (
    InvalidReturnsError,
    validate_returns,
)


class CorrelationEngine:
    """Computes correlation matrices, betas, and rolling correlation."""

    async def calculate(
        self,
        returns_by_symbol: Mapping[str, Sequence[float]],
        benchmark_returns: Sequence[float] | None = None,
        window: int | None = None,
    ) -> CorrelationResult:
        """Compute correlation analytics.

        Args:
            returns_by_symbol: Map of symbol to its returns series.
            benchmark_returns: Optional benchmark returns for betas.
            window: Optional rolling correlation window.

        Returns:
            A CorrelationResult.
        """
        if not returns_by_symbol:
            raise InvalidReturnsError("returns_by_symbol must not be empty")

        symbols = list(returns_by_symbol.keys())
        series: dict[str, list[float]] = {}
        for symbol in symbols:
            series[symbol] = validate_returns(returns_by_symbol[symbol])

        # Validate equal lengths across symbols.
        lengths = {len(s) for s in series.values()}
        if len(lengths) > 1:
            raise InvalidReturnsError("all returns series must have equal length")

        n = len(symbols)
        matrix: list[tuple[float, ...]] = []
        for i in range(n):
            row: list[float] = []
            for j in range(n):
                corr = self._pearson(series[symbols[i]], series[symbols[j]])
                row.append(round(corr, 6))
            matrix.append(tuple(row))

        betas: dict[str, float] = {}
        if benchmark_returns is not None:
            bench = validate_returns(benchmark_returns)
            if len(bench) != len(series[symbols[0]]):
                raise InvalidReturnsError(
                    "benchmark_returns must have the same length as asset returns"
                )
            for symbol in symbols:
                beta = self._beta(series[symbol], bench)
                betas[symbol] = round(beta, 6)

        rolling: dict[tuple[str, str], tuple[float, ...]] = {}
        if window is not None:
            if not isinstance(window, int) or window < 1:
                raise ValueError("window must be a positive integer")
            if window > len(series[symbols[0]]):
                raise ValueError(
                    f"window ({window}) exceeds data length ({len(series[symbols[0]])})"
                )
            for i in range(n):
                for j in range(i + 1, n):
                    pair = (symbols[i], symbols[j])
                    rolling[pair] = self._rolling_correlation(
                        series[symbols[i]], series[symbols[j]], window
                    )

        return CorrelationResult(
            symbols=tuple(symbols),
            correlation_matrix=tuple(matrix),
            betas=betas,
            rolling_correlation=rolling,
        )

    @staticmethod
    def _pearson(a: Sequence[float], b: Sequence[float]) -> float:
        """Pearson correlation coefficient between two series."""
        if len(a) != len(b):
            raise InvalidReturnsError("series must have equal length")
        n = len(a)
        mean_a = statistics.mean(a)
        mean_b = statistics.mean(b)
        cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b)) / n
        var_a = sum((x - mean_a) ** 2 for x in a) / n
        var_b = sum((y - mean_b) ** 2 for y in b) / n
        denom = math.sqrt(var_a * var_b)
        if denom == 0.0:
            return 0.0
        return cov / denom

    @staticmethod
    def _beta(asset_returns: Sequence[float], benchmark_returns: Sequence[float]) -> float:
        """Beta of an asset against a benchmark."""
        n = len(asset_returns)
        mean_a = statistics.mean(asset_returns)
        mean_b = statistics.mean(benchmark_returns)
        cov = sum(
            (x - mean_a) * (y - mean_b) for x, y in zip(asset_returns, benchmark_returns)
        ) / n
        var_b = sum((y - mean_b) ** 2 for y in benchmark_returns) / n
        if var_b == 0.0:
            return 0.0
        return cov / var_b

    @staticmethod
    def _rolling_correlation(
        a: Sequence[float],
        b: Sequence[float],
        window: int,
    ) -> tuple[float, ...]:
        """Compute rolling Pearson correlation."""
        result: list[float] = []
        for start in range(len(a) - window + 1):
            chunk_a = a[start : start + window]
            chunk_b = b[start : start + window]
            result.append(round(CorrelationEngine._pearson(chunk_a, chunk_b), 6))
        return tuple(result)

