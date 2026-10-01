"""API v1 router - aggregates all v1 endpoint routers."""

from fastapi import APIRouter

from netmind.api.v1.endpoints.health import router as health_router
from netmind.api.v1.endpoints.network import router as network_router
from netmind.api.v1.endpoints.predictions import router as predictions_router
from netmind.api.v1.endpoints.incidents import router as incidents_router
from netmind.api.v1.endpoints.topology import router as topology_router
from netmind.api.v1.endpoints.rag import router as rag_router
from netmind.api.v1.endpoints.agent import router as agent_router
from netmind.api.v1.endpoints.models import router as models_router

api_v1_router = APIRouter()

# Health is registered at module level only (not under /api/v1 prefix)
# because liveness probes need /health at root and /api/v1/health for versioned access.
# Both are handled by the health router itself using full path declarations.
api_v1_router.include_router(health_router)
api_v1_router.include_router(network_router, prefix="/api/v1/network", tags=["network"])
api_v1_router.include_router(predictions_router, prefix="/api/v1", tags=["predictions"])
api_v1_router.include_router(incidents_router, prefix="/api/v1", tags=["incidents"])
api_v1_router.include_router(topology_router, prefix="/api/v1/topology", tags=["topology"])
api_v1_router.include_router(rag_router, prefix="/api/v1/rag", tags=["rag"])
api_v1_router.include_router(agent_router, prefix="/api/v1/agent", tags=["agent"])
api_v1_router.include_router(models_router, prefix="/api/v1/models", tags=["models"])

from netmind.api.v1.endpoints.auth import router as auth_router
api_v1_router.include_router(auth_router, prefix="/api/v1")

__all__ = ["api_v1_router"]
