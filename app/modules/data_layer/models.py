from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Index, Text, JSON
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
    company_registry = "company_registry"
    kenya_gazette = "kenya_gazette"
    twitter = "twitter"
    news = "news"

class PriceTrend(Base):
    __tablename__ = "price_trends"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True) # "Construction Materials", "Pharmaceuticals"
    category = Column(String(100), nullable=True, index=True) # "Cement", "Painkillers" - was fmcg_category
    subcategory = Column(String(100), nullable=True, index=True)
    product_name = Column(String(255), nullable=False, index=True)
    brand = Column(String(100), nullable=True)
    sku = Column(String(100), nullable=True) # for non-FMCG products
    
    county = Column(String(50), nullable=True, index=True)
    source = Column(Enum(DataSource), default=DataSource.jumia)
    source_url = Column(String(500), nullable=True)
    
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
    sector = Column(String(100), nullable=False, index=True)
    county = Column(String(50), nullable=True, index=True)
    
    signal_type = Column(String(50), nullable=False) # knbs_index, google_trends, job_posts
    signal_value = Column(Float, nullable=False)
    signal_source = Column(Enum(DataSource), default=DataSource.google_trends)
    
    period = Column(String(20), nullable=False) # "2026-04"
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

class LocationMetric(Base):
    __tablename__ = "location_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    county = Column(String(50), nullable=False, index=True)
    sub_county = Column(String(50), nullable=True)
    
    metric_type = Column(String(50), nullable=False) # business_density, rent_per_sqm
    metric_value = Column(Float, nullable=False)
    metric_source = Column(Enum(DataSource), default=DataSource.osm)
    
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    geojson = Column(Text, nullable=True)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ProductCatalog(Base):
    __tablename__ = "product_catalog" # was fmcg_catalog
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True) # NEW: works for any sector
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True, index=True)
    product_name = Column(String(255), nullable=False)
    brand = Column(String(100), nullable=True)
    barcode = Column(String(50), nullable=True, unique=True)
    attributes = Column(JSON, nullable=True) # NEW: for specs. {dosage: "500mg", engine: "1.6L"}
    source = Column(Enum(DataSource), default=DataSource.openfoodfacts)

class CompanyProfile(Base):
    __tablename__ = "company_profiles" # NEW for Lane 2
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    company_name = Column(String(255), nullable=False, index=True)
    registration_number = Column(String(50), nullable=True, unique=True)
    county = Column(String(50), nullable=True, index=True)
    employees = Column(Integer, nullable=True)
    revenue_estimate_kes = Column(Float, nullable=True)
    website = Column(String(255), nullable=True)
    source = Column(Enum(DataSource), default=DataSource.company_registry)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
