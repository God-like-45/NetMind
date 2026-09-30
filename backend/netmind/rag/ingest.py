from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import uuid

from netmind.rag.config import QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME, EMBEDDING_MODEL

class KnowledgeIngestor:
    def __init__(self):
        self.qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)
        self._ensure_collection()

    def _ensure_collection(self):
        collections = self.qdrant.get_collections().collections
        if not any(c.name == COLLECTION_NAME for c in collections):
            self.qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        # Simple character-based chunking
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap
        return chunks

    def ingest_document(self, text: str, metadata: Dict[str, Any], allowed_roles: List[str]):
        """
        Ingests a document with security rules (allowed_roles).
        """
        chunks = self.chunk_text(text)
        points = []
        for i, chunk in enumerate(chunks):
            vector = self.embedder.encode(chunk).tolist()
            point_id = str(uuid.uuid4())
            payload = {
                "text": chunk,
                "allowed_roles": allowed_roles,
                **metadata,
                "chunk_index": i
            }
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))
        
        self.qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        return len(points)
