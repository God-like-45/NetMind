"""
Health check endpoints.

Two routes are registered:
  GET /health         - Root-level liveness probe (used by load balancers)
  GET /api/v1/health  - Full dependency health status

The root /health returns 200 as long as the API process is running
(used for container liveness probes that should not depend on DB).
The versioned endpoint returns the full dependency breakdown.
"""

from __future__ import annotations

from fastapi import APIRouter

from netmind.api.dependencies import DbSession
from netmind.schemas.health import HealthResponse, ServiceStatus
from netmind.services.health import get_health

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description=(
        "Returns 200 when the API process is alive. "
        "Does not check dependencies - use /api/v1/health for full status."
    ),
)
async def liveness_probe(db: DbSession) -> HealthResponse:
    """
    Lightweight liveness check.

    Suitable for container orchestrator liveness probes.
    Does probe PostgreSQL once to confirm the session layer is operational.
    """
    return await get_health(db)


@router.get(
    "/api/v1/health",
    response_model=HealthResponse,
    summary="Full dependency health check",
    description=(
        "Returns detailed health status for all system dependencies. "
        "Suitable for readiness probes and monitoring."
    ),
)
async def readiness_probe(db: DbSession) -> HealthResponse:
    """
    Full readiness check including all dependencies.

    Returns DEGRADED if any dependency is unavailable.
    Monitoring should alert on DEGRADED or UNAVAILABLE status.
    """
    return await get_health(db)
