from sqlmodel import SQLModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import Column, JSON

UTC = timezone.utc

# Keep your tables but as SQLModel - so they are counted
class Company(SQLModel, table=True):
    __tablename__ = "companies"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=255)
    sector: Optional[str] = Field(default=None, index=True, max_length=100)
    country: str = Field(default="Kenya", max_length=100)
    county: Optional[str] = Field(default=None, index=True, max_length=100)
    website: Optional[str] = Field(default=None, max_length=500)
    directors: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    valuation: Optional[float] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class FundingDeal(SQLModel, table=True):
    __tablename__ = "funding_deals"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    company_name: str = Field(index=True, max_length=255)
    founder: Optional[str] = Field(default=None, max_length=255)
    investor: Optional[str] = Field(default=None, index=True, max_length=255)
    amount_usd: Optional[float] = Field(default=None)
    round_type: Optional[str] = Field(default=None, max_length=100)
    sector: Optional[str] = Field(default=None, index=True, max_length=100)
    source_url: Optional[str] = Field(default=None, max_length=500)
    date: datetime = Field(default_factory=lambda: datetime.now(UTC))

class TrafficSnapshot(SQLModel, table=True):
    __tablename__ = "traffic_snapshots"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    competitor: str = Field(index=True, max_length=255)
    visits: Optional[int] = Field(default=0)
    bounce_rate: Optional[float] = Field(default=None)
    top_pages: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    date: datetime = Field(default_factory=lambda: datetime.now(UTC))
