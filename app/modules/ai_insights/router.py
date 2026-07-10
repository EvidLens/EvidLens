from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .service import generate_insights # note the S

router = APIRouter()

class InsightRequest(BaseModel):
    query: str
    sector: str
    county: str

@router.post("/ask")
def ask_insight(req: InsightRequest):
    market_data = {"sector": req.sector, "county": req.county}
    result = generate_insights(req.query, market_data) # 2 params now
    return {"analysis": result}

@router.post("/viability")
def viability_check(req: InsightRequest):
    market_data = {"sector": req.sector, "county": req.county}
    viab_query = f"Should I start a {req.query} business in {req.county}? Give Go, No-Go, or Needs Research."
    result = generate_insights(viab_query, market_data) # 2 params now
    return {"analysis": result}
