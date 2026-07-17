import os
import json
import httpx
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Dict, Any
from app.core.db import redis_client
from app.modules.market_engine.models import MarketSearch, MarketMetric
import africastalking
from bs4 import BeautifulSoup

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
LOCATIONIQ_KEY = os.getenv("LOCATIONIQ_KEY")

africastalking.initialize(os.getenv("AFRICASTALKING_USERNAME"), os.getenv("AFRICASTALKING_API_KEY"))

class MarketEngineService:
    def __init__(self, db: Session):
        self.db = db

    async def call_groq(self, prompt: str) -> str:
        if not GROQ_API_KEY: return "Set GROQ_API_KEY"
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 250})
            return r.json()["choices"][0]["message"]["content"]

    async def call_api(self, url: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url)
            return r.json() if r.status_code == 200 else {}

    async def scrape_knbs_prices(self) -> Dict[str, float]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get("https://www.knbs.or.ke/consumer-price-indices-cpi-and-inflation-rates/")
                forex = await self.call_api("https://api.exchangerate-api.com/v4/latest/USD")
                return {"usd_kes": forex.get("rates",{}).get("KES", 129.50)}
        except:
            return {"usd_kes": 0}

    async def scrape_fuel_prices(self) -> Dict[str, float]:
        try:
            async with httpx.AsyncClient() as client:
                await client.get("https://www.epra.go.ke/fuel-prices")
                return {"petrol": 0, "diesel": 0, "kerosene": 0}
        except:
            return {"petrol": 0, "diesel": 0, "kerosene": 0}

    async def get_real_time_terminal(self, sector: str, county: str, date_range: str) -> Dict[str, Any]:
        cache_key = "market_terminal"
        if redis_client:
            cached = redis_client.get(cache_key)
            if cached: return json.loads(cached)

        cbk = await self.call_api("https://www.centralbank.go.ke/wp-json/wp/v2/posts?categories=3&per_page=3")
        commodities = await self.scrape_knbs_prices()
        fuel = await self.scrape_fuel_prices()
        commodities.update(fuel)

        insights = self.db.query(func.count(MarketSearch.id)).scalar() or 0
        reports = self.db.query(func.count(MarketMetric.id)).scalar() or 0

        data = {
            "cbk_rates": cbk[:3],
            "commodities": commodities,
            "sector": sector,
            "county": county,
            "last_updated": datetime.utcnow().isoformat(),
            "insights_generated": insights,
            "reports_exported": reports
        }
        if redis_client: redis_client.setex(cache_key, 900, json.dumps(data))
        return data

    async def startup_tech_tracker(self, sector: str, date_range: str = "30d") -> Dict[str, Any]:
        days = {"7d":7,"30d":30,"90d":90}[date_range]
        from_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        news = await self.call_api(f"https://newsapi.org/v2/everything?q={sector} startup Kenya funding&from={from_date}&apiKey={NEWS_API_KEY}&pageSize=10")
        startups = []
        for a in news.get("articles",[]):
            extracted = await self.call_groq(f"Extract JSON: name, founder, amount_usd, date. From: {a['title']} {a['description']}")
            try:
                data = json.loads(extracted)
                if data.get("name"): startups.append(data)
            except: pass
        return {"startups": startups, "count": len(startups)}

    async def b2b_intent_signals(self, sector: str, county: str, keyword: str) -> Dict[str, Any]:
        q = self.db.query(MarketSearch).filter(MarketSearch.query.ilike(f"%{keyword}%"))
        if sector: q = q.filter(MarketSearch.sector==sector)
        if county: q = q.filter(MarketSearch.county==county)
        searches = q.order_by(desc(MarketSearch.created_at)).limit(50).all()
        trends = await self.call_api(f"https://serpapi.com/search.json?engine=google_trends&q={keyword} {county}&api_key={SERPAPI_KEY}")
        insight = await self.call_groq(f"Keyword: {keyword}. County: {county}. DB Searches: {len(searches)}. Demand up or down? 2 sentences.")
        return {"keyword": keyword, "county": county, "search_volume_db": len(searches), "trend_data": trends, "ai_insight": insight}

async def search_market(self, q: str, sector: str, county: str) -> Dict[str, Any]:
        search = MarketSearch(query=q, sector=sector, county=county)
        self.db.add(search)
        self.db.commit()
        similar = self.db.query(MarketSearch).filter(MarketSearch.sector==sector, MarketSearch.county==county).count()
        market_size = similar * 1000000
        demand = "High" if similar > 10 else "Medium"
        return {"query": q, "sector": sector, "county": county, "market_size_kes": market_size, "demand_level": demand}
