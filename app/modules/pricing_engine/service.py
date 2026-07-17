import os
import json
import httpx
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Dict, Any, List, Optional
from app.modules.db import redis_client
from app.modules.market_engine.models import MarketSearch, Competitor, MarketMetric

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
LOCATIONIQ_KEY = os.getenv("LOCATIONIQ_KEY")

KENYA_SECTORS_75 = ["Banks","Microfinance","Insurance","Fintech","Capital Markets","SACCOs","Retail Chains","Wholesale","FMCG Food","FMCG Personal","Manuf Food","Manuf Textile","Manuf Construction","Manuf Auto","Manuf Pharma","Manuf Chemical","Agri Crops","Agri Livestock","Agri Horticulture","Agri Fisheries","Agri Processing","Telcos","Media","Advertising","PR","RealEstate Dev","RealEstate Agent","RealEstate Mgmt","Construction","Architecture","Health Hospital","Health Pharmacy","Health Devices","Edu University","Edu School","Edu EdTech","Logistics","E-commerce","Hospitality Hotel","Hospitality QSR","Tourism","Aviation","Maritime","Energy Electric","Energy Oil","Energy Renewable","Energy Water","Mining","Gov National","Gov County","Gov StateCorp","Gov Regulatory","Public Safety","Defense","NGOs","INGOs","Donors","Foundations","Investors PEVC","Investors Angel","Law","Consulting","Accounting","HR","ICT","Data Centers","Digital Marketing","Auto Dealership","Auto Parts","Auto Boda","Gaming","Entertainment","Beauty","Waste","Environment"]

async def call_groq(prompt: str) -> str:
    if not GROQ_API_KEY: return "Set GROQ_API_KEY"
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json={"model": GROQ_MODEL, "messages": [{"role": "system", "content": "You are Lens, EvidLens AI for Kenya."}, {"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 500})
        return r.json()["choices"][0]["message"]["content"]

def search_market(db: Session, q: str, sector: str, county: str) -> Dict[str, Any]:
    db.add(MarketSearch(query=q, sector=sector, county=county, country="Kenya"))
    db.commit()
    metrics = db.query(MarketMetric).filter(MarketMetric.sector == sector, MarketMetric.county == county).all()
    competitors = db.query(Competitor).filter(Competitor.sector == sector, Competitor.county == county).limit(10).all()
    prices = [m.price_kes for m in metrics if m.price_kes]
    return {"query": q, "sector": sector, "county": county, "demand_level": "High" if len(metrics) > 10 else "Medium" if len(metrics) > 3 else "Low", "market_size_kes": sum([m.market_size_kes for m in metrics if m.market_size_kes]), "price_range": {"min": min(prices) if prices else 0, "max": max(prices) if prices else 0, "avg": sum(prices)/len(prices) if prices else 0}, "competitors": [{"name": c.name, "lat": c.lat, "lng": c.lng} for c in competitors], "competitor_count": len(competitors)}

async def analyze_with_ai(data: Dict) -> str:
    prompt = f"Analyze '{data['query']}' in {data['sector']}, {data['county']} Kenya. Demand:{data['demand_level']}. Market:KES{data['market_size_kes']}. Competitors:{data['competitor_count']}. Return: Demand, Top 3 Risks, Go/No-Go. Under 100 words."
    return await call_groq(prompt)

def get_dashboard_stats(db: Session) -> Dict[str, Any]:
    insights = db.query(func.count(MarketSearch.id)).scalar() or 0
    reports = insights
    trending = db.query(MarketSearch.query, func.count(MarketSearch.id).label("c")).group_by(MarketSearch.query).order_by(desc("c")).first()
    lanes = [
        {"name": "Market Intelligence", "icon": "M", "insights": db.query(func.count(MarketMetric.id)).scalar(), "growth": "+12%"},
        {"name": "Competitive Intelligence", "icon": "C", "insights": db.query(func.count(Competitor.id)).scalar(), "growth": "+8%"},
        {"name": "Pricing Intelligence", "icon": "P", "insights": db.query(func.count(MarketMetric.id)).scalar(), "growth": "+15%"},
        {"name": "Regulatory Intelligence", "icon": "R", "insights": 0, "growth": "+5%"},
        {"name": "Reports & Insights", "icon": "📄", "insights": reports, "growth": "+20%"},
        {"name": "AI Research", "icon": "AI", "insights": insights, "growth": "+30%"},
        {"name": "Consumer Intelligence", "icon": "S", "insights": 0, "growth": "+18%"},
        {"name": "Location Intelligence", "icon": "L", "insights": 0, "growth": "+10%"},
        {"name": "Business OS", "icon": "B", "insights": 0, "growth": "+7%"}
    ]
    return {"stats": {"insights": insights, "active_products": 21, "sectors": 75, "reports": reports}, "trending": {"category": "LIVE", "headline": trending[0] if trending else "No data"}, "lanes": lanes}

async def get_real_time_terminal(sector: str, county: str) -> Dict[str, Any]:
