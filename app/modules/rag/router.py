from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from.service import run_rag_pipeline # fixed relative import
from app.modules.db import get_db

router = APIRouter(prefix="/rag", tags=["RAG"]) # add prefix for clarity

class RAGRequest(BaseModel):
    query: str
    sector: str
    county: str

class RAGResponse(BaseModel):
    answer: str
    sources: List[str]
    confidence: float

@router.post("/query", response_model=RAGResponse)
def rag_query(req: RAGRequest, db: Session = Depends(get_db)):
    result = run_rag_pipeline(db, req.query, req.sector, req.county)
    return result

@router.post("/load")
def load_knowledge_base(db: Session = Depends(get_db)):
    from.loader import load_sector_data # fixed relative import
    count = load_sector_data(db)
    return {"status": "loaded", "sectors": count}
