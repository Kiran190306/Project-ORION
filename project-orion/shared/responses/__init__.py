"""
Project ORION - Standardized API Responses

Consistent response structures for all API endpoints.
Supports pagination, error details, and metadata.

Design:
- ApiResponse: Base response envelope
- PaginatedResponse: Paginated data response
- ErrorResponse: Error response with details
- SuccessResponse: Success response with data
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, Optional

from shared.common.result import Failure, Result, Success
from shared.types import T


@dataclass(frozen=True)
class ResponseMetadata:
    """Metadata attached to every API response."""

    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: str = "1.0"
    request_id: str = ""
    service: str = ""


@dataclass(frozen=True)
class ApiResponse(Generic[T]):
    """Standard API response envelope."""

    success: bool
    data: Optional[T] = None
    error: Optional[dict[str, Any]] = None
    message: str = ""
    metadata: ResponseMetadata = field(default_factory=ResponseMetadata)

    @classmethod
    def ok(
        cls,
        data: T,
        message: str = "Success",
        **kwargs: Any,
    ) -> ApiResponse[T]:
        """Create a success response."""
        return cls(
            success=True,
            data=data,
            message=message,
            **kwargs,
        )

    @classmethod
    def fail(
        cls,
        message: str = "An error occurred",
        code: str = "INTERNAL_ERROR",
        details: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ApiResponse[T]:
        """Create an error response."""
        return cls(
            success=False,
            error={
                "code": code,
                "message": message,
                "details": details or {},
            },
            message=message,
            **kwargs,
        )

    @classmethod
    def from_result(
        cls,
        result: Result[T, Exception],
        success_message: str = "Success",
        **kwargs: Any,
    ) -> ApiResponse[T]:
        """Create response from a Result monad."""
        match result:
            case Success(data):
                return cls.ok(data, message=success_message, **kwargs)
            case Failure(error):
                return cls(
                    success=False,
                    error={
                        "code": getattr(error, "code", type(error).__name__),
                        "message": str(error),
                        "details": getattr(error, "details", None) or {},
                    },
                    message=str(error),
                    **kwargs,
                )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        result: dict[str, Any] = {
            "success": self.success,
            "message": self.message,
            "metadata": {
                "timestamp": self.metadata.timestamp,
                "version": self.metadata.version,
                "request_id": self.metadata.request_id,
                "service": self.metadata.service,
            },
        }
        if self.data is not None:
            result["data"] = self.data
        if self.error is not None:
            result["error"] = self.error
        return result


@dataclass(frozen=True)
class PaginatedResponse(Generic[T]):
    """Paginated response wrapper."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[T]:
        """Create a paginated response with calculated metadata."""
        total_pages = max(1, (total + page_size - 1) // page_size)
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        return self.page > 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary wrapped in ApiResponse."""
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_previous": self.has_previous,
        }


def success_response(
    data: Any = None,
    message: str = "Success",
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a success response dictionary."""
    return ApiResponse.ok(data, message=message, **kwargs).to_dict()


def error_response(
    message: str = "An error occurred",
    code: str = "INTERNAL_ERROR",
    details: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create an error response dictionary."""
    return ApiResponse.fail(
        message=message,
        code=code,
        details=details,
        **kwargs,
    ).to_dict()


def paginated_response(
    items: list[Any],
    total: int,
    page: int,
    page_size: int,
    message: str = "Success",
) -> dict[str, Any]:
    """Create a paginated API response."""
    paginated = PaginatedResponse.create(items, total, page, page_size)
    response = ApiResponse.ok(
        data=paginated.to_dict(),
        message=message,
    )
    return response.to_dict()
