from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .service import generate_insight

router = APIRouter()

class InsightRequest(BaseModel):
    query: str
    sector: str
    county: str

@router.post("/ask")
def ask_insight(req: InsightRequest):
    result = generate_insight(req.query, req.sector, req.county)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@router.post("/viability")
def viability_check(req: InsightRequest):
    result = generate_insight(f"Should I start a {req.query} business in {req.county}? Give Go No-Go Needs Research.", req.sector, req.county)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result
