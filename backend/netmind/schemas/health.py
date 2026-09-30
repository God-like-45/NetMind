"""
Health check response schemas.

Separated from the endpoint to allow reuse across tests
and potential monitoring integrations.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ServiceStatus(StrEnum):
    """Possible status values for a service dependency."""

    OK = "ok"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class DependencyHealth(BaseModel):
    """Health status of a single external dependency."""

    name: str
    status: ServiceStatus
    latency_ms: float | None = Field(default=None, description="Round-trip latency in ms")
    detail: str | None = None


class HealthResponse(BaseModel):
    """
    Full system health response.

    Returned by GET /health and GET /api/v1/health.
    The 'status' field reflects the worst dependency.
    """

    status: ServiceStatus
    version: str
    environment: str
    timestamp: datetime
    uptime_seconds: float
    dependencies: list[DependencyHealth] = Field(default_factory=list)

    model_config = {"json_schema_extra": {
        "example": {
            "status": "ok",
            "version": "0.1.0",
            "environment": "development",
            "timestamp": "2026-09-30T15:00:00Z",
            "uptime_seconds": 42.3,
            "dependencies": [
                {"name": "postgres", "status": "ok", "latency_ms": 1.2},
                {"name": "redis", "status": "ok", "latency_ms": 0.4},
            ],
        }
    }}
