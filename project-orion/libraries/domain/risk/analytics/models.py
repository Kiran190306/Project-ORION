"""Immutable data models for the Risk Analytics sub-package.

Provides result containers for Value at Risk, Conditional VaR, Kelly
criterion, performance ratios, drawdown, volatility, correlation,
concentration, and exposure analytics.

Financial values use ``Decimal``; ratios and percentages use ``float``.
All dataclasses are frozen with ``slots=True`` and timezone-aware
timestamps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any


class VaRMethod(StrEnum):
    """Method used to compute Value at Risk."""

    HISTORICAL = "historical"
    PARAMETRIC = "parametric"
    MONTE_CARLO = "monte_carlo"


class VolatilityMethod(StrEnum):
    """Method used to estimate volatility."""

    HISTORICAL = "historical"
    EWMA = "ewma"


@dataclass(frozen=True, slots=True)
class VaRResult:
    """Value at Risk result.

    ``var_pct`` is a positive percentage loss. For example, ``2.3``
    means a 2.3% potential loss at the given confidence level.
    """

    method: VaRMethod
    confidence_level: float
    horizon_days: int
    var_pct: float
    var_amount: Decimal | None = None
    expected_return: float = 0.0
    volatility: float = 0.0
    simulations: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def var(self) -> float:
        """Alias for ``var_pct``."""
        return self.var_pct


@dataclass(frozen=True, slots=True)
class CvaRResult:
    """Conditional Value at Risk (expected shortfall) result.

    ``cvar_pct`` is the average loss beyond the VaR threshold,
    expressed as a positive percentage.
    """

    method: VaRMethod
    confidence_level: float
    horizon_days: int
    cvar_pct: float
    var_pct: float
    cvar_amount: Decimal | None = None
    simulations: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def expected_shortfall(self) -> float:
        """Alias for ``cvar_pct``."""
        return self.cvar_pct


@dataclass(frozen=True, slots=True)
class KellyResult:
    """Kelly criterion result.

    ``fraction`` is the optimal fraction of capital to risk per trade.
    """

    fraction: float
    win_probability: float
    win_loss_ratio: float
    expected_return_per_trade: float = 0.0
    edge: float = 0.0
    half_kelly_fraction: float = 0.0
    quarter_kelly_fraction: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    """Aggregated risk-adjusted performance metrics."""

    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    annualized_return: float = 0.0
    annualized_volatility: float = 0.0
    downside_deviation: float = 0.0
    max_drawdown: float = 0.0
    risk_free_rate: float = 0.0
    periods_per_year: int = 252
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DrawdownResult:
    """Drawdown analytics result.

    All drawdown values are positive percentages (e.g. ``15.0`` = 15%
    below peak). ``series`` holds the percentage drawdown at each step.
    """

    max_drawdown: float
    current_drawdown: float
    peak_value: float
    trough_value: float
    peak_index: int = -1
    trough_index: int = -1
    max_drawdown_duration: int = 0
    series: tuple[float, ...] = ()
    rolling_max_drawdowns: tuple[float, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VolatilityMetrics:
    """Volatility analytics result.

    ``volatility`` and ``annualized_volatility`` are annualized.
    """

    volatility: float
    annualized_volatility: float
    annualized_return: float = 0.0
    mean_return: float = 0.0
    method: VolatilityMethod = VolatilityMethod.HISTORICAL
    periods_per_year: int = 252
    rolling_volatility: tuple[float, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CorrelationResult:
    """Correlation analytics result.

    ``correlation_matrix`` is a square matrix indexed in the same order
    as ``symbols``. ``betas`` maps each symbol to its beta against the
    benchmark (empty when no benchmark is supplied).
    """

    symbols: tuple[str, ...]
    correlation_matrix: tuple[tuple[float, ...], ...]
    betas: dict[str, float] = field(default_factory=dict)
    rolling_correlation: dict[tuple[str, str], tuple[float, ...]] = field(
        default_factory=dict
    )
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConcentrationMetrics:
    """Portfolio concentration metrics.

    HHI (Herfindahl-Hirschman Index) is computed from fractional
    weights. ``effective_positions`` is the equivalent number of equal
    positions (1 / HHI).
    """

    hhi: float
    effective_positions: float
    top_holding_pct: float
    top_n_concentration: float
    position_count: int
    top_n: int = 3
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PositionExposure:
    """Exposure of a single portfolio position."""

    symbol: str
    market_value: Decimal
    side: str = "long"
    sector: str = ""
    risk_weight: float = 0.0


@dataclass(frozen=True, slots=True)
class ExposureMetrics:
    """Portfolio exposure analytics result.

    ``asset_allocation`` maps symbol to weight (0-1 fraction).
    ``sector_exposure`` maps sector name to total market value.
    ``risk_budget`` maps symbol to its risk weight (0-1 fraction).
    """

    gross_exposure: Decimal
    net_exposure: Decimal
    long_exposure: Decimal
    short_exposure: Decimal
    portfolio_equity: Decimal
    gross_exposure_pct: float = 0.0
    net_exposure_pct: float = 0.0
    long_exposure_pct: float = 0.0
    short_exposure_pct: float = 0.0
    sector_exposure: dict[str, Decimal] = field(default_factory=dict)
    asset_allocation: dict[str, float] = field(default_factory=dict)
    risk_budget: dict[str, float] = field(default_factory=dict)
    concentration: ConcentrationMetrics | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

