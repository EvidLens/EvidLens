from app.modules.database import engine
from sqlmodel import SQLModel

def init_db():
    # Import models here so tables get created. No circular import because SQLModel comes from database.py
    from app.modules.market_engine.models import MarketSearch, MarketMetric
    from app.modules.competitive_engine.models import Company, FundingDeal, TrafficSnapshot
    
    SQLModel.metadata.create_all(bind=engine)
