from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List
import httpx, os

from.service import search_market, get_competitor_overview, get_price_stats
from.models import MarketSearch, Competitor
from app.modules.db import get_db

router = APIRouter()
LOCATIONIQ_KEY = os.getenv("LOCATIONIQ_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")

class MarketSearchResponse(BaseModel):
    query: str
    sector: Optional[str]
    country: str
    county: Optional[str]
    sub_county: Optional[str]
    ward: Optional[str]
    town: Optional[str]
    demand_level: str
    market_size_kes: float
    price_range: dict
    competitor_count: int
    sentiment_summary: dict
    ai_insight: str

@router.get("/search", response_model=MarketSearchResponse)
async def search(
    q: str = Query(...),
    sector: Optional[str] = Query(None),
    country: str = "Kenya",
    county: Optional[str] = Query(None),
    sub_county: Optional[str] = Query(None),
    ward: Optional[str] = Query(None),
    town: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    db_search = MarketSearch(
        query=q, sector=sector, country=country,
        county=county, sub_county=sub_county, ward=ward, town=town
    )
    db.add(db_search)
    db.commit()

    result = search_market(db, q, sector, country, county, sub_county, ward, town)
    competitors = get_competitor_overview(db, sector, country, county, sub_county, ward, town) if sector else []

    location_str = town or ward or sub_county or county or country
    prompt = f"You are Lens, EvidLens AI for Kenya. Analyze business '{q}' for {sector} in {location_str}. Found {len(competitors)} competitors. Return: Demand, Risks, Top 3 Competitors, Go/No-Go. Under 120 words."
    
    ai_insight = "Add GROQ_API_KEY for AI analysis"
    if GROQ_KEY:
        async with httpx.AsyncClient(timeout=20) as client:
            ai_res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}"},
                json={"model": "llama-3.1-70b-versatile", "messages": [{"role": "user", "content": prompt}]}
            )
            ai_insight = ai_res.json()["choices"][0]["message"]["content"]

    if not result:
        result = {
            "demand_level": "Calculating",
            "market_size_kes": 0,
            "price_range": {"min": 0, "max": 0},
            "competitor_count": len(competitors),
            "sentiment_summary": {"positive": 0, "negative": 0}
        }

    return {
        "query": q, "sector": sector, "country": country, "county": county, 
        "sub_county": sub_county, "ward": ward, "town": town,
        **result, "competitor_count": len(competitors), "ai_insight": ai_insight
    }

@router.get("/competitors/{sector}")
async def competitors(
    sector: str,
    country: str = "Kenya",
    county: Optional[str] = Query(None),
    sub_county: Optional[str] = Query(None),
    ward: Optional[str] = Query(None),
    town: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    competitors = get_competitor_overview(db, sector, country, county, sub_county, ward, town)

    if not competitors and LOCATIONIQ_KEY:
        location = town or ward or sub_county or county
        search_term = f"{sector} in {location}, Kenya"
        async with httpx.AsyncClient() as client:
            location_res = await client.get(
                f"https://api.locationiq.com/v1/autocomplete.php?key={LOCATIONIQ_KEY}&q={search_term}&limit=10"
            )
            data = location_res.json()
            competitors = [
                {"business_name": c["display_name"], "lat": float(c["lat"]), "lng": float(c["lon"]), "avg_rating": 4.0, "review_count": 0}
                for c in data
            ]

    return {
        "sector": sector, "country": country, "county": county, "sub_county": sub_county, "ward": ward, "town": town,
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
    country: str = "Kenya",
    county: Optional[str] = Query(None),
    sub_county: Optional[str] = Query(None),
    ward: Optional[str] = Query(None),
    town: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    stats = get_price_stats(db, sector, product, country, county, sub_county, ward, town)
    return {
        "sector": sector, "product": product, "country": country, 
        "county": county, "sub_county": sub_county, "ward": ward, "town": town,
        "min_kes": stats.get("min", 0), "max_kes": stats.get("max", 0), "avg_kes": stats.get("avg", 0)
    }

@router.get("/trending")
def trending(db: Session = Depends(get_db)):
    trending = db.query(MarketSearch.query, func.count(MarketSearch.id).label("count"))\
    .group_by(MarketSearch.query)\
    .order_by(func.count(MarketSearch.id).desc())\
    .limit(5).all()
    return {"trending": [{"query": t[0], "searches": t[1]} for t in trending]}
