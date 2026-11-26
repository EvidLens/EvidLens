from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, Index
from sqlalchemy.sql import func
from app.modules.database import Base
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Column as SAColumn, JSON as SAJSON

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

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
    __table_args__ = (Index('ix_search_geo', 'sector', 'county', 'sub_county', 'ward', 'town'),)

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
    review_count = Column(Integer, nullable=True)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index('ix_competitor_geo', 'sector', 'county', 'sub_county', 'ward', 'town'),)

class PriceTrend(Base):
    __tablename__ = "price_trends"
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    county = Column(String(100), nullable=False, index=True)
    product_name = Column(String(255), nullable=False)
    price_kes = Column(Float, nullable=False)
    price_change_percent = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DemandSignal(Base):
    __tablename__ = "demand_signals"
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    county = Column(String(100), nullable=False, index=True)
    signal_type = Column(String(100), nullable=False)
    signal_value = Column(Float, nullable=True)
    period = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LocationMetric(Base):
    __tablename__ = "location_metrics"
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    county = Column(String(100), nullable=False, index=True)
    metric_type = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ProductCatalog(Base):
    __tablename__ = "product_catalog"
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    product_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MarketMetric(SQLModel, table=True):
    __tablename__ = "market_metrics"
    __table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    sector: str = Field(index=True)
    county: Optional[str] = Field(default=None, index=True)
    metric_name: str = Field(index=True)
    metric_value: Optional[float] = Field(default=None)
    year: Optional[int] = Field(default=None, index=True)
    source: Optional[str] = Field(default=None)
    extra_data: dict = Field(default={}, sa_column=SAColumn("metadata", SAJSON))
    created_at: datetime = Field(default_factory=_utcnow, sa_column_kwargs={"server_default": func.now()})

class MarketEngineReport(SQLModel, table=True):
    __tablename__ = "market_engine_reports"
    __table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, index=True)
    title: str = Field(index=True)
    sector: Optional[str] = Field(default=None, index=True)
    county: Optional[str] = Field(default=None, index=True)
    file_url: Optional[str] = Field(default=None)
    file_type: str = Field(default="pdf")
    report_data: dict = Field(default={}, sa_column=SAColumn("report_data", SAJSON))
    created_at: datetime = Field(default_factory=_utcnow, sa_column_kwargs={"server_default": func.now()})
