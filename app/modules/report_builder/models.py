from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from sqlalchemy.sql import func
# Use single Report from core - NO duplicate table
from app.core.models import Report, ReportType

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class ReportTemplate(SQLModel, table=True):
    __tablename__ = "report_templates"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=150, unique=True)
    report_type: str = Field(max_length=50)
    sections: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    is_premium: bool = Field(default=False)
    description: Optional[str] = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"server_default": func.now()})

class ReportShare(SQLModel, table=True):
    __tablename__ = "report_shares"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="reports.id", index=True)
    shared_by_user_id: int = Field(index=True)
    share_type: str = Field(default="link", max_length=50)
    recipient: Optional[str] = Field(default=None, max_length=255)
    access_token: Optional[str] = Field(default=None, max_length=64, unique=True)
    created_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"server_default": func.now()})
    report: Optional[Report] = Relationship(sa_relationship_kwargs={"foreign_keys": "[ReportShare.report_id]"})
