from sqlmodel import SQLModel, Field, Column
from typing import Optional, List
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
import json
import secrets

from app.modules.core.models import (
    UserSubscription as _UserSubscription,
    MarketMetric as _MarketMetric
)

class KenyaLensSubscription(_UserSubscription, table=True):
    __tablename__ = "kenya_lens_subscriptions"
    __table_args__ = {'extend_existing': True}
    tenant_id: Optional[str] = Field(default=None, index=True)
    plan: Optional[str] = Field(default=None)
    modules: List[str] = Field(default_factory=list, sa_column=Column(JSONB))
    expires_at: Optional[datetime] = Field(default=None)
    extra_data: dict = Field(default_factory=dict, sa_column=Column(JSONB))

    def __init__(self, **data):
        if 'tenant_id' in data and 'user_id' not in data:
            data['user_id'] = int(data['tenant_id'])
        if 'plan' in data and 'plan_code' not in data:
            plan_map = {"Trial": "EV-FREE", "Pro": "EV-PRO", "Enterprise": "EV-ENT"}
            data['plan_code'] = plan_map.get(data['plan'], data['plan'])
        if 'expires_at' in data and 'renews_at' not in data:
            data['renews_at'] = data['expires_at']
        if 'modules' in data and 'features_json' not in data:
            data['features_json'] = json.dumps(data['modules'])
        if 'extra_data' in data and 'metadata_json' not in data:
            data['metadata_json'] = json.dumps(data['extra_data'])
        if 'api_key' not in data or data['api_key'] is None:
            data['api_key'] = secrets.token_urlsafe(32)
        super().__init__(**data)

class MarketMetric(_MarketMetric, table=True):
    __tablename__ = "market_metrics"
    __table_args__ = {'extend_existing': True}
    tenant_id: Optional[str] = Field(default=None, index=True)

class KenyaLensBusiness(SQLModel, table=True):
    __tablename__ = "kenya_lens_business"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: Optional[str] = Field(index=True, default=None)
    name: str
    sector: str
    county: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KenyaLensSurvey(SQLModel, table=True):
    __tablename__ = "kenya_lens_survey"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(index=True, default=None)
    tenant_id: Optional[str] = Field(index=True, default=None)
    business_id: Optional[int] = Field(index=True, foreign_key="kenya_lens_business.id", default=None)
    title: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KenyaLensAlert(SQLModel, table=True):
    __tablename__ = "kenya_lens_alerts"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(index=True, default=None)
    tenant_id: Optional[str] = Field(index=True, default=None)
    title: str
    description: str
    module: str
    severity: str = Field(default="info")
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KenyaLensMember(SQLModel, table=True):
    __tablename__ = "kenya_lens_members"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(index=True, default=None)
    tenant_id: Optional[str] = Field(index=True, default=None)
    email: str
    role: str = Field(default="member")
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KenyaLensApiUsage(SQLModel, table=True):
    __tablename__ = "kenya_lens_api_usage"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(index=True, default=None)
    api_key: str = Field(index=True)
    endpoint: str
    tenant_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Notification(SQLModel, table=True):
    __tablename__ = "notifications"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    message: str
    type: str
    channel: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PriceData(SQLModel, table=True):
    __tablename__ = "price_data"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: Optional[str] = Field(index=True, default=None)
    product_name: str
    county: str
    sector: str
    price: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class NewsArticle(SQLModel, table=True):
    __tablename__ = "news_articles"
    __table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: Optional[str] = Field(index=True, default=None)
    product: str
    title: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SocialMention(SQLModel, table=True):
    __tablename__ = "social_mentions"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: Optional[str] = Field(index=True, default=None)
    product: str
    platform: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ExportOpportunity(SQLModel, table=True):
    __tablename__ = "export_opportunities"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: Optional[str] = Field(index=True, default=None)
    country: str
    product: str
    opportunity_score: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KenyaTenant(SQLModel, table=True):
    __tablename__ = "kenya_tenants"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KenyaLensResponse(SQLModel, table=True):
    __tablename__ = "kenya_lens_response"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: Optional[str] = Field(index=True, default=None)
    survey_id: int = Field(index=True)
    respondent_phone: Optional[str] = None
    data: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
