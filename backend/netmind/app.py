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

    from netmind.core.redis_client import init_redis
    try:
        await init_redis()
    except Exception as e:
        logger.warning(f"Redis client failed to connect on startup: {e}")

    logger.info("NetMind API ready")

    yield  # ← Application runs here

    logger.info("NetMind API shutting down")
    
    from netmind.core.redis_client import close_redis
    await close_redis()
    
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

    # ─── Production Engineering Middleware (Request ID, Timing, Rate Limiting) 
    from netmind.api.middleware import ProductionEngineeringMiddleware
    from netmind.core.redis_client import get_redis_client

    redis_client = None
    try:
        redis_client = get_redis_client()
    except RuntimeError:
        logger.warning("Redis not available for middleware.")

    app.add_middleware(ProductionEngineeringMiddleware, redis_client=redis_client)

    # ─── Routers ─────────────────────────────────────────────────────────────
    app.include_router(api_v1_router)

    return app
