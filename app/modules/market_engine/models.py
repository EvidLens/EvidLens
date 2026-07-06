from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, Index
from sqlalchemy.sql import func
from app.modules.database import Base

class MarketSearch(Base):
    __tablename__ = "market_searches"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    
    query = Column(String, nullable=False, index=True)
    sector = Column(String, nullable=True, index=True)
    county = Column(String, nullable=True, index=True)
    
    # Aggregated results from all lanes
    demand_level = Column(String, nullable=True)
    market_size_kes = Column(Float, nullable=True)
    growth_rate = Column(Float, nullable=True)
    
    price_min = Column(Float, nullable=True)
    price_max = Column(Float, nullable=True)
    price_avg = Column(Float, nullable=True)
    
    sentiment_summary = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_search_query_location', 'query', 'county'),
    )

class Competitor(Base):
    __tablename__ = "competitors"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String, nullable=False, index=True)
    county = Column(String, nullable=False, index=True)
    
    business_name = Column(String, nullable=False)
    source = Column(String, default="OSM")
    
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    address = Column(String, nullable=True)
    
    avg_rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0)
    
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_competitor_sector_county', 'sector', 'county'),
    )

class MarketMetric(Base):
    __tablename__ = "market_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String, nullable=False, index=True)
    county = Column(String, nullable=True, index=True)
    
    metric_type = Column(String, nullable=False)
    metric_value = Column(Float, nullable=False)
    
    period = Column(String, nullable=False)
    source = Column(String, nullable=False)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('ix_metric_sector_type', 'sector', 'metric_type'),
    )
