from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from datetime import datetime
from app.modules.database import Base

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    sector = Column(String, index=True)
    country = Column(String, default="Kenya")
    county = Column(String)
    website = Column(String)
    directors = Column(JSON)
    valuation = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class FundingDeal(Base):
    __tablename__ = "funding_deals"
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, index=True)
    founder = Column(String)
    investor = Column(String, index=True)
    amount_usd = Column(Float)
    round_type = Column(String)
    date = Column(DateTime, index=True)
    sector = Column(String, index=True)
    source_url = Column(String)

class TrafficSnapshot(Base):
    __tablename__ = "traffic_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    competitor = Column(String, index=True)
    visits = Column(Integer)
    bounce_rate = Column(Float)
    top_pages = Column(JSON)
    date = Column(DateTime, default=datetime.utcnow)
