"""Provider payload parsing into domain RawTick.

No broker-specific logic leaks into the domain layer; parsing remains
infrastructure-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.market import RawTick


def _utc_from_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, (int, float)):
        # Assume unix seconds.
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str):
        # Expect ISO8601.
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    raise TypeError("Unsupported timestamp")


@dataclass(frozen=True, slots=True)
class TickParseResult:
    raw_tick: RawTick


def parse_generic_bid_ask_tick(
    *,
    provider: str,
    symbol: str,
    timestamp: Any,
    bid: Any,
    ask: Any,
    bid_size: Any | None = None,
    ask_size: Any | None = None,
    sequence: int | None = None,
) -> RawTick:
    """Parse a generic provider tick format into domain RawTick."""

    return RawTick(
        symbol=symbol,
        timestamp=_utc_from_timestamp(timestamp),
        bid=Decimal(str(bid)),
        ask=Decimal(str(ask)),
        source=provider,
        bid_size=Decimal(str(bid_size)) if bid_size is not None else None,
        ask_size=Decimal(str(ask_size)) if ask_size is not None else None,
        sequence=sequence,
    )


def parse_provider_dict_tick(provider: str, payload: Any) -> RawTick:
    """Parse a dict-based provider tick.

    Expected payload keys:
    - symbol
    - timestamp
    - bid
    - ask
    Optional keys:
    - bid_size, ask_size, sequence
    """

    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")

    return parse_generic_bid_ask_tick(
        provider=provider,
        symbol=str(payload["symbol"]),
        timestamp=payload["timestamp"],
        bid=payload["bid"],
        ask=payload["ask"],
        bid_size=payload.get("bid_size"),
        ask_size=payload.get("ask_size"),
        sequence=payload.get("sequence"),
    )
