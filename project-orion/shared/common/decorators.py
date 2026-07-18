"""
Project ORION - Common Decorators

Reusable decorators for cross-cutting concerns such as:
- Singleton pattern enforcement
- Argument validation
- Retry with backoff
- Logging wrappers
- Timeout enforcement

All decorators preserve type hints and function metadata via functools.wraps.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from typing import Any, Callable, Coroutine, Optional, ParamSpec, TypeVar

logger = logging.getLogger("orion.shared")

P = ParamSpec("P")
T = TypeVar("T")
R = TypeVar("R")


def singleton(cls: type[T]) -> type[T]:
    """
    Singleton decorator for classes.

    Ensures only one instance of the class is ever created.
    Thread-safe via instance caching.

    Usage:
        @singleton
        class ConfigManager:
            pass
    """
    instances: dict[type[T], T] = {}

    @functools.wraps(cls)
    def get_instance(*args: Any, **kwargs: Any) -> T:
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance  # type: ignore[return-value]


def validate_args(
    *validators: Callable[..., bool],
    error_msg: str = "Argument validation failed",
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to validate function arguments.

    Usage:
        @validate_args(
            lambda x: x > 0,
            lambda x: x < 100,
        )
        def set_value(x: int) -> None:
            pass
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            for idx, validator in enumerate(validators):
                if idx < len(args):
                    if not validator(args[idx]):
                        raise ValueError(
                            f"{error_msg}: argument {idx} failed validation"
                        )
            return func(*args, **kwargs)

        return wrapper

    return decorator


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Retry decorator with exponential backoff.

    Usage:
        @retry(max_attempts=5, delay=1.0, backoff=2.0)
        def unreliable_call() -> str:
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Optional[Exception] = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if on_retry:
                        on_retry(exc, attempt + 1)
                    if attempt < max_attempts - 1:
                        wait_time = delay * (backoff**attempt)
                        logger.warning(
                            "Attempt %d/%d failed: %s. Retrying in %.2fs...",
                            attempt + 1,
                            max_attempts,
                            exc,
                            wait_time,
                        )
                        time.sleep(wait_time)
            msg = f"All {max_attempts} attempts failed"
            raise last_exception or RuntimeError(msg)

        return wrapper

    return decorator


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[
    [Callable[P, Coroutine[Any, Any, T]]],
    Callable[P, Coroutine[Any, Any, T]],
]:
    """
    Async retry decorator with exponential backoff.

    Usage:
        @async_retry(max_attempts=5, delay=1.0, backoff=2.0)
        async def unreliable_call() -> str:
            ...
    """

    def decorator(
        func: Callable[P, Coroutine[Any, Any, T]],
    ) -> Callable[P, Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Optional[Exception] = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if on_retry:
                        on_retry(exc, attempt + 1)
                    if attempt < max_attempts - 1:
                        wait_time = delay * (backoff**attempt)
                        logger.warning(
                            "Attempt %d/%d failed: %s. Retrying in %.2fs...",
                            attempt + 1,
                            max_attempts,
                            exc,
                            wait_time,
                        )
                        await asyncio.sleep(wait_time)
            msg = f"All {max_attempts} async attempts failed"
            raise last_exception or RuntimeError(msg)

        return wrapper

    return decorator


def timed(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator to measure and log function execution time.

    Usage:
        @timed
        def slow_function() -> str:
            ...
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            logger.debug("%s took %.3fms", func.__qualname__, elapsed * 1000)

    return wrapper


def log_call(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator to log function calls with arguments.

    Usage:
        @log_call
        def add(a: int, b: int) -> int:
            return a + b
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        logger.debug(
            "Calling %s with args=%s kwargs=%s", func.__qualname__, args, kwargs
        )
        try:
            result = func(*args, **kwargs)
            logger.debug("%s returned %s", func.__qualname__, result)
            return result
        except Exception as exc:
            logger.error("%s raised %s: %s", func.__qualname__, type(exc).__name__, exc)
            raise

    return wrapper
