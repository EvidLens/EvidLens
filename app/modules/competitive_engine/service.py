from sqlmodel import Session, select
from datetime import datetime, timedelta
from app.modules.data_layer.models import CompanyProfile, PriceTrend, DemandSignal

class CompetitiveEngineService:
    def __init__(self, db: Session):
        self.db = db

    async def company_deal_database(self, sector: str, company_name: str = None):
        query = select(CompanyProfile).where(CompanyProfile.sector == sector)
        if company_name:
            query = query.where(CompanyProfile.company_name.ilike(f"%{company_name}%"))
        return self.db.exec(query).all()

    async def funding_tracker(self, sector: str, investor: str = None, date_range: str = "90d"):
        # We don't have FundingDeal table yet
        return []

    async def digital_traffic_analyzer(self, competitor1: str, competitor2: str, date_range: str = "30d"):
        days = int(date_range.replace("d", ""))
        since = datetime.utcnow() - timedelta(days=days)
        query = select(PriceTrend).where(
            PriceTrend.sector.in_([competitor1, competitor2]),
            PriceTrend.scraped_at >= since
        )
        return self.db.exec(query).all()

    async def competitor_monitor(self, competitor: str, signal_type: str):
        query = select(DemandSignal).where(DemandSignal.sector == competitor)
        return self.db.exec(query).all()
