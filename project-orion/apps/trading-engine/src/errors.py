"""Centralised exception handlers for the Trading Engine FastAPI application.

Rules:
- No stack traces are returned to clients.
- All errors include a correlation_id and timestamp.
- Unexpected exceptions are logged in full server-side and return a safe 500.
- Domain exceptions are translated at this application boundary.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import ConfigurationError
from .schemas import ErrorResponse

logger = logging.getLogger("trading_engine.errors")


def _correlation_id(request: Request) -> str:
    """Extract correlation ID from request state or headers."""
    # Set by CorrelationIdMiddleware / ObservabilityMiddleware
    cid: str = getattr(request.state, "correlation_id", "")
    if not cid:
        cid = request.headers.get("x-correlation-id", "")
    return cid


def _error_response(error: str, message: str, status_code: int, correlation_id: str) -> JSONResponse:
    payload = ErrorResponse(
        error=error,
        message=message,
        correlation_id=correlation_id,
    )
    headers = {"x-correlation-id": correlation_id} if correlation_id else None
    return JSONResponse(status_code=status_code, content=payload.model_dump(), headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI application."""

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Return 422 with structured error for request validation failures."""
        cid = _correlation_id(request)
        # Summarise validation errors without exposing internals
        messages = "; ".join(
            f"{' → '.join(str(l) for l in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        )
        logger.warning(
            "Validation error on %s %s: %s [cid=%s]",
            request.method,
            request.url.path,
            messages,
            cid,
        )
        return _error_response(
            error="validation_error",
            message=messages,
            status_code=422,
            correlation_id=cid,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Return structured JSON for all HTTP errors."""
        cid = _correlation_id(request)
        logger.warning(
            "HTTP %d on %s %s [cid=%s]",
            exc.status_code,
            request.method,
            request.url.path,
            cid,
        )
        return _error_response(
            error="http_error",
            message=str(exc.detail),
            status_code=exc.status_code,
            correlation_id=cid,
        )

    @app.exception_handler(ConfigurationError)
    async def configuration_error_handler(
        request: Request, exc: ConfigurationError
    ) -> JSONResponse:
        """Return 503 for configuration / infrastructure errors."""
        cid = _correlation_id(request)
        logger.error(
            "Configuration error on %s %s: %s [cid=%s]",
            request.method,
            request.url.path,
            exc,
            cid,
        )
        return _error_response(
            error="configuration_error",
            message="Service is not properly configured. Check server logs.",
            status_code=503,
            correlation_id=cid,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Catch-all handler — logs full details, returns safe 500 to client."""
        cid = _correlation_id(request)
        logger.exception(
            "Unhandled exception on %s %s [cid=%s]: %s",
            request.method,
            request.url.path,
            cid,
            exc,
        )
        return _error_response(
            error="internal_error",
            message="An unexpected error occurred. Please try again later.",
            status_code=500,
            correlation_id=cid,
        )
