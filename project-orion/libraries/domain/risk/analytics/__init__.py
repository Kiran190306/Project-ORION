"""Enterprise Risk Analytics sub-package.

Provides pure-domain quantitative risk analytics engines:

- Value at Risk (historical / parametric / Monte Carlo)
- Conditional Value at Risk (expected shortfall)
- Kelly Criterion
- Sharpe / Sortino / Calmar ratios
- Maximum & rolling drawdown
- Volatility (historical / EWMA, rolling)
- Correlation matrix & beta
- Portfolio exposure, allocation, risk budget, concentration

The Risk Management Engine (EPIC-007) remains unchanged; this package
extends the Risk domain via composition.
"""

from __future__ import annotations

from libraries.domain.risk.analytics.correlation import CorrelationEngine
from libraries.domain.risk.analytics.cvar import ConditionalVarEngine
from libraries.domain.risk.analytics.drawdown import DrawdownEngine
from libraries.domain.risk.analytics.exposure import ExposureEngine
from libraries.domain.risk.analytics.interfaces import (
    ConcentrationPort,
    ConditionalVarPort,
    CorrelationPort,
    DrawdownPort,
    ExposurePort,
    KellyCriterionPort,
    PerformanceMetricsPort,
    ValueAtRiskPort,
    VolatilityPort,
)
from libraries.domain.risk.analytics.kelly import KellyCriterionEngine
from libraries.domain.risk.analytics.models import (
    ConcentrationMetrics,
    CorrelationResult,
    CvaRResult,
    DrawdownResult,
    ExposureMetrics,
    KellyResult,
    PerformanceMetrics,
    PositionExposure,
    VaRMethod,
    VaRResult,
    VolatilityMethod,
    VolatilityMetrics,
)
from libraries.domain.risk.analytics.ratios import PerformanceMetricsEngine
from libraries.domain.risk.analytics.validation import (
    InsufficientDataError,
    InvalidConfidenceLevelError,
    InvalidHorizonError,
    InvalidProbabilityError,
    InvalidReturnsError,
    InvalidValueError,
    InvalidWindowError,
    RiskAnalyticsError,
    validate_confidence_level,
    validate_horizon,
    validate_positive_float,
    validate_probability,
    validate_returns,
    validate_window,
)
from libraries.domain.risk.analytics.var import ValueAtRiskEngine
from libraries.domain.risk.analytics.volatility import VolatilityEngine

__all__ = [
    # Engines
    "ConditionalVarEngine",
    "CorrelationEngine",
    "DrawdownEngine",
    "ExposureEngine",
    "KellyCriterionEngine",
    "PerformanceMetricsEngine",
    "ValueAtRiskEngine",
    "VolatilityEngine",
    # Models
    "ConcentrationMetrics",
    "CorrelationResult",
    "CvaRResult",
    "DrawdownResult",
    "ExposureMetrics",
    "KellyResult",
    "PerformanceMetrics",
    "PositionExposure",
    "VaRMethod",
    "VaRResult",
    "VolatilityMethod",
    "VolatilityMetrics",
    # Interfaces
    "ConcentrationPort",
    "ConditionalVarPort",
    "CorrelationPort",
    "DrawdownPort",
    "ExposurePort",
    "KellyCriterionPort",
    "PerformanceMetricsPort",
    "ValueAtRiskPort",
    "VolatilityPort",
    # Validation
    "InsufficientDataError",
    "InvalidConfidenceLevelError",
    "InvalidHorizonError",
    "InvalidProbabilityError",
    "InvalidReturnsError",
    "InvalidValueError",
    "InvalidWindowError",
    "RiskAnalyticsError",
    "validate_confidence_level",
    "validate_horizon",
    "validate_positive_float",
    "validate_probability",
    "validate_returns",
    "validate_window",
]

