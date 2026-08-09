from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, UTC

# Re-export core models so old imports still work
from app.core.models import MarketSearch, MarketMetric

class ProductPrice(SQLModel, table=True):
    __tablename__ = "product_price"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    product_name: str = Field(index=True)
    brand: Optional[str] = None
    price_kes: float
    unit: str = "pcs" # pcs, kg, litre
    outlet_id: Optional[int] = Field(default=None, foreign_key="retail_outlet.id")
    county: str = Field(index=True)
    subcounty: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class RetailOutlet(SQLModel, table=True):
    __tablename__ = "retail_outlet"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    outlet_type: str = "Retail" # Retail, Wholesale, Market
    county: str = Field(index=True)
    subcounty: Optional[str] = None
    lat: float = 0
    lng: float = 0
    address: Optional[str] = None

class Competitor(SQLModel, table=True):
    __tablename__ = "competitor"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    sector: str = Field(index=True)
    county: str = Field(index=True)
    lat: float = 0
    lng: float = 0
    description: Optional[str] = None
    market_share: Optional[float] = None
