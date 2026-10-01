from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from netmind.models.incident import IncidentStatus

class RootCauseCandidate(BaseModel):
    hypothesis: str = Field(..., description="Model-generated hypothesis")
    evidence: List[str] = Field(..., description="Evidence supporting the candidate")
    score: float = Field(..., description="Confidence score")

class IncidentAuditBase(BaseModel):
    action: str
    timestamp: datetime
    user_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class IncidentAuditResponse(IncidentAuditBase):
    id: str

    class Config:
        from_attributes = True

class IncidentBase(BaseModel):
    title: str
    description: Optional[str] = None
    severity: str
    status: IncidentStatus = IncidentStatus.DETECTED
    entity_id: str
    entity_type: str
    
    detection_timestamp: Optional[datetime] = None
    triggering_metric: Optional[str] = None
    observed_value: Optional[float] = None
    expected_value: Optional[float] = None
    
    related_telemetry: Optional[Dict[str, Any]] = None
    related_devices: Optional[List[str]] = None
    topology_relationships: Optional[Dict[str, Any]] = None
    recent_config_changes: Optional[List[Dict[str, Any]]] = None
    related_incidents: Optional[List[str]] = None
    
    candidate_root_causes: Optional[List[RootCauseCandidate]] = None
    recommended_actions: Optional[List[str]] = None
    
    human_approval_state: Optional[str] = None
    resolution: Optional[str] = None
    
    model_version: Optional[str] = None
    features: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None

class IncidentCreate(IncidentBase):
    pass

class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[IncidentStatus] = None
    human_approval_state: Optional[str] = None
    resolution: Optional[str] = None

class IncidentActionRequest(BaseModel):
    action: str = Field(..., description="E.g., Approve, Reject, Escalate, Resolve")
    resolution_notes: Optional[str] = None

class IncidentResponse(IncidentBase):
    id: str
    created_at: datetime
    updated_at: datetime
    audit_trail: Optional[List[IncidentAuditResponse]] = None

    class Config:
        from_attributes = True
