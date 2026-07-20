from sqlmodel import Session
from typing import Dict, Any
from datetime import datetime

from app.modules.competitive_engine.service import CompetitiveEngineService
from app.modules.market_engine.service import MarketEngineService
from app.modules.lens_engine.service import LensEngineService

class APIService:
    def __init__(self, db: Session):
        self.db = db
        self.competitive = CompetitiveEngineService(db)
        self.market = MarketEngineService(db)
        self.lens = LensEngineService(db)

    async def get_companies(self, sector: str, county: str = None) -> Dict[str, Any]:
        data = await self.competitive.company_deal_database(sector)
        if county:
            data = [c for c in data if c.get("county") == county]
        return {
            "sector": sector,
            "county": county,
            "companies": data,
            "count": len(data),
            "timestamp": datetime.utcnow().isoformat()
        }

    async def get_funding(self, sector: str) -> Dict[str, Any]:
        data = await self.market.funding_tracker(sector)
        return {
            "sector": sector,
            "funding_rounds": data,
            "total_raised_kes": sum([d.get("amount", 0) for d in data]),
            "timestamp": datetime.utcnow().isoformat()
        }

    async def get_market_trends(self, sector: str) -> Dict[str, Any]:
        trends = await self.market.market_funding_trends(sector)
        return {
            "sector": sector,
            "trends": trends,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def get_lens_summary(self, sector: str, county: str = None) -> Dict[str, Any]:
        return await self.lens.generate_sector_insights(sector, county)
