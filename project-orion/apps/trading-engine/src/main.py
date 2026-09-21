"""Project ORION — Trading Engine ASGI Application Entrypoint.

Production-grade FastAPI application assembly:
- Application factory pattern
- Async lifespan management (startup & graceful shutdown)
- Centralised exception handling (no leaked stack traces)
- Dependency injection (no global mutable state)
- Health, metrics, authentication, account, orders, positions, trades, portfolio, and dashboard routes
- Security headers and correlation ID propagation middleware
"""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.execution.paper_execution import PaperExecutionAdapter
from libraries.infrastructure.persistence.config import DatabaseManager
from libraries.observability.logging import set_correlation_id

from .config import AppSettings, parse_cors_origins
from .errors import register_exception_handlers
from .lifespan import create_lifespan
from .routes.account import router as account_router
from .routes.auth import router as auth_router
from .routes.billing import router as billing_router
from .routes.dashboard import router as dashboard_router
from .routes.health import router as health_router
from .routes.market_data import router as market_data_router
from .routes.metrics import router as metrics_router
from .routes.onboarding import router as onboarding_router
from .routes.orders import router as orders_router
from .routes.organization import router as organization_router
from .routes.paper import router as paper_router
from .routes.portfolio import router as portfolio_router
from .routes.positions import router as positions_router
from .routes.risk import router as risk_router
from .routes.strategies import router as strategies_router
from .routes.subscription import router as subscription_router
from .routes.trades import router as trades_router
from .routes.trading import router as trading_router
from .routes.worker import router as worker_router

logger = logging.getLogger("trading_engine.main")


def create_app(
    settings: AppSettings | None = None,
    db_manager: DatabaseManager | None = None,
    redis_client: RedisClient | None = None,
    paper_adapter: PaperExecutionAdapter | None = None,
    worker: Any | None = None,
    market_data_service: Any | None = None,
) -> FastAPI:
    """FastAPI Application Factory for Project ORION Trading Engine.

    Args:
        settings: Optional AppSettings override for testing.
        db_manager: Optional DatabaseManager override for testing.
        redis_client: Optional RedisClient override for testing.
        paper_adapter: Optional PaperExecutionAdapter override for testing.
        worker: Optional AutonomousWorkerCoordinator override for testing.

    Returns:
        Configured FastAPI application instance.
    """
    lifespan = create_lifespan(
        settings_override=settings,
        db_manager_override=db_manager,
        redis_client_override=redis_client,
        paper_adapter_override=paper_adapter,
        worker_override=worker,
        market_data_service_override=market_data_service,
    )

    app = FastAPI(
        title="Project ORION — Trading Engine",
        description="Institutional-grade automated Forex trading platform runtime",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ─── Middleware ─────────────────────────────────────────────────────────
    if settings is not None:
        cors_origins: list[str] = list(settings.cors_origins)
    else:
        raw_cors = os.environ.get("ORION_CORS_ORIGINS")
        if raw_cors:
            cors_origins = list(parse_cors_origins(raw_cors))
        else:
            cors_origins = [
                "http://localhost:5173",
                "http://localhost:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:3000",
            ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def correlation_id_middleware(
        request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        """Propagate or generate X-Correlation-ID for all HTTP requests."""
        cid = request.headers.get("x-correlation-id") or uuid.uuid4().hex
        request.state.correlation_id = cid
        set_correlation_id(cid)

        response: Response = await call_next(request)
        response.headers["x-correlation-id"] = cid
        return response

    @app.middleware("http")
    async def security_headers_middleware(
        request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        """Apply institutional-grade HTTP security headers to all responses."""
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' ws: wss:;"
        )
        return response

    # ─── Exception Handlers ─────────────────────────────────────────────────
    register_exception_handlers(app)

    # ─── Routers ────────────────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(auth_router)
    app.include_router(onboarding_router)
    app.include_router(organization_router)
    app.include_router(account_router)
    app.include_router(worker_router)
    app.include_router(strategies_router)
    app.include_router(risk_router)
    app.include_router(trading_router)
    app.include_router(paper_router)
    app.include_router(orders_router)
    app.include_router(positions_router)
    app.include_router(trades_router)
    app.include_router(portfolio_router)
    app.include_router(dashboard_router)
    app.include_router(market_data_router)
    app.include_router(subscription_router)
    app.include_router(billing_router)

    return app


# Default ASGI application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = AppSettings.from_env()
    uvicorn.run(
        "apps.trading-engine.src.main:app",
        host=settings.server_host,
        port=settings.server_port,
        log_level=settings.log_level.lower(),
        reload=settings.is_development,
    )
