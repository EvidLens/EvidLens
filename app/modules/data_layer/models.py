from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Index
from sqlalchemy.sql import func
from app.modules.db import Base
import enum

class DataSource(str, enum.Enum):
    jumia = "jumia"
    naivas = "naivas"
    carrefour = "carrefour"
    knbs = "knbs"
    google_trends = "google_trends"
    openfoodfacts = "openfoodfacts"
    locationiq = "locationiq"
    osm = "osm"

class PriceTrend(Base):
    __tablename__ = "price_trends"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String, nullable=False, index=True)
    fmcg_category = Column(String, nullable=False, index=True)
    product_name = Column(String, nullable=False, index=True)
    brand = Column(String, nullable=True)
    
    county = Column(String, nullable=True, index=True)
    source = Column(Enum(DataSource), default=DataSource.jumia)
    source_url = Column(String, nullable=True)
    
    price_kes = Column(Float, nullable=False)
    previous_price_kes = Column(Float, nullable=True)
    price_change_percent = Column(Float, default=0.0)
    
    scraped_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    __table_args__ = (
        Index('ix_price_sector_county_product', 'sector', 'county', 'product_name'),
    )

class DemandSignal(Base):
    __tablename__ = "demand_signals"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String, nullable=False, index=True)
    county = Column(String, nullable=True, index=True)
    
    signal_type = Column(String, nullable=False)
    signal_value = Column(Float, nullable=False)
    signal_source = Column(Enum(DataSource), default=DataSource.google_trends)
    
    period = Column(String, nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

class LocationMetric(Base):
    __tablename__ = "location_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String, nullable=False, index=True)
    county = Column(String, nullable=False, index=True)
    sub_county = Column(String, nullable=True)
    
    metric_type = Column(String, nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_source = Column(Enum(DataSource), default=DataSource.osm)
    
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    geojson = Column(String, nullable=True)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class FMCGCatalog(Base):
    __tablename__ = "fmcg_catalog"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False, index=True)
    subcategory = Column(String, nullable=False, index=True)
    product_name = Column(String, nullable=False)
    brand = Column(String, nullable=True)
    barcode = Column(String, nullable=True, unique=True)
    source = Column(Enum(DataSource), default=DataSource.openfoodfacts)
