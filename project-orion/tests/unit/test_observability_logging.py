"""Tests for observability logging module."""

from __future__ import annotations

import json
import logging

import pytest

from libraries.observability.config import LoggingConfig
from libraries.observability.logging import (
    StructuredFormatter,
    StructuredLogger,
    configure_logging,
    get_correlation_id,
    get_logger,
    set_correlation_id,
)


class TestStructuredLogger:
    def test_get_logger(self) -> None:
        logger = get_logger("test_logger")
        assert isinstance(logger, StructuredLogger)
        assert logger.name == "test_logger"

    def test_logger_reuses_instance(self) -> None:
        logger1 = get_logger("reuse_test")
        logger2 = get_logger("reuse_test")
        assert logger1 is logger2

    def test_get_correlation_id_default_none(self) -> None:
        cid = get_correlation_id()
        assert cid is None

    def test_set_and_get_correlation_id(self) -> None:
        set_correlation_id("test-cid-123")
        cid = get_correlation_id()
        assert cid == "test-cid-123"
        set_correlation_id("")  # Reset

    def test_structured_logger_creation(self) -> None:
        config = LoggingConfig(level="DEBUG", service_name="test")
        logger = get_logger("test_svc")
        assert logger.name == "test_svc"

    def test_configure_logging_does_not_raise(self) -> None:
        config = LoggingConfig(level="DEBUG", service_name="test", enable_file=False)
        configure_logging(config)
        logger = get_logger("test_cfg")
        logger.info("test message", extra_key="value")
        logger.debug("debug message")
        logger.warning("warning message")
        logger.error("error message")
        logger.critical("critical message")
        logger.exception("exception test")
        assert True  # No exception raised


class TestStructuredFormatter:
    def test_formatter_creates_json(self) -> None:
        config = LoggingConfig(service_name="test")
        formatter = StructuredFormatter(config)
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=42,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["message"] == "hello world"
        assert data["level"] == "INFO"
        assert data["service"] == "test"

    def test_formatter_includes_correlation_id(self) -> None:
        set_correlation_id("test-cid")
        config = LoggingConfig(service_name="test")
        formatter = StructuredFormatter(config)
        record = logging.LogRecord(
            name="t",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["correlation_id"] == "test-cid"
        set_correlation_id("")

    def test_formatter_includes_exception(self) -> None:
        config = LoggingConfig(service_name="test")
        formatter = StructuredFormatter(config)
        import sys

        try:
            raise ValueError("test error")
        except ValueError:
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="t",
                level=logging.ERROR,
                pathname=__file__,
                lineno=1,
                msg="error",
                args=(),
                exc_info=exc_info,
            )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "ERROR"
        assert data["exception"]["type"] == "ValueError"

    def test_formatter_masks_sensitive_fields(self) -> None:
        config = LoggingConfig(service_name="test")
        formatter = StructuredFormatter(config)
        record = logging.LogRecord(
            name="t",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="login",
            args=(),
            exc_info=None,
        )
        record.extra_fields = {"password": "supersecret", "username": "admin"}
        output = formatter.format(record)
        data = json.loads(output)
        assert data["password"] == "***REDACTED***"
        assert data["username"] == "admin"

    def test_formatter_includes_metadata(self) -> None:
        config = LoggingConfig(service_name="test_svc", environment="testing", version="1.0.0")
        formatter = StructuredFormatter(config)
        record = logging.LogRecord(
            name="t",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["service"] == "test_svc"
        assert data["environment"] == "testing"
        assert data["version"] == "1.0.0"
        assert "hostname" in data
        assert "timestamp" in data
        assert "module" in data
        assert "function" in data
        assert "line" in data
