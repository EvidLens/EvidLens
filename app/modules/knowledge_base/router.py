from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from.service import get_sector_report, search_knowledge, ingest_sector_data, generate_report_with_groq
from.models import SectorReport, KnowledgeChunk, KENYA_SECTORS
from app.modules.database import get_db

router = APIRouter()

class ReportResponse(BaseModel):
    sector: str
    county: Optional[str]
    title: str
    summary: str
    key_insights: List[str]
    market_size_kes: Optional[float]
    growth_rate_percent: Optional[float]

class SearchRequest(BaseModel):
    query: str
    sector: Optional[str] = None
    county: Optional[str] = None
    top_k: int = 5

@router.get("/sectors")
def list_sectors():
    """Return all 36 Kenya sectors. Used for Zero Setup dropdown"""
    return {"sectors": KENYA_SECTORS}

@router.get("/report/{sector}", response_model=ReportResponse)
def get_report(
    sector: str,
    county: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get prebuilt industry report. Auto-loads on signup"""
    if sector not in KENYA_SECTORS:
        raise HTTPException(status_code=404, detail="Sector not found")

    report = get_sector_report(db, sector, county)
    if not report:
        # Auto-generate if missing
        report = generate_report_with_groq(db, sector, county)

    return report

@router.post("/search")
def search_kb(request: SearchRequest, db: Session = Depends(get_db)):
    """RAG search for Lens chatbot and AI Insight Generator"""
    results = search_knowledge(db, request.query, request.sector, request.county, request.top_k)
    return {
        "query": request.query,
        "results": [
            {
                "chunk_text": r.chunk_text,
                "sector": r.sector,
                "county": r.county
            } for r in results
        ]
    }
