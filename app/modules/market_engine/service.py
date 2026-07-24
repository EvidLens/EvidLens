from typing import Dict, Any, List
from sqlmodel import Session, select, func, desc
from datetime import datetime, timedelta
from app.modules.kenyalensiq.models import MarketMetric
from app.modules.data_layer.models import MarketSearch
import httpx
import os

LOCATIONIQ_KEY = os.getenv("LOCATIONIQ_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

class MarketEngineService:
    def __init__(self, db: Session):
        self.db = db

    async def _call_api(self, url: str) -> Dict:
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()

    async def market_funding_trends(self, sector: str) -> List[Dict[str, Any]]:
        q = select(MarketMetric)
        if sector:
            q = q.where(MarketMetric.sector == sector)
        results = self.db.exec(q).all()
        return [
            {
                "product": m.product,
                "price": m.avg_price_kes,
                "county": m.county,
                "sector": m.sector
            } for m in results
        ]

    async def get_competitor_overview(self, sector: str, county: str) -> Dict[str, Any]:
        q = select(MarketMetric).where(MarketMetric.sector==sector)
        if county:
            q = q.where(MarketMetric.county==county)
        competitors = self.db.exec(q).all()
        return {
            "sector": sector,
            "county": county,
            "total_companies_found": len(competitors),
            "companies": [
                {
                    "name": c.company_name,
                    "product": c.product,
                    "price_kes": c.avg_price_kes,
                    "county": c.county,
                    "sector": c.sector
                } for c in competitors
            ]
        }

    async def search_market(self, q: str, sector: str, county: str) -> Dict[str, Any]:
        self.db.add(MarketSearch(query=q, sector=sector, county=county, created_at=datetime.utcnow()))
        self.db.commit()
        last_30 = datetime.utcnow() - timedelta(days=30)
        volume_30d = self.db.query(MarketSearch).filter(MarketSearch.sector==sector, MarketSearch.county==county, MarketSearch.created_at >= last_30).count()
        total = self.db.query(MarketSearch).filter(MarketSearch.sector==sector, MarketSearch.county==county).count()
        macro_data = {}
        if NEWS_API_KEY:
            news_url = f"https://newsapi.org/v2/everything?q={sector}+Kenya&apiKey={NEWS_API_KEY}&pageSize=3"
            news = await self._call_api(news_url)
            macro_data["latest_news"] = [n["title"] for n in news.get("articles", [])]
        return {
            "query": q,
            "sector": sector,
            "county": county,
            "searches_30_days": volume_30d,
            "total_searches_all_time": total,
            "market_size_estimate_kes": volume_30d * 3500000,
            "macro_signals": macro_data,
            "data_source": "EvidLens DB + NewsAPI"
        }

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        total_searches = self.db.query(MarketSearch).count()
        total_companies = self.db.query(MarketMetric.company_name).distinct().count()
        top_sector = self.db.query(MarketSearch.sector, func.count(MarketSearch.id).label('c')).group_by(MarketSearch.sector).order_by(desc('c')).first()
        top_county = self.db.query(MarketSearch.county, func.count(MarketSearch.id).label('c')).group_by(MarketSearch.county).order_by(desc('c')).first()
        trending = self.db.query(MarketSearch.query, func.count(MarketSearch.id).label('c')).group_by(MarketSearch.query).order_by(desc('c')).limit(5).all()
        return {
            "insights_generated": total_searches,
            "active_products": 5,
            "sectors_covered": 75,
            "reports_exported": 0,
            "top_sector": top_sector[0] if top_sector else "N/A",
            "top_county": top_county[0] if top_county else "N/A",
            "trending_queries": [{"query": q, "count": c} for q,c in trending]
        }

    async def get_real_time_terminal(self, sector: str, county: str) -> Dict[str, Any]:
        now = datetime.utcnow()
        last_1h = self.db.query(MarketSearch).filter(MarketSearch.sector==sector, MarketSearch.county==county, MarketSearch.created_at >= now - timedelta(hours=1)).count()
        last_24h = self.db.query(MarketSearch).filter(MarketSearch.sector==sector, MarketSearch.county==county, MarketSearch.created_at >= now - timedelta(days=1)).count()
        last_7d = self.db.query(MarketSearch).filter(MarketSearch.sector==sector, MarketSearch.county==county, MarketSearch.created_at >= now - timedelta(days=7)).count()
        trend = "UP" if last_1h > (last_24h/24) else "DOWN"
        return {
            "sector": sector,
            "county": county,
            "intent_searches_1h": last_1h,
            "intent_searches_24h": last_24h,
            "intent_searches_7d": last_7d,
            "trend": trend,
            "last_updated": now.isoformat()
        }

    async def get_location_data(self, county: str) -> Dict[str, Any]:
        if not LOCATIONIQ_KEY:
            return {"error": "Set LOCATIONIQ_KEY in Render Env Vars"}
        url = f"https://us1.locationiq.com/v1/search.php?key={LOCATIONIQ_KEY}&q={county},Kenya&format=json"
        data = await self._call_api(url)
        return {"county": county, "geo_data": data}
