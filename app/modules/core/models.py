from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class GeoFilter(SQLModel, table=True):
    __tablename__ = "geofilter"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    country: str = "Kenya"
    county: Optional[str] = Field(index=True, default=None)
    sub_county: Optional[str] = Field(index=True, default=None)
    ward: Optional[str] = Field(index=True, default=None)
    sector_id: int = Field(foreign_key="sector.id")

class Plan(SQLModel, table=True):
    __tablename__ = "plan"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    monthly_price: int
    annual_price: int
    lanes: int
    modules: int
    users: int
    competitors: int
    leads_per_quarter: int
    support_sla: str
    description: str
    features: str

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

class Sector(SQLModel, table=True):
    __tablename__ = "sector"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    sector_number: int = Field(index=True, unique=True)
    name: str
    parent_category: str

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
    user_id: int = Field(index=True)
    plan_code: str
    lead_credits: int = 0
    api_credits: int = 0
    status: str = "active"
    renews_at: datetime
    default_county: Optional[str] = None
    default_sub_county: Optional[str] = None
    default_ward: Optional[str] = None
