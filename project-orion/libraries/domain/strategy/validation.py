"""Validation utilities for the Strategy Abstraction Layer.

Provides pure functions for validating strategy parameters,
signals, position sizes, and risk parameters.
"""

from __future__ import annotations

from decimal import Decimal

from libraries.domain.strategy.exceptions import (
    InvalidPositionSizeError,
    InvalidRiskRewardError,
    InvalidSignalError,
    StopLossTakeProfitError,
)
from libraries.domain.strategy.models import (
    PositionIntent,
    Signal,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MIN_CONFIDENCE = 0.0
_MAX_CONFIDENCE = 1.0
_MIN_POSITION_SIZE = Decimal(0)
_MAX_POSITION_SIZE = Decimal(999999999)
_MIN_RISK_REWARD_RATIO = Decimal("0.01")
_MAX_RISK_REWARD_RATIO = Decimal(100)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_signal(signal: Signal) -> Signal:
    """Validate a trading signal.

    Args:
        signal: The signal to validate.

    Returns:
        The validated signal.

    Raises:
        InvalidSignalError: If the signal is invalid.
    """
    if not isinstance(signal, Signal):
        raise InvalidSignalError(f"Expected Signal, got {type(signal).__name__}")

    if not signal.strategy_id:
        raise InvalidSignalError("Signal strategy_id must not be empty")

    if not signal.symbol:
        raise InvalidSignalError("Signal symbol must not be empty")

    if signal.confidence < _MIN_CONFIDENCE or signal.confidence > _MAX_CONFIDENCE:
        raise InvalidSignalError(
            f"Signal confidence {signal.confidence} must be "
            f"between {_MIN_CONFIDENCE} and {_MAX_CONFIDENCE}"
        )

    return signal


def validate_position_size(quantity: Decimal, field_name: str = "quantity") -> Decimal:
    """Validate a position size value.

    Args:
        quantity: The position size to validate.
        field_name: Name of the field for error messages.

    Returns:
        The validated quantity.

    Raises:
        InvalidPositionSizeError: If the quantity is invalid.
    """
    if not isinstance(quantity, Decimal):
        raise InvalidPositionSizeError(
            f"{field_name} must be a Decimal, got {type(quantity).__name__}"
        )
    if quantity <= _MIN_POSITION_SIZE:
        raise InvalidPositionSizeError(
            f"{field_name} ({quantity}) must be positive"
        )
    if quantity > _MAX_POSITION_SIZE:
        raise InvalidPositionSizeError(
            f"{field_name} ({quantity}) exceeds maximum ({_MAX_POSITION_SIZE})"
        )
    return quantity


def validate_risk_reward_ratio(
    stop_loss: Decimal | None,
    take_profit: Decimal | None,
    entry_price: Decimal,
) -> Decimal:
    """Validate the risk/reward ratio of a trade.

    Args:
        stop_loss: The stop loss price (or None).
        take_profit: The take profit price (or None).
        entry_price: The entry price.

    Returns:
        The calculated risk/reward ratio.

    Raises:
        InvalidRiskRewardError: If the ratio is invalid.
        StopLossTakeProfitError: If stop-loss/take-profit are inconsistent.
    """
    if stop_loss is None or take_profit is None:
        raise InvalidRiskRewardError(
            "Both stop_loss and take_profit must be provided"
        )

    if stop_loss == entry_price:
        raise InvalidRiskRewardError("Stop loss cannot equal entry price")

    risk = abs(entry_price - stop_loss)
    reward = abs(take_profit - entry_price)

    if risk <= Decimal(0):
        raise InvalidRiskRewardError("Risk must be positive")

    ratio = reward / risk

    if ratio < _MIN_RISK_REWARD_RATIO:
        raise InvalidRiskRewardError(
            f"Risk/reward ratio ({ratio}) is below minimum ({_MIN_RISK_REWARD_RATIO})"
        )
    if ratio > _MAX_RISK_REWARD_RATIO:
        raise InvalidRiskRewardError(
            f"Risk/reward ratio ({ratio}) exceeds maximum ({_MAX_RISK_REWARD_RATIO})"
        )

    return ratio


def validate_stop_loss_take_profit(
    stop_loss: Decimal | None,
    take_profit: Decimal | None,
    entry_price: Decimal,
    side: str,  # "long" or "short"
) -> None:
    """Validate stop-loss and take-profit consistency.

    For long positions:
        stop_loss < entry_price < take_profit
    For short positions:
        stop_loss > entry_price > take_profit

    Args:
        stop_loss: The stop loss price (or None).
        take_profit: The take profit price (or None).
        entry_price: The entry price.
        side: Position side ("long" or "short").

    Raises:
        StopLossTakeProfitError: If the values are inconsistent.
    """
    if stop_loss is None and take_profit is None:
        return

    if stop_loss is not None and take_profit is not None:
        if side == "long":
            if stop_loss >= entry_price:
                raise StopLossTakeProfitError(
                    f"For long positions, stop_loss ({stop_loss}) "
                    f"must be below entry_price ({entry_price})"
                )
            if take_profit <= entry_price:
                raise StopLossTakeProfitError(
                    f"For long positions, take_profit ({take_profit}) "
                    f"must be above entry_price ({entry_price})"
                )
        elif side == "short":
            if stop_loss <= entry_price:
                raise StopLossTakeProfitError(
                    f"For short positions, stop_loss ({stop_loss}) "
                    f"must be above entry_price ({entry_price})"
                )
            if take_profit >= entry_price:
                raise StopLossTakeProfitError(
                    f"For short positions, take_profit ({take_profit}) "
                    f"must be below entry_price ({entry_price})"
                )


def validate_position_intent(intent: PositionIntent) -> PositionIntent:
    """Validate a position intent.

    Args:
        intent: The position intent to validate.

    Returns:
        The validated position intent.

    Raises:
        InvalidPositionSizeError: If the position size is invalid.
        StopLossTakeProfitError: If stop-loss/take-profit are inconsistent.
    """
    validate_position_size(intent.target_quantity)

    if intent.stop_loss is not None or intent.take_profit is not None:
        validate_stop_loss_take_profit(
            stop_loss=intent.stop_loss,
            take_profit=intent.take_profit,
            entry_price=Decimal(0),  # Will be set at execution
            side=intent.side.value,
        )

    return intent