from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone

UTC = timezone.utc

# Re-export core models
from app.core.models import MarketSearch, MarketMetric

class ProductPrice(SQLModel, table=True):
    __tablename__ = "product_price"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    product_name: str = Field(index=True, max_length=255)
    brand: Optional[str] = Field(default=None, max_length=255)
    price_kes: float
    unit: str = Field(default="pcs", max_length=50)
    outlet_id: Optional[int] = Field(default=None, foreign_key="retail_outlet.id")
    county: str = Field(index=True, max_length=100)
    subcounty: Optional[str] = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)

class RetailOutlet(SQLModel, table=True):
    __tablename__ = "retail_outlet"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=255)
    outlet_type: str = Field(default="Retail", max_length=100)
    county: str = Field(index=True, max_length=100)
    subcounty: Optional[str] = Field(default=None, max_length=100)
    lat: float = Field(default=0.0)
    lng: float = Field(default=0.0)
    address: Optional[str] = Field(default=None, max_length=500)

class Competitor(SQLModel, table=True):
    __tablename__ = "competitor"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=255)
    sector: str = Field(index=True, max_length=100)
    county: str = Field(index=True, max_length=100)
    lat: float = Field(default=0.0)
    lng: float = Field(default=0.0)
    description: Optional[str] = Field(default=None, max_length=1000)
    market_share: Optional[float] = Field(default=None)
