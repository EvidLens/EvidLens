from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
import httpx, os

from.service import search_market, get_competitor_overview, calculate_market_size
from.models import MarketSearch, Competitor, MarketMetric # Make sure these exist
from app.modules.db import get_db

router = APIRouter()
LOCATIONIQ_KEY = os.getenv("LOCATIONIQ_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")

class MarketSearchResponse(BaseModel):
    query: str
    sector: Optional[str]
    county: Optional[str]
    demand_level: str
    market_size_kes: float
    price_range: dict
    competitor_count: int
    sentiment_summary: dict
    ai_insight: str # Added AI summary

@router.get("/search", response_model=MarketSearchResponse)
async def search(
    q: str = Query(..., description="Search query e.g 'maize milling in Nyeri'"),
    sector: Optional[str] = Query(None),
    county: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Search any market/idea. Powers Home Dashboard search bar + Quick Analyze"""
    # 1. Save search to DB for trending
    db_search = MarketSearch(query=q, sector=sector, county=county)
    db.add(db_search)
    db.commit()

    # 2. Get DB data
    result = search_market(db, q, sector, county)
    competitors = get_competitor_overview(db, sector, county) if sector and county else []

    # 3. Get AI Insight from Groq
    prompt = f"You are Lens, EvidLens AI for Kenya. Analyze business '{q}' for {sector} in {county}. Found {len(competitors)} competitors. Return: Demand, Risks, Top 3 Competitors, Go/No-Go. Under 120 words."
    ai_insight = "Add GROQ_API_KEY for AI analysis"
    if GROQ_KEY:
        ai_res = await httpx.AsyncClient().post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={"model": "llama-3.1-70b-versatile", "messages": [{"role": "user", "content": prompt}]}
        )
        ai_insight = ai_res.json()["choices"][0]["message"]["content"]

    if not result:
        # Fallback if DB is empty
        result = {
            "demand_level": "Calculating",
            "market_size_kes": 0,
            "price_range": {"min": 0, "max": 0},
            "competitor_count": len(competitors),
            "sentiment_summary": {"positive": 0, "negative": 0}
        }

    return {
        "query": q, "sector": sector, "county": county,
        "demand_level": result["demand_level"],
        "market_size_kes": result["market_size_kes"],
        "price_range": result["price_range"],
        "competitor_count": len(competitors),
        "sentiment_summary": result["sentiment_summary"],
        "ai_insight": ai_insight
    }

@router.get("/competitors/{sector}")
async def competitors(
    sector: str,
    county: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get competitor overview. Uses DB first, then LocationIQ if empty. Powers Competitor Tracker"""
    competitors = get_competitor_overview(db, sector, county)

    # Fallback to LocationIQ API if DB has no data
    if not competitors and LOCATIONIQ_KEY:
        search_term = f"{sector} in {county}, Kenya"
        location_res = await httpx.AsyncClient().get(
            f"https://api.locationiq.com/v1/autocomplete.php?key={LOCATIONIQ_KEY}&q={search_term}&limit=10"
        )
        data = location_res.json()
        competitors = [
            {"business_name": c["display_name"], "lat": c["lat"], "lng": c["lon"], "avg_rating": 4.0, "review_count": 0}
            for c in data
        ]

    return {
        "sector": sector,
        "county": county,
        "total_competitors": len(competitors),
        "competitors": [
            {
                "name": c.business_name if hasattr(c, 'business_name') else c["business_name"],
                "lat": c.lat if hasattr(c, 'lat') else c["lat"],
                "lng": c.lng if hasattr(c, 'lng') else c["lng"],
                "rating": c.avg_rating if hasattr(c, 'avg_rating') else c["avg_rating"],
                "reviews": c.review_count if hasattr(c, 'review_count') else c["review_count"]
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
        "min_kes": stats.get("min", 0),
        "max_kes": stats.get("max", 0),
        "avg_kes": stats.get("avg", 0)
    }

@router.get("/trending")
def trending(db: Session = Depends(get_db)):
    """Top 5 trending searches. Powers Home Dashboard"""
    trending = db.query(MarketSearch.query, func.count(MarketSearch.id).label("count"))\
      .group_by(MarketSearch.query)\
      .order_by(func.count(MarketSearch.id).desc())\
      .limit(5).all()

    return {"trending": [{"query": t[0], "searches": t[1]} for t in trending]}
