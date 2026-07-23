from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column, JSON
from sqlalchemy.sql import func

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str | None = Field(default=None, index=True, unique=True)
    phone: str | None = Field(default=None)
    name: str | None = Field(default=None)

class Notification(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    message: str
    type: str
    channel: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MarketMetric(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    product: str
    county: str
    sector: str
    demand_score: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PriceData(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    product_name: str
    county: str
    sector: str
    price: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class NewsArticle(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    product: str
    title: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SocialMention(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    product: str
    platform: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Tenant(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class LensBusiness(SQLModel, table=True):
    __tablename__ = "lensbusiness"
    id: int | None = Field(default=None, primary_key=True)
    tenant_id: int = Field(index=True)
    name: str
    sector: str
    county: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    surveys: List["app.models.LensSurvey"] = Relationship(back_populates="business")

class LensSurvey(SQLModel, table=True):
    __tablename__ = "lens_survey"
    id: int | None = Field(default=None, primary_key=True)
    business_id: int = Field(index=True, foreign_key="lensbusiness.id")
    title: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    business: "app.models.LensBusiness" = Relationship(back_populates="surveys")
    
class LensResponse(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    survey_id: int = Field(index=True)
    respondent_phone: str | None = None
    data: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Subscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    plan: str
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
