from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from netmind.agent.workflow import build_investigation_graph
from netmind.agent.state import AgentStateEnum

router = APIRouter()
graph = build_investigation_graph()

class InvestigationRequest(BaseModel):
    incident_id: str
    entity_id: str

class InvestigationResponse(BaseModel):
    status: str
    finding: str
    confidence: float
    recommended_action: str
    risk: str
    audit_log: list

@router.post("/investigate", response_model=InvestigationResponse)
async def run_investigation(req: InvestigationRequest):
    # Initialize the state
    initial_state = {
        "incident_id": req.incident_id,
        "entity_id": req.entity_id,
        "status": AgentStateEnum.CREATED,
        "plan": [],
        "telemetry_data": {},
        "topology_data": {},
        "ml_predictions": {},
        "historical_incidents": [],
        "engineering_docs": [],
        "evidence": [],
        "is_evidence_valid": False,
        "recommendation": {},
        "audit_log": []
    }
    
    try:
        # Run the workflow
        result = graph.invoke(initial_state)
        
        return InvestigationResponse(
            status=result["status"],
            finding=result["recommendation"].get("finding", ""),
            confidence=result["recommendation"].get("confidence", 0.0),
            recommended_action=result["recommendation"].get("recommended_action", ""),
            risk=result["recommendation"].get("risk", "UNKNOWN"),
            audit_log=result["audit_log"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
