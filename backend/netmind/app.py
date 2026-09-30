"""
FastAPI application factory.

Design principles:
- Application is created by a factory function (not module-level instantiation)
  so tests can create isolated instances without shared state.
- Startup/shutdown lifecycle hooks manage database connections and other resources.
- Middleware is layered in order: request ID -> logging -> CORS -> security headers.
- OpenAPI docs are only enabled in development mode.
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError as PydanticValidationError

from netmind import __version__
from netmind.api.exception_handlers import (
    netmind_exception_handler,
    validation_exception_handler,
)
from netmind.api.v1.router import api_v1_router
from netmind.core.config import get_settings
from netmind.core.exceptions import NetMindError
from netmind.core.logging import configure_logging, get_logger
from netmind.db.session import close_db, init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Startup: initialize DB, configure logging.
    Shutdown: dispose DB connections cleanly.
    """
    settings = get_settings()
    configure_logging()

    logger.info(
        "NetMind API starting",
        version=__version__,
        environment=settings.app_env,
    )

    await init_db()
    
    from netmind.core.kafka import get_kafka_producer, close_kafka_producer
    try:
        await get_kafka_producer()
    except Exception as e:
        logger.warning(f"Kafka producer failed to connect on startup: {e}")

    logger.info("NetMind API ready")

    yield  # ← Application runs here

    logger.info("NetMind API shutting down")
    await close_kafka_producer()
    await close_db()
    logger.info("NetMind API shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application instance.

    Returns a fully configured application ready for ASGI serving.
    """
    settings = get_settings()

    app = FastAPI(
        title="NetMind API",
        description=(
            "Autonomous Telecom Network Intelligence and Incident Resolution Platform. "
            "Provides endpoints for telemetry ingestion, anomaly detection, "
            "root cause analysis, AI-assisted investigation, and incident management."
        ),
        version=__version__,
        # Disable interactive docs in production
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # ─── Exception Handlers ──────────────────────────────────────────────────
    app.add_exception_handler(NetMindError, netmind_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, netmind_exception_handler)

    # ─── CORS ────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.api_cors_origins],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    # ─── Security Headers Middleware ─────────────────────────────────────────
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: object) -> Response:
        """Add security headers to every response."""
        # call_next is typed as Callable for mypy but works as awaitable
        import inspect

        if inspect.iscoroutinefunction(call_next):
            response: Response = await call_next(request)  # type: ignore[operator]
        else:
            response = call_next(request)  # type: ignore[operator]

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not settings.is_development:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains"
            )
        return response

    # ─── Request ID + Timing Middleware ──────────────────────────────────────
    @app.middleware("http")
    async def request_id_and_timing(request: Request, call_next: object) -> Response:
        """Attach request ID and measure processing time."""
        import inspect

        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        start = time.perf_counter()

        if inspect.iscoroutinefunction(call_next):
            response = await call_next(request)  # type: ignore[operator]
        else:
            response = call_next(request)  # type: ignore[operator]

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = str(round(duration_ms, 2))

        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            request_id=request_id,
        )
        return response

    # ─── Routers ─────────────────────────────────────────────────────────────
    app.include_router(api_v1_router)

    return app
