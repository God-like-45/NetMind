from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class PredictionRequest(BaseModel):
    entity_id: str = Field(..., description="ID of the device, link, or interface")
    entity_type: str = Field(..., description="Type of the entity, e.g., 'device'")
    features: Dict[str, float] = Field(..., description="Feature map for inference")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PredictionResponse(BaseModel):
    entity_id: str
    entity_type: str
    timestamp: datetime
    prediction: int = Field(..., description="1 for anomaly/failure, 0 for normal")
    confidence: Optional[float] = Field(None, description="Probability or anomaly score")
    model_name: str
    model_version: str
    important_features: Optional[Dict[str, float]] = None
