from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from netmind.db.session import get_db_session
from netmind.schemas.prediction import PredictionRequest, PredictionResponse, AnomalyResponse
from netmind.models.ml import Prediction, AnomalyDetection
from netmind.ml.loader import get_model_loader
import logging
import random
import pandas as pd
import time
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["predictions"])

def get_anomaly_score(features: dict) -> tuple[float, str, str, float]:
    loader = get_model_loader()
    start_time = time.time()
    try:
        model = loader.get_latest_run_model("netmind-anomaly-detection", "Isolation Forest", "isolation_forest")
        df = pd.DataFrame([features])
        
        score = -float(model.score_samples(df)[0])
        latency = (time.time() - start_time) * 1000
        
        return score, "isolation_forest", "latest", latency
    except Exception as e:
        logger.warning(f"Failed to load MLflow model, using fallback: {e}")
        latency = (time.time() - start_time) * 1000
        # Simple rule based fallback for phase 4 logic:
        if "rolling_mean_latency" in features and features["rolling_mean_latency"] > 150.0:
            return 1.2, "z_score_baseline", "1.0.0", latency
        if "rolling_z_score_cpu" in features and features["rolling_z_score_cpu"] > 3.0:
            return 0.8, "z_score_baseline", "1.0.0", latency
            
        return 0.1, "isolation_forest", "fallback", latency

def get_failure_risk(features: dict) -> tuple[int, float, str, str, float]:
    loader = get_model_loader()
    start_time = time.time()
    try:
        model = loader.get_latest_run_model("netmind-anomaly-detection", "LightGBM_Equivalent", "xgboost_baseline")
        df = pd.DataFrame([features])
        
        prob = float(model.predict_proba(df)[0][1])
        pred_label = int(prob > 0.5)
        latency = (time.time() - start_time) * 1000
        
        return pred_label, prob, "hist_gradient_boosting", "latest", latency
    except Exception as e:
        logger.warning(f"Failed to load MLflow model, using fallback: {e}")
        latency = (time.time() - start_time) * 1000
        if "rolling_z_score_cpu" in features and features["rolling_z_score_cpu"] > 4.0:
            return 1, 0.92, "hist_gradient_boosting", "fallback", latency
        return 0, 0.05, "hist_gradient_boosting", "fallback", latency

@router.post("/anomaly", response_model=AnomalyResponse)
async def predict_anomaly(req: PredictionRequest, db: AsyncSession = Depends(get_db_session)):
    try:
        score, model_name, version, latency = get_anomaly_score(req.features)
        
        metric = "unknown"
        observed_value = 0.0
        if "rolling_mean_latency" in req.features:
            metric = "latency"
            observed_value = req.features["rolling_mean_latency"]
        elif "rolling_z_score_cpu" in req.features:
            metric = "cpu"
            observed_value = req.features["rolling_z_score_cpu"]
            
        threshold = 0.5
        
        anomaly = AnomalyDetection(
            device_id=req.entity_id,
            timestamp=req.timestamp,
            metric=metric,
            observed_value=observed_value,
            anomaly_score=score,
            threshold=threshold,
            detector=model_name,
            detector_version=version
        )
        db.add(anomaly)
        await db.commit()
        
        return AnomalyResponse(
            anomaly_id=anomaly.anomaly_id,
            entity_id=req.entity_id,
            entity_type=req.entity_type,
            timestamp=req.timestamp,
            metric=metric,
            observed_value=observed_value,
            anomaly_score=score,
            threshold=threshold,
            detector=model_name,
            detector_version=version,
            important_features=req.features
        )
    except Exception as e:
        logger.error(f"Anomaly prediction failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Prediction failed")

@router.post("/failure-risk", response_model=PredictionResponse)
async def predict_failure_risk(req: PredictionRequest, db: AsyncSession = Depends(get_db_session)):
    try:
        pred, prob, model_name, version, latency = get_failure_risk(req.features)
        
        prediction = Prediction(
            device_id=req.entity_id,
            timestamp=req.timestamp,
            model_name=model_name,
            model_version=version,
            feature_version="1.0",
            prediction=pred,
            probability=prob,
            inference_latency=latency,
            input_window="10m"
        )
        db.add(prediction)
        await db.commit()
        
        return PredictionResponse(
            prediction_id=prediction.prediction_id,
            entity_id=req.entity_id,
            entity_type=req.entity_type,
            timestamp=req.timestamp,
            prediction=pred,
            probability=prob,
            inference_latency=latency,
            model_name=model_name,
            model_version=version,
            feature_version="1.0",
            input_window="10m",
            important_features=req.features
        )
    except Exception as e:
        logger.error(f"Failure risk prediction failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Prediction failed")
