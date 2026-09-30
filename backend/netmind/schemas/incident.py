from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from netmind.models.incident import IncidentStatus

class IncidentBase(BaseModel):
    title: str
    description: Optional[str] = None
    severity: str
    status: IncidentStatus = IncidentStatus.DETECTED
    entity_id: str
    entity_type: str
    confidence: Optional[float] = None
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

class IncidentResponse(IncidentBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
