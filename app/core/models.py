from sqlmodel import SQLModel, Field, Column, JSON
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, field_validator
from sqlalchemy.sql import func
from sqlalchemy import Enum as SAEnum, Index
from enum import Enum

UTC = timezone.utc

class ReportType(str, Enum):
    MARKET_FEASIBILITY = "MARKET_FEASIBILITY"
    CONSUMER_ANALYSIS = "CONSUMER_ANALYSIS"
    INVESTOR_PITCH = "INVESTOR_PITCH"
    KRA_TAX = "KRA_TAX"
    BUSINESS_PLAN = "BUSINESS_PLAN"
    COMPETITOR_TRACKER = "COMPETITOR_TRACKER"
    FINANCIAL_PROJECTIONS = "FINANCIAL_PROJECTIONS"
    SWOT_ANALYSIS = "SWOT_ANALYSIS"
    RISK_ANALYSIS = "RISK_ANALYSIS"
    PRICING_STRATEGY = "PRICING_STRATEGY"
    UNIT_ECONOMICS = "UNIT_ECONOMICS"
    GO_TO_MARKET = "GO_TO_MARKET"
    OPERATIONAL_PLAN = "OPERATIONAL_PLAN"
    ESG_IMPACT = "ESG_IMPACT"
    EXECUTIVE_SUMMARY = "EXECUTIVE_SUMMARY"

class ReportFormat(str, Enum):
    PDF = "pdf"
    EXCEL = "excel"

class ReportStatus(str, Enum):
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"

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

class Plan(SQLModel, table=True):
    __tablename__ = "plan"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    monthly_kes: int
    annual_kes: int
    areas: int
    products: int
    users: int
    competitors: int
    leads_qtr: int = 0
    lens_tier: str = "Basic"

class Sector(SQLModel, table=True):
    __tablename__ = "sector"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    sector_number: int = Field(index=True, unique=True)
    name: str
    parent_category: str

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

class KenyaLensBusiness(SQLModel, table=True):
    __tablename__ = "kenyalens_business"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sector: str
    county: str
    address: Optional[str] = None
    lat: float = 0
    lng: float = 0

class Workspace(SQLModel, table=True):
    __tablename__ = "workspace"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    owner_id: int = Field(foreign_key="user.id")
    credits: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

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

class Payment(SQLModel, table=True):
    __tablename__ = "payment"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    amount_kes: float
    plan_code: str
    status: str
    mpesa_code: Optional[str] = None
    created_at: Optional[str] = None

class Report(SQLModel, table=True):
    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_user_status", "user_id", "status"),
        Index("ix_reports_type_country", "report_type", "country"),
        {"extend_existing": True}
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str
    report_type: ReportType = Field(sa_column=Column(SAEnum(ReportType, name="reporttype", native_enum=False)))
    format: ReportFormat = Field(default=ReportFormat.PDF, sa_column=Column(SAEnum(ReportFormat, name="reportformat", native_enum=False)))
    file_type: Optional[str] = Field(default="pdf", max_length=20)
    status: ReportStatus = Field(default=ReportStatus.GENERATING, sa_column=Column(SAEnum(ReportStatus, name="reportstatus", native_enum=False)))
    query: Optional[str] = Field(default=None, max_length=500)
    sector: Optional[str] = Field(default=None, max_length=100)
    country: str = Field(default="Kenya", max_length=100)
    county: Optional[str] = Field(default=None, index=True, max_length=100)
    sub_county: Optional[str] = Field(default=None, index=True, max_length=100)
    ward: Optional[str] = Field(default=None, index=True, max_length=100)
    town: Optional[str] = Field(default=None, index=True, max_length=100)
    file_path: Optional[str] = Field(default=None, max_length=500)
    file_size_kb: Optional[int] = Field(default=None, ge=0)
    download_count: int = Field(default=0, ge=0)
    is_branded: bool = Field(default=False)
    kra_compliant: bool = Field(default=True)
    report_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    payment_id: Optional[int] = Field(default=None)
    is_auto_weekly: bool = Field(default=False)
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = Field(default=None, max_length=1000)
    data: dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), sa_column_kwargs={"server_default": func.now()})

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
    user_id: int = Field(index=True, foreign_key="user.id")
    tenant_id: Optional[str] = Field(index=True, default=None)
    module_name: Optional[str] = Field(index=True, default=None)
    plan_code: str
    lead_credits: int = 0
    api_credits: int = 0
    status: str = "active"
    renews_at: datetime
    default_county: Optional[str] = None
    default_sub_county: Optional[str] = None
    default_ward: Optional[str] = None

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
    category: Optional[str] = Field(default=None, index=True)
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
    user_id: int = Field(foreign_key="user.id", index=True)
    plan: str = Field(default="EV-FREE", index=True)
    status: str = Field(default="active")
    renews_at: Optional[datetime] = Field(default=None)
    api_credits: int = Field(default=10)
    features_json: str = Field(default="[]")
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

class DetailedAnalysisRequest(BaseModel):
    product: str
    sector: str
    county: str
    subcounties: List[str] = Field(default=["All"])
    budget_kes: float = 0
    business_model: str = "Retail"
    @field_validator("product", "sector", "county")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()
    model_config = {"extra": "allow"}
