from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from .service import search_market, get_competitor_overview, calculate_market_size
from.models import MarketSearch, Competitor, MarketMetric
from app.modules.db import get_db

router = APIRouter()

class MarketSearchResponse(BaseModel):
    query: str
    sector: Optional[str]
    county: Optional[str]
    demand_level: str
    market_size_kes: float
    price_range: dict
    competitor_count: int
    sentiment_summary: dict

@router.get("/search", response_model=MarketSearchResponse)
def search(
    q: str = Query(..., description="Search query e.g 'maize milling in Nyeri'"),
    sector: Optional[str] = Query(None),
    county: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Search any market/idea. Powers Home Dashboard search bar"""
    result = search_market(db, q, sector, county)
    if not result:
        raise HTTPException(status_code=404, detail="No data found for this query")
    return result

@router.get("/competitors/{sector}")
def competitors(
    sector: str,
    county: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get competitor overview for a sector + county. Powers Insight Page + Competitor Tracker"""
    competitors = get_competitor_overview(db, sector, county)
    return {
        "sector": sector,
        "county": county,
        "total_competitors": len(competitors),
        "competitors": [
            {
                "name": c.business_name,
                "lat": c.lat,
                "lng": c.lng,
                "rating": c.avg_rating,
                "reviews": c.review_count
            } for c in competitors
        ]
    }

@router.get("/pricing/{sector}")
def pricing(
    sector: str,
    product: Optional[str] = Query(None),
    county: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get pricing ranges from Jumia/Naivas scraper data. Lane 3"""
    from app.modules.data_layer.service import get_price_stats
    stats = get_price_stats(db, sector, product, county)
    return {
        "sector": sector,
        "product": product,
        "county": county,
        "min_kes": stats["min"],
        "max_kes": stats["max"],
        "avg_kes": stats["avg"]
    }

@router.get("/trending")
def trending(db: Session = Depends(get_db)):
    """Top 5 trending searches. Powers Home Dashboard"""
    trending = db.query(MarketSearch.query, func.count(MarketSearch.id).label("count"))\
       .group_by(MarketSearch.query)\
       .order_by(func.count(MarketSearch.id).desc())\
       .limit(5).all()

    return {"trending": [{"query": t[0], "searches": t[1]} for t in trending]}
