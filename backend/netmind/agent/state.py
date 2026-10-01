from enum import Enum
from typing import TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel, Field

class AgentStateEnum(str, Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    INVESTIGATING = "INVESTIGATING"
    ANALYZING = "ANALYZING"
    VALIDATING = "VALIDATING"
    RECOMMENDING = "RECOMMENDING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    ESCALATED = "ESCALATED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class WorkflowState(TypedDict, total=False):
    incident_id: str
    entity_id: str
    status: AgentStateEnum
    iteration_count: int
    validation_feedback: str
    plan: List[str]
    telemetry_data: Dict[str, Any]
    topology_data: Dict[str, Any]
    ml_predictions: Dict[str, Any]
    historical_incidents: List[Dict[str, Any]]
    engineering_docs: List[Dict[str, Any]]
    evidence: List[str]
    is_evidence_valid: bool
    recommendation: Dict[str, Any]
    audit_log: List[Dict[str, Any]]
    error: Optional[str]

# Structured output schemas for the LLM
class PlanOutput(BaseModel):
    steps: List[str] = Field(description="List of steps to investigate the incident.")

class EvidenceValidation(BaseModel):
    is_valid: bool = Field(description="True if the evidence strongly supports a root cause.")
    reason: str = Field(description="Explanation of the validation decision.")

class RecommendationOutput(BaseModel):
    finding: str = Field(description="Summary of the root cause finding.")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0.")
    recommended_action: str = Field(description="Step-by-step recommended action.")
    risk: str = Field(description="Risk level of applying the recommendation (e.g., LOW, HIGH).")
