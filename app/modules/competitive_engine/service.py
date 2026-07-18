from sqlmodel import Session, select
from datetime import datetime, timedelta
from app.modules.company_db.models import Company, FundingDeal
from app.modules.traffic.models import TrafficSnapshot

class CompetitiveEngineService:
    def __init__(self, db: Session):
        self.db = db

    async def company_deal_database(self, sector: str, company_name: str = None):
        query = select(Company).where(Company.sector == sector)
        if company_name:
            query = query.where(Company.name.ilike(f"%{company_name}%"))
        return self.db.exec(query).all()

    async def funding_tracker(self, sector: str, investor: str = None, date_range: str = "90d"):
        days = int(date_range.replace("d", ""))
        since = datetime.utcnow() - timedelta(days=days)
        query = select(FundingDeal).where(FundingDeal.sector == sector, FundingDeal.date >= since)
        if investor:
            query = query.where(FundingDeal.investor.ilike(f"%{investor}%"))
        return self.db.exec(query).all()

    async def digital_traffic_analyzer(self, competitor1: str, competitor2: str, date_range: str = "30d"):
        query = select(TrafficSnapshot).where(
            TrafficSnapshot.competitor.in_([competitor1, competitor2])
        )
        return self.db.exec(query).all()

    async def competitor_monitor(self, competitor: str, signal_type: str):
        query = select(Company).where(Company.name.ilike(f"%{competitor}%"))
        return self.db.exec(query).all()
