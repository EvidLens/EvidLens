from sqlmodel import SQLModel, Field, Relationship, Column, JSON, Index
from typing import Optional, Dict, List
from datetime import datetime
import uuid

class LensSubscription(SQLModel, table=True):
    __tablename__ = "lens_subscriptions"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, unique=True)
    plan: str = Field(default="Starter")
    modules: List[str] = Field(default=["core", "health"], sa_column=Column(JSON))
    regions: List[str] = Field(default=["Nairobi"], sa_column=Column(JSON))
    sectors: List[str] = Field(default=[], sa_column=Column(JSON))
    role: str = Field(default="viewer")
    expires_at: datetime
    api_key: str = Field(default_factory=lambda: str(uuid.uuid4()), index=True, unique=True)
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
    condition: Dict = Field(default={}, sa_column=Column(JSON))
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
    payload: Dict = Field(default={}, sa_column=Column(JSON))

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
    metadata: Dict = Field(default={}, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    surveys: List["LensSurvey"] = Relationship(back_populates="business")

class LensSurvey(SQLModel, table=True):
    __tablename__ = "lens_surveys"
    __table_args__ = (Index('ix_lens_data_gin', 'data', postgresql_using='gin'),)
    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: int = Field(foreign_key="lens_businesses.id", index=True)
    collected_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    source: str = Field(default="api")
    module: str = Field(default="core", index=True)
    data: Dict = Field(default={}, sa_column=Column(JSON))
    business: LensBusiness = Relationship(back_populates="surveys")
