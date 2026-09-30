import os

QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6334"))
COLLECTION_NAME = "netmind_knowledge"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
