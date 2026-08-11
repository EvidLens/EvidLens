from typing import Optional
from sqlmodel import SQLModel, Field, Index
from sqlalchemy import Column, Enum, JSON, Text
from datetime import datetime, date
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

class Subscription(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    user_id: int
    plan: str
    status: str
    expires_at: datetime
    mpesa_receipt: str = None

class QueryLog(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    user_id: int
    date: date

class MpesaTransaction(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    user_id: int
    phone: str
    amount: float
    receipt: str
    checkout_id: str
    plan: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Sector(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    sector_number: int
    parent_category: str = Field(default="General")
    name: str = Field(unique=True)

class County(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    name: str = Field(unique=True)

class SubCounty(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    name: str
    county_id: int = Field(foreign_key="county.id")

class FMCGProduct(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    category: str

class Company(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    name: str
    sector: str
    county: str
    subcounty: str = None
    rating: float = 0
    reviews: int = 0
    address: str
    lat: float
    lng: float

class MarketMetric(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    product_name: str
    sector: str
    county: str
    subcounty: str = "All"
    demand_score: int
    market_size_kes: float
    growth_percent: float
    volume: int
    opportunity_score: float = 0
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class MarketSearch(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    query: str
    sector: str
    county: str
    score: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MarketPrice(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    product_name: str
    price: float
    county: str
    market: str
    source: str = "AIT"
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

class NewsArticle(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str
    keywords: str
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

class SocialPost(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    platform: str
    post_id: str
    text: str
    author: str
    created_at: datetime
    keywords: str
    sentiment: str = "neutral"
    created_at_db: datetime = Field(default_factory=datetime.utcnow)

class PriceTrend(SQLModel, table=True):
    __tablename__ = "price_trends"
    __table_args__ = (
        Index('ix_price_sector_county_product', 'sector', 'county', 'product_name'),
        {"extend_existing": True}
    )
    id: int = Field(default=None, primary_key=True)
    sector: str = Field(index=True, max_length=100)
    category: str = Field(None, index=True, max_length=100)
    subcategory: str = Field(None, index=True, max_length=100)
    product_name: str = Field(index=True, max_length=255)
    brand: str = Field(None, max_length=100)
    sku: str = Field(None, max_length=100)
    county: str = Field(None, index=True, max_length=50)
    source: DataSource = Field(default=DataSource.jumia, sa_column=Column(Enum(DataSource)))
    source_url: str = Field(None, max_length=500)
    price_kes: float
    previous_price_kes: float = None
    price_change_percent: float = 0.0
    scraped_at: datetime = Field(default_factory=datetime.utcnow, index=True)

class DemandSignal(SQLModel, table=True):
    __tablename__ = "demand_signals"
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    sector: str = Field(index=True, max_length=100)
    county: str = Field(None, index=True, max_length=50)
    signal_type: str = Field(index=True, max_length=50)
    signal_value: float
    signal_source: DataSource = Field(default=DataSource.google_trends, sa_column=Column(Enum(DataSource)))
    period: str = Field(index=True, max_length=20)
    recorded_at: datetime = Field(default_factory=datetime.utcnow, index=True)

class LocationMetric(SQLModel, table=True):
    __tablename__ = "location_metrics"
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    sector: str = Field(index=True, max_length=100)
    county: str = Field(index=True, max_length=50)
    sub_county: str = Field(None, max_length=50)
    metric_type: str = Field(index=True, max_length=50)
    metric_value: float
    metric_source: DataSource = Field(default=DataSource.osm, sa_column=Column(Enum(DataSource)))
    lat: float = None
    lng: float = None
    geojson: str = Field(None, sa_column=Column(Text))
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ProductCatalog(SQLModel, table=True):
    __tablename__ = "product_catalog"
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    sector: str = Field(index=True, max_length=100)
    category: str = Field(index=True, max_length=100)
    subcategory: str = Field(None, index=True, max_length=100)
    product_name: str = Field(max_length=255)
    brand: str = Field(None, max_length=100)
    barcode: str = Field(None, max_length=50, unique=True)
    attributes: dict = Field(None, sa_column=Column(JSON))
    source: DataSource = Field(default=DataSource.openfoodfacts, sa_column=Column(Enum(DataSource)))

class CompanyProfile(SQLModel, table=True):
    __tablename__ = "company_profiles"
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, primary_key=True)
    sector: str = Field(index=True, max_length=100)
    company_name: str = Field(index=True, max_length=255)
    registration_number: str = Field(None, max_length=50, unique=True)
    county: str = Field(None, index=True, max_length=50)
    employees: int = None
    revenue_estimate_kes: float = None
    website: str = Field(None, max_length=255)
    source: DataSource = Field(default=DataSource.company_registry, sa_column=Column(Enum(DataSource)))
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class PolicyWatch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    country: str = Field(default="Kenya", index=True)
    category: str = Field(index=True)
    sector: str = Field(default="All", index=True)
    impact_level: str = Field(default="Medium")
    effective_date: Optional[date] = Field(default=None)
    summary: str
    source: str
    source_url: str
    status: str = Field(default="Active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ExportOpportunity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product: str = Field(index=True)
    sector: str = Field(index=True)
    origin_country: str = Field(default="Kenya")
    destination_country: str = Field(index=True)
    destination_region: Optional[str] = Field(default=None)
    hs_code: Optional[str] = Field(default=None)
    demand_score: int = Field(default=50)
    avg_price_usd: Optional[float] = Field(default=None)
    market_size_usd: Optional[float] = Field(default=None)
    growth_percent: Optional[float] = Field(default=None)
    tariff_percent: Optional[float] = Field(default=None)
    competitors: Optional[str] = Field(default=None)
    requirements: Optional[str] = Field(default=None)
    opportunity_score: int = Field(default=50)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
