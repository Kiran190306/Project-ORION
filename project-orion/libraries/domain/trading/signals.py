"""Signal direction and strength enums for the Trading Decision Engine."""

from __future__ import annotations

from enum import StrEnum


class SignalDirection(StrEnum):
    """Direction of a trading signal."""

    BUY = "buy"
    SELL = "sell"
    EXIT = "exit"
    HOLD = "hold"
    SCALE_IN = "scale_in"
    SCALE_OUT = "scale_out"


class SignalStrength(StrEnum):
    """Strength of a trading signal."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
