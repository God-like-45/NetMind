from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class PredictionRequest(BaseModel):
    entity_id: str = Field(..., description="ID of the device, link, or interface")
    entity_type: str = Field(..., description="Type of the entity, e.g., 'device'")
    features: Dict[str, float] = Field(..., description="Feature map for inference")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PredictionResponse(BaseModel):
    prediction_id: str = Field(..., description="Unique ID for the prediction")
    entity_id: str
    entity_type: str
    timestamp: datetime
    prediction: int = Field(..., description="1 for anomaly/failure, 0 for normal")
    probability: Optional[float] = Field(None, description="Calibrated probability if applicable")
    inference_latency: Optional[float] = Field(None, description="Inference latency in milliseconds")
    model_name: str
    model_version: str
    feature_version: Optional[str] = None
    input_window: Optional[str] = None
    important_features: Optional[Dict[str, float]] = None

class AnomalyResponse(BaseModel):
    anomaly_id: str = Field(..., description="Unique ID for the anomaly detection")
    entity_id: str
    entity_type: str
    timestamp: datetime
    metric: str
    observed_value: float
    expected_value: Optional[float] = None
    anomaly_score: float = Field(..., description="Raw anomaly score (e.g., from Isolation Forest)")
    threshold: float
    detector: str
    detector_version: str
    important_features: Optional[Dict[str, float]] = None

class ForecastingResponse(BaseModel):
    forecast_id: str = Field(..., description="Unique ID for the forecast")
    entity_id: str
    entity_type: str
    timestamp: datetime
    metric: str
    forecast: float
    prediction_interval_lower: Optional[float] = None
    prediction_interval_upper: Optional[float] = None
    forecast_horizon: str
    model_name: str
    model_version: str
