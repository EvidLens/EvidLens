from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Index
from sqlalchemy.sql import func
from app.modules.database import Base
from pydantic import BaseModel

KENYA_COUNTIES = [
    "Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Nyeri", "Meru", "Thika", "Malindi", "Kitale",
    "Garissa", "Kakamega", "Machakos", "Embu", "Kericho", "Bungoma", "Mumias", "Busia", "Homa Bay", 
    "Kilifi", "Kiambu", "Naivasha", "Nanyuki", "Voi", "Wajir", "Isiolo", "Mandera", "Lamu", "Marsabit"
]

# ========== SQLALCHEMY DB MODELS ==========
class LocationComparison(Base):
    __tablename__ = "location_comparisons"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String, nullable=False, index=True)
    
    location_type = Column(String, default="county")
    location_a = Column(String, nullable=False, index=True)
    location_b = Column(String, nullable=False, index=True)
    
    # Metrics from other lanes
    business_density_a = Column(Float, default=0.0)
    business_density_b = Column(Float, default=0.0)
    avg_price_a = Column(Float, default=0.0)
    avg_price_b = Column(Float, default=0.0)
    demand_score_a = Column(Float, default=0.0)
    demand_score_b = Column(Float, default=0.0)
    sentiment_score_a = Column(Float, default=0.0)
    sentiment_score_b = Column(Float, default=0.0)
    
    # Calculated
    opportunity_gap = Column(Float, default=0.0)
    recommendation = Column(String, nullable=True)
    
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_comparison_sector_locations', 'sector', 'location_a', 'location_b'),
    )

class OpportunityHeatmap(Base):
    __tablename__ = "opportunity_heatmaps"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String, nullable=False, index=True)
    county = Column(String, nullable=False, index=True)
    constituency = Column(String, nullable=True)
    
    # Geo
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    
    # Opportunity Score 0-100
    opportunity_score = Column(Float, nullable=False)
    urban_rural = Column(String, nullable=True)
    
    # Breakdown
    factors = Column(JSON, default=dict)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('ix_heatmap_sector_county', 'sector', 'county'),
    )

class PriceArbitrage(Base):
    __tablename__ = "price_arbitrage"
    
    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False)
    
    county_from = Column(String, nullable=False)
    county_to = Column(String, nullable=False)
    price_from = Column(Float, nullable=False)
    price_to = Column(Float, nullable=False)
    
    price_gap_kes = Column(Float, nullable=False)
    margin_percent = Column(Float, nullable=False)
    
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_arbitrage_product', 'product_name', 'county_from', 'county_to'),
    )

# ========== PYDANTIC API MODELS ==========
class LocationComparison(BaseModel):
    sector: str
    location_a: str
    location_b: str
    business_density_a: float = 0.0
    business_density_b: float = 0.0
    avg_price_a: float = 0.0
    avg_price_b: float = 0.0
    demand_score_a: float = 0.0
    demand_score_b: float = 0.0
    sentiment_score_a: float = 0.0
    sentiment_score_b: float = 0.0
    opportunity_gap: float = 0.0
    recommendation: str | None = None

    class Config:
        from_attributes = True
