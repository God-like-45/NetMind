import sys
import os

# Add backend directory to sys path so we can import netmind
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netmind.mlops.pipeline import MLPipeline

def mock_train():
    # In reality, this would train an IsolationForest or similar model
    print("Training mock Isolation Forest...")
    return {"model": "IsolationForest_v1"}

def mock_evaluate(model):
    print("Evaluating model...")
    # Mock metrics
    metrics = {
        "recall": 0.88,
        "pr_auc": 0.82,
        "precision": 0.80
    }
    latency_ms = 35.5
    return metrics, latency_ms

def main():
    print("=== MLOps Pipeline: Network Anomaly Model ===")
    
    pipeline = MLPipeline(experiment_name="network_anomaly_detection")
    
    # Run the pipeline with strict validation checks
    # Passing schema matching our requirements
    success = pipeline.run(
        data_version="dvc-commit-9f8a21b",
        train_fn=mock_train,
        eval_fn=mock_evaluate,
        schema=["latency", "packet_loss", "cpu_utilization"]
    )
    
    if success:
        print("Pipeline execution completed. Model promoted to registry.")
    else:
        print("Pipeline execution completed. Model rejected.")

if __name__ == "__main__":
    main()
