from app.modules.database import engine
from sqlmodel import SQLModel, Session

def init_db():
    from app.modules.market_engine.models import MarketSearch, MarketMetric
    from app.modules.competitive_engine.models import Company, FundingDeal, TrafficSnapshot
    SQLModel.metadata.create_all(bind=engine)

def get_session():
    with Session(engine) as session:
        yield session
