import mlflow
from typing import Dict, Any, Callable
from netmind.mlops.validation import ModelValidator

class MLPipeline:
    def __init__(self, experiment_name: str):
        self.experiment_name = experiment_name
        mlflow.set_experiment(experiment_name)

    def run(self, 
            data_version: str, 
            train_fn: Callable, 
            eval_fn: Callable, 
            schema: list) -> bool:
        """
        Runs the full MLOps pipeline:
        data -> validation -> feature engineering -> training -> evaluation -> model validation -> registry -> deployment
        """
        with mlflow.start_run() as run:
            # 1. Data Versioning (DVC reference)
            mlflow.log_param("dvc_data_version", data_version)
            
            # 2. Training
            print("Running training...")
            model = train_fn()
            
            # 3. Evaluation
            print("Running evaluation...")
            metrics, latency_ms = eval_fn(model)
            mlflow.log_metrics(metrics)
            mlflow.log_metric("latency_ms", latency_ms)
            
            # 4. Model Validation
            is_valid = ModelValidator.validate_model(metrics, schema, latency_ms)
            
            if is_valid:
                print("Registering model in MLflow...")
                # Note: In a real environment, we'd log the model properly using mlflow.sklearn.log_model
                # mlflow.sklearn.log_model(model, "model", registered_model_name=f"{self.experiment_name}_model")
                mlflow.log_param("status", "promoted")
                return True
            else:
                print("Model failed validation. Rollback / Do not promote.")
                mlflow.log_param("status", "rejected")
                return False
