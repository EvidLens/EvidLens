from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from.service import run_rag_pipeline
from app.modules.db import get_db

router = APIRouter()

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
    from.loader import load_sector_data
    load_sector_data(db)
    return {"status": "loaded", "sectors": 35}
