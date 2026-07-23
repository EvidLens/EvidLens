from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Index, Column
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, Dict, List
from datetime import datetime
import uuid

class LensSubscription(SQLModel, table=True):
    __tablename__ = "lens_subscriptions"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, unique=True)
    plan: str = Field(default="Starter")
    modules: List[str] = Field(default_factory=lambda: ["core", "health"], sa_column=Column(JSONB))
    regions: List[str] = Field(default_factory=list, sa_column=Column(JSONB))
    sectors: List[str] = Field(default_factory=list, sa_column=Column(JSONB))
    role: str = Field(default="viewer")
    expires_at: datetime
    api_key: str = Field(default_factory=lambda: str(uuid.uuid4()), index=True, unique=True)
    extra_data: Dict = Field(default_factory=dict, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow)

class LensAlert(SQLModel, table=True):
    __tablename__ = "lens_alerts"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True)
    name: str
    type: str = Field(default="custom")
    title: str = Field(default="")
    message: str = Field(default="")
    link: str = Field(default="")
    condition: Dict = Field(default_factory=dict, sa_column=Column(JSONB))
    destination: str = Field(default="email")
    is_active: bool = True
    last_triggered: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class LensAudit(SQLModel, table=True):
    __tablename__ = "lens_audit"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True)
    user_id: str
    action: str
    module: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict = Field(default_factory=dict, sa_column=Column(JSONB))

class LensBusiness(SQLModel, table=True):
    __tablename__ = "lens_businesses"
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: str = Field(index=True, unique=True)
    name: Optional[str] = Field(default=None, index=True)
    region: Optional[str] = Field(default=None, index=True)
    county: Optional[str] = Field(default=None, index=True)
    sector: Optional[str] = Field(default=None, index=True)
    size_category: Optional[str] = Field(default=None, index=True)
    employees_total: Optional[int] = None
    extra_data: Dict = Field(default_factory=dict, sa_column=Column(JSONB))
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    surveys: List["app.models.LensSurvey"] = Relationship(back_populates="business")

class LensSurvey(SQLModel, table=True):
    __tablename__ = "lens_surveys"
    __table_args__ = (Index('ix_lens_data_gin', 'data', postgresql_using='gin'),)
    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: int = Field(foreign_key="lens_businesses.id", index=True)
    collected_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    source: str = Field(default="api")
    module: str = Field(default="core", index=True)
    data: Dict = Field(default_factory=dict, sa_column=Column(JSONB))
    business: "app.models.LensBusiness" = Relationship(back_populates="surveys")

class LensMember(SQLModel, table=True):
    __tablename__ = "lens_members"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True)
    user_id: str = Field(index=True)
    email: str = Field(index=True)
    role: str = Field(default="viewer")
    invited_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class LensApiUsage(SQLModel, table=True):
    __tablename__ = "lens_api_usage"
    id: Optional[int] = Field(default=None, primary_key=True)
    api_key: str = Field(index=True)
    endpoint: str
    ts: datetime = Field(default_factory=datetime.utcnow)

class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, unique=True)
    name: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, unique=True)
    tenant_id: str = Field(index=True)
    name: str
    email: str = Field(index=True, unique=True)
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class LensResponse(SQLModel, table=True):
    __tablename__ = "lens_responses"
    __table_args__ = (Index('ix_lens_response_data_gin', 'data', postgresql_using='gin'),)
    id: Optional[int] = Field(default=None, primary_key=True)
    survey_id: int = Field(foreign_key="lens_surveys.id", index=True)
    business_id: int = Field(foreign_key="lens_businesses.id", index=True)
    tenant_id: str = Field(index=True)
    respondent_id: Optional[str] = Field(default=None, index=True)
    collected_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    source: str = Field(default="web")
    data: Dict = Field(default_factory=dict, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow)
