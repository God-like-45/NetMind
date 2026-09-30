"""
Health endpoint tests.

These tests use FastAPI's TestClient which runs the app in a synchronous context.
The database and Redis probes are mocked so no real infrastructure is needed.

Tests verify:
- Correct response schema
- HTTP status codes
- Dependency status aggregation
- Response headers (X-Request-ID, X-Process-Time-Ms)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from netmind.schemas.health import HealthResponse, ServiceStatus


@pytest.fixture()
def client() -> TestClient:
    """
    Create a TestClient with mocked database lifecycle.

    We patch init_db and close_db so no real DB is needed.
    Individual tests mock the probe functions as needed.
    """
    with (
        patch("netmind.app.init_db", new_callable=AsyncMock),
        patch("netmind.app.close_db", new_callable=AsyncMock),
        patch("netmind.db.session.get_session_factory"),
    ):
        from netmind.app import create_app

        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


class TestHealthEndpoints:
    """Tests for GET /health and GET /api/v1/health."""

    def test_root_health_returns_200_when_all_ok(self, client: TestClient) -> None:
        """Health endpoint should return 200 when all dependencies are OK."""
        from netmind.schemas.health import DependencyHealth

        mock_response = HealthResponse(
            status=ServiceStatus.OK,
            version="0.1.0",
            environment="development",
            timestamp=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
            uptime_seconds=1.0,
            dependencies=[
                DependencyHealth(name="postgres", status=ServiceStatus.OK, latency_ms=1.0),
                DependencyHealth(name="redis", status=ServiceStatus.OK, latency_ms=0.5),
            ],
        )

        with patch(
            "netmind.api.v1.endpoints.health.get_health",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            response = client.get("/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["version"] == "0.1.0"
        assert len(body["dependencies"]) == 2

    def test_versioned_health_returns_200(self, client: TestClient) -> None:
        """GET /api/v1/health should return 200."""
        from netmind.schemas.health import DependencyHealth

        mock_response = HealthResponse(
            status=ServiceStatus.OK,
            version="0.1.0",
            environment="development",
            timestamp=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
            uptime_seconds=5.0,
            dependencies=[
                DependencyHealth(name="postgres", status=ServiceStatus.OK, latency_ms=1.0),
            ],
        )

        with patch(
            "netmind.api.v1.endpoints.health.get_health",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            response = client.get("/api/v1/health")

        assert response.status_code == 200

    def test_health_response_has_request_id_header(self, client: TestClient) -> None:
        """Every response must include X-Request-ID header."""
        from netmind.schemas.health import DependencyHealth

        mock_response = HealthResponse(
            status=ServiceStatus.OK,
            version="0.1.0",
            environment="development",
            timestamp=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
            uptime_seconds=1.0,
            dependencies=[],
        )

        with patch(
            "netmind.api.v1.endpoints.health.get_health",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            response = client.get("/health")

        assert "x-request-id" in response.headers

    def test_health_response_matches_schema(self, client: TestClient) -> None:
        """Response body must parse as HealthResponse without errors."""
        from netmind.schemas.health import DependencyHealth

        mock_response = HealthResponse(
            status=ServiceStatus.DEGRADED,
            version="0.1.0",
            environment="development",
            timestamp=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
            uptime_seconds=10.0,
            dependencies=[
                DependencyHealth(name="postgres", status=ServiceStatus.OK, latency_ms=1.0),
                DependencyHealth(
                    name="redis",
                    status=ServiceStatus.UNAVAILABLE,
                    detail="Connection refused",
                ),
            ],
        )

        with patch(
            "netmind.api.v1.endpoints.health.get_health",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            response = client.get("/health")

        # Must parse cleanly into the schema
        parsed = HealthResponse.model_validate(response.json())
        assert parsed.status == ServiceStatus.DEGRADED
        assert len(parsed.dependencies) == 2

    def test_unknown_route_returns_404(self, client: TestClient) -> None:
        """Unknown routes must return 404."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404


class TestHealthService:
    """Unit tests for the health service logic (no HTTP)."""

    @pytest.mark.asyncio
    async def test_aggregate_status_all_ok(self) -> None:
        """All OK dependencies -> overall OK."""
        from netmind.schemas.health import DependencyHealth
        from netmind.services.health import _aggregate_status

        deps = [
            DependencyHealth(name="postgres", status=ServiceStatus.OK),
            DependencyHealth(name="redis", status=ServiceStatus.OK),
        ]
        assert _aggregate_status(deps) == ServiceStatus.OK

    @pytest.mark.asyncio
    async def test_aggregate_status_one_unavailable(self) -> None:
        """One UNAVAILABLE dependency -> overall DEGRADED."""
        from netmind.schemas.health import DependencyHealth
        from netmind.services.health import _aggregate_status

        deps = [
            DependencyHealth(name="postgres", status=ServiceStatus.OK),
            DependencyHealth(name="redis", status=ServiceStatus.UNAVAILABLE),
        ]
        assert _aggregate_status(deps) == ServiceStatus.DEGRADED
