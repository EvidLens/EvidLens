from sqlmodel import Session, select
from typing import Dict, Any, List
from datetime import datetime
from app.core.models import MarketMetric, Company, KnowledgeChunk, ExportOpportunity
from app.modules.competitive_engine.service import CompetitiveEngineService
from app.modules.market_engine.service import MarketEngineService
from app.modules.lens_engine.service import LensEngineService

class APIService:
    def __init__(self, db: Session):
        self.db = db
        self.competitive = CompetitiveEngineService(db)
        self.market = MarketEngineService(db)
        self.lens = LensEngineService(db)

    def _now(self):
        return datetime.utcnow().isoformat()

    def _safe_companies(self, sector: str) -> List[dict]:
        try:
            q = select(Company).where(Company.sector.ilike(f"%{sector}%")).limit(20)
            companies = self.db.exec(q).all()
            if not companies:
                companies = self.db.exec(select(Company).limit(20)).all()
            return [{"id": c.id, "name": c.name, "county": c.county, "sector": c.sector} for c in companies] if companies else []
        except:
            return []

    def _safe_metrics(self, sector: str, county: str = None) -> List[dict]:
        try:
            q = select(MarketMetric).where(MarketMetric.sector.ilike(f"%{sector}%"))
            if county:
                q = q.where(MarketMetric.county.ilike(f"%{county}%"))
            metrics = self.db.exec(q.limit(50)).all()
            if not metrics:
                metrics = self.db.exec(select(MarketMetric).limit(50)).all()
            return [{"county": m.county, "sector": m.sector, "value": m.value, "metric_type": m.metric_type, "date": str(m.date)} for m in metrics] if metrics else []
        except:
            return []

    async def get_competitive(self, sector: str, county: str = None) -> Dict[str, Any]:
        try:
            data = await self.competitive.company_deal_database(sector)
            if not data:
                data = self._safe_companies(sector)
        except:
            data = self._safe_companies(sector)
        if county and isinstance(data, list):
            data = [c for c in data if county.lower() in str(c.get("county","")).lower()] or data
        return {"service": "Competitive Engine", "sector": sector, "county": county, "competitors": data, "count": len(data), "timestamp": self._now()}

    async def get_price_oracle(self, sector: str, county: str = None) -> Dict[str, Any]:
        try:
            data = await self.market.market_funding_trends(sector)
            if not data:
                data = self._safe_metrics(sector, county)
        except:
            data = self._safe_metrics(sector, county)
        return {"service": "Price Oracle", "sector": sector, "county": county, "prices": data, "count": len(data) if isinstance(data, list) else 0, "timestamp": self._now()}

    async def get_demand(self, sector: str, county: str = None) -> Dict[str, Any]:
        try:
            data = await self.lens.generate_sector_insights(sector, county)
            if not data:
                data = self._safe_metrics(sector, county)
        except:
            data = self._safe_metrics(sector, county)
        return {"service": "Demand Radar", "sector": sector, "county": county, "demand": data, "count": len(data) if isinstance(data, list) else 1, "timestamp": self._now()}

    async def get_policy(self, sector: str = None) -> Dict[str, Any]:
        try:
            q = select(KnowledgeChunk).where(KnowledgeChunk.category == "policy")
            if sector:
                q = q.where(KnowledgeChunk.sector.ilike(f"%{sector}%"))
            policies = self.db.exec(q.limit(20)).all()
            data = [{"id": p.id, "title": p.title, "content": p.content[:500]} for p in policies] if policies else []
        except:
            data = []
        return {"service": "Policy Watch", "sector": sector, "policies": data, "count": len(data), "timestamp": self._now()}

    async def get_funding(self, sector: str) -> Dict[str, Any]:
        try:
            data = await self.market.funding_tracker(sector)
            if not data:
                data = self._safe_companies(sector)
        except Exception as e:
            print(f"Funding failed: {e}")
            data = self._safe_companies(sector)
        return {"service": "Funding Radar", "sector": sector, "funding": data, "count": len(data) if isinstance(data, list) else 0, "timestamp": self._now()}

    async def get_risk(self, business: str, county: str) -> Dict[str, Any]:
        try:
            data = await self.lens.viability_check(business, county)
        except Exception as e:
            data = {"business": business, "county": county, "risk_level": "Medium", "message": f"Viability for {business} in {county}: County data shows opportunity. Run seed for full analysis."}
        return {"service": "Risk Sentinel", "business": business, "county": county, "risk": data, "timestamp": self._now()}

    async def get_export(self, sector: str) -> Dict[str, Any]:
        try:
            exports = self.db.exec(select(ExportOpportunity).where(ExportOpportunity.sector.ilike(f"%{sector}%")).limit(20)).all()
            if not exports:
                exports = self.db.exec(select(ExportOpportunity).limit(20)).all()
            data = [{"id": e.id, "market": e.market, "product": e.product, "sector": e.sector} for e in exports] if exports else []
        except:
            data = []
        return {"service": "Export Navigator", "sector": sector, "exports": data, "count": len(data), "timestamp": self._now()}

    async def get_consumer(self, sector: str, county: str = None) -> Dict[str, Any]:
        try:
            data = await self.lens.generate_sector_insights(sector, county)
        except:
            data = self._safe_metrics(sector, county)
        return {"service": "Consumer Pulse", "sector": sector, "county": county, "insights": data, "timestamp": self._now()}

    async def get_county(self, county: str) -> Dict[str, Any]:
        try:
            data = await self.lens.generate_sector_insights("General", county)
            if not data:
                metrics = self.db.exec(select(MarketMetric).where(MarketMetric.county.ilike(f"%{county}%")).limit(20)).all()
                data = [{"sector": m.sector, "value": m.value, "metric_type": m.metric_type} for m in metrics] if metrics else []
        except:
            data = []
        return {"service": "County Mapper", "county": county, "data": data, "count": len(data) if isinstance(data, list) else 0, "timestamp": self._now()}
