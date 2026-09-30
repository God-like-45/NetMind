import os
import mlflow
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

class ModelLoader:
    """
    Clean interface to load models from MLflow artifact store or local fallback.
    Prevents coupling FastAPI directly to the training scripts.
    """
    def __init__(self, tracking_uri: str = None):
        self.tracking_uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        mlflow.set_tracking_uri(self.tracking_uri)
    
    def get_latest_model(self, model_name: str, stage: str = "Production"):
        """
        Loads a model from the MLflow model registry.
        """
        model_uri = f"models:/{model_name}/{stage}"
        logger.info(f"Loading model from {model_uri}")
        try:
            return mlflow.sklearn.load_model(model_uri)
        except Exception as e:
            logger.error(f"Failed to load model {model_name} from MLflow: {e}")
            raise
    
    def get_model_by_run_id(self, run_id: str, artifact_path: str):
        """
        Loads a model by a specific MLflow Run ID.
        """
        model_uri = f"runs:/{run_id}/{artifact_path}"
        logger.info(f"Loading model from {model_uri}")
        try:
            return mlflow.sklearn.load_model(model_uri)
        except Exception as e:
            logger.error(f"Failed to load model from {model_uri}: {e}")
            raise

@lru_cache(maxsize=2)
def get_model_loader() -> ModelLoader:
    return ModelLoader()
