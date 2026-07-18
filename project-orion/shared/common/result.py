"""
Project ORION - Result Pattern

A functional Result monad implementation for consistent error handling
across the platform. Eliminates the need for exception-based control flow
in domain logic.

Design:
- Success(data) for successful operations
- Failure(error, code) for failed operations
- Pattern matching via .is_success / .is_failure
- Type-safe with generics
"""

from __future__ import annotations

import traceback
from collections.abc import Awaitable
from dataclasses import dataclass, field
from typing import Callable, Generic, TypeVar, Union, final

T = TypeVar("T")
E = TypeVar("E", bound=Exception)
U = TypeVar("U")


@final
@dataclass(frozen=True)
class Success(Generic[T]):
    """Represents a successful operation result."""

    data: T

    def unwrap(self) -> T:
        return self.data

    def unwrap_or(self, default: T) -> T:
        return self.data

    def map(self, fn: Callable[[T], U]) -> Success[U]:
        return Success(fn(self.data))

    def bind(self, fn: Callable[[T], Result[U, Exception]]) -> Result[U, Exception]:
        return fn(self.data)

    def __repr__(self) -> str:
        return f"Success({self.data!r})"


@final
@dataclass(frozen=True)
class Failure(Generic[E]):
    """Represents a failed operation result with error context."""

    error: E
    code: str = ""
    message: str = ""
    stacktrace: str = field(default_factory=lambda: traceback.format_exc())

    def __post_init__(self) -> None:
        if not self.message:
            object.__setattr__(self, "message", str(self.error))
        if not self.code:
            object.__setattr__(self, "code", self.error.__class__.__name__)

    def unwrap(self) -> None:
        raise self.error

    def unwrap_or(self, default: T) -> T:
        return default

    def map(self, fn: Callable[..., U]) -> Failure[E]:
        return self

    def bind(self, fn: Callable[..., Result[U, Exception]]) -> Failure[E]:
        return self

    def __repr__(self) -> str:
        return f"Failure(code={self.code!r}, message={self.message!r})"


Result = Union[Success[T], Failure[E]]
"""Type alias for the Result monad pattern."""


def success(data: T) -> Success[T]:
    """Create a success result."""
    return Success(data)


def failure(
    error: E,
    code: str = "",
    message: str = "",
) -> Failure[E]:
    """Create a failure result."""
    return Failure(error, code=code, message=message)


def attempt(
    fn: Callable[..., T],
    *args: object,
    **kwargs: object,
) -> Result[T, Exception]:
    """Execute a function and wrap the result."""
    try:
        return success(fn(*args, **kwargs))
    except Exception as exc:
        return failure(exc)


async def attempt_async(
    fn: Callable[..., Awaitable[T]],
    *args: object,
    **kwargs: object,
) -> Result[T, Exception]:
    """Execute an async function and wrap the result."""
    try:
        result = await fn(*args, **kwargs)
        return success(result)
    except Exception as exc:
        return failure(exc)
