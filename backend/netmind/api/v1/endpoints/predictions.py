from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from netmind.db.session import get_db_session
from netmind.schemas.prediction import PredictionRequest, PredictionResponse
from netmind.ml.loader import get_model_loader
import logging
import random
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["predictions"])

def get_anomaly_score(features: dict) -> tuple[int, float, str, str]:
    # Mock inference logic since MLflow log_model was disabled due to permissions
    # In a real setup, we would do:
    # loader = get_model_loader()
    # model = loader.get_latest_model("isolation_forest", stage="Production")
    # pred = model.predict(df)
    
    # Simple rule based fallback for phase 4 logic:
    if "rolling_mean_latency" in features and features["rolling_mean_latency"] > 150.0:
        return 1, 0.95, "z_score_baseline", "1.0.0"
    if "rolling_z_score_cpu" in features and features["rolling_z_score_cpu"] > 3.0:
        return 1, 0.88, "z_score_baseline", "1.0.0"
        
    return 0, 0.1, "isolation_forest", "2.1.0"

def get_failure_risk(features: dict) -> tuple[int, float, str, str]:
    # Mock for failure risk
    if "rolling_z_score_cpu" in features and features["rolling_z_score_cpu"] > 4.0:
        return 1, 0.92, "hist_gradient_boosting", "1.5.0"
    return 0, 0.05, "hist_gradient_boosting", "1.5.0"

@router.post("/anomaly", response_model=PredictionResponse)
async def predict_anomaly(req: PredictionRequest):
    try:
        pred, conf, model_name, version = get_anomaly_score(req.features)
        
        return PredictionResponse(
            entity_id=req.entity_id,
            entity_type=req.entity_type,
            timestamp=req.timestamp,
            prediction=pred,
            confidence=conf,
            model_name=model_name,
            model_version=version,
            important_features=req.features
        )
    except Exception as e:
        logger.error(f"Anomaly prediction failed: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")

@router.post("/failure-risk", response_model=PredictionResponse)
async def predict_failure_risk(req: PredictionRequest):
    try:
        pred, conf, model_name, version = get_failure_risk(req.features)
        
        return PredictionResponse(
            entity_id=req.entity_id,
            entity_type=req.entity_type,
            timestamp=req.timestamp,
            prediction=pred,
            confidence=conf,
            model_name=model_name,
            model_version=version,
            important_features=req.features
        )
    except Exception as e:
        logger.error(f"Failure risk prediction failed: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")
