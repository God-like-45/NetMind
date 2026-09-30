import mlflow
import json
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class PromptVersion(BaseModel):
    version_id: str
    template: str
    description: str

# In a real system, these would be tracked in a database or MLflow tracking server
PROMPT_REGISTRY = {
    "investigation_v1": PromptVersion(
        version_id="investigation_v1",
        template="You are an expert telecom network planner. Generate a step-by-step investigation plan for incident {incident_id} on entity {entity_id}.",
        description="Initial planner prompt."
    )
}

class LLMOpsTracker:
    @staticmethod
    def log_interaction(
        prompt_version: str, 
        model_name: str, 
        inputs: Dict[str, Any], 
        output: str, 
        latency_ms: float, 
        input_tokens: int, 
        output_tokens: int,
        error: Optional[str] = None
    ):
        """Log LLM interaction for observability."""
        try:
            with mlflow.start_run(run_name=f"llm_{int(time.time())}", nested=True):
                mlflow.log_param("prompt_version", prompt_version)
                mlflow.log_param("model_name", model_name)
                mlflow.log_metric("latency_ms", latency_ms)
                mlflow.log_metric("input_tokens", input_tokens)
                mlflow.log_metric("output_tokens", output_tokens)
                mlflow.log_metric("total_tokens", input_tokens + output_tokens)
                
                # We log errors if any
                if error:
                    mlflow.log_param("error", str(error))
                    mlflow.log_metric("failed", 1)
                else:
                    mlflow.log_metric("failed", 0)
                    
                # Log inputs and outputs as artifacts for review/evaluation
                mlflow.log_dict({"inputs": inputs, "output": output}, "interaction.json")
        except Exception:
            # Fallback if MLflow isn't configured, print to stdout for basic observability
            print(f"LLMOps - Model: {model_name}, Latency: {latency_ms}ms, Tokens: {input_tokens+output_tokens}")

EVALUATION_DATASET = [
    {
        "query": "What should I do if a router experiences BGP flapping?",
        "expected_facts": ["clear ip bgp * soft", "Rollback the configuration", "identify recent commit"]
    },
    {
        "query": "Link down anomaly or high packet loss on core interface?",
        "expected_facts": ["Check interface optical levels", "Verify QoS queue drops"]
    }
]
