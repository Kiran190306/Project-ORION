"""
Project ORION - Common Utilities

This module provides common helper functions, decorators, and utilities
used across the platform. All functions here are stateless and purely
functional where possible.

Dependencies: None (standard library only)
"""

from .decorators import retry, singleton, validate_args
from .result import Failure, Result, Success

__all__ = [
    "Result",
    "Success",
    "Failure",
    "singleton",
    "validate_args",
    "retry",
]
