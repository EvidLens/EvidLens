from app.models import LensSurvey
from datetime import datetime
from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field, Column, JSON, Relationship
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLEnum
import enum

class ReportType(str, enum.Enum):
    MARKET_FEASIBILITY = "market_feasibility"
    CONSUMER_ANALYSIS = "consumer_analysis"
    BUSINESS_PLAN = "business_plan"
    KRA_TAX = "kra_tax"
    COMPETITOR_TRACKER = "competitor_tracker"
    INVESTOR_PITCH = "investor_pitch"

class ReportFormat(str, enum.Enum):
    PDF = "pdf"
    EXCEL = "excel"

class ReportStatus(str, enum.Enum):
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"

class Report(SQLModel, table=True):
    __tablename__ = "reports"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)

    # Report Details
    title: str
    report_type: ReportType = Field(sa_column=Column(SQLEnum(ReportType)))
    format: ReportFormat = Field(default=ReportFormat.PDF, sa_column=Column(SQLEnum(ReportFormat)))
    status: ReportStatus = Field(default=ReportStatus.GENERATING, sa_column=Column(SQLEnum(ReportStatus)))
    error_message: Optional[str] = Field(default=None)

    # 5-Level Geo Context
    query: Optional[str] = Field(default=None)
    sector: Optional[str] = Field(default=None)
    country: str = Field(default="Kenya")
    county: Optional[str] = Field(default=None)
    sub_county: Optional[str] = Field(default=None)
    ward: Optional[str] = Field(default=None)
    town: Optional[str] = Field(default=None)

    # Files
    file_path: Optional[str] = Field(default=None)
    file_size_kb: Optional[int] = Field(default=None)
    download_count: int = Field(default=0)

    # Branding + KRA
    is_branded: bool = Field(default=False)
    kra_compliant: bool = Field(default=True)
    report_metadata: Dict = Field(default={}, sa_column=Column(JSON))

    # Monetization
    payment_id: Optional[int] = Field(default=None)
    is_auto_weekly: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})
    expires_at: Optional[datetime] = Field(default=None)

    shares: List["ReportShare"] = Relationship(back_populates="report")

class ReportTemplate(SQLModel, table=True):
    __tablename__ = "report_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    report_type: ReportType = Field(sa_column=Column(SQLEnum(ReportType)))

    # Template config
    sections: List = Field(default=[], sa_column=Column(JSON))
    is_premium: bool = Field(default=False)

    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})

class ReportShare(SQLModel, table=True):
    __tablename__ = "report_shares"

    id: Optional[int] = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="reports.id")
    shared_by_user_id: int

    share_type: str = Field(default="link")
    recipient: Optional[str] = Field(default=None)
    access_token: Optional[str] = Field(default=None, unique=True)

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})

    report: Optional[Report] = Relationship(back_populates="shares")
