from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone

UTC = timezone.utc

class KenyaLensBusiness(SQLModel, table=True):
    __tablename__ = "kenya_lens_business"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: Optional[str] = Field(index=True, default=None)
    name: str
    sector: str
    county: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class KenyaLensSurvey(SQLModel, table=True):
    __tablename__ = "kenya_lens_survey"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(index=True, default=None)
    tenant_id: Optional[str] = Field(index=True, default=None)
    business_id: Optional[int] = Field(index=True, foreign_key="kenya_lens_business.id", default=None)
    title: str
    status: str
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

class KenyaLensMember(SQLModel, table=True):
    __tablename__ = "kenya_lens_members"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(index=True, default=None)
    tenant_id: Optional[str] = Field(index=True, default=None)
    email: str
    role: str = Field(default="member")
    status: str = Field(default="pending")
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

class KenyaTenant(SQLModel, table=True):
    __tablename__ = "kenya_tenants"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class KenyaLensResponse(SQLModel, table=True):
    __tablename__ = "kenya_lens_response"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: Optional[str] = Field(index=True, default=None)
    survey_id: int = Field(index=True)
    respondent_phone: Optional[str] = None
    data: str
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
