from sqlmodel import SQLModel, Field, Column, JSON
from typing import Optional, List, Dict
from datetime import datetime, timezone, UTC
from pydantic import BaseModel, field_validator
from sqlalchemy import Column, JSON
from sqlalchemy.sql import func
from enum import Enum

UTC = timezone.utc

class ReportType(str, Enum):
    market = "market"
    sector = "sector"

class ReportFormat(str, Enum):
    pdf = "pdf"
    excel = "excel"

class ReportStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"

# --- ALL YOUR EXISTING MODELS ---
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

class User(SQLModel, table=True):
    __tablename__ = "user"
    __table_args__ = {"extend_existing": True}
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class Workspace(SQLModel, table=True):
    __tablename__ = "workspace"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    owner_id: int = Field(foreign_key="user.id")
    credits: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class Subscription(SQLModel, table=True):
    __tablename__ = "subscription"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    plan: str
    billing: str
    status: str = Field(default="Pending")
    credits: int
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class GeoFilter(SQLModel, table=True):
    __tablename__ = "geofilter"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    country: str = "Kenya"
    county: Optional[str] = Field(index=True, default=None)
    sub_county: Optional[str] = Field(index=True, default=None)
    ward: Optional[str] = Field(index=True, default=None)
    sector_id: int = Field(foreign_key="sector.id")

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

class GeoData(SQLModel, table=True):
    __tablename__ = "geo_data"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=100)
    type: str = Field(index=True, max_length=20)
    parent: Optional[str] = Field(default=None, index=True, max_length=100)

class Company(SQLModel, table=True):
    __tablename__ = "company"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sector: str
    county: str

class KenyaLensBusiness(SQLModel, table=True):
    __tablename__ = "kenyalens_business" # FIXED: was kenya_lens_business
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sector: str
    county: str
    address: Optional[str] = None
    lat: float = 0
    lng: float = 0

class MarketMetric(SQLModel, table=True):
    __tablename__ = "market_metrics"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    product: Optional[str] = None
    county: Optional[str] = None
    subcounty: Optional[str] = None
    sector: Optional[str] = None
    company_name: Optional[str] = None
    avg_price_kes: Optional[float] = None
    demand_score: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class NewsArticle(SQLModel, table=True):
    __tablename__ = "news_articles"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    title: Optional[str] = None
    summary: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None
    url: Optional[str] = None
    county: Optional[str] = None
    published_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class SectorReport(SQLModel, table=True):
    __tablename__ = "sector_reports"
    __table_args__ = {"extend_existing": True}
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), sa_column_kwargs={"server_default": func.now()})
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()})

class Report(SQLModel, table=True):
    __tablename__ = "report"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    title: str
    data: dict = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class Deal(SQLModel, table=True):
    __tablename__ = "deals"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    funder_id: Optional[int] = Field(default=None, foreign_key="funder.id")
    
    title: str
    company_name: str
    amount: float
    deal_type: str = Field(description="Equity, Debt, Grant, etc")
    stage: str = Field(description="Seed, Series A, etc")
    status: str = Field(default="pending", description="pending, approved, rejected, closed")
    
    description: Optional[str] = None
    terms: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    closed_at: Optional[datetime] = None

class Funder(SQLModel, table=True):
    __tablename__ = "funder"
    __table_args__ = {"extend_existing": True}
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
    __tablename__ = "policy"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    summary: str
    impact_statement: str
    category: str
    sector: str
    county: str
    impact: str
    url: str
    published_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class KenyaLensSurvey(SQLModel, table=True):
    __tablename__ = "kenyalens_survey"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(index=True, default=None)
    tenant_id: Optional[str] = Field(index=True, default=None)
    business_id: Optional[int] = Field(index=True, foreign_key="kenyalens_business.id", default=None)
    title: str
    status: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class KenyaLensResponse(SQLModel, table=True):
    __tablename__ = "kenyalens_response"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: Optional[str] = Field(index=True, default=None)
    survey_id: int = Field(index=True)
    respondent_phone: Optional[str] = None
    data: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class KenyaTenant(SQLModel, table=True):
    __tablename__ = "kenya_tenants"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class KenyaLensMember(SQLModel, table=True):
    __tablename__ = "kenyalens_member"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(index=True, default=None)
    tenant_id: Optional[str] = Field(index=True, default=None)
    email: str
    role: str = Field(default="member")
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class KenyaLensAlert(SQLModel, table=True):
    __tablename__ = "kenya_lens_alerts"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(index=True, default=None)
    tenant_id: Optional[str] = Field(index=True, default=None)
    title: str
    description: str
    module: str
    severity: str = Field(default="info")
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class KenyaLensApiUsage(SQLModel, table=True):
    __tablename__ = "kenya_lens_api_usage"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(index=True, default=None)
    api_key: str = Field(index=True)
    endpoint: str
    tenant_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class Notification(SQLModel, table=True):
    __tablename__ = "notifications"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    message: str
    type: str
    channel: str
    status: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class PriceData(SQLModel, table=True):
    __tablename__ = "price_data"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: Optional[str] = Field(index=True, default=None)
    product_name: str
    county: str
    sector: str
    price: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class ExportOpportunity(SQLModel, table=True):
    __tablename__ = "export_opportunities"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: Optional[str] = Field(index=True, default=None)
    country: str
    product: str
    opportunity_score: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

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
        return v.strip()

    model_config = {"extra": "allow"}

class MarketSearch(SQLModel, table=True):
    __tablename__ = "market_searches"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    query: str
    sector: Optional[str] = Field(default=None, index=True)
    county: Optional[str] = Field(default=None, index=True)
    product: Optional[str] = Field(default=None, index=True)
    filters: Optional[Dict] = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class KnowledgeChunk(SQLModel, table=True):
    __tablename__ = "knowledge_chunks"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    sector: str = Field(index=True, max_length=100)
    county: Optional[str] = Field(default=None, index=True, max_length=50)
    chunk_text: str
    chunk_type: str = Field(max_length=50)
    source: str = Field(max_length=100)
    embedding: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    chunk_metadata: Dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class ConsumerFeedback(SQLModel, table=True):
    __tablename__ = "consumer_feedback"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(index=True, default=None)
    text: str
    sentiment: Optional[str] = None
    county: Optional[str] = None
    sector: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class SentimentSummary(SQLModel, table=True):
    __tablename__ = "sentiment_summaries"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    sector: str
    county: str
    sentiment: str
    count: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class DataSource(SQLModel, table=True):
    __tablename__ = "data_sources"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    url: Optional[str] = None
    last_fetched: datetime = Field(default_factory=lambda: datetime.now(UTC))

class KenyaLensSubscription(SQLModel, table=True):
    __tablename__ = "kenyalens_subscription"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    plan: str
    status: str

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"

class SubscriptionTier(str, Enum):
    FREE = "free"
    SME_STARTER = "sme_starter" 
    SME_PRO = "sme_pro"
    PROFESSIONAL = "professional"
    BUSINESS = "business"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"
    
class Payment(SQLModel, table=True):
    __tablename__ = "payment"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    amount: float
    status: PaymentStatus
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class SocialMention(SQLModel, table=True):
    __tablename__ = "social_mentions"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    platform: Optional[str] = Field(default=None, index=True, max_length=50)
    content: Optional[str] = None
    author: Optional[str] = Field(default=None, max_length=255)
    url: Optional[str] = None
    sentiment: Optional[str] = Field(default=None, max_length=50)
    county: Optional[str] = Field(default=None, index=True, max_length=50)
    sector: Optional[str] = Field(default=None, index=True, max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class Funding(SQLModel, table=True):
    __tablename__ = "fundings"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    deal_id: int = Field(foreign_key="deals.id")
    funder_id: int = Field(foreign_key="funder.id")
    user_id: int = Field(foreign_key="user.id")
    
    amount: float
    status: str = Field(default="applied")
    application_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    funding_date: Optional[datetime] = None

class Competitor(SQLModel, table=True):
    __tablename__ = "competitor"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sector: str
    county: str
    lat: float = 0
    lng: float = 0
