"""Enterprise structured JSON logging with correlation IDs and sensitive-data masking."""

from __future__ import annotations

import json
import logging
import os
import platform
import socket
import sys
import traceback
from datetime import datetime, timezone
from threading import local
from typing import Any

from libraries.observability.config import LoggingConfig

_thread_local = local()


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for the current thread/async context."""
    _thread_local.correlation_id = correlation_id


def get_correlation_id() -> str | None:
    """Get the current correlation ID."""
    return getattr(_thread_local, "correlation_id", None)


def set_trace_ids(trace_id: str | None, span_id: str | None) -> None:
    """Set trace and span IDs for the current context."""
    _thread_local.trace_id = trace_id
    _thread_local.span_id = span_id


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self, config: LoggingConfig) -> None:
        super().__init__()
        self._config = config
        self._hostname = socket.gethostname()

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self._config.service_name,
            "environment": self._config.environment,
            "version": self._config.version,
            "hostname": self._hostname,
            "correlation_id": get_correlation_id(),
            "trace_id": getattr(_thread_local, "trace_id", None),
            "span_id": getattr(_thread_local, "span_id", None),
        }

        # Add exception info if present
        if isinstance(record.exc_info, tuple) and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "stack_trace": "".join(traceback.format_exception(*record.exc_info)).splitlines(),
            }
        elif record.exc_text:
            log_entry["exception"] = {"text": record.exc_text}
        elif record.exc_info is True:
            log_entry["exception"] = {"type": "Exception", "resolved": True}

        # Add extra fields
        if hasattr(record, "extra_fields") and record.extra_fields:
            log_entry.update(self._mask_sensitive(record.extra_fields))

        # Add function/caller info
        log_entry["module"] = record.module
        log_entry["function"] = record.funcName
        log_entry["line"] = record.lineno

        return json.dumps(log_entry, default=str)

    def _mask_sensitive(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Mask sensitive fields in the log entry."""
        masked = dict(fields)
        sensitive_lower = {f.lower() for f in self._config.sensitive_fields}
        for key in list(masked.keys()):
            if key.lower() in sensitive_lower:
                masked[key] = "***REDACTED***"
        return masked


class StructuredLogger:
    """Structured logger wrapper providing context-aware logging."""

    def __init__(self, name: str, config: LoggingConfig) -> None:
        self._logger = logging.getLogger(name)
        self._config = config
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def debug(self, message: str, **extra: Any) -> None:
        self._log(logging.DEBUG, message, extra)

    def info(self, message: str, **extra: Any) -> None:
        self._log(logging.INFO, message, extra)

    def warning(self, message: str, **extra: Any) -> None:
        self._log(logging.WARNING, message, extra)

    def error(self, message: str, **extra: Any) -> None:
        self._log(logging.ERROR, message, extra)

    def critical(self, message: str, **extra: Any) -> None:
        self._log(logging.CRITICAL, message, extra)

    def exception(self, message: str, **extra: Any) -> None:
        self._logger.exception(message, extra={"extra_fields": extra})

    def _log(self, level: int, message: str, extra: dict[str, Any]) -> None:
        self._logger.log(level, message, extra={"extra_fields": extra})


_loggers: dict[str, StructuredLogger] = {}
_initialized = False


def configure_logging(config: LoggingConfig) -> None:
    """Configure the root logger with structured JSON formatting."""
    global _initialized
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    if config.enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(StructuredFormatter(config))
        root_logger.addHandler(console_handler)

    # File handler
    if config.enable_file:
        os.makedirs(os.path.dirname(config.file_path), exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            config.file_path,
            maxBytes=config.max_file_size_mb * 1024 * 1024,
            backupCount=config.backup_count,
        )
        file_handler.setFormatter(StructuredFormatter(config))
        root_logger.addHandler(file_handler)

    _initialized = True


def get_logger(name: str) -> StructuredLogger:
    """Get or create a structured logger."""
    if name not in _loggers:
        config = LoggingConfig()  # Default; real config used by configured root
        _loggers[name] = StructuredLogger(name, config)
    return _loggers[name]
