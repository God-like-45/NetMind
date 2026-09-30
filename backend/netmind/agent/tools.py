import time
import httpx
from typing import Dict, Any, List

# Tools MUST validate inputs, enforce permissions, and have timeouts.

def get_device_telemetry(entity_id: str, current_user_roles: List[str]) -> Dict[str, Any]:
    if "engineer" not in current_user_roles and "admin" not in current_user_roles:
        raise PermissionError("Access denied to telemetry")
    # Stub: Would query TSDB
    return {"latency": 45.2, "packet_loss": 0.02, "cpu_utilization": 88.5, "timestamp": time.time()}

def get_anomaly_history(entity_id: str) -> Dict[str, Any]:
    return {"recent_anomalies": [{"type": "CPU Spike", "severity": "HIGH", "age_minutes": 15}]}

def get_failure_risk(entity_id: str) -> Dict[str, Any]:
    return {"failure_probability": 0.82, "predicted_failure_type": "OOM"}

def get_topology(entity_id: str) -> Dict[str, Any]:
    return {"neighbors": ["router-c", "switch-a"]}

def get_dependencies(entity_id: str) -> Dict[str, Any]:
    return {"services_affected": ["voip-core", "billing-gateway"]}

def get_configuration_changes(entity_id: str) -> Dict[str, Any]:
    return {"changes": [{"commit": "c98f2a", "author": "system", "description": "Update BGP policies"}]}

def search_incidents(query: str, current_user_roles: List[str]) -> List[Dict[str, Any]]:
    # Would call actual RAG endpoint in production. Stub for now.
    return [{"id": "INC-2025-04", "resolution": "Reverted firewall rule"}]

def search_runbooks(query: str, current_user_roles: List[str]) -> List[Dict[str, Any]]:
    # Call the RAG API locally
    try:
        res = httpx.post("http://localhost:8000/api/v1/rag/query", json={
            "query": query,
            "user_roles": current_user_roles,
            "top_k": 2
        }, timeout=5.0)
        if res.status_code == 200:
            return res.json().get("citations", [])
        return []
    except Exception:
        return [{"source": "runbook_bgp.md", "content": "Clear BGP sessions"}]
