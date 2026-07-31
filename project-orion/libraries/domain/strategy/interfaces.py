"""Protocol/port definitions for the Strategy Abstraction Layer.

Defines all broker-agnostic ports for implementing, registering,
and executing trading strategies. Every external dependency is
injected through these protocol ports.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from libraries.domain.strategy.models import (
    ExecutionDecision,
    OrderIntent,
    PositionIntent,
    Signal,
    StrategyContext,
    StrategyResult,
)


@runtime_checkable
class SignalGenerator(Protocol):
    """Port for generating trading signals from market data."""

    async def generate(self, context: StrategyContext) -> Signal | None:
        """Generate a trading signal based on the current context.

        Args:
            context: Current market and account context.

        Returns:
            A Signal if one should be generated, or None to hold.
        """
        ...


@runtime_checkable
class PositionSizer(Protocol):
    """Port for determining position sizes based on risk parameters."""

    async def size_position(
        self,
        signal: Signal,
        context: StrategyContext,
    ) -> PositionIntent:
        """Calculate the desired position size for a given signal.

        Args:
            signal: The trading signal to size.
            context: Current market and account context.

        Returns:
            A PositionIntent with the target size and risk parameters.
        """
        ...


@runtime_checkable
class RiskController(Protocol):
    """Port for validating orders against risk limits."""

    async def validate_order(self, intent: OrderIntent, context: StrategyContext) -> bool:
        """Validate an order intent against risk limits.

        Args:
            intent: The order intent to validate.
            context: Current market and account context.

        Returns:
            True if the order passes risk checks, False otherwise.
        """
        ...

    async def validate_position(
        self,
        intent: PositionIntent,
        context: StrategyContext,
    ) -> bool:
        """Validate a position intent against risk limits.

        Args:
            intent: The position intent to validate.
            context: Current market and account context.

        Returns:
            True if the position passes risk checks, False otherwise.
        """
        ...

    async def max_position_size(
        self,
        symbol: str,
        context: StrategyContext,
    ) -> int:
        """Return the maximum allowed position size for a symbol.

        Args:
            symbol: The instrument symbol.
            context: Current market and account context.

        Returns:
            Maximum position size in units.
        """
        ...


@runtime_checkable
class PortfolioAllocator(Protocol):
    """Port for allocating capital across strategies and symbols."""

    async def allocate(
        self,
        strategy_id: str,
        symbol: str,
        desired_quantity: int,
        context: StrategyContext,
    ) -> int:
        """Determine the final allocated quantity for a trade.

        Args:
            strategy_id: The strategy requesting allocation.
            symbol: The instrument symbol.
            desired_quantity: The quantity the strategy wants.
            context: Current market and account context.

        Returns:
            The final allocated quantity (may be less than desired).
        """
        ...

    async def current_allocation(self, strategy_id: str) -> dict[str, int]:
        """Return current allocation for a strategy across symbols.

        Args:
            strategy_id: The strategy identifier.

        Returns:
            Dict mapping symbol to allocated quantity.
        """
        ...


@runtime_checkable
class Strategy(Protocol):
    """Port for a complete trading strategy.

    A strategy combines signal generation, position sizing,
    and risk management into a single evaluation cycle.
    """

    @property
    def strategy_id(self) -> str:
        """Return the unique identifier for this strategy."""
        ...

    async def evaluate(self, context: StrategyContext) -> StrategyResult:
        """Evaluate the strategy for the current market context.

        This is the main entry point for strategy execution.
        It generates signals, sizes positions, and returns
        the result for further processing.

        Args:
            context: Current market and account context.

        Returns:
            A StrategyResult containing signals and intents.
        """
        ...

    async def on_order_filled(self, decision: ExecutionDecision) -> None:
        """Called when an order resulting from this strategy is filled.

        Args:
            decision: The execution decision that was filled.
        """
        ...

    async def on_error(self, error: Exception) -> None:
        """Called when an error occurs during strategy execution.

        Args:
            error: The exception that occurred.
        """
        ...