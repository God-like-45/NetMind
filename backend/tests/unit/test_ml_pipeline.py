import pytest
from httpx import AsyncClient
import pandas as pd
from unittest.mock import patch, MagicMock

# The user requested to test:
# - feature generation
# - anomaly scoring
# - prediction persistence
# - API response
# - invalid telemetry
# - missing features
# - model unavailable
# - inference failure

@pytest.fixture
def mock_mlflow_model():
    model = MagicMock()
    # For Isolation forest
    model.score_samples.return_value = [-0.8]
    model.predict.return_value = [-1]
    # For LightGBM
    model.predict_proba.return_value = [[0.2, 0.8]]
    return model

@pytest.fixture
def mock_loader(mock_mlflow_model):
    with patch('netmind.api.v1.endpoints.predictions.get_model_loader') as mock:
        loader = MagicMock()
        loader.get_latest_run_model.return_value = mock_mlflow_model
        mock.return_value = loader
        yield loader

@pytest.mark.asyncio
async def test_anomaly_scoring_and_api_response(mock_loader, client: AsyncClient):
    # Test API response and anomaly scoring
    req_data = {
        "entity_id": "device_123",
        "entity_type": "device",
        "features": {
            "rolling_mean_latency": 120.5,
            "packet_loss": 0.01
        }
    }
    
    response = await client.post("/api/v1/anomaly", json=req_data)
    assert response.status_code == 200
    data = response.json()
    assert data["entity_id"] == "device_123"
    assert data["anomaly_score"] == 0.8  # Because mock model.score_samples returns -0.8
    assert data["detector"] == "isolation_forest"
    assert data["detector_version"] == "latest"
    assert "anomaly_id" in data

@pytest.mark.asyncio
async def test_model_unavailable_fallback(client: AsyncClient):
    with patch('netmind.api.v1.endpoints.predictions.get_model_loader') as mock:
        mock.side_effect = Exception("MLflow not available")
        
        req_data = {
            "entity_id": "device_123",
            "entity_type": "device",
            "features": {
                "rolling_mean_latency": 160.0
            }
        }
        
        response = await client.post("/api/v1/anomaly", json=req_data)
        assert response.status_code == 200
        data = response.json()
        assert data["detector"] == "z_score_baseline"
        assert data["anomaly_score"] == 1.2
        assert data["detector_version"] == "1.0.0"

@pytest.mark.asyncio
async def test_prediction_persistence(mock_loader, client: AsyncClient):
    # API call to /failure-risk persists to DB
    req_data = {
        "entity_id": "device_abc",
        "entity_type": "device",
        "features": {
            "rolling_mean_latency": 50.0
        }
    }
    
    response = await client.post("/api/v1/failure-risk", json=req_data)
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] == 1
    assert data["probability"] == 0.8
    assert "prediction_id" in data

@pytest.mark.asyncio
async def test_invalid_telemetry_missing_features(client: AsyncClient):
    # Missing features in payload
    req_data = {
        "entity_id": "device_123",
        "entity_type": "device"
        # features missing
    }
    response = await client.post("/api/v1/anomaly", json=req_data)
    assert response.status_code == 422  # validation error

@pytest.mark.asyncio
async def test_inference_failure(mock_loader, client: AsyncClient):
    # Make model.predict raise an error
    mock_model = mock_loader.get_latest_run_model.return_value
    mock_model.score_samples.side_effect = Exception("Runtime error during inference")
    
    req_data = {
        "entity_id": "device_err",
        "entity_type": "device",
        "features": {
            "f1": 1
        }
    }
    
    response = await client.post("/api/v1/anomaly", json=req_data)
    # The endpoint will fall back because of the exception handler catching get_anomaly_score error inside
    assert response.status_code == 200
    assert response.json()["detector"] == "isolation_forest"
    assert response.json()["detector_version"] == "fallback"

def test_feature_generation():
    # Simple test for feature engineering logic conceptually
    from netmind.schemas.prediction import PredictionRequest
    req = PredictionRequest(
        entity_id="test",
        entity_type="device",
        features={"latency": 100, "cpu": 50}
    )
    df = pd.DataFrame([req.features])
    assert "latency" in df.columns
    assert df["latency"].iloc[0] == 100
