"""
Project ORION - Production Indicator Engine (EPIC-006 Sprint-3).

A production-grade, streaming-friendly technical indicator framework.
Indicators are completely independent from strategies - strategies consume
indicators, indicators never know about strategies.

Provides:
- Base Indicator with initialize/warmup/update/batch_calculate/reset lifecycle
- 25+ technical indicators across trend, momentum, volatility, volume,
  breakout, and market strength categories
- Indicator Registry with version compatibility
- Indicator Manager for lifecycle orchestration
- Indicator Pipeline with dependency resolution and parallel execution
- Indicator Cache with rolling window, TTL, incremental reuse
- Indicator Statistics for execution tracking
- Immutable output models
- O(1) incremental updates where mathematically possible
"""

from __future__ import annotations

from libraries.domain.indicators.ad import AccumulationDistribution
from libraries.domain.indicators.adx import ADX
from libraries.domain.indicators.atr import ATR
from libraries.domain.indicators.base import BaseIndicator
from libraries.domain.indicators.bollinger import BollingerBands
from libraries.domain.indicators.cache import IndicatorCache, IndicatorCacheConfig
from libraries.domain.indicators.cci import CCI
from libraries.domain.indicators.context import IndicatorContext
from libraries.domain.indicators.donchian import DonchianChannel
from libraries.domain.indicators.ema import EMA
from libraries.domain.indicators.exceptions import (
    IndicatorCalculationError,
    IndicatorError,
    IndicatorInitializationError,
    IndicatorNotFoundError,
    IndicatorRegistrationError,
    IndicatorValidationError,
    WarmupError,
)
from libraries.domain.indicators.hma import HMA
from libraries.domain.indicators.ichimoku import IchimokuCloud
from libraries.domain.indicators.interfaces import Indicator, IndicatorConfig
from libraries.domain.indicators.keltner import KeltnerChannels
from libraries.domain.indicators.macd import MACD
from libraries.domain.indicators.manager import IndicatorManager, IndicatorManagerConfig
from libraries.domain.indicators.mfi import MoneyFlowIndex
from libraries.domain.indicators.models import (
    Bar,
    IndicatorMetadata,
    IndicatorResult,
    IndicatorType,
    IndicatorValue,
)
from libraries.domain.indicators.momentum import Momentum
from libraries.domain.indicators.obv import OnBalanceVolume
from libraries.domain.indicators.pipeline import (
    IndicatorPipeline,
    IndicatorPipelineConfig,
    PipelineNode,
    PipelineStage,
)
from libraries.domain.indicators.pivot import PivotPoints
from libraries.domain.indicators.registry import IndicatorRegistry
from libraries.domain.indicators.roc import ROC
from libraries.domain.indicators.rsi import RSI
from libraries.domain.indicators.sma import SMA
from libraries.domain.indicators.statistics import IndicatorStatistics
from libraries.domain.indicators.stddev import StandardDeviation
from libraries.domain.indicators.stochastic import Stochastic
from libraries.domain.indicators.supertrend import SuperTrend
from libraries.domain.indicators.vwap import VWAP
from libraries.domain.indicators.wma import WMA

__all__ = [
    "ADX",
    "ATR",
    "AccumulationDistribution",
    "BaseIndicator",
    "BollingerBands",
    "CCI",
    "DonchianChannel",
    "EMA",
    "HMA",
    "IchimokuCloud",
    "Indicator",
    "IndicatorCache",
    "IndicatorCacheConfig",
    "IndicatorCalculationError",
    "IndicatorConfig",
    "IndicatorContext",
    "IndicatorError",
    "IndicatorInitializationError",
    "IndicatorManager",
    "IndicatorManagerConfig",
    "IndicatorMetadata",
    "IndicatorNotFoundError",
    "IndicatorPipeline",
    "IndicatorPipelineConfig",
    "IndicatorRegistrationError",
    "IndicatorResult",
    "IndicatorStatistics",
    "IndicatorType",
    "IndicatorValidationError",
    "IndicatorValue",
    "KeltnerChannels",
    "MACD",
    "Momentum",
    "MoneyFlowIndex",
    "OnBalanceVolume",
    "PivotPoints",
    "PipelineNode",
    "PipelineStage",
    "ROC",
    "RSI",
    "SMA",
    "StandardDeviation",
    "Stochastic",
    "SuperTrend",
    "VWAP",
    "WMA",
    "WarmupError",
    "Bar",
]
