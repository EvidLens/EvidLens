from sqlmodel import SQLModel, Field
from datetime import datetime

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
    timestamp: datetime = Field(default_factory=datetime.utcnow) # fixed: added )
