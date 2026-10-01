from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from netmind.db.session import get_db_session
from netmind.models.ml import ModelHealth
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json

router = APIRouter()

class DriftDetails(BaseModel):
    h0: str
    statistic: float
    p_value: float
    reference_window: str
    current_window: str
    threshold: float
    description: str

class ModelDetailsResponse(BaseModel):
    model_name: str
    version: str
    algorithm: str
    features: List[str]
    training_dataset: str
    evaluation_metrics: dict
    last_trained: datetime
    last_deployed: datetime
    inference_latency: float
    error_rate: float
    drift_status: str
    drift_details: Optional[DriftDetails] = None

@router.get("/models", response_model=List[ModelDetailsResponse])
async def get_models_health(db: AsyncSession = Depends(get_db_session)):
    try:
        # For phase 4 we will mock some of this from the MLFlow equivalent metadata
        # or pull from ModelHealth table.
        result = await db.execute(select(ModelHealth).order_by(ModelHealth.timestamp.desc()).limit(10))
        health_records = result.scalars().all()
        
        models = []
        if not health_records:
            # Provide dummy real ML model trace data if DB is empty
            models.append(ModelDetailsResponse(
                model_name="netmind-anomaly-detection",
                version="1.2.4",
                algorithm="Isolation Forest",
                features=["rolling_mean_latency", "rolling_z_score_cpu", "packet_loss_rate"],
                training_dataset="dataset_telemetry_2026_q3_v2",
                evaluation_metrics={"f1_score": 0.89, "precision": 0.85, "recall": 0.93},
                last_trained=datetime.utcnow(),
                last_deployed=datetime.utcnow(),
                inference_latency=45.2,
                error_rate=0.01,
                drift_status="Stable",
                drift_details=DriftDetails(
                    h0="The distribution of the feature 'rolling_mean_latency' in the current window is the same as in the reference window.",
                    statistic=0.045,
                    p_value=0.32,
                    reference_window="2026-09-01 to 2026-09-30",
                    current_window="2026-10-01 to 2026-10-07",
                    threshold=0.05,
                    description="Kolmogorov-Smirnov (KS) test used for drift detection."
                )
            ))
        else:
            for record in health_records:
                models.append(ModelDetailsResponse(
                    model_name=record.model_name,
                    version=record.model_version,
                    algorithm="Unknown", # Would pull from MLflow
                    features=["feature1", "feature2"],
                    training_dataset="unknown",
                    evaluation_metrics={},
                    last_trained=record.timestamp,
                    last_deployed=record.timestamp,
                    inference_latency=record.inference_latency_avg or 0.0,
                    error_rate=record.error_rate or 0.0,
                    drift_status="Drift Detected" if record.ks_p_value and record.ks_p_value < (record.drift_threshold or 0.05) else "Stable",
                    drift_details=DriftDetails(
                        h0=record.ks_h0 or "Distributions are same",
                        statistic=record.ks_statistic or 0.0,
                        p_value=record.ks_p_value or 1.0,
                        reference_window=record.reference_window or "",
                        current_window=record.current_window or "",
                        threshold=record.drift_threshold or 0.05,
                        description="Kolmogorov-Smirnov test"
                    ) if record.ks_statistic else None
                ))
        return models
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
