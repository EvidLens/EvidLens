from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Index
from sqlalchemy.sql import func
from app.modules.db import Base
from pydantic import BaseModel

KENYA_COUNTIES = [
    "Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Nyeri", "Meru", "Thika", "Malindi", "Kitale",
    "Garissa", "Kakamega", "Machakos", "Embu", "Kericho", "Bungoma", "Mumias", "Busia", "Homa Bay", 
    "Kilifi", "Kiambu", "Naivasha", "Nanyuki", "Voi", "Wajir", "Isiolo", "Mandera", "Lamu", "Marsabit"
]

class LocationGeo(Base):
    __tablename__ = "location_geo"
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    parent = Column(String(100), nullable=True, index=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    __table_args__ = (
        Index('ix_geo_level_parent', 'level', 'parent'),
    )

class LocationComparison(Base):
    __tablename__ = "location_comparisons"
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    location_type = Column(String(20), default="county", nullable=False)
    location_a = Column(String(100), nullable=False, index=True)
    location_b = Column(String(100), nullable=False, index=True)
    comparison_data = Column(JSON, default=dict)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        Index('ix_comparison_sector_locations', 'sector', 'location_type', 'location_a', 'location_b'),
    )

class OpportunityHeatmap(Base):
    __tablename__ = "opportunity_heatmaps"
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    country = Column(String(50), default="Kenya")
    county = Column(String(100), nullable=True, index=True)
    sub_county = Column(String(100), nullable=True, index=True)
    ward = Column(String(100), nullable=True, index=True)
    town = Column(String(100), nullable=True, index=True)
    opportunity_score = Column(Float, nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    factors = Column(JSON, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        Index('ix_heatmap_geo', 'sector', 'county', 'sub_county', 'ward', 'town'),
    )

class PriceArbitrage(Base):
    __tablename__ = "price_arbitrage"
    id = Column(Integer, primary_key=True, index=True)
    product = Column(String(255), nullable=False, index=True)
    location_type = Column(String(20), nullable=False)
    county_from = Column(String(100), nullable=True)
    county_to = Column(String(100), nullable=True)
    sub_county_from = Column(String(100), nullable=True)
    sub_county_to = Column(String(100), nullable=True)
    town_from = Column(String(100), nullable=True)
    town_to = Column(String(100), nullable=True)
    price_gap_kes = Column(Float, nullable=False)
    margin_percent = Column(Float, nullable=False)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        Index('ix_arbitrage_product_location', 'product', 'location_type'),
    )

class LocationComparisonResponse(BaseModel):
    sector: str
    location_type: str
    location_a: str
    location_b: str
    comparison_data: dict
    class Config:
        from_attributes = True
