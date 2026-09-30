from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchAny
from sentence_transformers import SentenceTransformer

from netmind.rag.config import QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME, EMBEDDING_MODEL

class KnowledgeRetriever:
    def __init__(self):
        self.qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)

    def retrieve(self, query: str, user_roles: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves context while enforcing RBAC via Qdrant filtering.
        """
        query_vector = self.embedder.encode(query).tolist()
        
        # Security Filter: Only retrieve if one of user_roles is in allowed_roles
        security_filter = Filter(
            must=[
                FieldCondition(
                    key="allowed_roles",
                    match=MatchAny(any=user_roles)
                )
            ]
        )

        try:
            results = self.qdrant.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vector,
                query_filter=security_filter,
                limit=top_k
            )
        except Exception as e:
            # Fallback for Qdrant Failure (Scenario 4)
            print(f"[RECOVERY] Qdrant unavailable: {e}. Returning empty context.")
            return []
        
        return [
            {
                "score": hit.score,
                "text": hit.payload.get("text"),
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"}
            }
            for hit in results
        ]
