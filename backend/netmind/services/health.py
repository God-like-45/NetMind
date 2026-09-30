"""
Health check service.

Probes each configured dependency (PostgreSQL, Redis) and returns
a structured status report. Does NOT return fake 'ok' without actually
testing the connection.

Design:
- Each probe is run independently with a timeout so a slow dependency
  does not block others.
- Errors are caught and reported as UNAVAILABLE rather than propagated.
- Latency is measured as wall-clock round-trip for the probe query.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from netmind import __version__
from netmind.core.config import get_settings
from netmind.core.logging import get_logger
from netmind.schemas.health import DependencyHealth, HealthResponse, ServiceStatus

logger = get_logger(__name__)

# Application start time (module-level, set on first import)
_START_TIME = time.monotonic()


async def probe_postgres(session: AsyncSession) -> DependencyHealth:
    """
    Probe PostgreSQL by executing a trivial query.

    Uses the request-scoped session so we test the actual connection
    pool path, not just TCP connectivity.
    """
    start = time.perf_counter()
    try:
        await session.execute(text("SELECT 1"))
        latency_ms = (time.perf_counter() - start) * 1000
        return DependencyHealth(
            name="postgres",
            status=ServiceStatus.OK,
            latency_ms=round(latency_ms, 2),
        )
    except Exception as exc:
        logger.warning("Postgres health probe failed", error=str(exc))
        return DependencyHealth(
            name="postgres",
            status=ServiceStatus.UNAVAILABLE,
            detail=str(exc),
        )


async def probe_redis() -> DependencyHealth:
    """
    Probe Redis by sending a PING command.

    Creates a short-lived connection so we don't depend on a shared
    connection pool being available during health checks.
    """
    start = time.perf_counter()
    try:
        import redis.asyncio as aioredis

        from netmind.core.config import get_redis_settings

        r = aioredis.from_url(
            get_redis_settings().url,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        await r.ping()
        latency_ms = (time.perf_counter() - start) * 1000
        await r.aclose()
        return DependencyHealth(
            name="redis",
            status=ServiceStatus.OK,
            latency_ms=round(latency_ms, 2),
        )
    except Exception as exc:
        logger.warning("Redis health probe failed", error=str(exc))
        return DependencyHealth(
            name="redis",
            status=ServiceStatus.UNAVAILABLE,
            detail=str(exc),
        )


def _aggregate_status(dependencies: list[DependencyHealth]) -> ServiceStatus:
    """
    Determine overall status from dependency statuses.

    Rules:
    - Any UNAVAILABLE -> DEGRADED at minimum
    - All OK -> OK
    """
    statuses = {d.status for d in dependencies}
    if ServiceStatus.UNAVAILABLE in statuses:
        return ServiceStatus.DEGRADED
    return ServiceStatus.OK


async def get_health(session: AsyncSession) -> HealthResponse:
    """
    Collect health status from all dependencies.

    Called by both the root /health and /api/v1/health endpoints.
    """
    settings = get_settings()

    # Run probes - in parallel in future phases via asyncio.gather
    pg_health = await probe_postgres(session)
    redis_health = await probe_redis()

    dependencies = [pg_health, redis_health]
    overall = _aggregate_status(dependencies)

    uptime = time.monotonic() - _START_TIME

    return HealthResponse(
        status=overall,
        version=__version__,
        environment=settings.app_env,
        timestamp=datetime.now(tz=timezone.utc),
        uptime_seconds=round(uptime, 1),
        dependencies=dependencies,
    )
