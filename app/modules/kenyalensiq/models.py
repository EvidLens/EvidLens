from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column
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
    product: str
    county: str
    sector: str
    demand_score: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PriceData(SQLModel, table=True):
    __tablename__ = "price_data"
    id: Optional[int] = Field(default=None, primary_key=True)
    product_name: str
    county: str
    sector: str
    price: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class NewsArticle(SQLModel, table=True):
    __tablename__ = "news_articles"
    id: Optional[int] = Field(default=None, primary_key=True)
    product: str
    title: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SocialMention(SQLModel, table=True):
    __tablename__ = "social_mentions"
    id: Optional[int] = Field(default=None, primary_key=True)
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
    tenant_id: int = Field(index=True)
    name: str
    sector: str
    county: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    surveys: List["KenyaLensSurvey"] = Relationship(back_populates="business")

class KenyaLensSurvey(SQLModel, table=True):
    __tablename__ = "kenya_lens_survey"
    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: int = Field(index=True, foreign_key="kenya_lens_business.id")
    title: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    business: "KenyaLensBusiness" = Relationship(back_populates="surveys")

class KenyaLensResponse(SQLModel, table=True):
    __tablename__ = "kenya_lens_response"
    id: Optional[int] = Field(default=None, primary_key=True)
    survey_id: int = Field(index=True)
    respondent_phone: Optional[str] = None
    data: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KenyaLensSubscription(SQLModel, table=True):
    __tablename__ = "kenya_lens_subscriptions"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="auth_users.id")
    plan: str
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
