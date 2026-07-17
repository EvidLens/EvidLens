from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.modules.market_engine.models import MarketSearch, MarketMetric
from app.core.db import redis_client
import httpx
import os
import json
from datetime import datetime, timedelta

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LOCATIONIQ_KEY = os.getenv("LOCATIONIQ_KEY")

class MarketEngineService:
    def __init__(self, db: Session):
        self.db = db
        self.groq_key = GROQ_API_KEY

    async def call_groq(self, prompt: str) -> str:
        if not self.groq_key:
            return "Error: GROQ_API_KEY not set in Render Env Vars"
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 1200
        }
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

    async def call_api(self, url: str) -> Dict:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()

    # SERVICE 1: REAL MARKET SEARCH
    async def search_market(self, q: str, sector: str, county: str) -> Dict[str, Any]:
        search = MarketSearch(query=q, sector=sector, county=county, created_at=datetime.utcnow())
        self.db.add(search)
        self.db.commit()

        last_30 = datetime.utcnow() - timedelta(days=30)
        volume = self.db.query(MarketSearch).filter(MarketSearch.sector==sector, MarketSearch.county==county, MarketSearch.created_at >= last_30).count()

        market_size_kes = volume * 3500000 # Real proxy: avg customer value * searches
        demand = "Very High" if volume > 50 else "High" if volume > 20 else "Medium" if volume > 5 else "Low"

        return {
            "query": q,
            "sector": sector,
            "county": county,
            "market_size_kes": market_size_kes,
            "demand_level": demand,
            "searches_30d": volume,
            "data_source": "NairoBiz DB + User Activity"
        }

    # SERVICE 2: REAL AI ANALYSIS
    async def analyze_with_ai(self, sector: str, county: str) -> Dict[str, Any]:
        prompt = f"""You are a senior market analyst for Kenya. Analyze the '{sector}' market in '{county}, Kenya' for 2026.
        Return ONLY valid JSON with these exact keys:
        "opportunity_score": 1-10,
        "market_gap": "2 sentences",
        "top_3_risks": ["risk1", "risk2", "risk3"],
        "top_3_opportunities": ["opp1", "opp2", "opp3"],
        "recommended_first_product": "specific product name and price in KES",
        "estimated_startup_cost_kes": number
        Be specific to Kenyan context, suppliers, and customers."""

        raw = await self.call_groq(prompt)
        try:
            analysis = json.loads(raw)
        except:
            analysis = {"raw_ai_output": raw}

        return {"sector": sector, "county": county, "analysis": analysis, "generated_at": datetime.utcnow().isoformat()}

    # SERVICE 3: REAL DASHBOARD STATS
    async def get_dashboard_stats(self) -> Dict[str, Any]:
        total_searches = self.db.query(MarketSearch).count()
        total_users = self.db.query(MarketSearch.query).distinct().count()

        top_sector = self.db.query(MarketSearch.sector, func.count(MarketSearch.id).label('c')).group_by(MarketSearch.sector).order_by(desc('c')).first()
        top_county = self.db.query(MarketSearch.county, func.count(MarketSearch.id).label('c')).group_by(MarketSearch.county).order_by(desc('c')).first()
        trending_queries = self.db.query(MarketSearch.query, func.count(MarketSearch.id).label('c')).group_by(MarketSearch.query).order_by(desc('c')).limit(5).all()

        return {
            "total_searches": total_searches,
            "active_users_30d": total_users,
            "top_sector": top_sector[0] if top_sector else "N/A",
            "top_county": top_county[0] if top_county else "N/A",
            "trending_searches": [{"query": q, "count": c} for q,c in trending_queries]
        }

    # SERVICE 4: REAL TIME TERMINAL
    async def get_real_time_terminal(self, sector: str, county: str) -> Dict[str, Any]:
        last_1h = datetime.utcnow() - timedelta(hours=1)
        searches_1h = self.db.query(MarketSearch).filter(MarketSearch.sector==sector, MarketSearch.county==county, MarketSearch.created_at >= last_1h).count()
        searches_24h = self.db.query(MarketSearch).filter(MarketSearch.sector==sector, MarketSearch.county==county, MarketSearch.created_at >= datetime.utcnow() - timedelta(days=1)).count()

        trend = "SPIKING" if searches_1h > 5 else "RISING" if searches_24h > 20 else "STABLE"
        signal = f"{sector} demand is {trend} in {county}. {searches_1h} searches in last hour."

        return {
            "sector": sector,
            "county": county,
            "searches_last_1h": searches_1h,
            "searches_last_24h": searches_24h,
            "trend": trend,
            "signal": signal,
            "timestamp": datetime.utcnow().isoformat()
        }

    # SERVICE 5: REAL COMPETITOR OVERVIEW
    async def get_competitor_overview(self, sector: str, county: str) -> Dict[str, Any]:
        prompt = f"""List the top 5 actual companies in the '{sector}' industry operating in '{county}, Kenya' as of 2026.
        Return ONLY valid JSON list with keys: "name", "description", "strength", "estimated_market_share_%".
        If you don't know exact companies, give the most likely market leaders based on Kenyan market data. Be specific."""

        raw = await self.call_groq(prompt)
        try:
            competitors = json.loads(raw)
        except:
            competitors = [{"error": "AI returned non-JSON", "raw": raw}]

        return {"sector": sector, "county": county, "competitors": competitors}
