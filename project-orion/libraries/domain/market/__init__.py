"""Production-ready async domain engine for real-time market data."""

from .exceptions import (
    DuplicateSymbolError,
    EngineNotRunningError,
    InvalidMarketDataError,
    InvalidSessionError,
    MarketDataEngineError,
    UnknownSymbolError,
)
from .interfaces import (
    MarketDataPublisher,
    SessionManagerPort,
    SymbolRegistryPort,
    ValidationEnginePort,
)
from .manager import MarketDataManager
from .models import (
    OHLC,
    MarketDataKind,
    MarketDataSnapshot,
    RawTick,
    Symbol,
    Tick,
    TradingSession,
    ValidationIssue,
    ValidationReport,
)
from .normalization import NormalizationEngine
from .session_manager import SessionManager
from .symbol_registry import SymbolRegistry
from .validation import ValidationEngine

__all__ = [
    "DuplicateSymbolError",
    "EngineNotRunningError",
    "InvalidMarketDataError",
    "InvalidSessionError",
    "MarketDataEngineError",
    "MarketDataKind",
    "MarketDataManager",
    "MarketDataPublisher",
    "MarketDataSnapshot",
    "NormalizationEngine",
    "OHLC",
    "RawTick",
    "SessionManager",
    "SessionManagerPort",
    "Symbol",
    "SymbolRegistry",
    "SymbolRegistryPort",
    "Tick",
    "TradingSession",
    "UnknownSymbolError",
    "ValidationEngine",
    "ValidationEnginePort",
    "ValidationIssue",
    "ValidationReport",
]
