import httpx
from typing import List, Dict, Any
import os
import time
from netmind.mlops.llm_eval import LLMOpsTracker

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")

class KnowledgeGenerator:
    def __init__(self):
        self.host = OLLAMA_HOST
        self.model = OLLAMA_MODEL

    async def generate_answer(self, query: str, context_docs: List[Dict[str, Any]]) -> dict:
        """
        Generates an answer based on retrieved context, ensuring strict citation.
        """
        context_text = ""
        for i, doc in enumerate(context_docs):
            source = doc["metadata"].get("source", f"Doc-{i}")
            context_text += f"\n--- Source: {source} ---\n{doc['text']}\n"

        prompt = f"""You are a specialized telecom network AI assistant.
Answer the question based ONLY on the provided context.
If the answer is not in the context, say "I cannot answer this based on the provided documentation."
Always cite the source for your facts (e.g., [Source: runbook_bgp.md]).

Context:
{context_text}

Question: {query}
Answer:"""

        start_time = time.time()
        error_msg = None
        response_text = ""
        eval_metrics = {"eval_count": 0, "prompt_eval_count": 0}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=15.0  # Tight timeout for graceful fallback
                )
                response.raise_for_status()
                data = response.json()
                response_text = data.get("response", "")
                eval_metrics["eval_count"] = data.get("eval_count", 0)
                eval_metrics["prompt_eval_count"] = data.get("prompt_eval_count", 0)
                
            except httpx.TimeoutException:
                error_msg = "LLM Generation Timeout"
                response_text = "The AI service is currently experiencing high latency. Falling back to direct document retrieval (see sources below)."
            except Exception as e:
                error_msg = str(e)
                response_text = "The AI service is currently unavailable. Falling back to direct document retrieval (see sources below)."

        latency_ms = (time.time() - start_time) * 1000

        # MLOps: Track LLM Interactions
        LLMOpsTracker.log_interaction(
            prompt_version="rag_v1",
            model_name=self.model,
            inputs={"query": query, "context_len": len(context_text)},
            output=response_text,
            latency_ms=latency_ms,
            input_tokens=eval_metrics["prompt_eval_count"],
            output_tokens=eval_metrics["eval_count"],
            error=error_msg
        )

        citations = [doc["metadata"].get("source") for doc in context_docs] if context_docs else []

        return {
            "answer": response_text,
            "citations": list(set(citations)),
            "model": self.model,
            "fallback_active": error_msg is not None
        }
