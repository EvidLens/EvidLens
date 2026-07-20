from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, Index
from sqlalchemy.sql import func
from app.modules.database import Base

class MarketSearch(Base):
    __tablename__ = "market_searches"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    query = Column(String(255), nullable=False, index=True)
    sector = Column(String(100), nullable=True, index=True)
    
    country = Column(String(50), default="Kenya")
    county = Column(String(100), nullable=True, index=True)
    sub_county = Column(String(100), nullable=True, index=True)
    ward = Column(String(100), nullable=True, index=True)
    town = Column(String(100), nullable=True, index=True)
    
    demand_level = Column(String(20), nullable=True)
    market_size_kes = Column(Float, nullable=True)
    growth_rate = Column(Float, nullable=True)
    price_min = Column(Float, nullable=True)
    price_max = Column(Float, nullable=True)
    price_avg = Column(Float, nullable=True)
    sentiment_summary = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_search_geo', 'sector', 'county', 'sub_county', 'ward', 'town'),
    )

class Competitor(Base):
    __tablename__ = "competitors"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    
    country = Column(String(50), default="Kenya")
    county = Column(String(100), nullable=False, index=True)
    sub_county = Column(String(100), nullable=True, index=True)
    ward = Column(String(100), nullable=True, index=True)
    town = Column(String(100), nullable=True, index=True)
    
    business_name = Column(String(255), nullable=False)
    source = Column(String(50), default="OSM")
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    address = Column(Text, nullable=True)
    avg_rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0)
    
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_competitor_geo', 'sector', 'county', 'sub_county', 'ward', 'town'),
    )

class MarketMetric(Base):
    __tablename__ = "market_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    
    country = Column(String(50), default="Kenya")
    county = Column(String(100), nullable=True, index=True)
    sub_county = Column(String(100), nullable=True, index=True)
    ward = Column(String(100), nullable=True, index=True)
    town = Column(String(100), nullable=True, index=True)
    
    metric_type = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    period = Column(String(20), nullable=False)
    source = Column(String(100), nullable=False)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('ix_metric_geo_type', 'sector', 'metric_type', 'county', 'sub_county'),
    )

# KB DATA TABLES - Added to unblock knowledge_base service
class PriceTrend(Base):
    __tablename__ = "price_trends"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    county = Column(String(100), nullable=False, index=True)
    product_name = Column(String(255), nullable=False)
    price_kes = Column(Float, nullable=False)
    price_change_percent = Column(Float, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DemandSignal(Base):
    __tablename__ = "demand_signals"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    county = Column(String(100), nullable=False, index=True)
    signal_type = Column(String(100), nullable=False)
    signal_value = Column(Float, nullable=False)
    period = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LocationMetric(Base):
    __tablename__ = "location_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    county = Column(String(100), nullable=False, index=True)
    metric_type = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ProductCatalog(Base):
    __tablename__ = "product_catalog"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    product_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
