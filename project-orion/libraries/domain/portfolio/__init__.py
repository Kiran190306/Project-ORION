"""Portfolio & Position Management Engine for Project ORION.

This module is the single source of truth for all account, positions,
balances, margin, exposure, and P&L. No broker-specific logic exists
in this layer.

Exposed via PortfolioSyncPort for event-driven updates from the
Execution Engine, and via PortfolioDataPort / AccountDataPort for
consumption by the Risk Engine and Decision Engine.
"""

from __future__ import annotations

from libraries.domain.portfolio.analytics import PortfolioAnalytics, PortfolioAnalyticsEngine
from libraries.domain.portfolio.balance_manager import BalanceManager, BalanceSnapshot
from libraries.domain.portfolio.context import FillUpdate, PortfolioContext, PriceUpdate
from libraries.domain.portfolio.equity_manager import EquityManager, EquitySnapshot
from libraries.domain.portfolio.exceptions import (
    DuplicatePositionError,
    ExposureLimitExceededError,
    InsufficientBalanceError,
    InsufficientMarginError,
    InvalidPositionStateError,
    InvalidTradeError,
    MarginCallError,
    PositionNotFoundError,
    PositionSizeError,
    StopOutError,
)
from libraries.domain.portfolio.exposure_manager import (
    CurrencyExposure,
    ExposureManager,
    ExposureSnapshot,
    SymbolExposure,
)
from libraries.domain.portfolio.interfaces import (
    AccountDataProviderPort,
    AccountUpdateSink,
    ExecutionResultSource,
    PortfolioDataProviderPort,
    PortfolioPersistencePort,
    PortfolioSyncPort,
)
from libraries.domain.portfolio.journal import JournalEntry, JournalEntryType, TradeJournal
from libraries.domain.portfolio.margin_manager import MarginManager, MarginSnapshot
from libraries.domain.portfolio.models import (
    AccountSnapshot,
    CurrencyPosition,
    DrawdownSnapshot,
    MarginCallThresholds,
    PnLBreakdown,
    PortfolioSnapshot,
    Position,
    PositionSide,
    PositionStatus,
    PositionSummary,
)
from libraries.domain.portfolio.persistence import (
    AccountStore,
    AnalyticsStore,
    JournalStore,
    PersistenceManager,
    PositionStore,
)
from libraries.domain.portfolio.portfolio_manager import PortfolioManager, PortfolioManagerConfig
from libraries.domain.portfolio.position_manager import PositionManager, PositionManagerConfig

__all__ = [
    # Models
    "Position",
    "PositionSide",
    "PositionStatus",
    "PositionSummary",
    "AccountSnapshot",
    "PortfolioSnapshot",
    "PnLBreakdown",
    "CurrencyPosition",
    "MarginCallThresholds",
    "DrawdownSnapshot",
    # Exceptions
    "PositionNotFoundError",
    "DuplicatePositionError",
    "InvalidPositionStateError",
    "PositionSizeError",
    "InvalidTradeError",
    "InsufficientBalanceError",
    "InsufficientMarginError",
    "MarginCallError",
    "StopOutError",
    "ExposureLimitExceededError",
    # Interfaces
    "PortfolioSyncPort",
    "PortfolioDataProviderPort",
    "AccountDataProviderPort",
    "AccountUpdateSink",
    "ExecutionResultSource",
    "PortfolioPersistencePort",
    # Context
    "PortfolioContext",
    "FillUpdate",
    "PriceUpdate",
    # Position Management
    "PositionManager",
    "PositionManagerConfig",
    # Portfolio Aggregation
    "PortfolioManager",
    "PortfolioManagerConfig",
    # Balance & Equity & Margin
    "BalanceManager",
    "BalanceSnapshot",
    "EquityManager",
    "EquitySnapshot",
    "MarginManager",
    "MarginSnapshot",
    # Exposure
    "ExposureManager",
    "ExposureSnapshot",
    "SymbolExposure",
    "CurrencyExposure",
    # Journal
    "TradeJournal",
    "JournalEntry",
    "JournalEntryType",
    # Analytics
    "PortfolioAnalytics",
    "PortfolioAnalyticsEngine",
    # Persistence
    "PersistenceManager",
    "PositionStore",
    "AccountStore",
    "JournalStore",
    "AnalyticsStore",
]
