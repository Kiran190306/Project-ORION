"""
Tests for the Result monad pattern.
"""

import pytest

from shared.common.result import Failure, Success, attempt, failure, success


class TestResult:
    """Test suite for Result monad."""

    def test_success_creation(self):
        result = success(42)
        assert isinstance(result, Success)
        assert result.data == 42

    def test_failure_creation(self):
        result = failure(ValueError("test error"))
        assert isinstance(result, Failure)
        assert "test error" in result.message

    def test_success_unwrap(self):
        result = success(42)
        assert result.unwrap() == 42

    def test_failure_unwrap_raises(self):
        result = failure(ValueError("test error"))
        with pytest.raises(ValueError, match="test error"):
            result.unwrap()

    def test_success_map(self):
        result = success(42)
        mapped = result.map(lambda x: x * 2)
        assert isinstance(mapped, Success)
        assert mapped.data == 84

    def test_failure_map_returns_self(self):
        result = failure(ValueError("test error"))
        mapped = result.map(lambda x: x * 2)
        assert isinstance(mapped, Failure)

    def test_success_bind(self):
        result = success(42)
        bound = result.bind(lambda x: success(x * 2))
        assert isinstance(bound, Success)
        assert bound.data == 84

    def test_failure_bind_returns_self(self):
        result = failure(ValueError("test error"))
        bound = result.bind(lambda x: success(x * 2))
        assert isinstance(bound, Failure)

    def test_attempt_success(self):
        def fn():
            return 42

        result = attempt(fn)
        assert isinstance(result, Success)
        assert result.data == 42

    def test_attempt_failure(self):
        def fn():
            raise ValueError("boom")

        result = attempt(fn)
        assert isinstance(result, Failure)
        assert "boom" in result.message


class TestSuccess:
    """Test suite for Success."""

    def test_unwrap_or_returns_data(self):
        s = Success(42)
        assert s.unwrap_or(0) == 42

    def test_repr(self):
        s = Success(42)
        assert "Success" in repr(s)


class TestFailure:
    """Test suite for Failure."""

    def test_unwrap_or_returns_default(self):
        f = Failure(ValueError("error"))
        assert f.unwrap_or(0) == 0

    def test_repr(self):
        f = Failure(ValueError("error"))
        assert "Failure" in repr(f)

    def test_auto_code(self):
        f = Failure(ValueError("error"))
        assert f.code == "ValueError"
