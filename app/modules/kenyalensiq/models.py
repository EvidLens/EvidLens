from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: Optional[str] = Field(default=None, index=True, unique=True)
    phone: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)

class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    message: str
    type: str
    channel: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MarketMetric(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product: str
    county: str
    sector: str
    demand_score: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PriceData(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_name: str
    county: str
    sector: str
    price: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class NewsArticle(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product: str
    title: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SocialMention(SQLModel, table=True):
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
    surveys: List["app.modules.kenyalensiq.models.KenyaLensSurvey"] = Relationship(back_populates="business")

class KenyaLensSurvey(SQLModel, table=True):
    __tablename__ = "kenya_lens_survey"
    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: int = Field(index=True, foreign_key="kenya_lens_business.id")
    title: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    business: "app.modules.kenyalensiq.models.KenyaLensBusiness" = Relationship(back_populates="surveys")

class KenyaLensResponse(SQLModel, table=True):
    __tablename__ = "kenya_lens_response"
    id: Optional[int] = Field(default=None, primary_key=True)
    survey_id: int = Field(index=True)
    respondent_phone: Optional[str] = None
    data: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KenyaSubscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    plan: str
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
