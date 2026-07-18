"""
Project ORION - Structured Logging

Centralized structured logging system with correlation ID support,
configurable levels, and structured JSON output.

Supports:
- Structured JSON logging (production)
- Human-readable text logging (development)
- Correlation ID propagation
- Service context enrichment
- Log level configuration
"""

from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from types import TracebackType
from typing import Any, Optional, cast
from uuid import uuid4

from shared.common.result import Result, failure, success

# ─── Correlation ID ───────────────────────────────────────────

_correlation_id: Optional[str] = None


def set_correlation_id(correlation_id: str) -> None:
    """Set the global correlation ID for request tracing."""
    global _correlation_id
    _correlation_id = correlation_id


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID."""
    return _correlation_id


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return uuid4().hex[:16]


# ─── Structured Log Record ────────────────────────────────────


class StructuredLogRecord:
    """Structured log entry with metadata enrichment."""

    def __init__(
        self,
        level: str,
        message: str,
        logger_name: str,
        correlation_id: Optional[str] = None,
        service: str = "orion",
        environment: str = "development",
        extra: Optional[dict[str, Any]] = None,
        exception: Optional[Exception] = None,
    ) -> None:
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.level = level
        self.message = message
        self.logger = logger_name
        self.correlation_id = correlation_id or get_correlation_id()
        self.service = service
        self.environment = environment
        self.extra = extra or {}

        if exception:
            self.extra["exception"] = {
                "type": type(exception).__name__,
                "message": str(exception),
                "stacktrace": traceback.format_exc(),
            }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON output."""
        result: dict[str, Any] = {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
            "logger": self.logger,
            "correlation_id": self.correlation_id,
            "service": self.service,
            "environment": self.environment,
        }
        if self.extra:
            result["extra"] = self.extra
        return result

    def to_text(self) -> str:
        """Format as human-readable text."""
        parts = [
            f"[{self.timestamp}]",
            f"{self.level:8s}",
            f"[{self.service}]",
            f"[{self.correlation_id or '-'}]",
            self.message,
        ]
        if self.extra:
            parts.append(str(self.extra))
        return " ".join(parts)


# ─── Structured Log Handler ──────────────────────────────────


class StructuredLogHandler(logging.Handler):
    """
    Custom logging handler that emits structured log records.
    Supports both JSON (production) and text (development) formats.
    """

    def __init__(
        self,
        output_format: str = "json",
        service: str = "orion",
        environment: str = "development",
        stream: Any = sys.stdout,
    ) -> None:
        super().__init__()
        self.output_format = output_format
        self.service = service
        self.environment = environment
        self.stream = stream

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a structured log record."""
        try:
            structured = StructuredLogRecord(
                level=record.levelname,
                message=record.getMessage(),
                logger_name=record.name,
                correlation_id=get_correlation_id(),
                service=self.service,
                environment=self.environment,
                extra=getattr(record, "extra", None),
                exception=(
                    record.exc_info[1]
                    if record.exc_info and isinstance(record.exc_info[1], Exception)
                    else None
                ),
            )

            if self.output_format == "json":
                output = json.dumps(structured.to_dict(), default=str)
            else:
                output = structured.to_text()

            self.stream.write(output + "\n")
            self.stream.flush()
        except Exception:
            self.handleError(record)


# ─── Structured Logger ────────────────────────────────────────


class StructuredLogger:
    """
    Structured logger with convenience methods for different log levels.

    Usage:
        logger = StructuredLogger("my_service")
        logger.info("User logged in", user_id="123")
        logger.error("Database connection failed", error=exc)
    """

    def __init__(
        self,
        name: str = "orion",
        level: str = "INFO",
        output_format: str = "json",
        service: str = "orion",
        environment: str = "development",
    ) -> None:
        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self._logger.handlers.clear()

        handler = StructuredLogHandler(
            output_format=output_format,
            service=service,
            environment=environment,
        )
        handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        self._logger.addHandler(handler)

    def debug(self, message: str, *args: Any, **extra: Any) -> None:
        """Log a debug message.

        Compatible with Python logging:
        - logger.debug("msg %s", a, b)
        - logger.debug("msg", key=value)

        Additionally supports positional legacy key/value pairs:
        - logger.debug("message", "key", value, "key2", value2)
        """
        self._log(logging.DEBUG, message, extra, exc_info=False, args=args)

    def info(self, message: str, *args: Any, **extra: Any) -> None:
        """Log an info message.

        Compatible with Python logging:
        - info("message %s", value)
        - info("message", key=value)

        Also supports a legacy key/value positional style:
        - info("message", "key", value, ...)
        """
        self._log(logging.INFO, message, extra, exc_info=False, args=args)

    def warning(self, message: str, *args: Any, **extra: Any) -> None:
        """Log a warning message (Python logging compatible)."""
        self._log(logging.WARNING, message, extra, exc_info=False, args=args)

    def error(self, message: str, *args: Any, **extra: Any) -> None:
        """Log an error message (Python logging compatible)."""
        self._log(logging.ERROR, message, extra, exc_info=False, args=args)

    def critical(self, message: str, *args: Any, **extra: Any) -> None:
        """Log a critical message (Python logging compatible)."""
        self._log(logging.CRITICAL, message, extra, exc_info=False, args=args)

    def exception(self, message: str, exception: Exception, *args: Any, **extra: Any) -> None:
        """Log an exception with stacktrace.

        Compatible with Python logging formatting via positional args.
        """
        extra["exception"] = exception
        self._log(logging.ERROR, message, extra, exc_info=True, args=args)

    def _log(
        self,
        level: int,
        message: str,
        extra: Optional[dict[str, Any]] = None,
        exc_info: bool = False,
        args: tuple[Any, ...] = (),
    ) -> None:
        """Internal log method.

        Supports Python logging style positional formatting args.
        Additionally supports legacy key/value positional pairs:
        - ("key", value, "key2", value2, ...)
        """
        extra_dict: dict[str, Any] = dict(extra or {})

        # Legacy key/value pairs: all args must be usable as key/value pairs.
        if args:
            if len(args) % 2 == 0 and all(isinstance(args[i], str) for i in range(0, len(args), 2)):
                it = iter(args)
                extra_dict.update({str(k): v for k, v in zip(it, it)})
                fmt_args: tuple[Any, ...] = ()
            else:
                fmt_args = args
        else:
            fmt_args = ()

        exc_tuple: (
            tuple[type[BaseException], BaseException, TracebackType | None]
            | tuple[None, None, None]
        ) = (None, None, None)
        if exc_info:
            try:
                exc_tuple = (
                    (type(extra_dict["exception"]), extra_dict["exception"], None)
                    if "exception" in extra_dict
                    else (None, None, None)
                )
            except Exception:
                exc_tuple = (None, None, None)
        record = self._logger.makeRecord(
            self._logger.name,
            level,
            "",
            0,
            message,
            fmt_args,
            exc_tuple,
        )
        record.extra = extra_dict
        self._logger.handle(record)

    @property
    def level(self) -> str:
        """Get current log level."""
        return logging.getLevelName(self._logger.level)


# ─── Logger Factory ──────────────────────────────────────────

_loggers: dict[str, StructuredLogger] = {}


def get_logger(
    name: str = "orion",
    level: Optional[str] = None,
    output_format: Optional[str] = None,
    service: str = "orion",
    environment: Optional[str] = None,
) -> StructuredLogger:
    """
    Get or create a structured logger instance.

    Args:
        name: Logger name (typically service name).
        level: Log level override.
        output_format: "json" or "text".
        service: Service name for metadata.
        environment: Environment name.

    Returns:
        StructuredLogger instance.
    """
    if name in _loggers:
        return _loggers[name]

    from libraries.infrastructure.settings import get_settings

    try:
        settings = get_settings()
        level = level or settings.get("logging.level", "INFO")
        output_format = output_format or settings.get("logging.format", "json")
        env = environment or settings.get("environment", "development")
    except Exception:
        level = level or "INFO"
        output_format = output_format or "json"
        env = environment or "development"

    logger = StructuredLogger(
        name=name,
        level=level,
        output_format=output_format,
        service=service,
        environment=env,
    )
    _loggers[name] = logger
    return logger


def reset_loggers() -> None:
    """Reset all cached loggers (for testing)."""
    global _loggers
    _loggers = {}
