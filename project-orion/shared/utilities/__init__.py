"""
Project ORION - Utility Functions

Collection of general-purpose utility functions used across the platform.
All functions are pure (no side effects) where possible.

Provides:
- Timing and rate limiting
- Data transformation helpers
- Collection utilities
- Functional programming helpers
"""

from __future__ import annotations

import asyncio
import functools
import math
import time
from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Iterable, Optional, TypeVar

T = TypeVar("T")
U = TypeVar("U")


# ─── Timing Utilities ─────────────────────────────────────────


def now_ms() -> int:
    """Get current time in milliseconds since epoch."""
    return int(time.time() * 1000)


def now_ns() -> int:
    """Get current time in nanoseconds since epoch."""
    return time.time_ns()


def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds to a human-readable string.

    Examples:
        0.5 -> "500ms"
        1.5 -> "1.5s"
        65 -> "1m 5s"
        3665 -> "1h 1m 5s"
    """
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.0f}µs"
    if seconds < 1.0:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = int(seconds // 60)
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}m {secs:.0f}s"

    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}h {minutes}m {secs:.0f}s"


# ─── Rate Limiting ────────────────────────────────────────────


class RateLimiter:
    """
    Simple rate limiter using token bucket algorithm.

    Usage:
        limiter = RateLimiter(max_calls=10, period=1.0)
        if limiter.allow():
            # perform action
    """

    def __init__(self, max_calls: int, period: float = 1.0) -> None:
        self.max_calls = max_calls
        self.period = period
        self.tokens = float(max_calls)
        self.last_refill = time.monotonic()

    def allow(self) -> bool:
        """Check if a call is allowed under the rate limit."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.max_calls,
            self.tokens + elapsed * (self.max_calls / self.period),
        )
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


# ─── Math Utilities ───────────────────────────────────────────


def round_decimal(
    value: Decimal,
    precision: int = 2,
    rounding: str = ROUND_HALF_UP,
) -> Decimal:
    """Round a decimal value to specified precision."""
    quantize_str = f"1.{'0' * precision}" if precision > 0 else "1"
    return value.quantize(Decimal(quantize_str), rounding=rounding)


def pip_to_price(pips: float, pip_size: float) -> float:
    """Convert pips to price value."""
    return pips * pip_size


def price_to_pips(price_diff: float, pip_size: float) -> float:
    """Convert price difference to pips."""
    if pip_size == 0:
        return 0.0
    return price_diff / pip_size


def calculate_pip_value(
    position_size: float,
    pip_size: float,
    quote_currency_rate: float = 1.0,
) -> float:
    """Calculate the monetary value of one pip."""
    return position_size * pip_size / quote_currency_rate


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """Divide a by b safely, returning default if b is zero."""
    if b == 0:
        return default
    return a / b


# ─── Collection Utilities ─────────────────────────────────────


def chunk_list(items: list[T], chunk_size: int) -> list[list[T]]:
    """Split a list into chunks of specified size."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def deduplicate(items: list[T]) -> list[T]:
    """Remove duplicates while preserving order."""
    seen: set[T] = set()
    result: list[T] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def flatten(nested: list[list[T]]) -> list[T]:
    """Flatten a list of lists into a single list."""
    return [item for sublist in nested for item in sublist]


def group_by(items: list[T], key_fn: Callable[[T], U]) -> dict[U, list[T]]:
    """Group items by a key function."""
    result: dict[U, list[T]] = {}
    for item in items:
        key = key_fn(item)
        if key not in result:
            result[key] = []
        result[key].append(item)
    return result


def first_or_default(
    items: list[T],
    predicate: Optional[Callable[[T], bool]] = None,
    default: Optional[T] = None,
) -> Optional[T]:
    """Return first item matching predicate, or default."""
    for item in items:
        if predicate is None or predicate(item):
            return item
    return default


# ─── Functional Programming Utilities ─────────────────────────


def pipe(value: T, *functions: Callable[[Any], Any]) -> Any:
    """
    Pipe a value through a chain of functions.

    Usage:
        result = pipe(
            "hello",
            str.upper,
            lambda s: s + " world"
        )
        # result = "HELLO world"
    """
    result: Any = value
    for func in functions:
        result = func(result)
    return result


def compose(*functions: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """
    Compose functions right-to-left.

    Usage:
        f = compose(
            lambda s: s + " world",
            str.upper
        )
        result = f("hello")  # "HELLO world"
    """

    def composed(value: Any) -> Any:
        result = value
        for func in reversed(functions):
            result = func(result)
        return result

    return composed


def memoize(func: Callable[..., T]) -> Callable[..., T]:
    """
    Memoization decorator caching function results.

    Usage:
        @memoize
        def expensive_function(n: int) -> int:
            ...
    """
    cache: dict[str, T] = {}

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        key = str(args) + str(sorted(kwargs.items()))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    return wrapper


# ─── Async Utilities ─────────────────────────────────────────


async def async_retry(
    coro_factory: Callable[..., Any],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Retry an async coroutine with exponential backoff.

    Usage:
        result = await async_retry(
            fetch_data,
            max_attempts=5,
            url="https://example.com"
        )
    """
    last_exception: Optional[Exception] = None
    for attempt in range(max_attempts):
        try:
            return await coro_factory(*args, **kwargs)
        except Exception as exc:
            last_exception = exc
            if attempt < max_attempts - 1:
                wait_time = delay * (backoff**attempt)
                await asyncio.sleep(wait_time)

    msg = f"All {max_attempts} attempts failed"
    raise last_exception or RuntimeError(msg)


async def gather_with_concurrency(
    n: int,
    *coros: Any,
) -> list[Any]:
    """
    Run async tasks with a concurrency limit.

    Usage:
        results = await gather_with_concurrency(
            5,
            *[fetch_page(i) for i in range(100)]
        )
    """
    semaphore = asyncio.Semaphore(n)

    async def sem_task(coro: Any) -> Any:
        async with semaphore:
            return await coro

    return await asyncio.gather(*[sem_task(c) for c in coros])
