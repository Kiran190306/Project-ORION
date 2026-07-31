"""Base strategy implementation for the Strategy Abstraction Layer.

Provides common functionality for all trading strategies.
No broker logic, API calls, or infrastructure code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

from libraries.domain.strategy.exceptions import (
    InvalidSignalError,
    UnsupportedSymbolError,
)
from libraries.domain.strategy.models import (
    ExecutionAction,
    ExecutionDecision,
    OrderIntent,
    PositionIntent,
    PositionSide,
    Signal,
    SignalDirection,
    StrategyContext,
    StrategyMetadata,
    StrategyResult,
    StrategyStatus,
)


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies.

    Provides common lifecycle management, parameter handling,
    and validation. Subclasses implement the actual signal
    generation logic in ``generate_signal()``.

    No broker logic, no API calls, no infrastructure code.
    """

    def __init__(
        self,
        metadata: StrategyMetadata,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        self._metadata = metadata
        self._parameters: dict[str, Any] = parameters or {}
        self._status: StrategyStatus = StrategyStatus.DRAFT
        self._symbols: list[str] = list(metadata.tags) if metadata.tags else []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def strategy_id(self) -> str:
        """Return the unique identifier for this strategy."""
        return self._metadata.strategy_id

    @property
    def metadata(self) -> StrategyMetadata:
        """Return the strategy metadata."""
        return self._metadata

    @property
    def status(self) -> StrategyStatus:
        """Return the current strategy status."""
        return self._status

    @property
    def parameters(self) -> dict[str, Any]:
        """Return the strategy parameters."""
        return dict(self._parameters)

    @property
    def symbols(self) -> list[str]:
        """Return the list of symbols this strategy trades."""
        return list(self._symbols)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the strategy before first use.

        Validates parameters and sets status to ACTIVE.
        Override in subclasses for custom initialization.
        """
        self._validate_parameters()
        self._status = StrategyStatus.ACTIVE

    def pause(self) -> None:
        """Pause the strategy. It will not generate signals."""
        self._status = StrategyStatus.PAUSED

    def resume(self) -> None:
        """Resume a paused strategy."""
        self._status = StrategyStatus.ACTIVE

    def stop(self) -> None:
        """Stop the strategy permanently."""
        self._status = StrategyStatus.STOPPED

    # ------------------------------------------------------------------
    # Main evaluation
    # ------------------------------------------------------------------

    async def evaluate(self, context: StrategyContext) -> StrategyResult:
        """Evaluate the strategy for the current market context.

        Args:
            context: Current market and account context.

        Returns:
            A StrategyResult containing signals and intents.
        """
        errors: list[str] = []
        warnings: list[str] = []

        if self._status != StrategyStatus.ACTIVE:
            return StrategyResult(
                strategy_id=self.strategy_id,
                symbol=context.symbol,
                errors=[f"Strategy is {self._status.value}"],
            )

        if context.symbol not in self._symbols:
            errors.append(f"Symbol {context.symbol} not in strategy symbol list")
            return StrategyResult(
                strategy_id=self.strategy_id,
                symbol=context.symbol,
                errors=errors,
            )

        try:
            signal = await self.generate_signal(context)
        except Exception as e:
            errors.append(f"Signal generation failed: {e}")
            return StrategyResult(
                strategy_id=self.strategy_id,
                symbol=context.symbol,
                errors=errors,
            )

        if signal is None:
            return StrategyResult(
                strategy_id=self.strategy_id,
                symbol=context.symbol,
                warnings=["No signal generated"],
            )

        try:
            self._validate_signal(signal)
        except InvalidSignalError as e:
            errors.append(str(e))
            return StrategyResult(
                strategy_id=self.strategy_id,
                symbol=context.symbol,
                signal=signal,
                errors=errors,
            )

        position_intent = await self._size_position(signal, context)
        order_intent = self._create_order_intent(signal, position_intent)

        return StrategyResult(
            strategy_id=self.strategy_id,
            symbol=context.symbol,
            signal=signal,
            order_intent=order_intent,
            position_intent=position_intent,
            warnings=warnings,
        )

    async def on_order_filled(self, decision: ExecutionDecision) -> None:
        """Called when an order resulting from this strategy is filled.

        Override in subclasses for custom order fill handling.

        Args:
            decision: The execution decision that was filled.
        """
        pass

    async def on_error(self, error: Exception) -> None:
        """Called when an error occurs during strategy execution.

        Override in subclasses for custom error handling.

        Args:
            error: The exception that occurred.
        """
        pass

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    async def generate_signal(self, context: StrategyContext) -> Signal | None:
        """Generate a trading signal based on the current context.

        This is the main method subclasses must implement.

        Args:
            context: Current market and account context.

        Returns:
            A Signal if one should be generated, or None to hold.
        """
        ...

    # ------------------------------------------------------------------
    # Position sizing (overridable)
    # ------------------------------------------------------------------

    async def _size_position(
        self,
        signal: Signal,
        context: StrategyContext,
    ) -> PositionIntent:
        """Calculate the desired position size for a given signal.

        Override in subclasses for custom position sizing logic.

        Args:
            signal: The trading signal to size.
            context: Current market and account context.

        Returns:
            A PositionIntent with the target size and risk parameters.
        """
        side = PositionSide.LONG if signal.direction in (
            SignalDirection.BUY, SignalDirection.EXIT_SHORT,
        ) else PositionSide.SHORT

        return PositionIntent(
            strategy_id=self.strategy_id,
            symbol=signal.symbol,
            side=side,
            target_quantity=Decimal("1000"),
            reason=signal.reason,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_order_intent(
        self,
        signal: Signal,
        position_intent: PositionIntent,
    ) -> OrderIntent:
        """Create an order intent from a signal and position intent."""
        action_map: dict[SignalDirection, ExecutionAction] = {
            SignalDirection.BUY: ExecutionAction.ENTER_LONG,
            SignalDirection.SELL: ExecutionAction.ENTER_SHORT,
            SignalDirection.EXIT_LONG: ExecutionAction.EXIT_LONG,
            SignalDirection.EXIT_SHORT: ExecutionAction.EXIT_SHORT,
            SignalDirection.HOLD: ExecutionAction.HOLD,
        }

        return OrderIntent(
            strategy_id=self.strategy_id,
            symbol=signal.symbol,
            action=action_map.get(signal.direction, ExecutionAction.HOLD),
            quantity=position_intent.target_quantity,
            limit_price=signal.price,
            stop_price=position_intent.stop_loss,
            signal_id=signal.strategy_id,
            reason=signal.reason,
        )

    def _validate_signal(self, signal: Signal) -> None:
        """Validate a signal before processing.

        Args:
            signal: The signal to validate.

        Raises:
            InvalidSignalError: If the signal is invalid.
        """
        if signal.strategy_id != self.strategy_id:
            raise InvalidSignalError(
                f"Signal strategy_id {signal.strategy_id} does not match "
                f"this strategy {self.strategy_id}"
            )
        if signal.confidence < 0.0 or signal.confidence > 1.0:
            raise InvalidSignalError(
                f"Signal confidence {signal.confidence} must be between 0.0 and 1.0"
            )

    def _validate_parameters(self) -> None:
        """Validate strategy parameters.

        Override in subclasses for custom parameter validation.

        Raises:
            StrategyExecutionError: If parameters are invalid.
        """
        pass

    def _check_symbol_supported(self, symbol: str) -> None:
        """Check if a symbol is supported by this strategy.

        Args:
            symbol: The symbol to check.

        Raises:
            UnsupportedSymbolError: If the symbol is not supported.
        """
        if self._symbols and symbol not in self._symbols:
            raise UnsupportedSymbolError(
                f"Symbol {symbol} is not supported by strategy {self.strategy_id}"
            )