from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column, Index
from sqlalchemy.sql import func
from sqlalchemy import JSON
from pydantic import BaseModel

KENYA_COUNTIES = [
    "Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo-Marakwet", "Embu", "Garissa", "Homa Bay", "Isiolo",
    "Kajiado", "Kakamega", "Kericho", "Kiambu", "Kilifi", "Kirinyaga", "Kisii", "Kisumu", "Kitui",
    "Kwale", "Laikipia", "Lamu", "Machakos", "Makueni", "Mandera", "Marsabit", "Meru", "Migori",
    "Mombasa", "Murang'a", "Nairobi", "Nakuru", "Nandi", "Narok", "Nyamira", "Nyandarua", "Nyeri",
    "Samburu", "Siaya", "Taita-Taveta", "Tana River", "Tharaka-Nithi", "Trans Nzoia", "Turkana",
    "Uasin Gishu", "Vihiga", "Wajir", "West Pokot"
]

class LocationGeo(SQLModel, table=True):
    __tablename__ = "location_geo"

    id: Optional[int] = Field(default=None, primary_key=True)
    level: str = Field(max_length=20, index=True) # county, sub_county, ward, town
    name: str = Field(max_length=100, index=True)
    parent: Optional[str] = Field(default=None, max_length=100, index=True)
    lat: Optional[float] = Field(default=None)
    lng: Optional[float] = Field(default=None)

    __table_args__ = (
        Index('ix_geo_level_parent', 'level', 'parent'),
    )

class LocationComparison(SQLModel, table=True):
    __tablename__ = "location_comparisons"

    id: Optional[int] = Field(default=None, primary_key=True)
    sector: str = Field(max_length=100, index=True)
    location_type: str = Field(default="county", max_length=20)
    location_a: str = Field(max_length=100, index=True)
    location_b: str = Field(max_length=100, index=True)
    comparison_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    calculated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})

    __table_args__ = (
        Index('ix_comparison_sector_locations', 'sector', 'location_type', 'location_a', 'location_b'),
    )

class OpportunityHeatmap(SQLModel, table=True):
    __tablename__ = "opportunity_heatmaps"

    id: Optional[int] = Field(default=None, primary_key=True)
    sector: str = Field(max_length=100, index=True)
    country: str = Field(default="Kenya", max_length=50)
    county: Optional[str] = Field(default=None, max_length=100, index=True)
    sub_county: Optional[str] = Field(default=None, max_length=100, index=True)
    ward: Optional[str] = Field(default=None, max_length=100, index=True)
    town: Optional[str] = Field(default=None, max_length=100, index=True)
    opportunity_score: float
    lat: Optional[float] = Field(default=None)
    lng: Optional[float] = Field(default=None)
    factors: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()})

    __table_args__ = (
        Index('ix_heatmap_geo', 'sector', 'county', 'sub_county', 'ward', 'town'),
    )

class PriceArbitrage(SQLModel, table=True):
    __tablename__ = "price_arbitrage"

    id: Optional[int] = Field(default=None, primary_key=True)
    product: str = Field(max_length=255, index=True)
    location_type: str = Field(max_length=20)
    county_from: Optional[str] = Field(default=None, max_length=100)
    county_to: Optional[str] = Field(default=None, max_length=100)
    sub_county_from: Optional[str] = Field(default=None, max_length=100)
    sub_county_to: Optional[str] = Field(default=None, max_length=100)
    town_from: Optional[str] = Field(default=None, max_length=100)
    town_to: Optional[str] = Field(default=None, max_length=100)
    price_gap_kes: float
    margin_percent: float
    calculated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})

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
