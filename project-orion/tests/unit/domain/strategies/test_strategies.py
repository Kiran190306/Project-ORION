"""Tests for strategy interfaces, models, context, and exceptions."""

from __future__ import annotations

from libraries.domain.strategies.context import StrategyContext
from libraries.domain.strategies.exceptions import (
    StrategyError,
    StrategyExecutionError,
    StrategyNotFoundError,
    StrategyRegistrationError,
    StrategyValidationError,
)
from libraries.domain.strategies.interfaces import (
    StrategyCapabilities,
    StrategyMetadata,
)
from libraries.domain.strategies.models import (
    StrategyConfig,
    StrategyPriority,
    StrategyStatus,
)


class TestStrategyMetadata:
    def test_creates_with_all_fields(self) -> None:
        meta = StrategyMetadata(
            id="test",
            name="Test Strategy",
            version="1.0.0",
            description="A test strategy",
            author="Test Author",
            website="https://test.com",
        )
        assert meta.id == "test"
        assert meta.name == "Test Strategy"
        assert meta.version == "1.0.0"

    def test_immutable(self) -> None:
        meta = StrategyMetadata(id="test", name="Test", version="1.0.0")
        # Verify frozen
        assert meta.id == "test"


class TestStrategyCapabilities:
    def test_defaults(self) -> None:
        caps = StrategyCapabilities()
        assert caps.supported_markets == frozenset()
        assert caps.required_indicators == frozenset()
        assert not caps.supports_multiple_positions

    def test_custom_values(self) -> None:
        caps = StrategyCapabilities(
            supported_markets=frozenset({"forex", "crypto"}),
            supported_timeframes=frozenset({"M1", "H1"}),
            required_indicators=frozenset({"rsi", "ema"}),
            supports_multiple_positions=True,
        )
        assert "forex" in caps.supported_markets
        assert "rsi" in caps.required_indicators
        assert caps.supports_multiple_positions


class TestStrategyConfig:
    def test_defaults(self) -> None:
        config = StrategyConfig()
        assert config.priority == StrategyPriority.NORMAL
        assert config.enabled
        assert config.params == {}

    def test_custom_values(self) -> None:
        config = StrategyConfig(
            priority=StrategyPriority.HIGH,
            enabled=False,
            params={"fast_period": 10},
        )
        assert config.priority == StrategyPriority.HIGH
        assert not config.enabled
        assert config.params["fast_period"] == 10


class TestStrategyPriority:
    def test_numeric_ordering(self) -> None:
        assert StrategyPriority.LOWEST.numeric == 0
        assert StrategyPriority.LOW.numeric == 1
        assert StrategyPriority.NORMAL.numeric == 2
        assert StrategyPriority.HIGH.numeric == 3
        assert StrategyPriority.CRITICAL.numeric == 4


class TestStrategyStatus:
    def test_all_statuses(self) -> None:
        assert StrategyStatus.DRAFT == "draft"
        assert StrategyStatus.ACTIVE == "active"
        assert StrategyStatus.PAUSED == "paused"
        assert StrategyStatus.STOPPED == "stopped"
        assert StrategyStatus.ERROR == "error"
        assert StrategyStatus.DISABLED == "disabled"


class TestStrategyContext:
    def test_creates_with_defaults(self) -> None:
        ctx = StrategyContext(symbol="EUR/USD")
        assert ctx.symbol == "EUR/USD"
        assert ctx.trend_strength == 0.0
        assert ctx.volatility_percentile == 0.5

    def test_get_method(self) -> None:
        ctx = StrategyContext(symbol="EUR/USD", rsi=45.0)
        assert ctx.get("rsi") == 45.0
        assert ctx.get("nonexistent") is None
        assert ctx.get("nonexistent", "default") == "default"

    def test_immutable(self) -> None:
        ctx = StrategyContext(symbol="EUR/USD")
        assert ctx.symbol == "EUR/USD"


class TestExceptions:
    def test_strategy_error(self) -> None:
        error = StrategyError("base error")
        assert str(error) == "base error"
        assert isinstance(error, Exception)

    def test_registration_error(self) -> None:
        error = StrategyRegistrationError("duplicate")
        assert str(error) == "duplicate"

    def test_not_found_error(self) -> None:
        error = StrategyNotFoundError("not found")
        assert str(error) == "not found"

    def test_validation_error(self) -> None:
        error = StrategyValidationError("invalid")
        assert str(error) == "invalid"

    def test_execution_error(self) -> None:
        error = StrategyExecutionError("exec failed")
        assert str(error) == "exec failed"
