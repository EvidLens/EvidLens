from sqlmodel import SQLModel, Field, Column, JSON
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Company(SQLModel, table=True):
    __tablename__ = "companies"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=255)
    sector: Optional[str] = Field(default=None, index=True, max_length=100)
    country: str = Field(default="Kenya", max_length=100)
    county: Optional[str] = Field(default=None, index=True, max_length=100)
    website: Optional[str] = Field(default=None, max_length=500)
    company_type: Optional[str] = Field(default=None, index=True, max_length=100)
    is_funder: bool = Field(default=False, index=True)
    is_insurer: bool = Field(default=False, index=True)
    directors: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    valuation: Optional[float] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)

class FundingDeal(SQLModel, table=True):
    __tablename__ = "funding_deals"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    company_name: str = Field(index=True, max_length=255)
    founder: Optional[str] = Field(default=None, max_length=255)
    investor: Optional[str] = Field(default=None, index=True, max_length=255)
    amount_usd: Optional[float] = Field(default=None)
    amount_kes: Optional[float] = Field(default=None)
    round_type: Optional[str] = Field(default=None, max_length=100)
    sector: Optional[str] = Field(default=None, index=True, max_length=100)
    source_url: Optional[str] = Field(default=None, max_length=500)
    date: Optional[datetime] = Field(default=None)

class TrafficSnapshot(SQLModel, table=True):
    __tablename__ = "traffic_snapshots"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    competitor: str = Field(index=True, max_length=255)
    visits: Optional[int] = Field(default=None)
    bounce_rate: Optional[float] = Field(default=None)
    top_pages: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    date: Optional[datetime] = Field(default=None)
