from typing import Dict, Any, List, Optional
from sqlmodel import Session, select, func, desc
from datetime import datetime, timezone, timedelta
from app.modules.market_engine.models import MarketMetric, MarketSearch, Competitor, MarketEngineReport
from app.modules.location_intel.models import normalize_county
from app.modules.knowledge_base.models import normalize_sector
import httpx
import os

LOCATIONIQ_KEY = os.getenv("LOCATIONIQ_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _scalar(db: Session, stmt):
    result = db.exec(stmt).first()
    if result is None:
        return 0
    if isinstance(result, tuple):
        return result[0] or 0
    return result or 0

class MarketEngineService:
    def __init__(self, db: Session):
        self.db = db

    async def _call_api(self, url: str) -> Dict:
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()

    async def market_funding_trends(self, sector: Optional[str] = None, county: Optional[str] = None, sub_county: Optional[str] = None) -> List[Dict[str, Any]]:
        q = select(MarketMetric)
        if sector:
            q = q.where(MarketMetric.sector == normalize_sector(sector))
        if county:
            q = q.where(MarketMetric.county == normalize_county(county))
        q = q.order_by(desc(MarketMetric.created_at)).limit(100)
        results = self.db.exec(q).all()
        if sub_county:
            filtered = []
            for m in results:
                extra = m.extra_data or {}
                if extra.get("sub_county") == sub_county:
                    filtered.append(m)
            results = filtered
        return [
            {
                "id": m.id,
                "metric_name": m.metric_name,
                "metric_value": m.metric_value,
                "year": m.year,
                "county": m.county,
                "sector": m.sector,
                "source": m.source,
                "created_at": m.created_at.isoformat() if m.created_at else None
            } for m in results
        ]

    async def get_competitor_overview(self, sector: str, county: Optional[str] = None, sub_county: Optional[str] = None) -> Dict[str, Any]:
        q = select(Competitor).where(Competitor.sector == normalize_sector(sector))
        if county:
            q = q.where(Competitor.county == normalize_county(county))
        if sub_county:
            q = q.where(Competitor.sub_county == sub_county)
        q = q.order_by(desc(Competitor.last_seen_at)).limit(50)
        competitors = self.db.exec(q).all()
        return {
            "sector": sector,
            "county": county,
            "sub_county": sub_county,
            "total_companies_found": len(competitors),
            "companies": [
                {
                    "id": c.id,
                    "name": c.business_name,
                    "sector": c.sector,
                    "county": c.county,
                    "sub_county": c.sub_county,
                    "ward": c.ward,
                    "town": c.town,
                    "lat": c.lat,
                    "lng": c.lng,
                    "address": c.address,
                    "avg_rating": c.avg_rating,
                    "review_count": c.review_count,
                    "source": c.source,
                    "last_seen_at": c.last_seen_at.isoformat() if c.last_seen_at else None
                } for c in competitors
            ]
        }

    async def search_market(self, q: str, sector: Optional[str], county: Optional[str], sub_county: Optional[str] = None) -> Dict[str, Any]:
        sector_n = normalize_sector(sector) if sector else None
        county_n = normalize_county(county) if county else None
        self.db.add(MarketSearch(query=q, sector=sector_n, county=county_n, sub_county=sub_county))
        self.db.commit()
        last_30 = _utcnow() - timedelta(days=30)
        volume_30d = _scalar(self.db, select(func.count(MarketSearch.id)).where(MarketSearch.sector == sector_n, MarketSearch.county == county_n, MarketSearch.created_at >= last_30))
        total = _scalar(self.db, select(func.count(MarketSearch.id)).where(MarketSearch.sector == sector_n, MarketSearch.county == county_n))
        macro_data: Dict[str, Any] = {}
        if NEWS_API_KEY and sector:
            news_url = f"https://newsapi.org/v2/everything?q={sector}+{county}+Kenya&apiKey={NEWS_API_KEY}&pageSize=3&language=en&sortBy=publishedAt"
            try:
                news = await self._call_api(news_url)
                macro_data["latest_news"] = [n.get("title") for n in news.get("articles", []) if n.get("title")]
            except Exception:
                macro_data["latest_news"] = []
        market_size = _scalar(self.db, select(func.sum(MarketMetric.metric_value)).where(MarketMetric.sector == sector_n, MarketMetric.county == county_n, MarketMetric.metric_name == 'market_size_kes'))
        return {
            "query": q,
            "sector": sector_n,
            "county": county_n,
            "sub_county": sub_county,
            "searches_30_days": volume_30d or 0,
            "total_searches_all_time": total or 0,
            "market_size_estimate_kes": float(market_size) if market_size else None,
            "macro_signals": macro_data,
            "data_source": "EvidLens DB + NewsAPI"
        }

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        now = _utcnow()
        seven_days_ago = now - timedelta(days=7)
        fourteen_days_ago = now - timedelta(days=14)
        thirty_days_ago = now - timedelta(days=30)
        total_searches = _scalar(self.db, select(func.count(MarketSearch.id)))
        total_metrics = _scalar(self.db, select(func.count(MarketMetric.id)))
        total_companies = _scalar(self.db, select(func.count(Competitor.id)))
        total_reports = _scalar(self.db, select(func.count(MarketEngineReport.id)))
        searches_last_7 = _scalar(self.db, select(func.count(MarketSearch.id)).where(MarketSearch.created_at >= seven_days_ago))
        searches_prev_7 = _scalar(self.db, select(func.count(MarketSearch.id)).where(MarketSearch.created_at >= fourteen_days_ago, MarketSearch.created_at < seven_days_ago))
        search_growth_pct = round(((searches_last_7 - searches_prev_7) / searches_prev_7 * 100), 2) if searches_prev_7 > 0 else None
        sector_stmt = select(MarketSearch.sector, func.count(MarketSearch.id).label('count')).group_by(MarketSearch.sector).order_by(desc('count')).limit(5)
        top_sectors = [{"sector": s, "count": c} for s, c in self.db.exec(sector_stmt).all() if s]
        county_stmt = select(MarketSearch.county, func.count(MarketSearch.id).label('count')).group_by(MarketSearch.county).order_by(desc('count')).limit(5)
        top_counties = [{"county": c, "count": cnt} for c, cnt in self.db.exec(county_stmt).all() if c]
        sub_county_stmt = select(Competitor.sub_county, func.count(Competitor.id).label('count')).where(Competitor.sub_county.isnot(None)).group_by(Competitor.sub_county).order_by(desc('count')).limit(5)
        top_sub_counties = [{"sub_county": s, "count": cnt} for s, cnt in self.db.exec(sub_county_stmt).all() if s]
        trending_stmt = select(MarketSearch.query, func.count(MarketSearch.id).label('c')).where(MarketSearch.created_at >= seven_days_ago).group_by(MarketSearch.query).order_by(desc('c')).limit(5)
        trending = [{"query": q, "count": c} for q, c in self.db.exec(trending_stmt).all() if q]
        activity_stmt = select(func.date(MarketSearch.created_at).label('day'), func.count(MarketSearch.id)).where(MarketSearch.created_at >= thirty_days_ago).group_by(func.date(MarketSearch.created_at)).order_by('day')
        activity = [{"date": str(d), "searches": cnt} for d, cnt in self.db.exec(activity_stmt).all()]
        metrics_by_sector_stmt = select(MarketMetric.sector, func.avg(MarketMetric.metric_value).label('avg_value')).group_by(MarketMetric.sector).limit(10)
        metrics_by_sector = [{"sector": s, "avg_metric_value": round(v, 2) if v is not None else None} for s, v in self.db.exec(metrics_by_sector_stmt).all() if s]
        latest_reports_stmt = select(MarketEngineReport).order_by(desc(MarketEngineReport.created_at)).limit(5)
        latest_reports = [{"id": r.id, "title": r.title, "sector": r.sector, "county": r.county, "file_type": r.file_type, "created_at": r.created_at.isoformat() if r.created_at else None} for r in self.db.exec(latest_reports_stmt).all()]
        return {
            "overview": {
                "insights_generated": total_searches,
                "total_metrics": total_metrics,
                "total_companies": total_companies,
                "reports_exported": total_reports,
                "sectors_covered": len(top_sectors),
                "search_growth_7d_pct": search_growth_pct
            },
            "breakdowns": {
                "top_sectors": top_sectors,
                "top_counties": top_counties,
                "top_sub_counties": top_sub_counties,
                "metrics_by_sector": metrics_by_sector
            },
            "trends": {
                "trending_queries_7d": trending,
                "activity_last_30_days": activity
            },
            "latest": {
                "reports": latest_reports
            },
            "last_updated": now.isoformat()
        }

    async def get_real_time_terminal(self, sector: str, county: str, sub_county: Optional[str] = None) -> Dict[str, Any]:
        now = _utcnow()
        sector_n = normalize_sector(sector)
        county_n = normalize_county(county)
        base_filters = [MarketSearch.sector == sector_n, MarketSearch.county == county_n]
        if sub_county:
            base_filters.append(MarketSearch.sub_county == sub_county)
        last_1h = _scalar(self.db, select(func.count(MarketSearch.id)).where(*base_filters, MarketSearch.created_at >= now - timedelta(hours=1)))
        last_24h = _scalar(self.db, select(func.count(MarketSearch.id)).where(*base_filters, MarketSearch.created_at >= now - timedelta(days=1)))
        last_7d = _scalar(self.db, select(func.count(MarketSearch.id)).where(*base_filters, MarketSearch.created_at >= now - timedelta(days=7)))
        avg_per_hour = (last_24h or 0) / 24 if last_24h else 0
        trend = "UP" if (last_1h or 0) > avg_per_hour else "DOWN"
        return {
            "sector": sector_n,
            "county": county_n,
            "sub_county": sub_county,
            "intent_searches_1h": last_1h or 0,
            "intent_searches_24h": last_24h or 0,
            "intent_searches_7d": last_7d or 0,
            "trend": trend,
            "last_updated": now.isoformat()
        }

    async def get_location_data(self, county: str, sub_county: Optional[str] = None) -> Dict[str, Any]:
        if not LOCATIONIQ_KEY:
            return {"error": "Set LOCATIONIQ_KEY in Render Env Vars"}
        query = f"{sub_county}, {county}, Kenya" if sub_county else f"{county}, Kenya"
        url = f"https://us1.locationiq.com/v1/search.php?key={LOCATIONIQ_KEY}&q={query}&format=json"
        try:
            data = await self._call_api(url)
            return {"county": county, "sub_county": sub_county, "geo_data": data}
        except Exception:
            return {"county": county, "sub_county": sub_county, "geo_data": None}

from app.core.db import SessionLocal

def _get_service():
    db = SessionLocal()
    service = MarketEngineService(db)
    return service

async def search_market(q, sector, county, sub_county=None):
    s = _get_service()
    try:
        return await s.search_market(q, sector, county, sub_county)
    finally:
        s.db.close()

async def get_dashboard_stats():
    s = _get_service()
    try:
        return await s.get_dashboard_stats()
    finally:
        s.db.close()

async def get_real_time_terminal(sector, county, sub_county=None):
    s = _get_service()
    try:
        return await s.get_real_time_terminal(sector, county, sub_county)
    finally:
        s.db.close()

async def get_competitor_overview(sector, county, sub_county=None):
    s = _get_service()
    try:
        return await s.get_competitor_overview(sector, county, sub_county)
    finally:
        s.db.close()

async def get_location_data(county, sub_county=None):
    s = _get_service()
    try:
        return await s.get_location_data(county, sub_county)
    finally:
        s.db.close()

async def call_groq(prompt):
    return {"status": "removed_per_request"}
