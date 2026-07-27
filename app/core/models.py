from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class GeoFilter(SQLModel, table=True):
    __tablename__ = "geofilter"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    country: str = "Kenya"
    county: Optional[str] = Field(index=True, default=None)
    sub_county: Optional[str] = Field(index=True, default=None)
    ward: Optional[str] = Field(index=True, default=None)
    sector_id: int = Field(foreign_key="sector.id")

class Plan(SQLModel, table=True):
    __tablename__ = "plan"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    monthly_price: int
    annual_price: int
    lanes: int
    modules: int
    users: int
    competitors: int
    leads_per_quarter: int
    support_sla: str
    description: str
    features: str

class Module(SQLModel, table=True):
    __tablename__ = "module"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    module_number: int
    lane: str
    name: str
    usage: str
    how_it_helps: str
    sector_examples: str
    min_plan: str = Field(index=True)
    geo_enabled: bool = True

class Sector(SQLModel, table=True):
    __tablename__ = "sector"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    sector_number: int = Field(index=True, unique=True)
    name: str
    parent_category: str

class AddOn(SQLModel, table=True):
    __tablename__ = "addon"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    setup_fee: int
    annual_fee: int
    best_for: str

class ALCService(SQLModel, table=True):
    __tablename__ = "alcservice"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    price: int
    best_for: str

class UserSubscription(SQLModel, table=True):
    __tablename__ = "usersubscription"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    plan_code: str
    lead_credits: int = 0
    api_credits: int = 0
    status: str = "active"
    renews_at: datetime
    default_county: Optional[str] = None
    default_sub_county: Optional[str] = None
    default_ward: Optional[str] = None

# ========== 2. DATABASE MODELS ==========
class MarketMetric(SQLModel, table=True):
    __tablename__ = "market_metrics"
    id: Optional[int] = Field(default=None, primary_key=True)
    product: Optional[str] = None
    county: Optional[str] = None
    subcounty: Optional[str] = None
    sector: Optional[str] = None
    avg_price_kes: Optional[float] = None
    demand_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SocialMention(SQLModel, table=True):
    __tablename__ = "social_mentions"
    id: Optional[int] = Field(default=None, primary_key=True)
    platform: Optional[str] = None
    text: Optional[str] = None
    county: Optional[str] = None
    subcounty: Optional[str] = None
    sector: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class NewsArticle(SQLModel, table=True):
    __tablename__ = "news_articles"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: Optional[str] = None
    summary: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None
    county: Optional[str] = None
    published_at: datetime = Field(default_factory=datetime.utcnow)

class GeoData(SQLModel, table=True):
    __tablename__ = "geo_data"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=100)
    type: str = Field(index=True, max_length=20)
    parent: Optional[str] = Field(default=None, index=True, max_length=100)

class SectorReport(SQLModel, table=True):
    __tablename__ = "sector_reports"
    id: Optional[int] = Field(default=None, primary_key=True)
    sector: str = Field(index=True, max_length=100)
    county: Optional[str] = Field(default=None, index=True, max_length=50)
    title: str = Field(max_length=255)
    summary: str
    key_insights: List[dict] = Field(default=[], sa_column=Column(JSON))
    market_size_kes: Optional[float] = Field(default=None)
    growth_rate_percent: Optional[float] = Field(default=None)
    top_challenges: List[dict] = Field(default=[], sa_column=Column(JSON))
    opportunities: List[dict] = Field(default=[], sa_column=Column(JSON))
    data_sources: List[dict] = Field(default=[], sa_column=Column(JSON))
    generated_by: str = Field(default="EvidLens AI RAG", max_length=100)
    version: str = Field(default="v1.0", max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()})

# ========== 3. REQUEST MODEL ==========
class DetailedAnalysisRequest(BaseModel):
    product: str
    sector: str
    county: str
    subcounties: List[str] = Field(default=["All"])
    budget_kes: float = 0
    business_model: str = "Retail"

    @field_validator('product', 'sector', 'county')
    @classmethod
    def strip_text(cls, v: str) -> str:

# ========== 1. DATABASE MODELS ==========
class MarketMetric(SQLModel, table=True):
    __tablename__ = "market_metrics"

    id: int | None = Field(default=None, primary_key=True)
    product: str | None = None
    county: str | None = None
    sector: str | None = None
    avg_price_kes: float | None = None
    demand_score: float | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SocialMention(SQLModel, table=True):
    __tablename__ = "social_mentions"

    id: int | None = Field(default=None, primary_key=True)
    platform: str | None = None
    text: str | None = None
    county: str | None = None
    sector: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class NewsArticle(SQLModel, table=True):
    __tablename__ = "news_articles"

    id: int | None = Field(default=None, primary_key=True)
    title: str | None = None
    summary: str | None = None
    source: str | None = None
    category: str | None = None
    published_at: datetime = Field(default_factory=datetime.utcnow)

# ========== 2. REQUEST MODEL ==========
class DetailedAnalysisRequest(BaseModel):
    product: str
    sector: str
    county: str
    subcounty: str = ""
    budget_kes: float = 0
    business_model: str = "Retail"

# ====== 2. DB MODELS ======
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    name: str
    phone: Optional[str] = None
    county: Optional[str] = None
    sector: Optional[str] = None
    current_workspace_id: Optional[int] = Field(default=None, foreign_key="workspace.id")
    reset_token: Optional[str] = None
    reset_token_expires: Optional[datetime] = None
    consent_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Workspace(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    owner_id: int = Field(foreign_key="user.id")
    credits: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Subscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    plan: str
    billing: str
    status: str = Field(default="Pending")
    credits: int
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MarketMetric(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    product: str
    sector: str
    county: str
    company_name: Optional[str] = None
    avg_price_kes: float = 0
    demand_score: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KenyaLensBusiness(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sector: str
    county: str
    address: Optional[str] = None
    lat: float = 0
    lng: float = 0

class Funder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    type: str
    sector: str
    county: str
    rating: int
    min_amount: int
    max_amount: int
    interest_rate: float
    requirements: str
    apply_link: str

class Policy(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    summary: str
    impact_statement: str
    category: str
    sector: str
    county: str
    impact: str
    url: str
    published_at: datetime = Field(default_factory=datetime.utcnow)

class SocialMention(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    platform: str
    author: str
    content: str
    sentiment: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class NewsArticle(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    summary: str
    category: str
    url: str
    published_at: datetime = Field(default_factory=datetime.utcnow)

class Company(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sector: str
    county: str

class Report(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    title: str
    data: dict = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KenyaLensSurvey(SQLModel, table=True): id: Optional[int] = Field(default=None, primary_key=True)
class KenyaLensResponse(SQLModel, table=True): id: Optional[int] = Field(default=None, primary_key=True)
class KenyaTenant(SQLModel, table=True): id: Optional[int] = Field(default=None, primary_key=True)
class KenyaLensMember(SQLModel, table=True): id: Optional[int] = Field(default=None, primary_key=True)
        return v.strip()

    class Config:
        extra = "allow"
