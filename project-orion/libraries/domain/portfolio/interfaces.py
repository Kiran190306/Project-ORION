"""Protocol/port definitions for the Portfolio & Position Management Engine.

Defines:
- PortfolioSyncPort — event-driven updates from Execution Engine
- PortfolioDataProviderPort — data consumed by Risk Engine
- AccountDataProviderPort — account data consumed by Risk Engine
- AccountUpdateSink — external account update notifications
- ExecutionResultSource — source of execution results for position updates
- PortfolioPersistencePort — persistence abstraction
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from libraries.domain.portfolio.models import (
    AccountSnapshot,
    PortfolioSnapshot,
    Position,
)


@runtime_checkable
class PortfolioSyncPort(Protocol):
    """Port for receiving execution results and updating positions.

    This is the PRIMARY integration point with the Execution Engine.
    Implemented by PortfolioManager / PortfolioEngine.
    """

    async def on_fill(
        self,
        execution_id: str,
        decision_id: str,
        symbol: str,
        side: str,
        quantity: Any,
        price: Any,
        commission: Any,
        timestamp: Any,
        **kwargs: Any,
    ) -> Position:
        """Called when a fill is confirmed.

        Creates or updates positions based on the fill.
        Returns the created/updated Position.
        """
        ...

    async def on_order_rejected(
        self,
        execution_id: str,
        decision_id: str,
        symbol: str,
        reason: str,
    ) -> None:
        """Called when an order is rejected."""
        ...

    async def on_order_cancelled(
        self,
        execution_id: str,
        decision_id: str,
        symbol: str,
    ) -> None:
        """Called when an order is cancelled."""
        ...


@runtime_checkable
class PortfolioDataProviderPort(Protocol):
    """Port for querying portfolio-level data.

    Implemented by PortfolioManager / PortfolioEngine.
    Consumed by RiskEngine (via PortfolioDataPort).
    """

    async def get_portfolio_snapshot(self) -> PortfolioSnapshot:
        """Return the current portfolio snapshot."""
        ...

    async def get_portfolio_heat(self) -> float:
        """Return current portfolio heat (0–100)."""
        ...

    async def get_net_exposure(self) -> float:
        """Return net exposure as % of account."""
        ...

    async def get_long_exposure(self) -> float:
        """Return long exposure as % of account."""
        ...

    async def get_short_exposure(self) -> float:
        """Return short exposure as % of account."""
        ...

    async def get_currency_exposure(self, currency: str) -> float:
        """Return exposure to a specific currency as % of account."""
        ...

    async def get_symbol_exposure(self, symbol: str) -> float:
        """Return exposure to a specific symbol as % of account."""
        ...

    async def get_position_count(self) -> int:
        """Return the number of open positions."""
        ...

    async def get_open_positions(self) -> list[Position]:
        """Return all open positions."""
        ...


@runtime_checkable
class AccountDataProviderPort(Protocol):
    """Port for querying account-level data.

    Implemented by PortfolioManager / PortfolioEngine.
    Consumed by RiskEngine (via AccountDataPort).
    """

    async def get_account_snapshot(self) -> AccountSnapshot:
        """Return the current account snapshot."""
        ...

    async def get_balance(self) -> float:
        """Return current account balance."""
        ...

    async def get_equity(self) -> float:
        """Return current account equity."""
        ...

    async def get_margin_used(self) -> float:
        """Return currently used margin."""
        ...

    async def get_free_margin(self) -> float:
        """Return free margin."""
        ...

    async def get_margin_level(self) -> float:
        """Return margin level (equity / used_margin * 100)."""
        ...

    async def get_leverage(self) -> float:
        """Return current effective leverage."""
        ...

    async def get_buying_power(self) -> float:
        """Return available buying power."""
        ...


@runtime_checkable
class AccountUpdateSink(Protocol):
    """Port for notifying external systems of account changes.

    Designed for future integration with dashboards, alerts, etc.
    """

    async def on_account_updated(self, snapshot: AccountSnapshot) -> None:
        """Called when account state changes."""
        ...

    async def on_margin_call_warning(self, margin_level: float) -> None:
        """Called when margin level drops to warning levels."""
        ...

    async def on_stop_out_warning(self, margin_level: float) -> None:
        """Called when margin level approaches stop-out."""
        ...


@runtime_checkable
class ExecutionResultSource(Protocol):
    """Port for subscribing to execution results.

    For future event-driven integration: the portfolio engine
    subscribes to execution results and updates positions.
    """

    async def subscribe(self, callback: Any) -> None:
        """Subscribe to execution results."""
        ...

    async def unsubscribe(self, callback: Any) -> None:
        """Unsubscribe from execution results."""
        ...


@runtime_checkable
class PortfolioPersistencePort(Protocol):
    """Port for persisting portfolio state.

    Implementations expected for:
    - SQLite
    - PostgreSQL
    - Redis
    - Cloud Storage
    """

    async def save_position(self, position: Position) -> None:
        """Persist a position."""
        ...

    async def load_position(self, position_id: str) -> Position | None:
        """Load a position by ID."""
        ...

    async def load_positions_by_symbol(self, symbol: str) -> list[Position]:
        """Load all positions for a symbol."""
        ...

    async def load_all_open_positions(self) -> list[Position]:
        """Load all open positions."""
        ...

    async def load_all_closed_positions(self) -> list[Position]:
        """Load all closed positions."""
        ...

    async def save_account_snapshot(self, snapshot: AccountSnapshot) -> None:
        """Persist an account snapshot."""
        ...

    async def load_latest_account_snapshot(self) -> AccountSnapshot | None:
        """Load the most recent account snapshot."""
        ...

    async def save_portfolio_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        """Persist a portfolio snapshot."""
        ...

    async def load_latest_portfolio_snapshot(self) -> PortfolioSnapshot | None:
        """Load the most recent portfolio snapshot."""
        ...

    async def delete_position(self, position_id: str) -> None:
        """Delete a position record."""
        ...
