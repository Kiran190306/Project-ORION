"""Quantitative Research and Strategy Lab domain package."""

from __future__ import annotations

from libraries.domain.research.models import (
    EquityCurvePoint,
    OverfittingWarning,
    ResearchExperiment,
    ResearchExperimentStatus,
    ResearchPerformanceMetrics,
    ResearchWarning,
    TradeRecord,
    WarningSeverity,
)
from libraries.domain.research.optimization_engine import OptimizationEngine
from libraries.domain.research.optimization_models import (
    FitnessObjective,
    OptimizationCandidate,
    OptimizationJob,
    OptimizationStatus,
    OptimizationType,
    OptimizationWarningCode,
    ParameterRange,
    ParameterSpaceDefinition,
    ParameterStabilityAnalysis,
    ParameterType,
    RegimePerformanceBreakdown,
    SensitivityHeatmapMatrix,
    SensitivityHeatmapPoint,
    WalkForwardAnalysisResult,
    WalkForwardRobustness,
    WalkForwardWindowResult,
)
from libraries.domain.research.overfitting_guard import OverfittingGuard
from libraries.domain.research.parameter_space_engine import ParameterSpaceEngine
from libraries.domain.research.parameter_stability_analyzer import (
    ParameterStabilityAnalyzer,
)
from libraries.domain.research.regime_analyzer import RegimeAnalyzer
from libraries.domain.research.walk_forward_engine import WalkForwardEngine

__all__ = [
    "EquityCurvePoint",
    "FitnessObjective",
    "OptimizationCandidate",
    "OptimizationEngine",
    "OptimizationJob",
    "OptimizationStatus",
    "OptimizationType",
    "OptimizationWarningCode",
    "OverfittingGuard",
    "OverfittingWarning",
    "ParameterRange",
    "ParameterSpaceDefinition",
    "ParameterSpaceEngine",
    "ParameterStabilityAnalysis",
    "ParameterStabilityAnalyzer",
    "ParameterType",
    "RegimeAnalyzer",
    "RegimePerformanceBreakdown",
    "ResearchExperiment",
    "ResearchExperimentStatus",
    "ResearchPerformanceMetrics",
    "ResearchWarning",
    "SensitivityHeatmapMatrix",
    "SensitivityHeatmapPoint",
    "TradeRecord",
    "WalkForwardAnalysisResult",
    "WalkForwardEngine",
    "WalkForwardRobustness",
    "WalkForwardWindowResult",
    "WarningSeverity",
]

