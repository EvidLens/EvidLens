from sqlmodel import SQLModel, Field, Relationship, Column
from typing import Optional, List
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB

class Notification(SQLModel, table=True):
    __tablename__ = "notifications"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="auth_users.id")
    message: str
    type: str
    channel: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MarketMetric(SQLModel, table=True):
    __tablename__ = "market_metrics"
    id: Optional[int] = Field(default=None, primary_key=True)
    # tenant_id: str = Field(index=True)
    product: str
    county: str
    sector: str
    demand_score: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PriceData(SQLModel, table=True):
    __tablename__ = "price_data"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True)
    product_name: str
    county: str
    sector: str
    price: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class NewsArticle(SQLModel, table=True):
    __tablename__ = "news_articles"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True)
    product: str
    title: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SocialMention(SQLModel, table=True):
    __tablename__ = "social_mentions"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True)
    product: str
    platform: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class KenyaTenant(SQLModel, table=True):
    __tablename__ = "kenya_tenants"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KenyaLensBusiness(SQLModel, table=True):
    __tablename__ = "kenya_lens_business"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True)
    name: str
    sector: str
    county: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    surveys: List["KenyaLensSurvey"] = Relationship(back_populates="business")

class KenyaLensSurvey(SQLModel, table=True):
    __tablename__ = "kenya_lens_survey"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True)
    business_id: int = Field(index=True, foreign_key="kenya_lens_business.id")
    title: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    business: "KenyaLensBusiness" = Relationship(back_populates="surveys")

class KenyaLensResponse(SQLModel, table=True):
    __tablename__ = "kenya_lens_response"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True)
    survey_id: int = Field(index=True)
    respondent_phone: Optional[str] = None
    data: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KenyaLensSubscription(SQLModel, table=True):
    __tablename__ = "kenya_lens_subscriptions"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(foreign_key="auth_users.id")
    tenant_id: str = Field(index=True)
    plan: str
    status: str = "active"
    modules: List[str] = Field(default_factory=list, sa_column=Column(JSONB))
    expires_at: Optional[datetime] = None
    extra_data: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    api_key: Optional[str] = Field(default=None, index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KenyaLensAlert(SQLModel, table=True):
    __tablename__ = "kenya_lens_alerts"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True)
    title: str
    description: str
    module: str
    severity: str = Field(default="info")
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KenyaLensMember(SQLModel, table=True):
    __tablename__ = "kenya_lens_members"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True)
    user_id: str
    email: str
    role: str = Field(default="member")
    invited_by: str
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KenyaLensApiUsage(SQLModel, table=True):
    __tablename__ = "kenya_lens_api_usage"
    id: Optional[int] = Field(default=None, primary_key=True)
    api_key: str = Field(index=True)
    endpoint: str
    tenant_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
