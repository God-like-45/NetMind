from typing import Dict, Any

class ModelValidationConfig:
    # Project-defined thresholds
    MIN_RECALL = 0.85
    MIN_PR_AUC = 0.80
    MAX_LATENCY_MS = 50.0
    REQUIRED_SCHEMA = ["latency", "packet_loss", "cpu_utilization"]

class ModelValidator:
    @staticmethod
    def validate_model(metrics: Dict[str, float], schema: list, latency_ms: float) -> bool:
        """
        A model cannot be promoted unless it passes these predefined checks.
        """
        print(f"Validating model with Recall: {metrics.get('recall', 0)}, PR-AUC: {metrics.get('pr_auc', 0)}")
        
        if metrics.get("recall", 0.0) < ModelValidationConfig.MIN_RECALL:
            print("Validation failed: Recall below minimum threshold.")
            return False
            
        if metrics.get("pr_auc", 0.0) < ModelValidationConfig.MIN_PR_AUC:
            print("Validation failed: PR-AUC below minimum threshold.")
            return False
            
        if latency_ms > ModelValidationConfig.MAX_LATENCY_MS:
            print("Validation failed: Inference latency too high.")
            return False
            
        for feature in ModelValidationConfig.REQUIRED_SCHEMA:
            if feature not in schema:
                print(f"Validation failed: Missing required schema feature {feature}.")
                return False
                
        print("Model validation passed! Ready for promotion.")
        return True
