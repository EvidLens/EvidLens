from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from sqlalchemy import Enum as SAEnum, Index
from sqlalchemy.sql import func


class ReportType(str, Enum):
    MARKET_FEASIBILITY = "market_feasibility"
    CONSUMER_ANALYSIS = "consumer_analysis"
    BUSINESS_PLAN = "business_plan"
    KRA_TAX = "kra_tax"
    COMPETITOR_TRACKER = "competitor_tracker"
    INVESTOR_PITCH = "investor_pitch"
    FINANCIAL_PROJECTIONS = "financial_projections"
    SWOT_ANALYSIS = "swot_analysis"
    RISK_ANALYSIS = "risk_analysis"
    PRICING_STRATEGY = "pricing_strategy"
    UNIT_ECONOMICS = "unit_economics"
    GO_TO_MARKET = "go_to_market"
    OPERATIONAL_PLAN = "operational_plan"
    ESG_IMPACT = "esg_impact"
    EXECUTIVE_SUMMARY = "executive_summary"


class ReportFormat(str, Enum):
    PDF = "pdf"
    EXCEL = "excel"


class ReportStatus(str, Enum):
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Report(SQLModel, table=True):
    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_user_status", "user_id", "status"),
        Index("ix_reports_type_country", "report_type", "country"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)

    title: str = Field(max_length=255)
    report_type: ReportType = Field(
        sa_column=Column(SAEnum(ReportType, name="reporttype", native_enum=False))
    )
    format: ReportFormat = Field(
        default=ReportFormat.PDF,
        sa_column=Column(SAEnum(ReportFormat, name="reportformat", native_enum=False)),
    )
    status: ReportStatus = Field(
        default=ReportStatus.GENERATING,
        sa_column=Column(SAEnum(ReportStatus, name="reportstatus", native_enum=False)),
    )
    error_message: Optional[str] = Field(default=None, max_length=1000)

    # 5-level geo
    query: Optional[str] = Field(default=None, max_length=500)
    sector: Optional[str] = Field(default=None, max_length=100)
    country: str = Field(default="Kenya", max_length=100)
    county: Optional[str] = Field(default=None, max_length=100)
    sub_county: Optional[str] = Field(default=None, max_length=100)
    ward: Optional[str] = Field(default=None, max_length=100)
    town: Optional[str] = Field(default=None, max_length=100)

    # Files
    file_path: Optional[str] = Field(default=None, max_length=500)
    file_size_kb: Optional[int] = Field(default=None, ge=0)
    download_count: int = Field(default=0, ge=0)

    # Branding + KRA
    is_branded: bool = Field(default=False)
    kra_compliant: bool = Field(default=True)
    report_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Monetization
    payment_id: Optional[int] = Field(default=None)
    is_auto_weekly: bool = Field(default=False)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": func.now()},
    )
    expires_at: Optional[datetime] = Field(default=None)

    shares: List["ReportShare"] = Relationship(
        back_populates="report",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class ReportTemplate(SQLModel, table=True):
    __tablename__ = "report_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=150, unique=True)
    report_type: ReportType = Field(
        sa_column=Column(SAEnum(ReportType, name="reporttype", native_enum=False))
    )

    sections: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    is_premium: bool = Field(default=False)
    description: Optional[str] = Field(default=None, max_length=1000)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": func.now()},
    )


class ReportShare(SQLModel, table=True):
    __tablename__ = "report_shares"

    id: Optional[int] = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="reports.id", index=True)
    shared_by_user_id: int = Field(index=True)

    share_type: str = Field(default="link", max_length=50)
    recipient: Optional[str] = Field(default=None, max_length=255)
    access_token: Optional[str] = Field(default=None, max_length=64, unique=True)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": func.now()},
    )

    report: Optional[Report] = Relationship(back_populates="shares")
