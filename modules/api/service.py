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

    async def get_competitive(self, sector: str, county: str = None) -> Dict[str, Any]:
        data = await self.competitive.company_deal_database(sector)
        if county:
            data = [c for c in data if c.get("county") == county]
        return {"service": "Competitive Engine", "sector": sector, "county": county, "competitors": data, "count": len(data), "timestamp": datetime.utcnow().isoformat()}

    async def get_price_oracle(self, sector: str, county: str = None) -> Dict[str, Any]:
        data = await self.market.market_funding_trends(sector)
        return {"service": "Price Oracle", "sector": sector, "county": county, "prices": data, "timestamp": datetime.utcnow().isoformat()}

    async def get_demand(self, sector: str, county: str = None) -> Dict[str, Any]:
        data = await self.lens.generate_sector_insights(sector, county)
        return {"service": "Demand Radar", "sector": sector, "county": county, "demand": data, "timestamp": datetime.utcnow().isoformat()}

    async def get_policy(self, sector: str = None) -> Dict[str, Any]:
        return {"service": "Policy Watch", "sector": sector, "policies": [], "timestamp": datetime.utcnow().isoformat()}

    async def get_funding(self, sector: str) -> Dict[str, Any]:
        data = await self.market.funding_tracker(sector)
        return {"service": "Funding Radar", "sector": sector, "funding": data, "timestamp": datetime.utcnow().isoformat()}

    async def get_risk(self, business: str, county: str) -> Dict[str, Any]:
        data = await self.lens.viability_check(business, county)
        return {"service": "Risk Sentinel", "business": business, "county": county, "risk": data, "timestamp": datetime.utcnow().isoformat()}

    async def get_export(self, sector: str) -> Dict[str, Any]:
        return {"service": "Export Navigator", "sector": sector, "exports": [], "timestamp": datetime.utcnow().isoformat()}

    async def get_consumer(self, sector: str, county: str = None) -> Dict[str, Any]:
        data = await self.lens.generate_sector_insights(sector, county)
        return {"service": "Consumer Pulse", "sector": sector, "county": county, "insights": data, "timestamp": datetime.utcnow().isoformat()}

    async def get_county(self, county: str) -> Dict[str, Any]:
        data = await self.lens.generate_sector_insights("General", county)
        return {"service": "County Mapper", "county": county, "data": data, "timestamp": datetime.utcnow().isoformat()}
