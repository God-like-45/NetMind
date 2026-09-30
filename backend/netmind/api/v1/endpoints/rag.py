from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from netmind.rag.ingest import KnowledgeIngestor
from netmind.rag.retriever import KnowledgeRetriever
from netmind.rag.generator import KnowledgeGenerator

router = APIRouter()
ingestor = None
retriever = None
generator = None

def get_ingestor():
    global ingestor
    if not ingestor:
        ingestor = KnowledgeIngestor()
    return ingestor

def get_retriever():
    global retriever
    if not retriever:
        retriever = KnowledgeRetriever()
    return retriever

def get_generator():
    global generator
    if not generator:
        generator = KnowledgeGenerator()
    return generator

class IngestRequest(BaseModel):
    text: str
    metadata: dict
    allowed_roles: List[str]

class QueryRequest(BaseModel):
    query: str
    user_roles: List[str]
    top_k: Optional[int] = 5

@router.post("/ingest")
async def ingest_document(req: IngestRequest):
    i = get_ingestor()
    chunks = i.ingest_document(req.text, req.metadata, req.allowed_roles)
    return {"status": "success", "chunks_ingested": chunks}

@router.post("/query")
async def query_knowledge(req: QueryRequest):
    r = get_retriever()
    g = get_generator()
    
    # 1. Retrieve Context
    results = r.retrieve(req.query, req.user_roles, req.top_k)
    
    # 2. Generate Answer
    gen_result = await g.generate_answer(req.query, results)
    
    return {
        "status": "success", 
        "retrieved_documents": results,
        "answer": gen_result["answer"],
        "citations": gen_result["citations"],
        "model": gen_result["model"]
    }
